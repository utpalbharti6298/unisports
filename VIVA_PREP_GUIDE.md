# UniSports — Viva Examination Preparation Guide & Technical Defense

> **Final-Year BCA Project Defense**  
> **Student**: Utpal Bharti  
> **Supervisor**: Mr. Brijesh Rai  
> **Department**: Electronics & Communication, University of Allahabad  

---

## 1. Project Synopsis & Objectives

### Problem Statement
Traditional university athletic departments rely on fragmented spreadsheets, printed physical notices, or rigid relational databases. When querying multi-sport standings across dozens of colleges, relational SQL databases require multi-table JOINs across `Universities`, `Tournaments`, `Fixtures`, and `MedalTables`, causing latency spikes and query complexity.

### Proposed Solution
**UniSports** provides a unified, real-time sports intelligence platform using a **document-oriented NoSQL architecture (MongoDB)**. Embedded sub-documents store medal tallies and team scores directly within tournament records, delivering O(1) reads for leaderboards, dynamic points tables, and head-to-head analytical matrices.

---

## 2. Relational (SQL) vs Document (MongoDB) Defense

| Architectural Aspect | Relational Database (SQL / MySQL) | UniSports Architecture (MongoDB NoSQL) |
|:---|:---|:---|
| **Data Modeling** | Strict normalized tables with Foreign Keys | Rich Document schema with embedded sub-documents |
| **Tournament Standings** | Multi-table JOIN (`Tournaments` ⨝ `Matches` ⨝ `Teams` ⨝ `Medals`) | Single document read (`tournament.medal_tally`) in O(1) |
| **Schema Flexibility** | Rigid columns requiring DDL `ALTER TABLE` migrations | Dynamic schema adapting to varied sports scoring rules |
| **Horizontal Scaling** | Difficult sharding across relational constraints | Native horizontal scale-out and replica set support |
| **Aggregation Performance** | Expensive multi-level nested SQL queries | Native Aggregation Pipelines (`$unwind`, `$group`) |

---

## 3. Data Architecture: 6 Collections

1. **`users`**: Role-based access (`admin`, `university_admin`, `viewer`) with bcrypt password hashes.
2. **`universities`**: Institutional profiles, enrolled athletic disciplines list, contact information.
3. **`sports`**: Athletic disciplines with customized point weights (`win_points`, `draw_points`).
4. **`tournaments`**:
   - Contains embedded `TournamentUniversity` sub-documents.
   - Contains embedded `MedalEntry` sub-documents (`gold`, `silver`, `bronze`, `total_score`).
5. **`fixtures`**: Match records with embedded `MatchTeam` scores, round stages, winners, and dates.
6. **`rankings`**: Pre-computed cached leaderboard snapshots for sub-second retrieval.

---

## 4. Core Algorithms & Mathematical Formulations

### Algorithm 1: Overall University Ranking Score
- **Formula**:
  $$\text{Score} = (\text{Gold} \times 5) + (\text{Silver} \times 3) + (\text{Bronze} \times 1)$$
- **MongoDB Pipeline**:
  ```python
  pipeline = [
      {'$match': {'status': 'Completed', 'year': year}},
      {'$unwind': '$medal_tally'},
      {
          '$group': {
              '_id': '$medal_tally.university_id',
              'university_name': {'$first': '$medal_tally.university_name'},
              'gold': {'$sum': '$medal_tally.gold'},
              'silver': {'$sum': '$medal_tally.silver'},
              'bronze': {'$sum': '$medal_tally.bronze'}
          }
      },
      {
          '$project': {
              'total_points': {
                  '$add': [
                      {'$multiply': ['$gold', 5]},
                      {'$multiply': ['$silver', 3]},
                      {'$multiply': ['$bronze', 1]}
                  ]
              }
          }
      },
      {'$sort': {'total_points': -1, 'gold': -1}}
  ]
  ```

---

### Algorithm 2: Competitive Win Percentage
- **Formula**:
  $$\text{Win } \% = \left( \frac{\text{Matches Won}}{\text{Total Matches Played}} \right) \times 100$$
- **Edge-Case Protection**:
  ```python
  win_pct = round((matches_won / matches_played) * 100, 2) if matches_played > 0 else 0.0
  ```
  Guards against division-by-zero (`ZeroDivisionError`) when an institution has zero completed fixtures.

---

### Algorithm 3: League Points Table Accumulation
- **Standard Points System**: Win = 2 pts, Draw = 1 pt, Loss = 0 pts.
- **Sorting Logic**: Sorted by `points` descending, tie-broken by `won` descending.

---

### Algorithm 4: Head-to-Head (H2H) Comparative Matrix via Pandas
- Retrieves historical head-to-head fixtures between University A and University B.
- Loads records into a Pandas `DataFrame` for vectorized evaluation:
  - Vectorized win filter: `(df['winner_id'] == team_a_id).sum()`.
  - Computes victory differential: `team_a_wins - team_b_wins`.

---

## 5. Frequently Asked Viva Questions & Model Answers

### Q1: Why did you not use Django's built-in Admin panel?
> **Answer**: Django's built-in admin panel (`django.contrib.admin`) is tightly coupled to Django's relational SQL ORM (`django.db.models`). Because UniSports was deliberately engineered around a pure NoSQL MongoDB backend with MongoEngine, we built a dedicated, secure Custom Admin Control Center (`/accounts/admin-panel/`) utilizing bcrypt password verification and role-based session authorization.

### Q2: How are user sessions handled without a SQL database?
> **Answer**: We configured Django's signed cookies session backend:
> ```python
> SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
> ```
> Sessions are cryptographically signed using `SECRET_KEY` and stored securely in client cookies, eliminating any database dependency for session management.

### Q3: What is the purpose of `$unwind` in your ranking pipeline?
> **Answer**: In our `tournaments` collection, `medal_tally` is stored as an array of embedded sub-documents. The `$unwind` stage deconstructs the array field, outputting one document for each element in the array. This allows the subsequent `$group` stage to aggregate medals across multiple tournaments by university ID.

### Q4: How is the application deployed for free?
> **Answer**: The application is configured for:
> 1. **MongoDB Atlas M0**: 512MB free tier cloud MongoDB cluster.
> 2. **Render.com / PythonAnywhere**: Free tier web service.
> Connection string is managed via environment variable `MONGO_URI`. If offline or running tests, the system automatically falls back to `mongomock`.

---

## 6. Project Checklist for Examiner Presentation

- [x] Django 5 dev server running at `http://127.0.0.1:8000/` with live auto-reload.
- [x] All 7 universities and 4 tournaments seeded.
- [x] Interactive Chart.js analytics dashboard demonstrating 4 dynamic charts.
- [x] ReportLab PDF generation verified at `/tournaments/<id>/pdf/`.
- [x] 27 automated PyTest unit & integration tests passing (`pytest`).
- [x] Visual codebase knowledge graph generated in `graphify-out/graph.html`.
