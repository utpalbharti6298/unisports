import pytest
from bson import ObjectId
from unittest.mock import MagicMock, patch
from analytics.services import (
    calculate_ranking_scores,
    calculate_win_percentage,
    compute_tournament_points_table,
    compute_h2h_matrix
)
from tournaments.models import Tournament, MedalEntry

def test_algorithm1_ranking_score_calculation():
    """Verify (G*5)+(S*3)+(B*1) ranking score computation."""
    u1_id = ObjectId()
    u2_id = ObjectId()

    mock_aggregate_result = [
        {
            '_id': u1_id,
            'university_name': 'University of Allahabad',
            'university_code': 'UOA',
            'gold': 4,
            'silver': 2,
            'bronze': 1,
            'total_points': (4 * 5) + (2 * 3) + (1 * 1) # 27
        },
        {
            '_id': u2_id,
            'university_name': 'Banaras Hindu University',
            'university_code': 'BHU',
            'gold': 2,
            'silver': 3,
            'bronze': 4,
            'total_points': (2 * 5) + (3 * 3) + (4 * 1) # 23
        }
    ]

    with patch.object(Tournament, '_get_collection') as mock_coll:
        mock_coll.return_value.aggregate.return_value = mock_aggregate_result
        ranked = calculate_ranking_scores(year=2025)

        assert len(ranked) == 2
        assert ranked[0]['rank'] == 1
        assert ranked[0]['university_code'] == 'UOA'
        assert ranked[0]['total_points'] == 27
        assert ranked[1]['rank'] == 2
        assert ranked[1]['total_points'] == 23

def test_algorithm2_win_percentage_division_by_zero_guard():
    """Verify 0.0% is safely returned when zero matches played."""
    u_id = ObjectId()
    with patch('tournaments.models.Fixture._get_collection') as mock_coll:
        mock_coll.return_value.find.return_value = []
        result = calculate_win_percentage(u_id)
        assert result['played'] == 0
        assert result['won'] == 0
        assert result['win_percentage'] == 0.0

def test_algorithm2_win_percentage_accuracy():
    """Verify accurate win percentage calculation."""
    u_id = ObjectId()
    mock_fixtures = [
        {'is_draw': False, 'winner_university_id': u_id},
        {'is_draw': False, 'winner_university_id': u_id},
        {'is_draw': False, 'winner_university_id': ObjectId()},
        {'is_draw': True, 'winner_university_id': None},
    ]
    with patch('tournaments.models.Fixture._get_collection') as mock_coll:
        mock_coll.return_value.find.return_value = mock_fixtures
        result = calculate_win_percentage(u_id)
        # 4 played, 2 won -> 50.0%
        assert result['played'] == 4
        assert result['won'] == 2
        assert result['drawn'] == 1
        assert result['lost'] == 1
        assert result['win_percentage'] == 50.0

def test_algorithm3_points_table_computation():
    """Verify league points: win=2, draw=1, loss=0."""
    t_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()

    mock_fixtures = [
        {
            'team_a': {'university_id': u1_id, 'name': 'UOA', 'short_code': 'UOA'},
            'team_b': {'university_id': u2_id, 'name': 'BHU', 'short_code': 'BHU'},
            'is_draw': False,
            'winner_university_id': u1_id
        },
        {
            'team_a': {'university_id': u1_id, 'name': 'UOA', 'short_code': 'UOA'},
            'team_b': {'university_id': u2_id, 'name': 'BHU', 'short_code': 'BHU'},
            'is_draw': True,
            'winner_university_id': None
        }
    ]

    with patch('tournaments.models.Fixture._get_collection') as mock_coll:
        mock_coll.return_value.find.return_value = mock_fixtures
        table = compute_tournament_points_table(t_id)

        assert len(table) == 2
        # UOA won 1, drew 1 -> 3 points
        assert table[0]['short_code'] == 'UOA'
        assert table[0]['points'] == 3
        assert table[0]['won'] == 1
        assert table[0]['drawn'] == 1
        assert table[0]['rank'] == 1

        # BHU lost 1, drew 1 -> 1 point
        assert table[1]['short_code'] == 'BHU'
        assert table[1]['points'] == 1
        assert table[1]['rank'] == 2

def test_algorithm4_h2h_matrix():
    """Verify Head-to-Head analytics and differentials."""
    u1_id = ObjectId()
    u2_id = ObjectId()

    mock_matches = [
        {
            '_id': ObjectId(),
            'sport_name': 'Cricket',
            'round_name': 'Final',
            'tournament_name': 'Championship 2025',
            'match_date': None,
            'team_a': {'name': 'UOA', 'short_code': 'UOA', 'score_display': '210/4'},
            'team_b': {'name': 'BHU', 'short_code': 'BHU', 'score_display': '195/8'},
            'is_draw': False,
            'winner_university_id': u1_id,
            'winner_name': 'UOA'
        },
        {
            '_id': ObjectId(),
            'sport_name': 'Cricket',
            'round_name': 'League',
            'tournament_name': 'Championship 2024',
            'match_date': None,
            'team_a': {'name': 'UOA', 'short_code': 'UOA', 'score_display': '150 AO'},
            'team_b': {'name': 'BHU', 'short_code': 'BHU', 'score_display': '152/3'},
            'is_draw': False,
            'winner_university_id': u2_id,
            'winner_name': 'BHU'
        },
        {
            '_id': ObjectId(),
            'sport_name': 'Cricket',
            'round_name': 'Semifinal',
            'tournament_name': 'Championship 2023',
            'match_date': None,
            'team_a': {'name': 'UOA', 'short_code': 'UOA', 'score_display': '180/6'},
            'team_b': {'name': 'BHU', 'short_code': 'BHU', 'score_display': '160/9'},
            'is_draw': False,
            'winner_university_id': u1_id,
            'winner_name': 'UOA'
        }
    ]

    with patch('tournaments.models.Fixture._get_collection') as mock_coll:
        mock_coll.return_value.find.return_value.sort.return_value = mock_matches
        matrix = compute_h2h_matrix(u1_id, u2_id, sport_name='Cricket')

        assert matrix['total_matches'] == 3
        assert matrix['team_a_wins'] == 2
        assert matrix['team_b_wins'] == 1
        assert matrix['draws'] == 0
        assert matrix['differential'] == 1
