"""
Unit tests for tournaments application.
Tests Tournament and Fixture models, listing views, detail views, and PDF export.
"""
import unittest
from django.test import RequestFactory
from django.http import Http404
from tournaments.models import Tournament, Fixture, MatchTeam, MedalEntry
from tournaments.views import tournament_list, tournament_detail, export_tournament_pdf

class TournamentsTestCase(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        Tournament.objects(name='Test Championship Cup').delete()
        self.tourn = Tournament(
            name='Test Championship Cup',
            sport_name='Cricket',
            sport_code='CRIC',
            year=2025,
            host_university_name='Test University',
            status='Ongoing'
        )
        self.tourn.save()

    def tearDown(self):
        Tournament.objects(name='Test Championship Cup').delete()

    def test_tournament_list_all_and_filtered(self):
        req = self.rf.get('/tournaments/?status=Ongoing')
        req.session = {}
        resp = tournament_list(req)
        self.assertEqual(resp.status_code, 200)

    def test_tournament_detail_view(self):
        req = self.rf.get(f'/tournaments/{self.tourn.id}/')
        req.session = {}
        resp = tournament_detail(req, tournament_id=str(self.tourn.id))
        self.assertEqual(resp.status_code, 200)

    def test_tournament_detail_not_found(self):
        req = self.rf.get('/tournaments/000000000000000000000000/')
        req.session = {}
        with self.assertRaises(Http404):
            tournament_detail(req, tournament_id='000000000000000000000000')

    def test_export_tournament_pdf_returns_pdf(self):
        req = self.rf.get(f'/tournaments/{self.tourn.id}/pdf/')
        req.session = {}
        resp = export_tournament_pdf(req, tournament_id=str(self.tourn.id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['content-type'], 'application/pdf')

    def test_tournament_create_unauthorized_redirect(self):
        from tournaments.views import tournament_create
        req = self.rf.get('/tournaments/create/')
        req.session = {}
        resp = tournament_create(req)
        self.assertEqual(resp.status_code, 302)

    def test_tournament_create_by_coach_or_admin(self):
        from tournaments.views import tournament_create
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware

        from sports.models import Sport
        from universities.models import University

        Tournament.objects(name='Created By Coach 2026').delete()
        sport = Sport.objects(code='CRIC').first()
        if not sport:
            sport = Sport(name='Cricket', code='CRIC', category='Team').save()

        uni = University.objects(short_code='T_HOST').first()
        if not uni:
            uni = University(name='Test Host Uni', short_code='T_HOST', city='City', state='State').save()

        req = self.rf.post('/tournaments/create/', {
            'name': 'Created By Coach 2026',
            'sport_code': 'CRIC',
            'year': '2026',
            'host_university_id': str(uni.id),
            'venue': 'Coach Ground',
            'status': 'Upcoming'
        })
        SessionMiddleware(lambda r: None).process_request(req)
        MessageMiddleware(lambda r: None).process_request(req)
        req.session['user'] = {'role': 'university_admin', 'username': 'coach_test', 'university_id': str(uni.id)}
        resp = tournament_create(req)
        self.assertEqual(resp.status_code, 302)
        created = Tournament.objects(name='Created By Coach 2026').first()
        self.assertIsNotNone(created)
        Tournament.objects(name='Created By Coach 2026').delete()
        University.objects(short_code='T_HOST').delete()

    def test_fixture_disallows_self_match(self):
        from bson import ObjectId
        from mongoengine import ValidationError

        same_id = ObjectId()
        fix = Fixture(
            tournament_id=ObjectId(),
            tournament_name="Test Tourn",
            sport_name="Cricket",
            team_a=MatchTeam(university_id=same_id, name="Uni A", short_code="UA"),
            team_b=MatchTeam(university_id=same_id, name="Uni A", short_code="UA")
        )
        with self.assertRaises(ValidationError):
            fix.clean()
