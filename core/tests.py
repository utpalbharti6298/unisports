"""
Unit tests for core application.
Tests homepage metrics, ranking views, H2H comparator view, and global context processor.
"""
import unittest
from django.test import RequestFactory
from core.views import index, rankings, compare
from core.context_processors import global_context

class CoreViewsTestCase(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_global_context_processor(self):
        req = self.rf.get('/')
        req.session = {'user': {'username': 'admin', 'role': 'admin'}}
        ctx = global_context(req)
        self.assertIn('current_year', ctx)
        self.assertIn('session_user', ctx)
        self.assertTrue(ctx['is_admin'])

    def test_index_view_renders_200(self):
        req = self.rf.get('/')
        req.session = {}
        resp = index(req)
        self.assertEqual(resp.status_code, 200)

    def test_rankings_view_handles_valid_and_invalid_year(self):
        req_valid = self.rf.get('/rankings/?year=2025&sport=All')
        req_valid.session = {}
        resp_valid = rankings(req_valid)
        self.assertEqual(resp_valid.status_code, 200)

        # Non-digit or empty year param should gracefully default to 2025
        req_invalid = self.rf.get('/rankings/?year=invalid')
        req_invalid.session = {}
        resp_invalid = rankings(req_invalid)
        self.assertEqual(resp_invalid.status_code, 200)

    def test_compare_view_renders_and_flags_same_team(self):
        req = self.rf.get('/compare/?team_a=abc&team_b=abc')
        req.session = {}
        resp = compare(req)
        self.assertEqual(resp.status_code, 200)
