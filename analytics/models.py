# What this file does:
# Defines RankingSnapshot and RankingEntry document models in MongoEngine for caching precomputed annual leaderboards and medal statistics.

from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

# Calculated annual ranking entry for an individual institution
class RankingEntry(EmbeddedDocument):
    """Calculated annual ranking entry for an institution."""
    rank = fields.IntField(required=True)
    university_id = fields.ObjectIdField(required=True)
    university_name = fields.StringField(required=True)
    university_code = fields.StringField(required=True)
    gold = fields.IntField(default=0)
    silver = fields.IntField(default=0)
    bronze = fields.IntField(default=0)
    total_points = fields.IntField(default=0) # (G*5) + (S*3) + (B*1)
    matches_played = fields.IntField(default=0)
    matches_won = fields.IntField(default=0)
    win_percentage = fields.FloatField(default=0.0)


class RankingSnapshot(Document):
    """
    Cached leaderboard snapshot recomputed via aggregation pipelines.
    """
    year = fields.IntField(required=True)
    sport_name = fields.StringField(default='All') # 'All' or specific sport name
    rankings = fields.EmbeddedDocumentListField(RankingEntry, default=list)
    generated_at = fields.DateTimeField(default=now_utc)


    meta = {
        'collection': 'rankings',
        'indexes': [
            'year',
            'sport_name',
        ]
    }

    def __str__(self):
        return f"Ranking Snapshot: {self.sport_name} ({self.year}) — {len(self.rankings)} Universities"
