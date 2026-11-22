# What this file does:
# Manages user session views (login/logout), coach self-registration, super-admin approval queues, admin dashboard CRUD operations, tournament finalization, and match score submissions.

from django.shortcuts import render, redirect, Http404
from django.contrib import messages
from bson import ObjectId
from datetime import datetime, timezone
from accounts.auth_service import authenticate_user, admin_required, login_required_custom, coach_or_admin_required, hash_password
from universities.models import University
from sports.models import Sport
from tournaments.models import Tournament, Fixture, MatchTeam
from accounts.models import User, now_utc

# Portal login view with redirection to admin dashboard or coach portal
def login_view(request):
    """Handles admin / coach login."""
    session_user = request.session.get('user')
    if session_user:
        if session_user.get('role') == 'admin':
            return redirect('accounts:admin_dashboard')
        else:
            return redirect('accounts:university_portal')

    requested_role = request.GET.get('role', request.POST.get('role', '')).strip().lower()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user_data, status_code, err_msg = authenticate_user(username, password, return_status=True)
        if user_data:
            request.session.cycle_key()
            request.session['user'] = user_data
            messages.success(request, f"Welcome back, {user_data.get('full_name') or user_data['username']}!")
            if user_data.get('role') == 'admin':
                return redirect('accounts:admin_dashboard')
            else:
                return redirect('accounts:university_portal')
        else:
            if status_code == 'PENDING_APPROVAL':
                messages.warning(request, err_msg)
            elif status_code == 'REJECTED':
                messages.error(request, err_msg)
            elif status_code == 'ROLE_DENIED':
                messages.error(request, err_msg)
            else:
                messages.error(request, err_msg or "Invalid username or password.")

    page_title = 'Login'
    return render(request, 'accounts/login.html', {
        'title': page_title,
        'role': requested_role,
    })

def logout_view(request):
    """Flushes session and logs out user."""
    request.session.flush()
    messages.info(request, "Logged out successfully.")
    return redirect('core:index')

def register_coach(request):
    """Handles registration for new University Coaches / Sports Officials."""
    session_user = request.session.get('user')
    if session_user:
        if session_user.get('role') == 'admin':
            return redirect('accounts:admin_dashboard')
        return redirect('accounts:university_portal')

    universities = list(University.objects.all().order_by('name')) if hasattr(University.objects, 'all') else []

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip().lower()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        designation = request.POST.get('designation', '').strip() or 'Sports Officer / Coach'
        university_id = request.POST.get('university_id', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()

        # Validations
        if not all([full_name, username, email, university_id, password]):
            messages.error(request, "Please fill in all required fields marked with *.")
            return render(request, 'accounts/register_coach.html', {
                'title': 'Register',
                'universities': universities,
                'form_data': request.POST
            })

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, 'accounts/register_coach.html', {
                'title': 'Register',
                'universities': universities,
                'form_data': request.POST
            })

        if password != password_confirm:
            messages.error(request, "Passwords do not match. Please re-enter.")
            return render(request, 'accounts/register_coach.html', {
                'title': 'Register',
                'universities': universities,
                'form_data': request.POST
            })

        # Check existing username or email
        if User.objects(username=username).first():
            messages.error(request, f"Username '{username}' is already in use. Please choose another.")
            return render(request, 'accounts/register_coach.html', {
                'title': 'Register',
                'universities': universities,
                'form_data': request.POST
            })

        if User.objects(email=email).first():
            messages.error(request, f"An account with email '{email}' already exists.")
            return render(request, 'accounts/register_coach.html', {
                'title': 'Register',
                'universities': universities,
                'form_data': request.POST
            })

        # Find university
        uni = None
        try:
            uni = University.objects.get(id=ObjectId(university_id))
        except Exception:
            messages.error(request, "Selected university was not found. Please choose a valid university.")
            return render(request, 'accounts/register_coach.html', {
                'title': 'Register',
                'universities': universities,
                'form_data': request.POST
            })

        # Create coach user with pending approval status
        new_coach = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role='university_admin',
            full_name=full_name,
            phone=phone,
            designation=designation,
            university_id=uni.id,
            university_name=uni.name,
            approval_status='pending',
            is_active=True
        )
        new_coach.save()

        messages.success(
            request,
            f"Registration submitted for {uni.name}! Your account is pending Super Admin verification. You will be able to log in once approved."
        )
        return redirect('accounts:login')

    return render(request, 'accounts/register_coach.html', {
        'title': 'Register',
        'universities': universities
    })

@admin_required
def admin_dashboard(request):
    """Custom admin control panel with pending approvals alert."""
    universities = list(University.objects.all()) if hasattr(University.objects, 'all') else []
    sports = list(Sport.objects.all()) if hasattr(Sport.objects, 'all') else []
    tournaments = list(Tournament.objects.all().order_by('-year')) if hasattr(Tournament.objects, 'all') else []
    fixtures_count = Fixture.objects.count() if hasattr(Fixture.objects, 'count') else 0
    pending_count = Fixture.objects(approval_status='Pending').count() if hasattr(Fixture.objects, 'filter') else 0
    pending_coaches_count = User.objects(role='university_admin', approval_status='pending').count() if hasattr(User.objects, 'filter') else 0
    pending_tournaments_count = Tournament.objects(approval_status='Pending').count() if hasattr(Tournament.objects, 'filter') else 0
    users_count = User.objects.count() if hasattr(User.objects, 'count') else 0

    context = {
        'title': 'Admin',
        'universities': universities,
        'sports': sports,
        'tournaments': tournaments,
        'stats': {
            'universities_count': len(universities),
            'sports_count': len(sports),
            'tournaments_count': len(tournaments),
            'fixtures_count': fixtures_count,
            'pending_count': pending_count,
            'pending_coaches_count': pending_coaches_count,
            'pending_tournaments_count': pending_tournaments_count,
            'users_count': users_count,
        }
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@admin_required
def admin_approvals(request):
    """Lists match scores submitted by university coaches awaiting board approval."""
    pending_fixtures = list(Fixture.objects(approval_status='Pending').order_by('-created_at'))
    return render(request, 'accounts/admin_approvals.html', {
        'title': 'Approvals',
        'pending_fixtures': pending_fixtures
    })

@admin_required
def admin_approve_fixture(request, fixture_id):
    """Approves a fixture score submission, publishing it to public standings."""
    try:
        fix = Fixture.objects.get(id=ObjectId(fixture_id))
        fix.approval_status = 'Approved'
        fix.save()

        # If associated tournament was 'Upcoming', promote to 'Ongoing' since matches have begun
        try:
            tourn = Tournament.objects.get(id=fix.tournament_id)
            if tourn and tourn.status == 'Upcoming':
                tourn.status = 'Ongoing'
                tourn.save()
        except Exception:
            pass

        messages.success(request, f"Approved match result: {fix.team_a.short_code} vs {fix.team_b.short_code}. It is now live on the public website!")
    except Exception as e:
        messages.error(request, f"Error approving match: {e}")
    return redirect('accounts:admin_approvals')

@admin_required
def admin_reject_fixture(request, fixture_id):
    """Rejects a fixture score submission."""
    try:
        fix = Fixture.objects.get(id=ObjectId(fixture_id))
        fix.approval_status = 'Rejected'
        fix.save()
        messages.info(request, f"Rejected match result: {fix.team_a.short_code} vs {fix.team_b.short_code}.")
    except Exception as e:
        messages.error(request, f"Error rejecting match: {e}")
    return redirect('accounts:admin_approvals')

@admin_required
def admin_coach_approvals(request):
    """Lists coach registration requests for admin review and approval."""
    status_filter = request.GET.get('status', 'pending')
    query = {'role': 'university_admin'}
    if status_filter in ('pending', 'approved', 'rejected'):
        query['approval_status'] = status_filter

    coaches = list(User.objects(**query).order_by('-created_at'))
    pending_count = User.objects(role='university_admin', approval_status='pending').count()
    approved_count = User.objects(role='university_admin', approval_status='approved').count()
    rejected_count = User.objects(role='university_admin', approval_status='rejected').count()

    return render(request, 'accounts/admin_coach_approvals.html', {
        'title': 'Members',
        'coaches': coaches,
        'current_status': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    })

@admin_required
def admin_approve_coach(request, user_id):
    """Approves a member account, granting immediate access to university portal."""
    try:
        coach = User.objects.get(id=ObjectId(user_id))
        coach.approval_status = 'approved'
        coach.approved_at = now_utc()
        coach.is_active = True
        coach.admin_notes = None
        coach.save()
        messages.success(request, f"Approved member account '{coach.full_name or coach.username}' for {coach.university_name}!")
    except Exception as e:
        messages.error(request, f"Error approving member: {e}")
    return redirect('accounts:admin_coach_approvals')

@admin_required
def admin_reject_coach(request, user_id):
    """Declines a member registration request."""
    try:
        coach = User.objects.get(id=ObjectId(user_id))
        reason = request.POST.get('reason', '').strip() or 'Registration declined by Super Admin.'
        coach.approval_status = 'rejected'
        coach.admin_notes = reason
        coach.save()
        messages.info(request, f"Registration for '{coach.username}' ({coach.university_name}) was declined.")
    except Exception as e:
        messages.error(request, f"Error rejecting member: {e}")
    return redirect('accounts:admin_coach_approvals')

@admin_required
def admin_tournament_approvals(request):
    """Lists tournaments proposed by coaches requiring one-time central board sanctioning."""
    status_filter = request.GET.get('status', 'Pending')
    query = {}
    if status_filter in ('Pending', 'Approved', 'Rejected'):
        query['approval_status'] = status_filter

    tournaments = list(Tournament.objects(**query).order_by('-created_at'))
    pending_count = Tournament.objects(approval_status='Pending').count()
    approved_count = Tournament.objects(approval_status='Approved').count()
    rejected_count = Tournament.objects(approval_status='Rejected').count()

    return render(request, 'accounts/admin_tournament_approvals.html', {
        'title': 'Sanctions',
        'tournaments': tournaments,
        'current_status': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    })

@admin_required
def admin_approve_tournament(request, tournament_id):
    """Sanctions a tournament proposed by a coach. Host coach is granted autonomous management."""
    try:
        tourn = Tournament.objects.get(id=ObjectId(tournament_id))
        session_user = request.session.get('user', {})
        tourn.approval_status = 'Approved'
        tourn.approved_by = session_user.get('username', 'admin')
        tourn.approved_at = now_utc()
        tourn.save()

        # Auto-approve any pending fixtures belonging to this newly sanctioned tournament
        try:
            Fixture.objects(tournament_id=tourn.id, approval_status='Pending').update(set__approval_status='Approved')
        except Exception:
            pass

        messages.success(request, f"Tournament '{tourn.name}' has been sanctioned and approved! Host coach can now freely update venues, schedules, and scores.")
    except Exception as e:
        messages.error(request, f"Error sanctioning tournament: {e}")

    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('accounts:admin_tournament_approvals')

@admin_required
def admin_reject_tournament(request, tournament_id):
    """Declines a tournament hosting proposal."""
    try:
        tourn = Tournament.objects.get(id=ObjectId(tournament_id))
        tourn.approval_status = 'Rejected'
        tourn.save()
        messages.info(request, f"Tournament proposal '{tourn.name}' was declined.")
    except Exception as e:
        messages.error(request, f"Error rejecting tournament: {e}")

    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('accounts:admin_tournament_approvals')

@admin_required
def admin_finalize_tournament(request, tournament_id):
    """
    Finalizes a tournament, transitioning status to 'Completed' and awarding podium medals.
    This immediately feeds Algorithm 1 for the Overall University Rankings.
    """
    try:
        tourn = Tournament.objects.get(id=ObjectId(tournament_id))
    except Exception:
        raise Http404("Tournament not found")

    from analytics.services import compute_tournament_points_table
    from tournaments.models import MedalEntry
    points_table = compute_tournament_points_table(tourn.id)

    if request.method == 'POST':
        gold_id = request.POST.get('gold_uni_id', '').strip()
        silver_id = request.POST.get('silver_uni_id', '').strip()
        bronze_id = request.POST.get('bronze_uni_id', '').strip()

        if not gold_id:
            messages.error(request, "Gold medal winner is required to finalize the tournament.")
        else:
            try:
                medal_tally = []
                if gold_id:
                    uni = University.objects.get(id=ObjectId(gold_id))
                    medal_tally.append(MedalEntry(
                        university_id=uni.id,
                        university_name=uni.name,
                        university_code=uni.short_code,
                        gold=1, silver=0, bronze=0, total_score=5
                    ))
                if silver_id and silver_id != gold_id:
                    uni = University.objects.get(id=ObjectId(silver_id))
                    medal_tally.append(MedalEntry(
                        university_id=uni.id,
                        university_name=uni.name,
                        university_code=uni.short_code,
                        gold=0, silver=1, bronze=0, total_score=3
                    ))
                if bronze_id and bronze_id not in (gold_id, silver_id):
                    uni = University.objects.get(id=ObjectId(bronze_id))
                    medal_tally.append(MedalEntry(
                        university_id=uni.id,
                        university_name=uni.name,
                        university_code=uni.short_code,
                        gold=0, silver=0, bronze=1, total_score=1
                    ))

                tourn.medal_tally = medal_tally
                tourn.status = 'Completed'
                tourn.compute_medal_scores()
                tourn.save()
                messages.success(request, f"Tournament '{tourn.name}' finalized! Medals awarded & Overall Rankings updated.")
                return redirect('tournaments:detail', tournament_id=str(tourn.id))
            except Exception as e:
                messages.error(request, f"Error finalizing tournament: {e}")

    return render(request, 'accounts/admin_finalize_tournament.html', {
        'title': 'Finalize',
        'tournament': tourn,
        'points_table': points_table,
        'universities': list(University.objects.all().order_by('name'))
    })

@coach_or_admin_required
def admin_create_university(request):
    """Form view to add a new university (accessible to Admins & Coaches)."""
    session_user = request.session.get('user', {})
    redirect_target = 'accounts:university_portal' if session_user.get('role') == 'university_admin' else 'accounts:admin_dashboard'

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        short_code = request.POST.get('short_code', '').strip().upper()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        year = request.POST.get('established_year', '').strip()
        website = request.POST.get('website', '').strip()
        sports = [s.strip() for s in request.POST.get('sports', '').split(',') if s.strip()]

        if name and short_code:
            try:
                uni = University(
                    name=name,
                    short_code=short_code,
                    city=city,
                    state=state,
                    established_year=int(year) if year and year.isdigit() else None,
                    website=website if website else None,
                    sports_enrolled=sports
                )
                uni.save()
                messages.success(request, f"University '{name}' ({short_code}) registered successfully.")
            except Exception as e:
                messages.error(request, f"Error creating university: {e}")
        else:
            messages.error(request, "University name and short code are required.")
        return redirect(redirect_target)

    return render(request, 'accounts/admin_form.html', {
        'title': 'University',
        'form_type': 'university',
        'back_url': redirect_target
    })

@coach_or_admin_required
def admin_create_sport(request):
    """Form view to add a new sport (accessible to Admins & Coaches)."""
    session_user = request.session.get('user', {})
    redirect_target = 'accounts:university_portal' if session_user.get('role') == 'university_admin' else 'accounts:admin_dashboard'

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        category = request.POST.get('category', 'Team')
        win_points = request.POST.get('win_points', '2').strip()
        draw_points = request.POST.get('draw_points', '1').strip()
        loss_points = request.POST.get('loss_points', '0').strip()

        if name and code:
            try:
                sport = Sport(
                    name=name,
                    code=code,
                    category=category,
                    win_points=int(win_points) if win_points.isdigit() else 2,
                    draw_points=int(draw_points) if draw_points.isdigit() else 1,
                    loss_points=int(loss_points) if loss_points.isdigit() else 0
                )
                sport.save()
                messages.success(request, f"Sport discipline '{name}' ({code}) registered with custom rules (W: {sport.win_points}, D: {sport.draw_points}).")
            except Exception as e:
                messages.error(request, f"Error creating sport: {e}")
        else:
            messages.error(request, "Sport name and discipline code are required.")
        return redirect(redirect_target)

    return render(request, 'accounts/admin_form.html', {
        'title': 'Sport',
        'form_type': 'sport',
        'back_url': redirect_target
    })

# ==============================================================================
# UNIVERSITY COACH / USER PORTAL
# ==============================================================================

@coach_or_admin_required
def university_portal(request):
    """
    University Coach / Sports Officer Portal
    Shows my university profile, submitted scores, and submission statuses.
    """
    session_user = request.session.get('user', {})
    username = session_user.get('username')
    user_uni_name = session_user.get('university_name', '')

    # Fetch submissions by this user/university
    try:
        if session_user.get('role') == 'admin':
            my_fixtures = list(Fixture.objects.all().order_by('-created_at')[:15])
        else:
            my_fixtures = list(Fixture.objects(submitted_by=username).order_by('-created_at'))
    except Exception:
        my_fixtures = []

    # Fetch tournaments in which this university is competing (Approved) or coach's own proposals
    my_tournaments = []
    try:
        from mongoengine import Q
        uid_str = session_user.get('university_id')
        if uid_str and ObjectId.is_valid(uid_str):
            uid = ObjectId(uid_str)
            coach_q = (Q(approval_status='Approved') & Q(participating_universities__university_id=uid)) | Q(host_university_id=uid) | Q(created_by=username)
            my_tournaments = list(Tournament.objects(coach_q).order_by('-year')[:8])
        elif user_uni_name:
            coach_q = (Q(approval_status='Approved') & Q(participating_universities__name=user_uni_name)) | Q(created_by=username)
            my_tournaments = list(Tournament.objects(coach_q).order_by('-year')[:8])
        if not my_tournaments and session_user.get('role') == 'admin':
            my_tournaments = list(Tournament.objects.all().order_by('-year')[:8])
    except Exception:
        my_tournaments = []

    return render(request, 'accounts/university_portal.html', {
        'title': 'Portal',
        'user': session_user,
        'my_fixtures': my_fixtures,
        'my_tournaments': my_tournaments,
        'user_uni_name': user_uni_name
    })

@coach_or_admin_required
def submit_score(request):
    """
    Allows a university coach to submit a match score.
    Automatically marked approval_status = 'Pending' until admin approves.
    """
    session_user = request.session.get('user', {})
    username = session_user.get('username')
    user_uni_name = session_user.get('university_name', '')

    try:
        if session_user.get('role') == 'admin':
            tournaments = list(Tournament.objects.all().order_by('-year'))
        else:
            from mongoengine import Q
            uid_str = session_user.get('university_id')
            score_q = Q(approval_status='Approved')
            if uid_str and ObjectId.is_valid(uid_str):
                score_q = score_q | Q(host_university_id=ObjectId(uid_str))
            if username:
                score_q = score_q | Q(created_by=username)
            tournaments = list(Tournament.objects(score_q).order_by('-year'))
    except Exception:
        tournaments = []
    universities = list(University.objects.all().order_by('name'))

    if request.method == 'POST':
        tournament_id = request.POST.get('tournament_id')
        opponent_id = request.POST.get('opponent_id')
        my_score = request.POST.get('my_score', '').strip()
        opponent_score = request.POST.get('opponent_score', '').strip()
        round_name = request.POST.get('round_name', 'League Match')
        match_result = request.POST.get('match_result', 'win') # 'win', 'loss', 'draw'
        notes = request.POST.get('notes', '').strip()

        if not tournament_id or not opponent_id or not my_score or not opponent_score:
            messages.error(request, "Please fill in all required match details (Tournament, Opponent, and Scores).")
            return render(request, 'accounts/submit_score.html', {
                'title': 'Submit',
                'tournaments': tournaments,
                'universities': universities,
                'user_uni_name': user_uni_name
            })

        try:
            if not ObjectId.is_valid(tournament_id) or not ObjectId.is_valid(opponent_id):
                messages.error(request, "Invalid tournament or opponent selected.")
                return render(request, 'accounts/submit_score.html', {
                    'title': 'Submit',
                    'tournaments': tournaments,
                    'universities': universities,
                    'user_uni_name': user_uni_name
                })

            tournament = Tournament.objects.get(id=ObjectId(tournament_id))
            opponent = University.objects.get(id=ObjectId(opponent_id))

            # Find submitter's university
            my_uni = None
            if session_user.get('university_id'):
                try:
                    my_uni = University.objects.get(id=ObjectId(session_user['university_id']))
                except Exception:
                    pass
            if not my_uni and user_uni_name:
                my_uni = University.objects(name=user_uni_name).first()
            if not my_uni:
                my_uni = University.objects.first()

            if not my_uni:
                messages.error(request, "No university profile available for your account. Please contact an administrator.")
                return render(request, 'accounts/submit_score.html', {
                    'title': 'Submit',
                    'tournaments': tournaments,
                    'universities': universities,
                    'user_uni_name': user_uni_name
                })

            if str(my_uni.id) == str(opponent.id):
                messages.error(request, "Cannot submit a match against your own university! Please select a valid opponent.")
                return render(request, 'accounts/submit_score.html', {
                    'title': 'Submit',
                    'tournaments': tournaments,
                    'universities': universities,
                    'user_uni_name': user_uni_name
                })

            # Determine winner
            if match_result == 'win':
                winner_id = my_uni.id
                winner_name = my_uni.name
                is_draw = False
                summary = f"{my_uni.short_code} won vs {opponent.short_code} ({my_score} - {opponent_score})"
            elif match_result == 'loss':
                winner_id = opponent.id
                winner_name = opponent.name
                is_draw = False
                summary = f"{opponent.short_code} won vs {my_uni.short_code} ({opponent_score} - {my_score})"
            else:
                winner_id = None
                winner_name = None
                is_draw = True
                summary = f"Match drawn between {my_uni.short_code} and {opponent.short_code} ({my_score} - {opponent_score})"

            if notes:
                summary += f" — {notes}"

            fixture = Fixture(
                tournament_id=tournament.id,
                tournament_name=tournament.name,
                sport_name=tournament.sport_name,
                round_name=round_name,
                venue=tournament.venue,
                team_a=MatchTeam(
                    university_id=my_uni.id,
                    name=my_uni.name,
                    short_code=my_uni.short_code,
                    score_display=my_score
                ),
                team_b=MatchTeam(
                    university_id=opponent.id,
                    name=opponent.name,
                    short_code=opponent.short_code,
                    score_display=opponent_score
                ),
                status='Completed',
                approval_status='Approved' if (tournament.approval_status == 'Approved' or session_user.get('role') == 'admin') else 'Pending',
                submitted_by=username,
                submitted_by_university=my_uni.name,
                winner_university_id=winner_id,
                winner_name=winner_name,
                is_draw=is_draw,
                result_summary=summary
            )
            fixture.save()

            if fixture.approval_status == 'Approved':
                if tournament.status == 'Upcoming':
                    tournament.status = 'Ongoing'
                    tournament.save()
                messages.success(
                    request,
                    f"Match score submitted and published live! Since '{tournament.name}' is sanctioned by the Board, your result is immediately updated in tournament standings."
                )
            else:
                messages.warning(
                    request,
                    f"Match score saved! Since '{tournament.name}' is pending Board sanctioning, this match will be published once the tournament receives approval."
                )
            return redirect('accounts:university_portal')
        except Exception as e:
            messages.error(request, f"Error submitting match score: {e}")

    return render(request, 'accounts/submit_score.html', {
        'title': 'Submit',
        'tournaments': tournaments,
        'universities': universities,
        'user_uni_name': user_uni_name
    })
