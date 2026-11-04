# What this file does:
# Automated end-to-end audit test suite verifying frontend routing, database models, aggregation pipelines, and role permissions.

import pytest
from django.test import Client
from bson import ObjectId
from accounts.models import User
from universities.models import University
from sports.models import Sport
from tournaments.models import Tournament, Fixture, MatchTeam, TournamentUniversity, MedalEntry
from analytics.services import (
    calculate_ranking_scores,
    calculate_win_percentage,
    compute_tournament_points_table,
    compute_h2h_matrix
)
from accounts.auth_service import hash_password, ensure_master_admin

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def master_admin():
    return ensure_master_admin()

@pytest.fixture
def approved_coach():
    User.objects(username='audit_coach').delete()
    u = University.objects.first()
    coach = User(
        username='audit_coach',
        email='coach@audituni.edu.in',
        password_hash=hash_password('coachPass123!'),
        role='university_admin',
        full_name='Audit Coach',
        university_id=u.id if u else None,
        university_name=u.name if u else 'Audit Uni',
        approval_status='approved',
        is_active=True
    )
    coach.save()
    return coach

@pytest.fixture
def pending_coach():
    User.objects(username='audit_pending_coach').delete()
    coach = User(
        username='audit_pending_coach',
        email='pending@audituni.edu.in',
        password_hash=hash_password('coachPass123!'),
        role='university_admin',
        full_name='Pending Coach',
        approval_status='pending',
        is_active=True
    )
    coach.save()
    return coach

# ==============================================================================
# 1. PUBLIC ROUTE & VIEW AUDIT
# ==============================================================================
def test_public_routes(client):
    """Test all public views return 200 OK and render correctly."""
    routes = [
        ('/', 'Home'),
        ('/rankings/', 'Rankings'),
        ('/compare/', 'H2H Compare'),
        ('/universities/', 'Universities'),
        ('/sports/', 'Sports'),
        ('/tournaments/', 'Tournaments'),
        ('/analytics/', 'Analytics'),
        ('/analytics/api/stats/', 'API Stats'),
        ('/accounts/login/', 'Login'),
        ('/accounts/register/', 'Register'),
    ]
    for url, name in routes:
        resp = client.get(url)
        assert resp.status_code == 200, f"Route '{name}' at {url} returned {resp.status_code}"

def test_api_stats_payload_format(client):
    """Test /analytics/api/stats/ returns required JSON structure."""
    resp = client.get('/analytics/api/stats/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'success'
    assert 'rankings' in data
    assert 'medals' in data
    assert 'sports' in data
    assert 'win_rates' in data

def test_invalid_objectid_handling(client):
    """Ensure invalid / malformed ObjectIds in URLs raise 404 cleanly, never 500."""
    invalid_urls = [
        '/universities/invalid-id-string/',
        '/universities/123456789012345678901234/', # Valid length, non-existent ID
        '/tournaments/invalid-tourn-id/',
        '/tournaments/123456789012345678901234/',
        '/tournaments/invalid-id/pdf/',
        '/sports/definitely-not-a-sport-xyz-999/',
    ]
    for url in invalid_urls:
        resp = client.get(url)
        assert resp.status_code == 404, f"URL {url} should return 404, got {resp.status_code}"

# ==============================================================================
# 2. ATHLETIC ALGORITHMS & ZERO DIVISION EDGE CASES
# ==============================================================================
def test_algorithm_empty_or_zero_division():
    """Ensure algorithms handle empty inputs or zero division gracefully."""
    fake_id = ObjectId()
    
    # Algorithm 2: Win percentage on university with 0 matches
    win_stats = calculate_win_percentage(fake_id)
    assert win_stats['played'] == 0
    assert win_stats['win_percentage'] == 0.0

    # Algorithm 3: Points table on non-existent tournament
    table = compute_tournament_points_table(fake_id)
    assert isinstance(table, list)
    assert len(table) == 0

    # Algorithm 4: H2H matrix between two universities with 0 matches
    h2h = compute_h2h_matrix(fake_id, ObjectId())
    assert h2h['total_matches'] == 0
    assert h2h['differential'] == 0

    # Algorithm 1: Ranking scores for arbitrary year with 0 completed tournaments
    ranks = calculate_ranking_scores(year=1999)
    assert isinstance(ranks, list)

# ==============================================================================
# 3. AUTHENTICATION & ROLE ACCESS AUDIT
# ==============================================================================
def test_unauthenticated_protected_routes(client):
    """Ensure anonymous users are redirected away from protected admin/coach routes."""
    protected_urls = [
        '/accounts/admin-panel/',
        '/accounts/admin-panel/approvals/',
        '/accounts/admin-panel/coach-approvals/',
        '/accounts/admin-panel/university/create/',
        '/accounts/admin-panel/sport/create/',
        '/accounts/university-portal/',
        '/accounts/university-portal/submit-score/',
        '/tournaments/create/',
    ]
    for url in protected_urls:
        resp = client.get(url)
        assert resp.status_code == 302, f"Protected URL {url} should redirect anonymous user, got {resp.status_code}"
        assert '/accounts/login/' in resp.url

def test_coach_cannot_access_admin_panel(client, approved_coach):
    """Ensure a coach cannot access /accounts/admin-panel/ or admin approval routes."""
    login_resp = client.post('/accounts/login/', {
        'username': 'audit_coach',
        'password': 'coachPass123!'
    })
    assert login_resp.status_code == 302

    admin_only_routes = [
        '/accounts/admin-panel/',
        '/accounts/admin-panel/approvals/',
        '/accounts/admin-panel/coach-approvals/',
    ]
    for url in admin_only_routes:
        resp = client.get(url)
        assert resp.status_code == 302, f"Coach should be blocked from {url}, got {resp.status_code}"
        assert '/accounts/login/' in resp.url

def test_admin_can_access_admin_panel(client, master_admin):
    """Ensure master admin can access admin dashboard and approval panels."""
    login_resp = client.post('/accounts/login/', {
        'username': master_admin.username,
        'password': 'admin123'
    })
    assert login_resp.status_code == 302

    resp = client.get('/accounts/admin-panel/')
    assert resp.status_code == 200
    assert b"Administrator Control Center" in resp.content or b"Platform Administration" in resp.content

    resp_coach_approvals = client.get('/accounts/admin-panel/coach-approvals/')
    assert resp_coach_approvals.status_code == 200
    assert b"Member & Official Approvals" in resp_coach_approvals.content or b"Coach & Official Approvals" in resp_coach_approvals.content

# ==============================================================================
# 4. REPORTLAB PDF EXPORT AUDIT
# ==============================================================================
def test_pdf_export_success(client):
    """Test PDF generation for real tournament."""
    tourn = Tournament.objects.first()
    if tourn:
        resp = client.get(f'/tournaments/{tourn.id}/pdf/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
        assert len(resp.content) > 500 # Valid non-empty PDF bytes

# ==============================================================================
# 5. ROBUST LOOKUP & RESILIENCE AUDIT
# ==============================================================================
def test_university_short_code_lookup(client):
    """Ensure universities can be visited via short_code in addition to ObjectId."""
    uni = University.objects.first()
    if uni:
        resp = client.get(f'/universities/{uni.short_code}/')
        assert resp.status_code == 200
        assert uni.name.encode('utf-8') in resp.content

def test_compare_resilience_to_invalid_inputs(client):
    """Ensure compare view does not crash when passed arbitrary/invalid strings in GET."""
    resp = client.get('/compare/?team_a=not-an-id&team_b=also-invalid&sport=InvalidSport')
    assert resp.status_code == 200

def test_coach_score_submission_flow(client, approved_coach):
    """Ensure an approved coach can submit scores and gets redirected with Pending approval status."""
    login_resp = client.post('/accounts/login/', {
        'username': 'audit_coach',
        'password': 'coachPass123!'
    })
    assert login_resp.status_code == 302

    tourn = Tournament.objects.first()
    unis = list(University.objects.all())
    if tourn and len(unis) >= 2:
        uni_b = [u for u in unis if str(u.id) != str(approved_coach.university_id)][0]
        
        # 1. Sanctioned tournament -> auto-approved immediately
        tourn.approval_status = 'Approved'
        tourn.save()
        resp = client.post('/accounts/university-portal/submit-score/', {
            'tournament_id': str(tourn.id),
            'opponent_id': str(uni_b.id),
            'my_score': '4',
            'opponent_score': '2',
            'round_name': 'Semifinal',
            'match_result': 'win',
            'notes': 'Test fixture audit sanctioned'
        })
        assert resp.status_code == 302
        saved_fix = Fixture.objects(submitted_by='audit_coach').order_by('-created_at').first()
        assert saved_fix is not None
        assert saved_fix.approval_status == 'Approved'
        saved_fix.delete()

        # 2. Unsanctioned (Pending) tournament -> score remains Pending
        tourn.approval_status = 'Pending'
        tourn.save()
        resp2 = client.post('/accounts/university-portal/submit-score/', {
            'tournament_id': str(tourn.id),
            'opponent_id': str(uni_b.id),
            'my_score': '3',
            'opponent_score': '1',
            'round_name': 'Final',
            'match_result': 'win',
            'notes': 'Test fixture audit unsanctioned'
        })
        assert resp2.status_code == 302
        saved_fix2 = Fixture.objects(submitted_by='audit_coach').order_by('-created_at').first()
        assert saved_fix2 is not None
        assert saved_fix2.approval_status == 'Pending'
        saved_fix2.delete()

        # Restore tournament status to Approved
        tourn.approval_status = 'Approved'
        tourn.save()

def test_submit_score_validation_guards(client, approved_coach):
    """Ensure submitting incomplete or invalid scores displays clear error messages."""
    client.post('/accounts/login/', {
        'username': 'audit_coach',
        'password': 'coachPass123!'
    })

    # Missing required fields
    resp = client.post('/accounts/university-portal/submit-score/', {})
    assert resp.status_code == 200
    assert b"Please fill in all required match details" in resp.content

    # Self-match prevention
    tourn = Tournament.objects.first()
    if tourn and approved_coach.university_id:
        resp = client.post('/accounts/university-portal/submit-score/', {
            'tournament_id': str(tourn.id),
            'opponent_id': str(approved_coach.university_id),
            'my_score': '3',
            'opponent_score': '1',
        })
        assert resp.status_code == 200
        assert b"Cannot submit a match against your own university" in resp.content

def test_admin_create_entity_validation_guards(client, master_admin):
    """Ensure empty entity submissions in admin forms provide error feedback."""
    client.post('/accounts/login/', {
        'username': master_admin.username,
        'password': 'admin123'
    })

    # University missing name and code
    resp_uni = client.post('/accounts/admin-panel/university/create/', {}, follow=True)
    assert resp_uni.status_code == 200
    assert b"University name and short code are required" in resp_uni.content

    # Sport missing name and code
    resp_sport = client.post('/accounts/admin-panel/sport/create/', {}, follow=True)
    assert resp_sport.status_code == 200
    assert b"Sport name and discipline code are required" in resp_sport.content

def test_tournament_sanction_and_autonomous_coach_edit(client, approved_coach, master_admin):
    """Verifies that coach proposes tournament -> Pending -> Admin sanctions -> Coach edits autonomously without re-approval."""
    # 1. Coach logs in and creates tournament
    client.post('/accounts/login/', {'username': 'audit_coach', 'password': 'coachPass123!'})
    sport = Sport.objects.first()
    uni = University.objects.get(id=approved_coach.university_id)
    
    resp_create = client.post('/tournaments/create/', {
        'name': 'Inter-College Invitational Meet',
        'sport_code': sport.code,
        'year': '2026',
        'host_university_id': str(uni.id),
        'venue': 'Campus Sports Ground',
        'status': 'Upcoming',
    }, follow=True)
    assert resp_create.status_code == 200

    created_tourn = Tournament.objects(name='Inter-College Invitational Meet').first()
    assert created_tourn is not None
    assert created_tourn.approval_status == 'Pending'
    assert created_tourn.created_by == 'audit_coach'

    # 2. Admin logs in (after logging out coach) and sanctions tournament
    client.get('/accounts/logout/')
    login_admin = client.post('/accounts/login/', {'username': master_admin.username, 'password': 'admin123'})
    assert login_admin.status_code == 302
    resp_approve = client.get(f'/accounts/admin-panel/tournament-approvals/{created_tourn.id}/approve/', follow=True)
    assert resp_approve.status_code == 200

    created_tourn.reload()
    assert created_tourn.approval_status == 'Approved'

    # 3. Coach logs back in and edits tournament details (venue and status)
    client.get('/accounts/logout/')
    login_coach = client.post('/accounts/login/', {'username': 'audit_coach', 'password': 'coachPass123!'})
    assert login_coach.status_code == 302
    resp_edit = client.post(f'/tournaments/{created_tourn.id}/edit/', {
        'name': 'Inter-College Invitational Meet (Grand Season)',
        'year': '2026',
        'venue': 'Upgraded Olympic Stadium',
        'status': 'Ongoing',
    }, follow=True)
    assert resp_edit.status_code == 200

    created_tourn.reload()
    assert created_tourn.name == 'Inter-College Invitational Meet (Grand Season)'
    assert created_tourn.venue == 'Upgraded Olympic Stadium'
    assert created_tourn.status == 'Ongoing'
    # Crucial assertion: Status REMAINS Approved, not reset to Pending!
    assert created_tourn.approval_status == 'Approved'

    created_tourn.delete()

def test_fixture_auto_syncs_participating_universities(master_admin):
    """Verifies that saving a fixture automatically populates tournament.participating_universities."""
    unis = list(University.objects.all()[:2])
    if len(unis) >= 2:
        sport = Sport.objects.first()
        t = Tournament(
            name='Temporary Auto Sync Championship',
            sport_name=sport.name,
            sport_code=sport.code,
            year=2026,
            host_university_name=unis[0].name,
            host_university_id=unis[0].id,
            participating_universities=[],
        )
        t.save()
        assert t.university_count == 0

        # Create fixture between unis[0] and unis[1]
        from tournaments.models import MatchTeam
        f = Fixture(
            tournament_id=t.id,
            tournament_name=t.name,
            sport_name=sport.name,
            round_name='Group A',
            team_a=MatchTeam(university_id=unis[0].id, name=unis[0].name, short_code=unis[0].short_code),
            team_b=MatchTeam(university_id=unis[1].id, name=unis[1].name, short_code=unis[1].short_code),
            status='Completed',
        )
        f.save()

        t.reload()
        assert t.university_count == 2
        assert len(t.participating_universities) == 2
        codes = {u.short_code for u in t.participating_universities}
        assert unis[0].short_code in codes
        assert unis[1].short_code in codes

        f.delete()
        t.delete()

def test_pending_tournament_public_privacy_guard(client, approved_coach, master_admin):
    """Verifies that unsanctioned (Pending/Rejected) tournaments are hidden from the public and unauthorized users."""
    sport = Sport.objects.first()
    uni = University.objects.get(id=approved_coach.university_id)

    pending_tourn = Tournament(
        name='Secret Unsanctioned League',
        sport_name=sport.name,
        sport_code=sport.code,
        year=2026,
        host_university_name=uni.name,
        host_university_id=uni.id,
        approval_status='Pending',
        created_by='audit_coach',
        created_by_role='university_admin'
    )
    pending_tourn.save()

    # 1. Anonymous public visitor -> Hidden from calendar, detail 404, export PDF 404
    client.get('/accounts/logout/')
    resp_list = client.get('/tournaments/')
    assert resp_list.status_code == 200
    assert b"Secret Unsanctioned League" not in resp_list.content

    resp_detail = client.get(f'/tournaments/{pending_tourn.id}/')
    assert resp_detail.status_code == 404

    resp_pdf = client.get(f'/tournaments/{pending_tourn.id}/pdf/')
    assert resp_pdf.status_code == 404

    # 2. Host Coach who proposed it -> CAN access to monitor and edit
    client.post('/accounts/login/', {'username': 'audit_coach', 'password': 'coachPass123!'})
    coach_detail = client.get(f'/tournaments/{pending_tourn.id}/')
    assert coach_detail.status_code == 200
    assert b"Secret Unsanctioned League" in coach_detail.content
    assert b"Sanction Pending" in coach_detail.content

    # 3. Super Admin -> CAN access and review in admin queue and detail
    client.get('/accounts/logout/')
    client.post('/accounts/login/', {'username': master_admin.username, 'password': 'admin123'})
    admin_detail = client.get(f'/tournaments/{pending_tourn.id}/')
    assert admin_detail.status_code == 200
    assert b"Sanction Tournament" in admin_detail.content

    pending_tourn.delete()
