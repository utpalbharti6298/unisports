"""
Unit tests for sports application.
Tests Sport MongoEngine model, sport list view, and sport detail view.
"""
import unittest
from django.test import RequestFactory
from django.http import Http404
from sports.models import Sport
from sports.views import sport_list, sport_detail

class SportsTestCase(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        Sport.objects(code='TST_SPORT').delete()
        self.sport = Sport(
            name='Test Sport Discipline',
            code='TST_SPORT',
            category='Team',
            win_points=2,
            draw_points=1,
            loss_points=0
        )
        self.sport.save()

    def tearDown(self):
        Sport.objects(code='TST_SPORT').delete()

    def test_sport_model_fields_and_string(self):
        self.assertEqual(str(self.sport), "Test Sport Discipline [Team]")
        self.assertEqual(self.sport.win_points, 2)
        self.assertEqual(self.sport.draw_points, 1)

    def test_sport_list_view(self):
        req = self.rf.get('/sports/')
        req.session = {}
        resp = sport_list(req)
        self.assertEqual(resp.status_code, 200)

    def test_sport_detail_view_found_and_not_found(self):
        req = self.rf.get(f'/sports/{self.sport.code}/')
        req.session = {}
        resp = sport_detail(req, sport_id=self.sport.code)
        self.assertEqual(resp.status_code, 200)

        with self.assertRaises(Http404):
            sport_detail(req, sport_id='NONEXISTENT_CODE_XYZ')
