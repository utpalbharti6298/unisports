"""
Unit and integration tests for accounts application.
Covers authentication, password hashing, role permissions, and views.
"""
import unittest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from accounts.models import User
from accounts.auth_service import hash_password, verify_password, authenticate_user, login_required_custom, admin_required
from accounts.views import login_view, logout_view, admin_dashboard, university_portal
from universities.models import University

class AccountsTestCase(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        User.objects(username='test_accounts_user').delete()
        self.test_user = User(
            username='test_accounts_user',
            email='test_acc@unisports.edu.in',
            password_hash=hash_password('secret123'),
            role='university_admin',
            university_name='Test University'
        )
        self.test_user.save()

    def tearDown(self):
        User.objects(username='test_accounts_user').delete()

    def test_hash_and_verify_password(self):
        pwd = "SafePassword99"
        hashed = hash_password(pwd)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_authenticate_valid_and_invalid(self):
        res = authenticate_user('test_accounts_user', 'secret123')
        self.assertIsNotNone(res)
        self.assertEqual(res['username'], 'test_accounts_user')

        res_bad = authenticate_user('test_accounts_user', 'wrongpassword')
        self.assertIsNone(res_bad)

    def test_login_required_decorator_redirect(self):
        @login_required_custom
        def dummy_view(request):
            return "OK"

        req = self.rf.get('/')
        req.session = {}
        resp = dummy_view(req)
        self.assertEqual(resp.status_code, 302)

    def test_admin_required_decorator_redirect_for_non_admin(self):
        @admin_required
        def dummy_admin_view(request):
            return "OK"

        req = self.rf.get('/')
        req.session = {'user': {'role': 'university_admin'}}
        resp = dummy_admin_view(req)
        self.assertEqual(resp.status_code, 302)

    def test_logout_flushes_session(self):
        req = self.rf.get('/accounts/logout/')
        SessionMiddleware(lambda r: None).process_request(req)
        MessageMiddleware(lambda r: None).process_request(req)
        req.session['user'] = {'username': 'test_accounts_user'}
        resp = logout_view(req)
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('user', req.session)

    def test_coach_or_admin_decorator_allows_coach_and_admin(self):
        from accounts.auth_service import coach_or_admin_required

        @coach_or_admin_required
        def protected_view(request):
            return "SUCCESS"

        # Coach role allowed
        req_coach = self.rf.get('/')
        req_coach.session = {'user': {'role': 'university_admin'}}
        self.assertEqual(protected_view(req_coach), "SUCCESS")

        # Admin role allowed
        req_admin = self.rf.get('/')
        req_admin.session = {'user': {'role': 'admin'}}
        self.assertEqual(protected_view(req_admin), "SUCCESS")

        # Viewer role blocked
        req_viewer = self.rf.get('/')
        req_viewer.session = {'user': {'role': 'viewer'}}
        resp_viewer = protected_view(req_viewer)
        self.assertEqual(resp_viewer.status_code, 302)

        # Unauthenticated blocked
        req_anon = self.rf.get('/')
        req_anon.session = {}
        self.assertEqual(protected_view(req_anon).status_code, 302)

    def test_coach_can_create_university_and_sport(self):
        from accounts.views import admin_create_university, admin_create_sport

        University.objects(short_code='COACH_U').delete()
        req_uni = self.rf.post('/accounts/admin-panel/university/create/', {
            'name': 'Coach Registered University',
            'short_code': 'COACH_U',
            'city': 'Varanasi',
            'state': 'UP'
        })
        SessionMiddleware(lambda r: None).process_request(req_uni)
        MessageMiddleware(lambda r: None).process_request(req_uni)
        req_uni.session['user'] = {'role': 'university_admin', 'username': 'coach_test'}
        resp_uni = admin_create_university(req_uni)
        self.assertEqual(resp_uni.status_code, 302)
        self.assertEqual(resp_uni.url, '/accounts/university-portal/')
        self.assertIsNotNone(University.objects(short_code='COACH_U').first())
        University.objects(short_code='COACH_U').delete()

    def test_front_ui_navbar_admin_login(self):
        from django.test import Client
        c = Client()
        resp = c.get('/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Member Login', content)
        self.assertIn('Admin Login', content)
        self.assertNotIn('Member Sign Up', content)
        # Member Login appears first, Admin Login appears second
        member_idx = content.find('Member Login')
        admin_idx = content.find('Admin Login')
        self.assertTrue(member_idx < admin_idx)

    def test_login_page_role_toggle(self):
        from django.test import Client
        c = Client()
        # Admin login page
        resp_admin = c.get('/accounts/login/?role=admin')
        self.assertEqual(resp_admin.status_code, 200)
        content_admin = resp_admin.content.decode('utf-8')
        self.assertIn('Admin Login', content_admin)
        self.assertIn('Admin Sign In', content_admin)

        # Member login page
        resp_member = c.get('/accounts/login/')
        self.assertEqual(resp_member.status_code, 200)
        content_member = resp_member.content.decode('utf-8')
        self.assertIn('Member Login', content_member)
