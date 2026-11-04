# What this file does:
# Analytics dashboard views: serves the interactive Chart.js visualization frontend and the JSON statistics API endpoint.

from django.shortcuts import render
from django.http import JsonResponse
from universities.models import University
from sports.models import Sport
from tournaments.models import Tournament
from analytics.services import calculate_ranking_scores, calculate_win_percentage

# Renders the interactive analytics dashboard template
def analytics_dashboard(request):
    """Interactive Chart.js visual analytics dashboard."""
    return render(request, 'analytics/dashboard.html', {
        'title': 'Athletic Intelligence & Analytics // UniSports'
    })

def api_stats(request):
    """
    JSON API supplying datasets for Chart.js interactive visualizations:
    1. Leaderboard Ranking Points (Bar)
    2. Overall Medal Distribution (Doughnut)
    3. Sport Participation (Bar)
    4. Win-rate comparisons (Horizontal Bar)
    """
    # 1. Ranking Points (2025)
    ranked = calculate_ranking_scores(year=2025)
    ranking_labels = [r.get('university_code', r.get('university_name', '')) for r in ranked]
    ranking_points = [r.get('total_points', 0) for r in ranked]
    gold_counts = [r.get('gold', 0) for r in ranked]
    silver_counts = [r.get('silver', 0) for r in ranked]
    bronze_counts = [r.get('bronze', 0) for r in ranked]

    total_gold = sum(gold_counts)
    total_silver = sum(silver_counts)
    total_bronze = sum(bronze_counts)

    # 2. Sports participation (count of enrolled universities per sport)
    sports = list(Sport.objects.all().order_by('name')) if hasattr(Sport.objects, 'all') else []
    universities = list(University.objects.all()) if hasattr(University.objects, 'all') else []

    sport_names = [s.name for s in sports]
    sport_counts = []
    for s in sports:
        count = sum(1 for u in universities if any(s.name.lower() == str(sp).lower() for sp in getattr(u, 'sports_enrolled', [])))
        sport_counts.append(count)

    # 3. Top universities win rates
    win_rate_labels = []
    win_rate_data = []
    for u in universities[:6]:
        stats = calculate_win_percentage(u.id)
        win_rate_labels.append(u.short_code)
        win_rate_data.append(stats['win_percentage'])

    payload = {
        'status': 'success',
        'rankings': {
            'labels': ranking_labels,
            'points': ranking_points,
            'gold': gold_counts,
            'silver': silver_counts,
            'bronze': bronze_counts
        },
        'medals': {
            'labels': ['Gold Medals', 'Silver Medals', 'Bronze Medals'],
            'data': [total_gold, total_silver, total_bronze]
        },
        'sports': {
            'labels': sport_names,
            'data': sport_counts
        },
        'win_rates': {
            'labels': win_rate_labels,
            'data': win_rate_data
        }
    }
    return JsonResponse(payload)
