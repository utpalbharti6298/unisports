import pytest
from bson import ObjectId
from accounts.models import User
from universities.models import University
from sports.models import Sport
from tournaments.models import Tournament, Fixture, TournamentUniversity, MedalEntry, MatchTeam
from analytics.models import RankingSnapshot, RankingEntry

def test_user_instantiation():
    user = User(
        username='testadmin',
        email='admin@unisports.edu',
        password_hash='hashed_secret',
        role='admin'
    )
    assert user.username == 'testadmin'
    assert user.role == 'admin'
    assert str(user) == 'testadmin [admin]'

def test_university_instantiation():
    uni = University(
        name='University of Allahabad',
        short_code='UOA',
        city='Prayagraj',
        state='Uttar Pradesh',
        established_year=1887,
        sports_enrolled=['Cricket', 'Football']
    )
    assert uni.short_code == 'UOA'
    assert len(uni.sports_enrolled) == 2
    assert 'UOA' in str(uni)

def test_sport_instantiation():
    sport = Sport(
        name='Cricket',
        code='CRIC',
        category='Team',
        win_points=2,
        draw_points=1,
        loss_points=0
    )
    assert sport.code == 'CRIC'
    assert sport.category == 'Team'

def test_tournament_with_embedded_medal_tally():
    u_id = ObjectId()
    entry = MedalEntry(
        university_id=u_id,
        university_name='University of Allahabad',
        university_code='UOA',
        gold=3,
        silver=2,
        bronze=1
    )
    tournament = Tournament(
        name='North Zone Inter-University Trophy',
        sport_name='Cricket',
        sport_code='CRIC',
        year=2025,
        host_university_name='University of Allahabad',
        status='Ongoing',
        medal_tally=[entry]
    )
    tournament.compute_medal_scores()
    # (3*5) + (2*3) + (1*1) = 15 + 6 + 1 = 22
    assert tournament.medal_tally[0].total_score == 22

def test_fixture_with_embedded_teams():
    team_a = MatchTeam(
        university_id=ObjectId(),
        name='University of Allahabad',
        short_code='UOA',
        score_display='245/6'
    )
    team_b = MatchTeam(
        university_id=ObjectId(),
        name='Banaras Hindu University',
        short_code='BHU',
        score_display='201 AO'
    )
    fixture = Fixture(
        tournament_id=ObjectId(),
        tournament_name='All India Trophy',
        sport_name='Cricket',
        round_name='Semifinal',
        team_a=team_a,
        team_b=team_b,
        status='Completed',
        winner_name='University of Allahabad'
    )
    assert fixture.team_a.short_code == 'UOA'
    assert fixture.winner_name == 'University of Allahabad'
    assert 'UOA vs BHU' in str(fixture)

def test_ranking_snapshot():
    entry = RankingEntry(
        rank=1,
        university_id=ObjectId(),
        university_name='University of Allahabad',
        university_code='UOA',
        gold=5,
        silver=3,
        bronze=2,
        total_points=36,
        matches_played=10,
        matches_won=8,
        win_percentage=80.0
    )
    snapshot = RankingSnapshot(
        year=2025,
        sport_name='All',
        rankings=[entry]
    )
    assert snapshot.year == 2025
    assert len(snapshot.rankings) == 1
    assert snapshot.rankings[0].win_percentage == 80.0
