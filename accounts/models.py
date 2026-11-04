# What this file does:
# Defines the User document schema for MongoEngine with role-based permissions (admin, university_admin/coach, viewer) and approval tracking.

from mongoengine import Document, fields
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

# User database document storing login credentials, roles, institutional affiliation, and approval lifecycle
class User(Document):
    """
    User collection for role-based authentication.
    Roles: 'admin', 'university_admin', 'viewer'
    """
    username = fields.StringField(required=True, unique=True, max_length=50)
    email = fields.EmailField(required=True, unique=True)
    password_hash = fields.StringField(required=True)
    role = fields.StringField(
        required=True,
        default='viewer',
        choices=['admin', 'university_admin', 'viewer']
    )
    full_name = fields.StringField(max_length=100, default='')
    phone = fields.StringField(max_length=25, default='')
    designation = fields.StringField(max_length=100, default='Coach / Sports Director')
    university_id = fields.ObjectIdField(null=True)
    university_name = fields.StringField(null=True)
    approval_status = fields.StringField(
        required=True,
        default='approved',
        choices=['pending', 'approved', 'rejected']
    )
    is_active = fields.BooleanField(default=True)
    created_at = fields.DateTimeField(default=now_utc)
    approved_at = fields.DateTimeField(null=True)
    admin_notes = fields.StringField(null=True)


    meta = {
        'collection': 'users',
        'indexes': [
            'username',
            'email',
            'role',
        ]
    }

    def save(self, *args, **kwargs):
        """Ensures approval_status is always set before saving."""
        if not getattr(self, 'approval_status', None):
            self.approval_status = 'approved'
        return super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.username} [{self.role}]"
