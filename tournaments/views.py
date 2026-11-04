# What this file does:
# Tournament views: browse championship calendars, inspect tournament points tables and match fixtures, create new championships, and export official PDF tournament summary reports.

from django.shortcuts import render, redirect, Http404
from django.contrib import messages
from django.http import HttpResponse
from bson import ObjectId
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from tournaments.models import Tournament, Fixture, TournamentUniversity
from universities.models import University
from sports.models import Sport
from analytics.services import compute_tournament_points_table
from accounts.auth_service import coach_or_admin_required

# Browse tournaments calendar filtered by status (All, Ongoing, Completed, Upcoming)
def tournament_list(request):
    """Lists tournaments. Public users only see sanctioned ('Approved') tournaments. Coaches see approved tournaments plus their own proposals."""
    status_filter = request.GET.get('status', 'All')
    session_user = request.session.get('user', {})
    is_admin = (session_user.get('role') == 'admin')
    is_coach = (session_user.get('role') == 'university_admin')
    user_uni_id = str(session_user.get('university_id') or '')
    username = session_user.get('username')

    try:
        from mongoengine import Q
        if is_admin:
            # Admins see all tournaments
            query = Q()
            if status_filter != 'All':
                query = query & Q(status=status_filter)
            tournaments = list(Tournament.objects(query).order_by('-year'))
        elif is_coach:
            # Coaches see Approved tournaments + their own proposals (Pending or Rejected)
            visibility_q = Q(approval_status__nin=['Pending', 'Rejected'])
            if user_uni_id and ObjectId.is_valid(user_uni_id):
                visibility_q = visibility_q | Q(host_university_id=ObjectId(user_uni_id))
            if username:
                visibility_q = visibility_q | Q(created_by=username)
            if status_filter != 'All':
                visibility_q = visibility_q & Q(status=status_filter)
            tournaments = list(Tournament.objects(visibility_q).order_by('-year'))
        else:
            # Public view: STRICTLY sanctioned tournaments only (resilient against missing/empty approval_status fields)
            query = Q(approval_status__nin=['Pending', 'Rejected'])
            if status_filter != 'All':
                query = query & Q(status=status_filter)
            tournaments = list(Tournament.objects(query).order_by('-year'))
    except Exception:
        tournaments = []

    return render(request, 'tournaments/list.html', {
        'title': 'Championship Tournaments // UniSports',
        'tournaments': tournaments,
        'current_status': status_filter
    })

def tournament_detail(request, tournament_id):
    """Tournament dashboard: Points table, medal tally, and fixtures."""
    try:
        t_id = ObjectId(tournament_id)
        tournament = Tournament.objects.get(id=t_id)
    except Exception:
        raise Http404("Tournament not found")

    session_user = request.session.get('user', {})
    is_admin = (session_user.get('role') == 'admin')
    user_uni_id = str(session_user.get('university_id') or '')
    is_host_coach = (
        session_user.get('role') == 'university_admin' and (
            bool(user_uni_id and tournament.host_university_id and str(tournament.host_university_id) == user_uni_id) or
            bool(tournament.created_by and tournament.created_by == session_user.get('username'))
        )
    )

    # Privacy Guard: If tournament is pending or rejected, only Board Admin or Host Coach may access
    if getattr(tournament, 'approval_status', 'Approved') in ['Pending', 'Rejected'] and not (is_admin or is_host_coach):
        raise Http404("Tournament proposal is currently pending official board sanctioning and is not publicly accessible.")

    # Algorithm 3: Points table
    points_table = compute_tournament_points_table(tournament.id)

    # Fixtures (public view displays verified and sanctioned fixtures)
    try:
        fixtures = list(Fixture.objects(
            tournament_id=tournament.id,
            approval_status__nin=['Pending', 'Rejected']
        ).order_by('match_date'))
    except Exception:
        fixtures = []

    can_edit = is_admin or is_host_coach

    return render(request, 'tournaments/detail.html', {
        'title': f'{tournament.name} ({tournament.year}) // Tournament Dashboard',
        'tournament': tournament,
        'points_table': points_table,
        'fixtures': fixtures,
        'can_edit': can_edit,
    })

def export_tournament_pdf(request, tournament_id):
    """Generates official tournament summary PDF via ReportLab with Latin-1 safety."""
    try:
        t_id = ObjectId(tournament_id)
        tournament = Tournament.objects.get(id=t_id)
    except Exception:
        raise Http404("Tournament not found")

    session_user = request.session.get('user', {})
    is_admin = (session_user.get('role') == 'admin')
    user_uni_id = str(session_user.get('university_id') or '')
    is_host_coach = (
        session_user.get('role') == 'university_admin' and (
            bool(user_uni_id and tournament.host_university_id and str(tournament.host_university_id) == user_uni_id) or
            bool(tournament.created_by and tournament.created_by == session_user.get('username'))
        )
    )
    if getattr(tournament, 'approval_status', 'Approved') in ['Pending', 'Rejected'] and not (is_admin or is_host_coach):
        raise Http404("Official tournament report is unavailable for unsanctioned tournaments.")

    points_table = compute_tournament_points_table(tournament.id)

    def safe_text(val):
        """Prevents ReportLab Helvetica UnicodeEncodeErrors."""
        if val is None:
            return ''
        return str(val).encode('latin-1', 'replace').decode('latin-1')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # PDF Content
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "UniSports — Official Tournament Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 75, safe_text(f"Tournament: {tournament.name} ({tournament.year})"))
    p.drawString(50, height - 95, safe_text(f"Sport: {tournament.sport_name}  |  Status: {tournament.status}"))
    p.drawString(50, height - 115, safe_text(f"Venue: {tournament.venue}"))
    p.line(50, height - 125, width - 50, height - 125)

    y = height - 155
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Points Table Standings")
    y -= 25

    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Rank")
    p.drawString(90, y, "University")
    p.drawString(270, y, "P")
    p.drawString(310, y, "W")
    p.drawString(350, y, "D")
    p.drawString(390, y, "L")
    p.drawString(430, y, "Points")
    y -= 15
    p.line(50, y + 10, width - 50, y + 10)

    p.setFont("Helvetica", 10)
    if not points_table:
        p.drawString(50, y, "No match results recorded yet. Points table is currently empty.")
    else:
        for row in points_table:
            p.drawString(50, y, safe_text(row.get('rank', '-')))
            p.drawString(90, y, safe_text(row.get('name', ''))[:35])
            p.drawString(270, y, safe_text(row.get('played', 0)))
            p.drawString(310, y, safe_text(row.get('won', 0)))
            p.drawString(350, y, safe_text(row.get('drawn', 0)))
            p.drawString(390, y, safe_text(row.get('lost', 0)))
            p.drawString(430, y, safe_text(row.get('points', 0)))
            y -= 20
            if y < 80:
                p.showPage()
                y = height - 50

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="unisports_{tournament.sport_code}_{tournament.year}.pdf"'
    return response


@coach_or_admin_required
def tournament_create(request):
    """
    Allows Board Admins and University Coaches to host/create a new tournament.
    Coaches' tournaments require one-time Admin sanctioning.
    """
    session_user = request.session.get('user', {})
    is_coach = (session_user.get('role') == 'university_admin')
    back_url = 'accounts:university_portal' if is_coach else 'accounts:admin_dashboard'

    sports = list(Sport.objects.all().order_by('name'))
    universities = list(University.objects.all().order_by('name'))
    user_uni_id = session_user.get('university_id')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sport_code = request.POST.get('sport_code', '').strip().upper()
        year = request.POST.get('year', '').strip()
        host_uni_id = request.POST.get('host_university_id', '').strip()
        venue = request.POST.get('venue', '').strip()
        status = request.POST.get('status', 'Upcoming').strip()
        selected_uni_ids = request.POST.getlist('participating_universities')

        sport = Sport.objects(code=sport_code).first()
        if not sport and sports:
            sport = sports[0]

        host_uni = None
        if host_uni_id:
            try:
                host_uni = University.objects.get(id=ObjectId(host_uni_id))
            except Exception:
                pass
        if not host_uni and user_uni_id:
            try:
                host_uni = University.objects.get(id=ObjectId(user_uni_id))
            except Exception:
                pass
        if not host_uni and universities:
            host_uni = universities[0]

        participating = []
        seen_uids = set()
        for uid in selected_uni_ids:
            try:
                u = University.objects.get(id=ObjectId(uid))
                if str(u.id) not in seen_uids:
                    seen_uids.add(str(u.id))
                    participating.append(TournamentUniversity(
                        university_id=u.id,
                        name=u.name,
                        short_code=u.short_code
                    ))
            except Exception:
                pass

        if host_uni and str(host_uni.id) not in seen_uids:
            seen_uids.add(str(host_uni.id))
            participating.append(TournamentUniversity(
                university_id=host_uni.id,
                name=host_uni.name,
                short_code=host_uni.short_code
            ))

        if name and sport and host_uni:
            try:
                approval_status = 'Pending' if is_coach else 'Approved'
                created_by = session_user.get('username', 'admin')
                created_by_role = session_user.get('role', 'admin')

                tourn = Tournament(
                    name=name,
                    sport_name=sport.name,
                    sport_code=sport.code,
                    year=int(year) if year and year.isdigit() else 2026,
                    host_university_name=host_uni.name,
                    host_university_id=host_uni.id,
                    venue=venue or f"{host_uni.name} Sports Complex",
                    status=status if status in ['Upcoming', 'Ongoing', 'Completed'] else 'Upcoming',
                    approval_status=approval_status,
                    created_by=created_by,
                    created_by_role=created_by_role,
                    participating_universities=participating
                )
                tourn.save()
                if is_coach:
                    messages.success(request, f"Tournament '{name}' proposal submitted for Board Admin approval! Once sanctioned, you can freely manage venues, dates, and fixtures.")
                else:
                    messages.success(request, f"Tournament '{name}' created and sanctioned successfully!")
                return redirect('tournaments:detail', tournament_id=str(tourn.id))
            except Exception as e:
                messages.error(request, f"Error creating tournament: {e}")
        else:
            messages.error(request, "Please fill in all required fields (Name, Sport, Host University).")

    return render(request, 'tournaments/create.html', {
        'title': 'Host Championship Tournament // UniSports',
        'sports': sports,
        'universities': universities,
        'user_uni_id': user_uni_id,
        'back_url': back_url
    })


@coach_or_admin_required
def tournament_edit(request, tournament_id):
    """
    Allows the host coach or admin to update tournament details (venue, year, status, roster)
    without requiring repeated admin approval once sanctioned.
    """
    try:
        t_id = ObjectId(tournament_id)
        tournament = Tournament.objects.get(id=t_id)
    except Exception:
        raise Http404("Tournament not found")

    session_user = request.session.get('user', {})
    is_admin = (session_user.get('role') == 'admin')
    user_uni_id = str(session_user.get('university_id') or '')
    is_host_coach = (
        session_user.get('role') == 'university_admin' and (
            bool(user_uni_id and tournament.host_university_id and str(tournament.host_university_id) == user_uni_id) or
            bool(tournament.created_by and tournament.created_by == session_user.get('username'))
        )
    )

    if not (is_admin or is_host_coach):
        messages.error(request, "Permission denied. Only the host coach or a board admin can edit this tournament.")
        return redirect('tournaments:detail', tournament_id=str(tournament.id))

    universities = list(University.objects.all().order_by('name'))
    existing_uni_ids = {str(u.university_id) for u in tournament.participating_universities}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        year = request.POST.get('year', '').strip()
        venue = request.POST.get('venue', '').strip()
        status = request.POST.get('status', tournament.status).strip()
        selected_uni_ids = request.POST.getlist('participating_universities')

        if not name:
            messages.error(request, "Tournament name cannot be empty.")
        else:
            try:
                tournament.name = name
                if year and year.isdigit():
                    tournament.year = int(year)
                if venue:
                    tournament.venue = venue
                if status in ['Upcoming', 'Ongoing', 'Completed']:
                    tournament.status = status

                # Update participating universities roster
                new_roster = []
                seen_uids = set()
                for uid in selected_uni_ids:
                    try:
                        u = University.objects.get(id=ObjectId(uid))
                        if str(u.id) not in seen_uids:
                            seen_uids.add(str(u.id))
                            new_roster.append(TournamentUniversity(
                                university_id=u.id,
                                name=u.name,
                                short_code=u.short_code
                            ))
                    except Exception:
                        pass
                
                # Ensure host is retained in participating
                if tournament.host_university_id and str(tournament.host_university_id) not in seen_uids:
                    try:
                        host_u = University.objects.get(id=tournament.host_university_id)
                        new_roster.insert(0, TournamentUniversity(
                            university_id=host_u.id,
                            name=host_u.name,
                            short_code=host_u.short_code
                        ))
                    except Exception:
                        pass

                if new_roster:
                    tournament.participating_universities = new_roster

                # Explicitly preserve tournament.approval_status!
                # Once sanctioned, coach does not need repeated admin approval.
                tournament.save()
                messages.success(request, f"Tournament '{tournament.name}' details updated successfully!")
                return redirect('tournaments:detail', tournament_id=str(tournament.id))
            except Exception as e:
                messages.error(request, f"Error updating tournament: {e}")

    return render(request, 'tournaments/edit.html', {
        'title': f'Edit {tournament.name} // UniSports',
        'tournament': tournament,
        'universities': universities,
        'existing_uni_ids': existing_uni_ids,
        'is_admin': is_admin,
    })
