# What this file does:
# University directory views: list all participating institutions with text search, and display university detail profiles with win-rate statistics and recent fixtures.

from django.shortcuts import render, Http404
from bson import ObjectId
from universities.models import University
from tournaments.models import Fixture
from analytics.services import calculate_win_percentage

# Searchable list of all participating universities
def university_list(request):
    """Lists all enrolled universities."""
    search_query = request.GET.get('q', '').strip()
    try:
        if search_query:
            unis = list(University.objects(name__icontains=search_query).order_by('name'))
        else:
            unis = list(University.objects.all().order_by('name'))
    except Exception:
        unis = []

    return render(request, 'universities/list.html', {
        'title': 'Universities',
        'universities': unis,
        'search_query': search_query
    })

def university_detail(request, uni_id):
    """Displays university athletic profile, win rate, and match log."""
    uni = None
    if ObjectId.is_valid(uni_id):
        try:
            uni = University.objects.get(id=ObjectId(uni_id))
        except Exception:
            pass

    if not uni:
        try:
            uni = University.objects.get(short_code__iexact=uni_id)
        except Exception:
            try:
                uni = University.objects.get(name__iexact=uni_id)
            except Exception:
                raise Http404("University not found")

    stats = calculate_win_percentage(uni.id)

    # Recent fixtures involving this university (Approved only)
    try:
        from mongoengine import Q
        fixtures = list(Fixture.objects(
            Q(approval_status__nin=['Pending', 'Rejected']) & (Q(team_a__university_id=uni.id) | Q(team_b__university_id=uni.id))
        ).order_by('-match_date')[:10])
    except Exception:
        fixtures = []

    return render(request, 'universities/detail.html', {
        'title': uni.short_code,
        'university': uni,
        'stats': stats,
        'fixtures': fixtures
    })
