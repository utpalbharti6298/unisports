# What this file does:
# Sports catalog views: list all athletic disciplines with rules, and display sport detail page with championships conducted under that sport.

from django.shortcuts import render, Http404
from sports.models import Sport
from tournaments.models import Tournament

# List all regulated sports disciplines and their point rules
def sport_list(request):
    """Lists sports disciplines and points system."""
    sports = list(Sport.objects.all().order_by('name'))
    return render(request, 'sports/list.html', {
        'title': 'Sports',
        'sports': sports
    })

def sport_detail(request, sport_id):
    """Detailed view for a specific athletic discipline and tournaments."""
    from bson import ObjectId
    sport = None
    if ObjectId.is_valid(sport_id):
        try:
            sport = Sport.objects.get(id=ObjectId(sport_id))
        except Exception:
            pass
    if not sport:
        try:
            sport = Sport.objects.get(code=sport_id.upper())
        except Exception:
            try:
                sport = Sport.objects.get(name__iexact=sport_id)
            except Exception:
                raise Http404("Sport discipline not found")

    tournaments = list(Tournament.objects(sport_code=sport.code, approval_status='Approved').order_by('-year'))

    return render(request, 'sports/detail.html', {
        'title': sport.name,
        'sport': sport,
        'tournaments': tournaments
    })
