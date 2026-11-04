# What this file does:
# Database seeder script that clears and populates MongoDB with initial test data: universities, sports disciplines, tournaments, match fixtures, and user accounts.

import os
import django
from datetime import datetime, timezone, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unisports.settings')
django.setup()

from accounts.models import User
from accounts.auth_service import hash_password
from universities.models import University
from sports.models import Sport
from tournaments.models import (
    Tournament, Fixture, TournamentUniversity, MedalEntry, MatchTeam
)
from analytics.models import RankingSnapshot, RankingEntry

def seed():
    print("Connecting to MongoDB and clearing old test documents...")
    try:
        User.objects.delete()
        University.objects.delete()
        Sport.objects.delete()
        Tournament.objects.delete()
        Fixture.objects.delete()
        RankingSnapshot.objects.delete()
    except Exception as e:
        print(f"Note on clearing existing collections: {e}")

    # 1. Admin User
    print("Creating default admin account...")
    admin_user = User(
        username='admin',
        email='admin@unisports.edu.in',
        password_hash=hash_password('admin123'),
        role='admin',
        approval_status='approved',
        university_name='University of Allahabad'
    )
    admin_user.save()
    print(f"Created Admin: {admin_user.username} / admin123")

    # 2. Universities (7 Premier Universities)
    print("Seeding universities...")
    universities_data = [
        {
            'name': 'University of Allahabad',
            'short_code': 'UOA',
            'city': 'Prayagraj',
            'state': 'Uttar Pradesh',
            'established_year': 1887,
            'website': 'https://allduniv.ac.in',
            'sports_enrolled': ['Cricket', 'Football', 'Basketball', 'Athletics', 'Badminton', 'Volleyball']
        },
        {
            'name': 'Banaras Hindu University',
            'short_code': 'BHU',
            'city': 'Varanasi',
            'state': 'Uttar Pradesh',
            'established_year': 1916,
            'website': 'https://bhu.ac.in',
            'sports_enrolled': ['Cricket', 'Football', 'Basketball', 'Volleyball', 'Athletics']
        },
        {
            'name': 'University of Delhi',
            'short_code': 'DU',
            'city': 'New Delhi',
            'state': 'Delhi',
            'established_year': 1922,
            'website': 'https://du.ac.in',
            'sports_enrolled': ['Cricket', 'Football', 'Basketball', 'Badminton', 'Athletics']
        },
        {
            'name': 'Aligarh Muslim University',
            'short_code': 'AMU',
            'city': 'Aligarh',
            'state': 'Uttar Pradesh',
            'established_year': 1875,
            'website': 'https://amu.ac.in',
            'sports_enrolled': ['Cricket', 'Football', 'Volleyball', 'Athletics']
        },
        {
            'name': 'University of Lucknow',
            'short_code': 'LU',
            'city': 'Lucknow',
            'state': 'Uttar Pradesh',
            'established_year': 1921,
            'website': 'https://lkouniv.ac.in',
            'sports_enrolled': ['Cricket', 'Football', 'Basketball', 'Badminton']
        },
        {
            'name': 'Jawaharlal Nehru University',
            'short_code': 'JNU',
            'city': 'New Delhi',
            'state': 'Delhi',
            'established_year': 1969,
            'website': 'https://jnu.ac.in',
            'sports_enrolled': ['Football', 'Badminton', 'Athletics']
        },
        {
            'name': 'Guru Nanak Dev University',
            'short_code': 'GNDU',
            'city': 'Amritsar',
            'state': 'Punjab',
            'established_year': 1969,
            'website': 'https://gndu.ac.in',
            'sports_enrolled': ['Cricket', 'Football', 'Basketball', 'Athletics', 'Volleyball']
        }
    ]

    uni_docs = {}
    for data in universities_data:
        uni = University(**data)
        uni.save()
        uni_docs[uni.short_code] = uni
    print(f"Seeded {len(uni_docs)} universities.")

    # 2.b University Coaches (Role: university_admin)
    print("Creating university coach accounts...")
    coaches_data = [
        ('coach_uoa', 'coach_uoa@allduniv.ac.in', 'coach123', 'UOA'),
        ('coach_bhu', 'coach_bhu@bhu.ac.in', 'coach123', 'BHU'),
        ('coach_du', 'coach_du@du.ac.in', 'coach123', 'DU'),
        ('coach_amu', 'coach_amu@amu.ac.in', 'coach123', 'AMU'),
    ]
    for c_user, c_email, c_pass, c_code in coaches_data:
        uni = uni_docs.get(c_code)
        if uni:
            coach_user = User(
                username=c_user,
                email=c_email,
                password_hash=hash_password(c_pass),
                role='university_admin',
                approval_status='approved',
                university_id=uni.id,
                university_name=uni.name
            )
            coach_user.save()
            print(f"Created Coach: {c_user} / {c_pass} [{uni.short_code}]")

    # 3. Sports Disciplines (6 Disciplines)
    print("Seeding sports...")
    sports_data = [
        {'name': 'Cricket', 'code': 'CRIC', 'category': 'Team', 'win_points': 2, 'draw_points': 1, 'loss_points': 0},
        {'name': 'Football', 'code': 'FB', 'category': 'Team', 'win_points': 3, 'draw_points': 1, 'loss_points': 0},
        {'name': 'Basketball', 'code': 'BB', 'category': 'Team', 'win_points': 2, 'draw_points': 0, 'loss_points': 0},
        {'name': 'Badminton', 'code': 'BADM', 'category': 'Individual', 'win_points': 2, 'draw_points': 0, 'loss_points': 0},
        {'name': 'Volleyball', 'code': 'VB', 'category': 'Team', 'win_points': 2, 'draw_points': 0, 'loss_points': 0},
        {'name': 'Athletics', 'code': 'ATHL', 'category': 'Individual', 'win_points': 5, 'draw_points': 0, 'loss_points': 0}
    ]

    for s_data in sports_data:
        sport = Sport(**s_data)
        sport.save()
    print(f"Seeded {len(sports_data)} sports.")

    # 4. Tournaments
    print("Seeding tournaments with embedded medal tallies...")
    # Cricket 2025
    cric_participants = [
        TournamentUniversity(university_id=uni_docs[code].id, name=uni_docs[code].name, short_code=code)
        for code in ['UOA', 'BHU', 'DU', 'AMU', 'GNDU', 'LU']
    ]
    cric_medals = [
        MedalEntry(university_id=uni_docs['UOA'].id, university_name=uni_docs['UOA'].name, university_code='UOA', gold=1, silver=0, bronze=0, total_score=5),
        MedalEntry(university_id=uni_docs['BHU'].id, university_name=uni_docs['BHU'].name, university_code='BHU', gold=0, silver=1, bronze=0, total_score=3),
        MedalEntry(university_id=uni_docs['DU'].id, university_name=uni_docs['DU'].name, university_code='DU', gold=0, silver=0, bronze=1, total_score=1),
    ]
    t_cricket = Tournament(
        name='All India Inter-University Cricket Trophy',
        sport_name='Cricket',
        sport_code='CRIC',
        year=2025,
        host_university_name='University of Allahabad',
        host_university_id=uni_docs['UOA'].id,
        venue='Madan Mohan Malviya Stadium, Prayagraj',
        status='Completed',
        approval_status='Approved',
        participating_universities=cric_participants,
        medal_tally=cric_medals
    )
    t_cricket.save()

    # Football 2025
    fb_participants = [
        TournamentUniversity(university_id=uni_docs[code].id, name=uni_docs[code].name, short_code=code)
        for code in ['DU', 'GNDU', 'UOA', 'JNU', 'AMU', 'BHU']
    ]
    fb_medals = [
        MedalEntry(university_id=uni_docs['GNDU'].id, university_name=uni_docs['GNDU'].name, university_code='GNDU', gold=1, silver=0, bronze=0, total_score=5),
        MedalEntry(university_id=uni_docs['DU'].id, university_name=uni_docs['DU'].name, university_code='DU', gold=0, silver=1, bronze=0, total_score=3),
        MedalEntry(university_id=uni_docs['UOA'].id, university_name=uni_docs['UOA'].name, university_code='UOA', gold=0, silver=0, bronze=1, total_score=1),
    ]
    t_football = Tournament(
        name='North Zone Inter-University Football League',
        sport_name='Football',
        sport_code='FB',
        year=2025,
        host_university_name='University of Delhi',
        host_university_id=uni_docs['DU'].id,
        venue='Rugby Stadium, North Campus, DU',
        status='Completed',
        approval_status='Approved',
        participating_universities=fb_participants,
        medal_tally=fb_medals
    )
    t_football.save()

    # Basketball 2026
    bb_participants = [
        TournamentUniversity(university_id=uni_docs[code].id, name=uni_docs[code].name, short_code=code)
        for code in ['UOA', 'BHU', 'DU', 'LU']
    ]
    t_basketball = Tournament(
        name='Inter-University Basketball Championship',
        sport_name='Basketball',
        sport_code='BB',
        year=2026,
        host_university_name='Banaras Hindu University',
        host_university_id=uni_docs['BHU'].id,
        venue='Shivaji Hall, BHU Varanasi',
        status='Ongoing',
        approval_status='Approved',
        participating_universities=bb_participants,
        medal_tally=[]
    )
    t_basketball.save()

    # Athletics 2026
    athl_participants = [
        TournamentUniversity(university_id=uni_docs[code].id, name=uni_docs[code].name, short_code=code)
        for code in ['GNDU', 'UOA', 'AMU', 'BHU', 'DU']
    ]
    t_athletics = Tournament(
        name='National Inter-University Athletics Meet',
        sport_name='Athletics',
        sport_code='ATHL',
        year=2026,
        host_university_name='Guru Nanak Dev University',
        host_university_id=uni_docs['GNDU'].id,
        venue='Guru Hargobind Stadium, Amritsar',
        status='Upcoming',
        approval_status='Approved',
        created_by='admin',
        created_by_role='admin',
        participating_universities=athl_participants,
        medal_tally=[]
    )
    t_athletics.save()
    print("Seeded 4 tournaments.")

    # 5. Fixtures (24+ Matches)
    print("Seeding fixtures across tournaments...")
    fixture_specs = [
        # Cricket Tournament Fixtures
        (t_cricket, 'Cricket', 'Group Stage', 'UOA', '238/5', 'BHU', '210 AO', 'UOA', 'UOA won by 28 runs', -120),
        (t_cricket, 'Cricket', 'Group Stage', 'DU', '198/7', 'AMU', '180/9', 'DU', 'DU won by 18 runs', -115),
        (t_cricket, 'Cricket', 'Group Stage', 'GNDU', '245/4', 'LU', '190 AO', 'GNDU', 'GNDU won by 55 runs', -110),
        (t_cricket, 'Cricket', 'Group Stage', 'UOA', '280/3', 'DU', '275/8', 'UOA', 'UOA won by 5 runs', -105),
        (t_cricket, 'Cricket', 'Group Stage', 'BHU', '215/6', 'GNDU', '210/9', 'BHU', 'BHU won by 5 runs', -100),
        (t_cricket, 'Cricket', 'Group Stage', 'AMU', '165/8', 'LU', '166/4', 'LU', 'LU won by 6 wickets', -95),
        (t_cricket, 'Cricket', 'Semifinal 1', 'UOA', '262/6', 'GNDU', '240 AO', 'UOA', 'UOA won by 22 runs', -80),
        (t_cricket, 'Cricket', 'Semifinal 2', 'BHU', '245/5', 'DU', '230/8', 'BHU', 'BHU won by 15 runs', -75),
        (t_cricket, 'Cricket', '3rd Place', 'DU', '210/4', 'GNDU', '180 AO', 'DU', 'DU won by 30 runs', -70),
        (t_cricket, 'Cricket', 'Final', 'UOA', '285/4', 'BHU', '255 AO', 'UOA', 'UOA won by 30 runs — Champions', -65),

        # Football Tournament Fixtures
        (t_football, 'Football', 'Group Stage', 'DU', '3', 'JNU', '1', 'DU', 'DU won 3-1', -150),
        (t_football, 'Football', 'Group Stage', 'GNDU', '2', 'AMU', '0', 'GNDU', 'GNDU won 2-0', -145),
        (t_football, 'Football', 'Group Stage', 'UOA', '2', 'BHU', '1', 'UOA', 'UOA won 2-1', -140),
        (t_football, 'Football', 'Group Stage', 'GNDU', '1', 'DU', '1', None, 'Match drawn 1-1', -135),
        (t_football, 'Football', 'Group Stage', 'JNU', '2', 'BHU', '0', 'JNU', 'JNU won 2-0', -130),
        (t_football, 'Football', 'Group Stage', 'UOA', '3', 'AMU', '0', 'UOA', 'UOA won 3-0', -125),
        (t_football, 'Football', 'Semifinal 1', 'GNDU', '2', 'UOA', '1', 'GNDU', 'GNDU won 2-1 (AET)', -100),
        (t_football, 'Football', 'Semifinal 2', 'DU', '4', 'JNU', '2', 'DU', 'DU won 4-2', -95),
        (t_football, 'Football', '3rd Place', 'UOA', '1', 'JNU', '0', 'UOA', 'UOA won 1-0 — Bronze Medal', -85),
        (t_football, 'Football', 'Final', 'GNDU', '2', 'DU', '1', 'GNDU', 'GNDU won 2-1 — Gold Medal', -80),

        # Basketball Tournament Fixtures (Ongoing Season 2026)
        (t_basketball, 'Basketball', 'Round 1', 'UOA', '78', 'BHU', '72', 'UOA', 'UOA won 78-72', -20),
        (t_basketball, 'Basketball', 'Round 1', 'DU', '85', 'LU', '66', 'DU', 'DU won 85-66', -15),
        (t_basketball, 'Basketball', 'Round 2', 'BHU', '80', 'LU', '65', 'BHU', 'BHU won 80-65', -10),
        (t_basketball, 'Basketball', 'Round 2', 'UOA', '74', 'DU', '79', 'DU', 'DU won 79-74', -5),
    ]

    base_time = datetime.now(timezone.utc)
    for spec in fixture_specs:
        tournament, sport, rnd, code_a, score_a, code_b, score_b, winner_code, summary, days_offset = spec
        uni_a = uni_docs[code_a]
        uni_b = uni_docs[code_b]
        winner_id = uni_docs[winner_code].id if winner_code else None
        winner_name = uni_docs[winner_code].name if winner_code else None
        is_draw = winner_code is None

        fixture = Fixture(
            tournament_id=tournament.id,
            tournament_name=tournament.name,
            sport_name=sport,
            round_name=rnd,
            match_date=base_time + timedelta(days=days_offset),
            venue=tournament.venue,
            team_a=MatchTeam(university_id=uni_a.id, name=uni_a.name, short_code=code_a, score_display=score_a),
            team_b=MatchTeam(university_id=uni_b.id, name=uni_b.name, short_code=code_b, score_display=score_b),
            status='Completed',
            winner_university_id=winner_id,
            winner_name=winner_name,
            is_draw=is_draw,
            result_summary=summary
        )
        fixture.save()

    print(f"Seeded {len(fixture_specs)} match fixtures.")

    # 6. Pre-computed 2025 Ranking Snapshot
    print("Generating 2025 Ranking Snapshot...")
    # Points: UOA (1G + 1B = 6 pts), GNDU (1G = 5 pts), DU (1S + 1B = 4 pts), BHU (1S = 3 pts)
    ranking_entries = [
        RankingEntry(rank=1, university_id=uni_docs['UOA'].id, university_name=uni_docs['UOA'].name, university_code='UOA', gold=1, silver=0, bronze=1, total_points=6, matches_played=8, matches_won=6, win_percentage=75.0),
        RankingEntry(rank=2, university_id=uni_docs['GNDU'].id, university_name=uni_docs['GNDU'].name, university_code='GNDU', gold=1, silver=0, bronze=0, total_points=5, matches_played=7, matches_won=5, win_percentage=71.43),
        RankingEntry(rank=3, university_id=uni_docs['DU'].id, university_name=uni_docs['DU'].name, university_code='DU', gold=0, silver=1, bronze=1, total_points=4, matches_played=8, matches_won=5, win_percentage=62.5),
        RankingEntry(rank=4, university_id=uni_docs['BHU'].id, university_name=uni_docs['BHU'].name, university_code='BHU', gold=0, silver=1, bronze=0, total_points=3, matches_played=7, matches_won=3, win_percentage=42.86),
        RankingEntry(rank=5, university_id=uni_docs['LU'].id, university_name=uni_docs['LU'].name, university_code='LU', gold=0, silver=0, bronze=0, total_points=0, matches_played=4, matches_won=1, win_percentage=25.0),
        RankingEntry(rank=6, university_id=uni_docs['AMU'].id, university_name=uni_docs['AMU'].name, university_code='AMU', gold=0, silver=0, bronze=0, total_points=0, matches_played=4, matches_won=0, win_percentage=0.0),
        RankingEntry(rank=7, university_id=uni_docs['JNU'].id, university_name=uni_docs['JNU'].name, university_code='JNU', gold=0, silver=0, bronze=0, total_points=0, matches_played=4, matches_won=1, win_percentage=25.0),
    ]
    snapshot = RankingSnapshot(
        year=2025,
        sport_name='All',
        rankings=ranking_entries
    )
    snapshot.save()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
