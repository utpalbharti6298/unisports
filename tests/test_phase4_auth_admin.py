import pytest
from accounts.auth_service import hash_password, verify_password, authenticate_user
from accounts.models import User

def test_bcrypt_hashing():
    pw = "SuperSecret123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_authenticate_user_success():
    User.objects(username='coach_raj').delete()
    user = User(
        username='coach_raj',
        email='coach@uoa.ac.in',
        password_hash=hash_password('coachPass!'),
        role='university_admin',
        university_name='University of Allahabad'
    )
    user.save()

    auth_result = authenticate_user('coach_raj', 'coachPass!')
    assert auth_result is not None
    assert auth_result['username'] == 'coach_raj'
    assert auth_result['role'] == 'university_admin'
    assert auth_result['university_name'] == 'University of Allahabad'
    user.delete()

def test_authenticate_user_invalid():
    assert authenticate_user('nonexistent', 'any') is None
    assert authenticate_user('coach_raj', 'wrong') is None
