"""
Unit and algorithmic tests for analytics application.
Tests ranking formulas, points tables, win rates, and H2H comparative matrix.
"""
import unittest
from bson import ObjectId
from django.test import RequestFactory
from analytics.services import (
    calculate_ranking_scores,
    calculate_win_percentage,
    compute_tournament_points_table,
    compute_h2h_matrix
)
from analytics.views import analytics_dashboard, api_stats

class AnalyticsAlgorithmsTestCase(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_calculate_win_percentage_division_by_zero_safe(self):
        # Nonexistent university should return 0.0 without division by zero
        res = calculate_win_percentage(ObjectId())
        self.assertEqual(res['played'], 0)
        self.assertEqual(res['won'], 0)
        self.assertEqual(res['win_percentage'], 0.0)

    def test_ranking_scores_calculation_returns_list(self):
        rankings = calculate_ranking_scores(year=2025)
        self.assertIsInstance(rankings, list)
        if rankings:
            first = rankings[0]
            self.assertIn('total_points', first)
            self.assertIn('gold', first)
            self.assertIn('silver', first)
            self.assertIn('bronze', first)
            self.assertIn('rank', first)

    def test_points_table_computation_empty_or_valid(self):
        table = compute_tournament_points_table(ObjectId())
        self.assertIsInstance(table, list)

    def test_h2h_matrix_identical_or_empty(self):
        uid1 = ObjectId()
        uid2 = ObjectId()
        matrix = compute_h2h_matrix(uid1, uid2)
        self.assertIn('total_matches', matrix)
        self.assertIn('team_a_wins', matrix)
        self.assertIn('team_b_wins', matrix)
        self.assertIn('draws', matrix)
        self.assertEqual(matrix['total_matches'], 0)

    def test_api_stats_json_response(self):
        req = self.rf.get('/analytics/api/stats/')
        resp = api_stats(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['content-type'], 'application/json')
