"""
Unit tests for universities application.
Tests University MongoEngine model, university directory search, and athletic profile views.
"""
import unittest
from django.test import RequestFactory
from django.http import Http404
from universities.models import University
from universities.views import university_list, university_detail

class UniversitiesTestCase(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        University.objects(short_code='TST_UNI').delete()
        self.uni = University(
            name='Test Central University',
            short_code='TST_UNI',
            city='Prayagraj',
            state='Uttar Pradesh',
            established_year=1900,
            sports_enrolled=['Cricket', 'Football']
        )
        self.uni.save()

    def tearDown(self):
        University.objects(short_code='TST_UNI').delete()

    def test_university_model_representation(self):
        self.assertEqual(str(self.uni), "Test Central University (TST_UNI)")
        self.assertIn('Cricket', self.uni.sports_enrolled)

    def test_university_list_view_and_search(self):
        req = self.rf.get('/universities/?q=Central')
        req.session = {}
        resp = university_list(req)
        self.assertEqual(resp.status_code, 200)

    def test_university_detail_view(self):
        req = self.rf.get(f'/universities/{self.uni.id}/')
        req.session = {}
        resp = university_detail(req, uni_id=str(self.uni.id))
        self.assertEqual(resp.status_code, 200)

    def test_university_detail_not_found(self):
        req = self.rf.get('/universities/000000000000000000000000/')
        req.session = {}
        with self.assertRaises(Http404):
            university_detail(req, uni_id='000000000000000000000000')
