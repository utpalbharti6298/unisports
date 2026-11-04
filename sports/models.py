# What this file does:
# Defines the Sport document model in MongoEngine, representing athletic disciplines, sport categories, and points rules.

from mongoengine import Document, fields
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

# Sport discipline document defining sport name, code, category, and tournament point allocations
class Sport(Document):
    """
    Sport collection defining athletic disciplines.
    """
    name = fields.StringField(required=True, unique=True, max_length=60) # e.g. 'Cricket', 'Football'
    code = fields.StringField(required=True, unique=True, max_length=15) # e.g. 'CRIC', 'FB'
    category = fields.StringField(required=True, choices=['Team', 'Individual'], default='Team')
    icon_name = fields.StringField(default='trophy')
    rules_summary = fields.StringField(default='')
    win_points = fields.IntField(default=2)
    draw_points = fields.IntField(default=1)
    loss_points = fields.IntField(default=0)
    created_at = fields.DateTimeField(default=now_utc)


    meta = {
        'collection': 'sports',
        'indexes': [
            'code',
            'category',
        ]
    }

    def __str__(self):
        return f"{self.name} [{self.category}]"
