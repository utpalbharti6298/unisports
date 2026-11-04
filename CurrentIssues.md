# Current Platform Issues & Permanent Resolutions

## Issue: Tournament List Disappearing / Database Missing Records [RESOLVED]
- **User Report:** *Tournament lsit fir khali ho gyi jabki mongodb atlas me wo database hai, ye database issue dobara nhi hona chahiye. Keep all the issue related to database at top priority*
- **Root-Cause Analysis:**
  1. **NoSQL Schema Evolution Discrepancy:**
     - In MongoDB Atlas, documents are schemaless BSON objects.
     - When the `approval_status` field was introduced with a model default of `'Approved'`, existing documents in MongoDB Atlas (`North Zone Inter-University Football League`, `Inter-University Basketball Championship`, `National Inter-University Athletics Meet`) were created prior to this field or without the `approval_status` key in their raw BSON storage.
     - When public views queried `Tournament.objects(approval_status='Approved')`, MongoDB translated this into `{ "approval_status": "Approved" }`.
     - In MongoDB's native query engine, `{ "approval_status": "Approved" }` **does not match** documents where the field does not exist! MongoDB does not read Python-level MongoEngine defaults during database query filtering.
     - As a result, MongoDB Atlas filtered out those 3 valid tournaments, returning only 1 single tournament on `/tournaments/`, causing the tournament calendar to appear empty for "Ongoing" and other filters.
     - The same issue affected homepage counts in [core/views.py](file:///c:/Users/UTPAL/Downloads/projectMINI/core/views.py), aggregate medal queries in [analytics/services.py](file:///c:/Users/UTPAL/Downloads/projectMINI/analytics/services.py), and fixture queries in [universities/views.py](file:///c:/Users/UTPAL/Downloads/projectMINI/universities/views.py).
  2. **User Collection Inconsistency:**
     - The legacy `admin` and `coach_uoa` users in Atlas also lacked the `approval_status` field.

- **Permanent Multi-Layered Resolution Applied:**
  1. **Self-Healing Database Auto-Migration Module ([unisports/db_integrity.py](file:///c:/Users/UTPAL/Downloads/projectMINI/unisports/db_integrity.py)):**
     - Runs automatically on application startup ([unisports/settings.py](file:///c:/Users/UTPAL/Downloads/projectMINI/unisports/settings.py)).
     - Automatically scans `tournaments`, `fixtures`, and `users` collections in MongoDB Atlas.
     - Safely backfills missing, null, or empty `approval_status` fields to `'Approved'` / `'approved'`, ensuring complete data consistency across all MongoDB Atlas documents without data loss.
  2. **Schema-Evolution Resilient Queries Across All Views & Services:**
     - [tournaments/views.py](file:///c:/Users/UTPAL/Downloads/projectMINI/tournaments/views.py): Public views query `Q(approval_status__nin=['Pending', 'Rejected'])` instead of strictly `Q(approval_status='Approved')`. This guarantees that legacy documents are never accidentally excluded.
     - [core/views.py](file:///c:/Users/UTPAL/Downloads/projectMINI/core/views.py): Metrics and recent tournaments count and display all sanctioned tournaments using `approval_status__nin=['Pending', 'Rejected']`.
     - [analytics/services.py](file:///c:/Users/UTPAL/Downloads/projectMINI/analytics/services.py): Leaderboard aggregation pipeline uses `approval_status: {'$nin': ['Pending', 'Rejected']}`, ensuring all completed tournaments are counted in national rankings.
     - [universities/views.py](file:///c:/Users/UTPAL/Downloads/projectMINI/universities/views.py): Fixture history uses `approval_status__nin=['Pending', 'Rejected']`.
  3. **Guaranteed Model Save Hooks ([tournaments/models.py](file:///c:/Users/UTPAL/Downloads/projectMINI/tournaments/models.py) & [accounts/models.py](file:///c:/Users/UTPAL/Downloads/projectMINI/accounts/models.py)):**
     - `Tournament.save()`, `Fixture.save()`, and `User.save()` now explicitly enforce that `approval_status` is always set before writing to BSON, preventing documents from ever being saved without lifecycle fields.
  4. **Database Seeder Protection ([seed_db.py](file:///c:/Users/UTPAL/Downloads/projectMINI/seed_db.py)):**
     - Explicitly populates `approval_status='Approved'` and `approval_status='approved'` for all seeded entities.

- **Verification:**
  - Verified live MongoDB Atlas documents: all 4 sanctioned tournaments (`Cricket`, `Football`, `Basketball`, `Athletics`) and 26 fixtures are fully accessible and properly categorized.
  - Verified that `Pending` proposals remain securely gated from unauthenticated public viewing.
  - Automated test suite passed with 100% success rate across all 78 tests.