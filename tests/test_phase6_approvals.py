import pytest
import uuid
from bson import ObjectId
from accounts.models import User
from universities.models import University
from tournaments.models import Tournament, Fixture, MatchTeam, TournamentUniversity
from sports.models import Sport
from analytics.services import compute_tournament_points_table

def test_coach_submission_pending_and_admin_approval():
    uid = uuid.uuid4().hex[:6]
    sport = Sport(name=f"Sport_{uid}", code=f"S_{uid}", category="Individual", win_points=2, draw_points=0, loss_points=0)
    sport.save()

    uni_a = University(
        name=f"Uni_A_{uid}",
        short_code=f"UA_{uid}",
        city="Prayagraj",
        state="Uttar Pradesh",
        sports_enrolled=[sport.name]
    )
    uni_a.save()
    uni_b = University(
        name=f"Uni_B_{uid}",
        short_code=f"UB_{uid}",
        city="Varanasi",
        state="Uttar Pradesh",
        sports_enrolled=[sport.name]
    )
    uni_b.save()

    tournament = Tournament(
        name=f"Inter-Uni Tourn {uid}",
        sport_code=sport.code,
        sport_name=sport.name,
        year=2026,
        status="Ongoing",
        host_university_name=uni_a.name,
        participating_universities=[
            TournamentUniversity(university_id=uni_a.id, name=uni_a.name, short_code=uni_a.short_code),
            TournamentUniversity(university_id=uni_b.id, name=uni_b.name, short_code=uni_b.short_code)
        ]
    )
    tournament.save()

    # 1. Coach submits a match score -> fixture created with approval_status='Pending'
    fixture = Fixture(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        sport_name=tournament.sport_name,
        round_name="Quarter-Final",
        venue="Prayagraj",
        team_a=MatchTeam(university_id=uni_a.id, name=uni_a.name, short_code=uni_a.short_code, score_display="3"),
        team_b=MatchTeam(university_id=uni_b.id, name=uni_b.name, short_code=uni_b.short_code, score_display="1"),
        winner_university_id=uni_a.id,
        winner_name=uni_a.name,
        is_draw=False,
        status="Completed",
        approval_status="Pending",
        submitted_by="coach_uoa",
        submitted_by_university=uni_a.name
    )
    fixture.save()

    assert fixture.approval_status == "Pending"
    assert fixture.submitted_by == "coach_uoa"

    # 2. Points table must NOT count Pending matches
    table_pending = compute_tournament_points_table(str(tournament.id))
    for row in table_pending:
        assert row['played'] == 0
        assert row['points'] == 0

    # 3. Admin approves the fixture
    fixture.approval_status = "Approved"
    fixture.save()

    # 4. Now the fixture must register in points table
    table_approved = compute_tournament_points_table(str(tournament.id))
    assert len(table_approved) == 2
    top_team = table_approved[0]
    assert top_team['short_code'] == uni_a.short_code
    assert top_team['played'] == 1
    assert top_team['won'] == 1
    assert top_team['points'] == 2

    # Clean up test records
    fixture.delete()
    tournament.delete()
    uni_a.delete()
    uni_b.delete()
    sport.delete()

def test_admin_rejection_fixture():
    uid = uuid.uuid4().hex[:6]
    uni_c = University(name=f"Uni_C_{uid}", short_code=f"UC_{uid}", city="Lucknow", state="Uttar Pradesh")
    uni_c.save()
    uni_d = University(name=f"Uni_D_{uid}", short_code=f"UD_{uid}", city="Kanpur", state="Uttar Pradesh")
    uni_d.save()

    tourn = Tournament(
        name=f"Cup_{uid}",
        sport_code="CRIC",
        sport_name="Cricket",
        year=2026,
        host_university_name=uni_c.name,
        participating_universities=[
            TournamentUniversity(university_id=uni_c.id, name=uni_c.name, short_code=uni_c.short_code),
            TournamentUniversity(university_id=uni_d.id, name=uni_d.name, short_code=uni_d.short_code)
        ]
    )
    tourn.save()

    fixture = Fixture(
        tournament_id=tourn.id,
        tournament_name=tourn.name,
        sport_name="Cricket",
        team_a=MatchTeam(university_id=uni_c.id, name=uni_c.name, short_code=uni_c.short_code),
        team_b=MatchTeam(university_id=uni_d.id, name=uni_d.name, short_code=uni_d.short_code),
        approval_status="Pending",
        status="Completed"
    )
    fixture.save()

    # Reject fixture
    fixture.approval_status = "Rejected"
    fixture.save()

    reloaded = Fixture.objects.get(id=fixture.id)
    assert reloaded.approval_status == "Rejected"
    # Rejected matches are not counted in points table
    table = compute_tournament_points_table(str(tourn.id))
    for row in table:
        assert row['played'] == 0

    # Clean up
    fixture.delete()
    tourn.delete()
    uni_c.delete()
    uni_d.delete()
