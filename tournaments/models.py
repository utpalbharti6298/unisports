# What this file does:
# Defines Tournament, Fixture, MatchTeam, MedalEntry, and TournamentUniversity document models in MongoEngine for sports championships and match schedules.

from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

# Embedded reference for university participating in a tournament
class TournamentUniversity(EmbeddedDocument):
    """Embedded reference for university participating in a tournament."""
    university_id = fields.ObjectIdField(required=True)
    name = fields.StringField(required=True)
    short_code = fields.StringField(required=True)

class MedalEntry(EmbeddedDocument):
    """Embedded medal tally row eliminating SQL JOINs."""
    university_id = fields.ObjectIdField(required=True)
    university_name = fields.StringField(required=True)
    university_code = fields.StringField(required=True)
    gold = fields.IntField(default=0)
    silver = fields.IntField(default=0)
    bronze = fields.IntField(default=0)
    total_score = fields.IntField(default=0) # (G * 5) + (S * 3) + (B * 1)

class Tournament(Document):
    """
    Tournament collection storing inter-university competitions.
    """
    name = fields.StringField(required=True, max_length=150)
    sport_name = fields.StringField(required=True) # e.g. 'Cricket'
    sport_code = fields.StringField(required=True)
    year = fields.IntField(required=True)
    host_university_name = fields.StringField(required=True)
    host_university_id = fields.ObjectIdField(null=True)
    venue = fields.StringField(default='')
    status = fields.StringField(
        required=True,
        default='Upcoming',
        choices=['Upcoming', 'Ongoing', 'Completed']
    )
    approval_status = fields.StringField(
        required=True,
        default='Approved',
        choices=['Approved', 'Pending', 'Rejected']
    )
    created_by = fields.StringField(default='admin')
    created_by_role = fields.StringField(default='admin') # 'admin' or 'university_admin'
    approved_by = fields.StringField(default='')
    approved_at = fields.DateTimeField(null=True)
    participating_universities = fields.EmbeddedDocumentListField(TournamentUniversity, default=list)
    medal_tally = fields.EmbeddedDocumentListField(MedalEntry, default=list)
    created_at = fields.DateTimeField(default=now_utc)


    meta = {
        'collection': 'tournaments',
        'indexes': [
            'year',
            'sport_code',
            'status',
            'approval_status',
        ]
    }

    def save(self, *args, **kwargs):
        """Ensures approval_status is always explicitly set before persisting to BSON."""
        if not getattr(self, 'approval_status', None):
            self.approval_status = 'Approved'
        return super().save(*args, **kwargs)


    @property
    def university_count(self):
        """Returns the count of participating universities, falling back to fixtures if list is empty."""
        count = len(self.participating_universities)
        if count > 0:
            return count
        try:
            fixtures = Fixture.objects(tournament_id=self.id)
            seen = set()
            for f in fixtures:
                if f.team_a and f.team_a.university_id:
                    seen.add(str(f.team_a.university_id))
                if f.team_b and f.team_b.university_id:
                    seen.add(str(f.team_b.university_id))
            return len(seen)
        except Exception:
            return 0

    def sync_participating_universities(self, save=True):
        """Discovers any universities playing in tournament fixtures not yet registered in participating_universities."""
        try:
            fixtures = Fixture.objects(tournament_id=self.id)
            existing_ids = {str(u.university_id) for u in self.participating_universities}
            updated = False
            for f in fixtures:
                for team in [f.team_a, f.team_b]:
                    if team and team.university_id and str(team.university_id) not in existing_ids:
                        self.participating_universities.append(
                            TournamentUniversity(
                                university_id=team.university_id,
                                name=team.name,
                                short_code=team.short_code
                            )
                        )
                        existing_ids.add(str(team.university_id))
                        updated = True
            if updated and save:
                self.save()
            return updated
        except Exception:
            return False

    def compute_medal_scores(self):
        """Calculates (G*5)+(S*3)+(B*1) for all embedded medal entries."""
        for entry in self.medal_tally:
            entry.total_score = (entry.gold * 5) + (entry.silver * 3) + (entry.bronze * 1)

    def __str__(self):
        return f"{self.name} ({self.year}) [{self.status}]"


class MatchTeam(EmbeddedDocument):
    """Embedded team match result and score."""
    university_id = fields.ObjectIdField(required=True)
    name = fields.StringField(required=True)
    short_code = fields.StringField(required=True)
    score_display = fields.StringField(default='-') # e.g. "245/6", "3", "78"
    points = fields.IntField(default=0)


class Fixture(Document):
    """
    Fixture/Match collection storing games between universities.
    """
    tournament_id = fields.ObjectIdField(required=True)
    tournament_name = fields.StringField(required=True)
    sport_name = fields.StringField(required=True)
    round_name = fields.StringField(default='Group Stage') # 'Quarterfinal', 'Semifinal', 'Final'
    match_date = fields.DateTimeField(default=now_utc)
    venue = fields.StringField(default='')
    
    team_a = fields.EmbeddedDocumentField(MatchTeam, required=True)
    team_b = fields.EmbeddedDocumentField(MatchTeam, required=True)
    
    status = fields.StringField(
        required=True,
        default='Scheduled',
        choices=['Scheduled', 'Live', 'Completed']
    )
    approval_status = fields.StringField(
        required=True,
        default='Approved',
        choices=['Approved', 'Pending', 'Rejected']
    )
    submitted_by = fields.StringField(default='admin')
    submitted_by_university = fields.StringField(default='')
    winner_university_id = fields.ObjectIdField(null=True)
    winner_name = fields.StringField(null=True)
    is_draw = fields.BooleanField(default=False)
    result_summary = fields.StringField(default='')
    created_at = fields.DateTimeField(default=now_utc)

    meta = {
        'collection': 'fixtures',
        'indexes': [
            'tournament_id',
            'sport_name',
            'status',
            'approval_status',
            'match_date',
            ('tournament_id', 'approval_status', 'match_date'),
            ('approval_status', 'created_at'),
        ]
    }

    def clean(self):
        """Model-level validation ensuring team_a and team_b are distinct."""
        if self.team_a and self.team_b:
            if str(self.team_a.university_id) == str(self.team_b.university_id):
                from mongoengine import ValidationError
                raise ValidationError("A university cannot play a match against itself.")

    def save(self, *args, **kwargs):
        """Saves fixture and automatically syncs team_a and team_b into tournament participating_universities."""
        if not getattr(self, 'approval_status', None):
            self.approval_status = 'Approved'
        self.clean()
        super().save(*args, **kwargs)
        try:
            tournament = Tournament.objects(id=self.tournament_id).first()
            if tournament:
                existing_ids = {str(u.university_id) for u in tournament.participating_universities}
                updated = False
                for team in [self.team_a, self.team_b]:
                    if team and team.university_id and str(team.university_id) not in existing_ids:
                        tournament.participating_universities.append(
                            TournamentUniversity(
                                university_id=team.university_id,
                                name=team.name,
                                short_code=team.short_code
                            )
                        )
                        existing_ids.add(str(team.university_id))
                        updated = True
                if updated:
                    tournament.save()
        except Exception:
            pass

    def __str__(self):
        return f"{self.team_a.short_code} vs {self.team_b.short_code} ({self.sport_name}) [{self.status}]"
