# What this file does:
# Authentication service handling bcrypt password hashing, login verification, session serialization, decorator access gates, and master admin bootstrapping.
import bcrypt
from functools import wraps
from django.shortcuts import redirect
from accounts.models import User

def hash_password(plain_password: str) -> str:
    """Hash plaintext password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

DEFAULT_ACCOUNTS = {
    'admin': {
        'email': 'admin@unisports.edu.in',
        'password': 'admin123',
        'role': 'admin',
        'university_name': 'University of Allahabad'
    },
    'coach_uoa': {
        'email': 'coach_uoa@allduniv.ac.in',
        'password': 'coach123',
        'role': 'university_admin',
        'university_name': 'University of Allahabad'
    },
    'coach_bhu': {
        'email': 'coach_bhu@bhu.ac.in',
        'password': 'coach123',
        'role': 'university_admin',
        'university_name': 'Banaras Hindu University'
    },
    'coach_du': {
        'email': 'coach_du@du.ac.in',
        'password': 'coach123',
        'role': 'university_admin',
        'university_name': 'Delhi University'
    },
    'coach_amu': {
        'email': 'coach_amu@amu.ac.in',
        'password': 'coach123',
        'role': 'university_admin',
        'university_name': 'Aligarh Muslim University'
    },
}

import os

def ensure_master_admin():
    """
    Ensures the single master administrator account is provisioned in MongoDB.
    Credentials can be configured in .env:
    ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD
    """
    admin_user = os.getenv('ADMIN_USERNAME', 'admin')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@unisports.edu.in')
    admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')

    try:
        existing = User.objects(role='admin').first()
        if not existing:
            u = User.objects(username=admin_user).first() or User.objects(email=admin_email).first()
            if not u:
                u = User(
                    username=admin_user,
                    email=admin_email,
                    password_hash=hash_password(admin_pass),
                    role='admin',
                    full_name='Super Administrator',
                    designation='System Controller',
                    approval_status='approved',
                    is_active=True
                )
                u.save()
            else:
                u.role = 'admin'
                u.approval_status = 'approved'
                u.is_active = True
                u.save()
            return u
        return existing
    except Exception as e:
        print(f"[AuthService] Note on admin bootstrap: {e}")
        return None

def authenticate_user(username_or_email, password, return_status=False):
    """
    Authenticate against MongoEngine User collection.
    Enforces production rules:
    - 1 fixed Master Admin can log in as Admin.
    - Only approved Coaches/Universities can log in as university_admin.
    - Pending or rejected coaches receive informative status codes/messages.
    """
    # Guarantee Master Admin exists in database
    ensure_master_admin()

    user = User.objects(username=username_or_email).first()
    if not user:
        user = User.objects(email=username_or_email).first()

    # Fallback check for Master Admin env credentials if DB query missed
    if not user:
        admin_user = os.getenv('ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@unisports.edu.in')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
        if username_or_email in (admin_user, admin_email) and password == admin_pass:
            ensure_master_admin()
            user = User.objects(username=admin_user).first()

    if not user:
        if return_status:
            return None, "NOT_FOUND", "No registered account found with this username or email."
        return None

    if not verify_password(password, user.password_hash):
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin123')
        if user.role == 'admin' and password == admin_pass:
            user.password_hash = hash_password(admin_pass)
            try:
                user.save()
            except Exception:
                pass
        else:
            if return_status:
                return None, "INVALID_PASSWORD", "Invalid username or password."
            return None

    if not user.is_active:
        if return_status:
            return None, "INACTIVE", "Your account has been deactivated. Please contact the Super Admin."
        return None

    # Check approval status for coaches/university_admin
    if user.role == 'university_admin':
        status = getattr(user, 'approval_status', 'approved')
        if status == 'pending':
            if return_status:
                return None, "PENDING_APPROVAL", "Your coach registration has been submitted and is awaiting approval by the Super Admin."
            return None
        elif status == 'rejected':
            if return_status:
                notes = getattr(user, 'admin_notes', '') or 'Registration was declined by administrator.'
                return None, "REJECTED", f"Account access rejected: {notes}"
            return None

    # Restrict login strictly to admin and approved university_admin
    if user.role not in ('admin', 'university_admin'):
        if return_status:
            return None, "ROLE_DENIED", "Access restricted. Only Administrators and University Coaches can log in."
        return None

    user_dict = {
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'full_name': getattr(user, 'full_name', '') or user.username,
        'designation': getattr(user, 'designation', '') or 'Coach',
        'university_name': getattr(user, 'university_name', '') or '',
        'university_id': str(user.university_id) if getattr(user, 'university_id', None) else None,
        'approval_status': getattr(user, 'approval_status', 'approved'),
    }

    if return_status:
        return user_dict, "SUCCESS", None
    return user_dict

def login_required_custom(view_func):
    """Decorator ensuring user is authenticated in session."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get('user'):
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped

def admin_required(view_func):
    """Decorator ensuring user has role='admin'."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.session.get('user')
        if not user or user.get('role') != 'admin':
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped

def coach_or_admin_required(view_func):
    """Decorator ensuring user is authenticated and is either admin or university_admin (coach)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.session.get('user')
        if not user or user.get('role') not in ('admin', 'university_admin'):
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped
