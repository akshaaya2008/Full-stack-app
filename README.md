# OODA SIM — Military Strategy Training Simulator

A full-stack military decision-making simulator built on the OODA Loop framework (Observe → Orient → Decide → Act), developed by Colonel John Boyd.

## Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Django 4.2 + Django REST Framework  |
| Database  | PostgreSQL 15                       |
| Frontend  | React 18 + Vite                     |
| Container | Docker + Docker Compose             |

---

## Quick Start (Docker — Recommended)

```bash
# Clone / navigate to project
cd ooda_simulator

# Launch everything
docker-compose up --build

# App available at:
#   Frontend: http://localhost:5173
#   Backend API: http://localhost:8000/api
#   Django Admin: http://localhost:8000/admin
```

The database is seeded automatically with 4 classified scenarios across Land, Sea, Cyber, and Hybrid theaters.

---

## Manual Setup (Without Docker)

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Node.js 20+

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create PostgreSQL database
createdb ooda_sim

# Run migrations
python manage.py migrate

# Load scenario fixtures
python manage.py loaddata ooda_app/fixtures/scenarios.json

# Create superuser (optional, for Django admin)
python manage.py createsuperuser

# Start server
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
ooda_simulator/
├── backend/
│   ├── ooda_project/          # Django project config
│   │   ├── settings.py
│   │   └── urls.py
│   ├── ooda_app/              # Main Django app
│   │   ├── models.py          # Scenario, Session, OODAEntry, CommanderProfile
│   │   ├── serializers.py     # DRF serializers
│   │   ├── views.py           # API views & business logic
│   │   ├── urls.py            # API routes
│   │   └── fixtures/
│   │       └── scenarios.json # 4 pre-built scenarios
│   ├── requirements.txt
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Full React app (single-file)
│   │   └── main.jsx           # Entry point
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── docker-compose.yml
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new commander |
| POST | `/api/auth/login/` | Authenticate |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/me/` | Current user + profile |
| GET | `/api/scenarios/` | List scenarios |
| GET | `/api/scenarios/{id}/` | Scenario detail (with intel) |
| GET | `/api/sessions/` | User's sessions |
| POST | `/api/sessions/` | Start new session |
| POST | `/api/sessions/{id}/submit_phase_data/` | Submit OODA phase data |
| POST | `/api/sessions/{id}/advance_phase/` | Advance to next phase |
| POST | `/api/sessions/{id}/generate_aar/` | Generate After Action Report |
| GET | `/api/leaderboard/` | Global commander rankings |

---

## Scenarios Included

| # | Title | Theater | Difficulty |
|---|-------|---------|------------|
| 1 | Operation Iron Veil | Land | Novice |
| 2 | Operation Phantom Tide | Sea | Operator |
| 3 | Operation Crimson Signal | Cyber | Commander |
| 4 | Operation Fractured Shield | Hybrid | Strategic |

---

## OODA Loop Flow

```
OBSERVE → ORIENT → DECIDE → ACT → (loop back or COMPLETE)
```

Each phase:
- **Observe**: Select relevant intelligence from available data
- **Orient**: Assess threat level and build situational analysis  
- **Decide**: Evaluate 5 courses of action and commit to one
- **Act**: Execute and document results (triggers next loop or mission end)

Score is calculated per phase based on completeness and quality of inputs. An After Action Report is generated automatically on mission completion.

---

## Extending the App

**Add new scenarios**: Edit `ooda_app/fixtures/scenarios.json` and re-run `loaddata`

**Custom intel items**: Update `intel_data` JSON field in fixtures

**New phase scoring logic**: Modify `_calculate_phase_score()` in `views.py`

**Add more COAs**: Update the `options` array in `DecidePhase` in `App.jsx`

Author:
Akshaaya Sri G 
Intern ID:CITS3704
