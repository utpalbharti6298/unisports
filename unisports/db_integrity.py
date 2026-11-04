# What this file does:
# Self-healing database integrity and schema synchronization for MongoDB.
# Automatically detects and migrates legacy documents in MongoDB Atlas so new fields like approval_status
# are backfilled without data loss or missing query results.

import logging
from mongoengine.connection import get_db

logger = logging.getLogger(__name__)

def ensure_db_schema_integrity():
    """
    Scans MongoDB collections on application startup and guarantees that all documents
    have required lifecycle and security fields populated.
    This prevents NoSQL query misses when filtering on newly added fields.
    """
    try:
        db = get_db()
        if db is None:
            return

        # 1. Self-heal Tournaments: backfill missing approval_status to 'Approved'
        if 'tournaments' in db.list_collection_names():
            tourn_coll = db['tournaments']
            # Match any tournament that does not have approval_status set to 'Pending' or 'Rejected'
            t_res = tourn_coll.update_many(
                {
                    '$or': [
                        {'approval_status': {'$exists': False}},
                        {'approval_status': None},
                        {'approval_status': ''}
                    ]
                },
                {'$set': {'approval_status': 'Approved'}}
            )
            if t_res.modified_count > 0:
                print(f"[UniSports DB Integrity] Backfilled 'approval_status': 'Approved' for {t_res.modified_count} tournaments.")

        # 2. Self-heal Fixtures: backfill missing approval_status to 'Approved'
        if 'fixtures' in db.list_collection_names():
            fix_coll = db['fixtures']
            f_res = fix_coll.update_many(
                {
                    '$or': [
                        {'approval_status': {'$exists': False}},
                        {'approval_status': None},
                        {'approval_status': ''}
                    ]
                },
                {'$set': {'approval_status': 'Approved'}}
            )
            if f_res.modified_count > 0:
                print(f"[UniSports DB Integrity] Backfilled 'approval_status': 'Approved' for {f_res.modified_count} fixtures.")

        # 3. Self-heal Users: backfill missing approval_status to 'approved'
        if 'users' in db.list_collection_names():
            users_coll = db['users']
            u_res = users_coll.update_many(
                {
                    '$or': [
                        {'approval_status': {'$exists': False}},
                        {'approval_status': None},
                        {'approval_status': ''}
                    ]
                },
                {'$set': {'approval_status': 'approved'}}
            )
            if u_res.modified_count > 0:
                print(f"[UniSports DB Integrity] Backfilled 'approval_status': 'approved' for {u_res.modified_count} users.")

    except Exception as e:
        # Non-blocking log to ensure server boot is never halted by integrity check
        print(f"[UniSports DB Integrity WARNING] Schema integrity check note: {e}")
