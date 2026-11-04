# What this file does:
# Automated tests verifying the coach self-registration and administrative verification lifecycle, single master admin bootstrap, and role-based login restrictions.

import pytest
from accounts.models import User
from accounts.auth_service import hash_password, authenticate_user, ensure_master_admin
from universities.models import University

def test_single_fixed_master_admin():
    """Ensure the single master admin is provisioned and has role='admin'."""
    admin = ensure_master_admin()
    assert admin is not None
    assert admin.role == 'admin'
    assert admin.approval_status == 'approved'

    # Admin should authenticate successfully
    user_data, status, err = authenticate_user(admin.username, 'admin123', return_status=True)
    assert user_data is not None
    assert status == 'SUCCESS'
    assert user_data['role'] == 'admin'

def test_coach_registration_and_approval_cycle():
    """Test full cycle: coach registers -> pending -> denied login -> admin approves -> allowed login."""
    User.objects(username='coach_test_approval').delete()

    # 1. Coach registers with pending status
    coach = User(
        username='coach_test_approval',
        email='coach_test@testuni.edu.in',
        password_hash=hash_password('coachSecure123'),
        role='university_admin',
        full_name='Test Coach Official',
        university_name='Test University',
        approval_status='pending',
        is_active=True
    )
    coach.save()

    # 2. Attempt login while pending -> must be blocked
    user_data, status, err = authenticate_user('coach_test_approval', 'coachSecure123', return_status=True)
    assert user_data is None
    assert status == 'PENDING_APPROVAL'
    assert "awaiting approval" in err

    # 3. Backward-compatible authenticate_user returns None
    assert authenticate_user('coach_test_approval', 'coachSecure123') is None

    # 4. Admin approves the coach
    coach.approval_status = 'approved'
    coach.save()

    # 5. Attempt login after approval -> must succeed
    user_data, status, err = authenticate_user('coach_test_approval', 'coachSecure123', return_status=True)
    assert user_data is not None
    assert status == 'SUCCESS'
    assert user_data['username'] == 'coach_test_approval'
    assert user_data['role'] == 'university_admin'
    assert user_data['approval_status'] == 'approved'

    # 6. Admin rejects / revokes access -> must be blocked
    coach.approval_status = 'rejected'
    coach.admin_notes = 'Incomplete accreditation document'
    coach.save()

    user_data, status, err = authenticate_user('coach_test_approval', 'coachSecure123', return_status=True)
    assert user_data is None
    assert status == 'REJECTED'
    assert "Incomplete accreditation document" in err

    coach.delete()

def test_non_admin_non_coach_blocked():
    """Ensure regular viewers cannot log in through the portal."""
    User.objects(username='random_viewer').delete()
    viewer = User(
        username='random_viewer',
        email='viewer@test.com',
        password_hash=hash_password('pass123'),
        role='viewer',
        approval_status='approved',
        is_active=True
    )
    viewer.save()

    user_data, status, err = authenticate_user('random_viewer', 'pass123', return_status=True)
    assert user_data is None
    assert status == 'ROLE_DENIED'
    viewer.delete()
