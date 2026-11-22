# What this file does:
# Core views for UniSports platform: homepage with aggregate counts, annual leaderboard rankings, and head-to-head match comparison.

from django.shortcuts import render
from universities.models import University
from sports.models import Sport
from tournaments.models import Tournament, Fixture
from analytics.services import calculate_ranking_scores, compute_h2h_matrix

# Homepage view showing platform metrics and recent tournaments
def index(request):
    """Platform homepage with live aggregated metrics and recent fixtures."""
    universities_count = University.objects.count() if hasattr(University.objects, 'count') else 0
    sports_count = Sport.objects.count() if hasattr(Sport.objects, 'count') else 0
    tournaments_count = Tournament.objects(approval_status__nin=['Pending', 'Rejected']).count() if hasattr(Tournament.objects, 'filter') else 0
    fixtures_count = Fixture.objects(approval_status__nin=['Pending', 'Rejected']).count() if hasattr(Fixture.objects, 'filter') else 0

    recent_tournaments = list(Tournament.objects(approval_status__nin=['Pending', 'Rejected']).order_by('-year')[:4]) if hasattr(Tournament.objects, 'filter') else []

    context = {
        'title': 'Home',
        'metrics': {
            'universities': universities_count,
            'sports': sports_count,
            'tournaments': tournaments_count,
            'fixtures': fixtures_count,
        },
        'recent_tournaments': recent_tournaments,
    }
    return render(request, 'core/index.html', context)


def rankings(request):
    """
    Algorithm 1: Annual Leaderboard & Rankings Matrix
    Score = (G*5) + (S*3) + (B*1)
    """
    selected_year = request.GET.get('year', '2025')
    selected_sport = request.GET.get('sport', 'All')

    years = [2026, 2025, 2024, 2023]
    sports = list(Sport.objects.all().order_by('name')) if hasattr(Sport.objects, 'all') else []

    safe_year = int(selected_year) if selected_year and selected_year.isdigit() else 2025
    ranked_universities = calculate_ranking_scores(
        year=safe_year,
        sport_name=selected_sport
    )

    context = {
        'title': 'Rankings',
        'ranked_universities': ranked_universities,
        'selected_year': safe_year,
        'selected_sport': selected_sport,
        'years': years,
        'sports': sports
    }
    return render(request, 'core/rankings.html', context)


def compare(request):
    """
    Algorithm 4: Head-to-Head Comparative Matrix via Pandas
    """
    from bson import ObjectId
    universities = list(University.objects.all().order_by('name')) if hasattr(University.objects, 'all') else []
    sports = list(Sport.objects.all().order_by('name')) if hasattr(Sport.objects, 'all') else []

    team_a_id = request.GET.get('team_a')
    team_b_id = request.GET.get('team_b')
    sport_name = request.GET.get('sport', 'All')

    # Defaults if not provided
    if not team_a_id and len(universities) > 0:
        team_a_id = str(universities[0].id)
    if not team_b_id and len(universities) > 1:
        team_b_id = str(universities[1].id)

    uni_a = None
    uni_b = None

    if team_a_id:
        if ObjectId.is_valid(team_a_id):
            try:
                uni_a = University.objects.get(id=ObjectId(team_a_id))
            except Exception:
                pass
        if not uni_a:
            try:
                uni_a = University.objects.get(short_code__iexact=team_a_id)
            except Exception:
                uni_a = universities[0] if universities else None

    if team_b_id:
        if ObjectId.is_valid(team_b_id):
            try:
                uni_b = University.objects.get(id=ObjectId(team_b_id))
            except Exception:
                pass
        if not uni_b:
            try:
                uni_b = University.objects.get(short_code__iexact=team_b_id)
            except Exception:
                uni_b = universities[1] if len(universities) > 1 else (universities[0] if universities else None)

    is_same_team = (uni_a and uni_b and str(uni_a.id) == str(uni_b.id))
    h2h_data = None

    if uni_a and uni_b and not is_same_team:
        try:
            h2h_data = compute_h2h_matrix(uni_a.id, uni_b.id, sport_name=sport_name)
        except Exception:
            h2h_data = None

    context = {
        'title': 'Compare',
        'universities': universities,
        'sports': sports,
        'team_a_id': str(uni_a.id) if uni_a else '',
        'team_b_id': str(uni_b.id) if uni_b else '',
        'selected_sport': sport_name,
        'uni_a': uni_a,
        'uni_b': uni_b,
        'h2h': h2h_data,
        'is_same_team': is_same_team
    }
    return render(request, 'core/compare.html', context)
