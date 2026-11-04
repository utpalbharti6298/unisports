# What this file does:
# Core statistical analytics engine implementing algorithms for annual leaderboard rankings, university win percentages, tournament round-robin points tables, and Pandas head-to-head matchup comparisons.

import pandas as pd
from bson import ObjectId
from tournaments.models import Tournament, Fixture
from universities.models import University
from analytics.models import RankingSnapshot, RankingEntry

def calculate_ranking_scores(year=None, sport_name=None):
    """
    Algorithm 1: Ranking Score Calculation
    Score = (Gold * 5) + (Silver * 3) + (Bronze * 1)
    Aggregates medal tallies across all completed tournaments for the given year/sport.
    Returns sorted list of dictionaries with rank.
    """
    match_query = {'status': 'Completed', 'approval_status': {'$nin': ['Pending', 'Rejected']}}
    if year:
        match_query['year'] = int(year)
    if sport_name and sport_name != 'All':
        match_query['sport_name'] = sport_name

    pipeline = [
        {'$match': match_query},
        {'$unwind': '$medal_tally'},
        {
            '$group': {
                '_id': '$medal_tally.university_id',
                'university_name': {'$first': '$medal_tally.university_name'},
                'university_code': {'$first': '$medal_tally.university_code'},
                'gold': {'$sum': '$medal_tally.gold'},
                'silver': {'$sum': '$medal_tally.silver'},
                'bronze': {'$sum': '$medal_tally.bronze'},
            }
        },
        {
            '$project': {
                'university_name': 1,
                'university_code': 1,
                'gold': 1,
                'silver': 1,
                'bronze': 1,
                'total_points': {
                    '$add': [
                        {'$multiply': ['$gold', 5]},
                        {'$multiply': ['$silver', 3]},
                        {'$multiply': ['$bronze', 1]}
                    ]
                }
            }
        },
        {'$sort': {'total_points': -1, 'gold': -1, 'silver': -1}}
    ]

    try:
        results = list(Tournament._get_collection().aggregate(pipeline))
    except Exception:
        # Python fallback when DB is offline or in memory testing
        tallies = {}
        query = Tournament.objects(**match_query) if hasattr(Tournament.objects, 'filter') else []
        for t in query:
            for m in t.medal_tally:
                uid = str(m.university_id)
                if uid not in tallies:
                    tallies[uid] = {
                        '_id': m.university_id,
                        'university_name': m.university_name,
                        'university_code': m.university_code,
                        'gold': 0, 'silver': 0, 'bronze': 0
                    }
                tallies[uid]['gold'] += m.gold
                tallies[uid]['silver'] += m.silver
                tallies[uid]['bronze'] += m.bronze

        results = []
        for uid, d in tallies.items():
            pts = (d['gold'] * 5) + (d['silver'] * 3) + (d['bronze'] * 1)
            d['total_points'] = pts
            results.append(d)
        results.sort(key=lambda x: (x['total_points'], x['gold'], x['silver']), reverse=True)

    # Assign sequential ranks and exposed university_id
    ranked_output = []
    for idx, row in enumerate(results, start=1):
        row['rank'] = idx
        row['university_id'] = str(row.get('_id', ''))
        ranked_output.append(row)


    return ranked_output


def calculate_win_percentage(university_id, year=None, sport_name=None):
    """
    Algorithm 2: Win Percentage Calculator
    Win % = (Total Wins / Total Played) * 100
    Includes division-by-zero protection.
    """
    u_id = ObjectId(university_id) if isinstance(university_id, str) else university_id

    # Filter completed matches where this university participated
    matches_played = 0
    matches_won = 0
    matches_lost = 0
    matches_drawn = 0

    try:
        fixtures_coll = Fixture._get_collection()
        query = {
            'status': 'Completed',
            'approval_status': {'$nin': ['Pending', 'Rejected']},
            '$or': [{'team_a.university_id': u_id}, {'team_b.university_id': u_id}]
        }
        if sport_name and sport_name != 'All':
            query['sport_name'] = sport_name

        cursor = fixtures_coll.find(query)

        for fix in cursor:
            matches_played += 1
            if fix.get('is_draw'):
                matches_drawn += 1
            elif str(fix.get('winner_university_id', '')) == str(u_id):
                matches_won += 1
            else:
                matches_lost += 1
    except Exception:
        pass

    # Division-by-zero safe guard
    win_pct = round((matches_won / matches_played) * 100, 2) if matches_played > 0 else 0.0

    return {
        'played': matches_played,
        'won': matches_won,
        'lost': matches_lost,
        'drawn': matches_drawn,
        'win_percentage': win_pct
    }


def compute_tournament_points_table(tournament_id):
    """
    Algorithm 3: Tournament Points Table Generator
    Standard League scoring: Win = 2 pts, Draw = 1 pt, Loss = 0 pts.
    Sorts by Points desc -> Wins desc.
    """
    t_id = ObjectId(tournament_id) if isinstance(tournament_id, str) else tournament_id

    points_map = {}

    try:
        t_doc = Tournament._get_collection().find_one({'_id': t_id})
        if t_doc and 'participating_universities' in t_doc:
            for uni in t_doc['participating_universities']:
                uid_str = str(uni['university_id'])
                points_map[uid_str] = {
                    'university_id': uni['university_id'],
                    'name': uni.get('name', 'Unknown'),
                    'short_code': uni.get('short_code', 'UNI'),
                    'played': 0,
                    'won': 0,
                    'drawn': 0,
                    'lost': 0,
                    'points': 0
                }
    except Exception:
        pass

    try:
        fixtures = Fixture._get_collection().find({
            'tournament_id': t_id,
            'status': 'Completed',
            'approval_status': {'$nin': ['Pending', 'Rejected']}
        })
        for fix in fixtures:
            try:
                team_a = fix.get('team_a') or {}
                team_b = fix.get('team_b') or {}
                if not team_a or not team_b:
                    continue

                uid_a = str(team_a.get('university_id', ''))
                uid_b = str(team_b.get('university_id', ''))
                if not uid_a or not uid_b:
                    continue

                for uid in (uid_a, uid_b):
                    if uid not in points_map:
                        t_obj = team_a if uid == uid_a else team_b
                        points_map[uid] = {
                            'university_id': ObjectId(uid) if ObjectId.is_valid(uid) else uid,
                            'name': t_obj.get('name', 'Unknown'),
                            'short_code': t_obj.get('short_code', 'UNI'),
                            'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'points': 0
                        }
                    points_map[uid]['played'] += 1

                if fix.get('is_draw'):
                    points_map[uid_a]['drawn'] += 1
                    points_map[uid_b]['drawn'] += 1
                    points_map[uid_a]['points'] += 1
                    points_map[uid_b]['points'] += 1
                else:
                    winner_id = str(fix.get('winner_university_id', ''))
                    if winner_id == uid_a:
                        points_map[uid_a]['won'] += 1
                        points_map[uid_a]['points'] += 2
                        points_map[uid_b]['lost'] += 1
                    elif winner_id == uid_b:
                        points_map[uid_b]['won'] += 1
                        points_map[uid_b]['points'] += 2
                        points_map[uid_a]['lost'] += 1
            except Exception:
                continue
    except Exception:
        pass

    table = list(points_map.values())
    table.sort(key=lambda x: (x['points'], x['won']), reverse=True)

    for idx, item in enumerate(table, start=1):
        item['rank'] = idx

    return table


def compute_h2h_matrix(university_a_id, university_b_id, sport_name=None):
    """
    Algorithm 4: Head-to-Head Comparative Matrix via Pandas
    Aggregates historical matchups between two universities and generates comparative metrics.
    """
    uid_a = ObjectId(university_a_id) if isinstance(university_a_id, str) else university_a_id
    uid_b = ObjectId(university_b_id) if isinstance(university_b_id, str) else university_b_id

    query = {
        'status': 'Completed',
        'approval_status': {'$nin': ['Pending', 'Rejected']},
        '$or': [
            {'team_a.university_id': uid_a, 'team_b.university_id': uid_b},
            {'team_a.university_id': uid_b, 'team_b.university_id': uid_a}
        ]
    }

    if sport_name and sport_name != 'All':
        query['sport_name'] = sport_name

    raw_matches = []
    try:
        cursor = Fixture._get_collection().find(query).sort('match_date', -1)
        for m in cursor:
            try:
                team_a = m.get('team_a') or {}
                team_b = m.get('team_b') or {}
                raw_matches.append({
                    'id': str(m['_id']),
                    'sport': m.get('sport_name', ''),
                    'round': m.get('round_name', ''),
                    'tournament': m.get('tournament_name', ''),
                    'date': m.get('match_date'),
                    'team_a_name': team_a.get('name', ''),
                    'team_a_code': team_a.get('short_code', ''),
                    'team_a_score': team_a.get('score_display', '-'),
                    'team_b_name': team_b.get('name', ''),
                    'team_b_code': team_b.get('short_code', ''),
                    'team_b_score': team_b.get('score_display', '-'),
                    'is_draw': m.get('is_draw', False),
                    'winner_id': str(m.get('winner_university_id', '')),
                    'winner_name': m.get('winner_name', '')
                })
            except Exception:
                continue
    except Exception:
        pass

    if not raw_matches:
        return {
            'total_matches': 0,
            'team_a_wins': 0,
            'team_b_wins': 0,
            'draws': 0,
            'matches': [],
            'differential': 0
        }

    df = pd.DataFrame(raw_matches)
    str_uid_a = str(uid_a)
    str_uid_b = str(uid_b)

    team_a_wins = int((df['winner_id'] == str_uid_a).sum())
    team_b_wins = int((df['winner_id'] == str_uid_b).sum())
    draws = int(df['is_draw'].sum())
    total_matches = len(df)
    differential = team_a_wins - team_b_wins

    return {
        'total_matches': total_matches,
        'team_a_wins': team_a_wins,
        'team_b_wins': team_b_wins,
        'draws': draws,
        'differential': differential,
        'matches': raw_matches
    }
