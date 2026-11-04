# What this file does:
# Defines the University document model in MongoEngine, representing higher education institutions participating in sports championships.

from mongoengine import Document, fields
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

# University profile document storing institution name, short code, location, and enrolled sports
class University(Document):
    """
    University collection storing institutional athletic profiles.
    """
    name = fields.StringField(required=True, unique=True, max_length=150)
    short_code = fields.StringField(required=True, unique=True, max_length=10) # e.g. 'UOA', 'BHU', 'DU'
    city = fields.StringField(required=True, max_length=80)
    state = fields.StringField(required=True, max_length=80)
    established_year = fields.IntField()
    logo_url = fields.StringField(default='')
    sports_enrolled = fields.ListField(fields.StringField(), default=list)
    contact_email = fields.EmailField()
    website = fields.URLField()
    created_at = fields.DateTimeField(default=now_utc)


    meta = {
        'collection': 'universities',
        'indexes': [
            'short_code',
            'name',
            'state',
        ]
    }

    def __str__(self):
        return f"{self.name} ({self.short_code})"
