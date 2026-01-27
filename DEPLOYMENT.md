# Deployment Guide

## Render.com Deployment

### Database Persistence Issue

**Important:** Render's free tier uses **ephemeral file systems**. This means:
- The SQLite database (`data/advisor.db`) is **not persisted** across deployments
- All recommendations, validations, and weight history are **lost** when you redeploy
- The database starts fresh/empty on each deployment

### Solution: Migrate to PostgreSQL

For production use with data persistence, you should migrate to PostgreSQL:

#### 1. Create PostgreSQL Database on Render

1. Go to Render Dashboard → New → PostgreSQL
2. Create a free PostgreSQL database
3. Note the **Internal Database URL** provided

#### 2. Install PostgreSQL Dependencies

Add to `requirements.txt`:
```
psycopg2-binary==2.9.9
```

#### 3. Update Database Configuration

Modify `src/database/session.py` to support PostgreSQL:

```python
import os

# Use PostgreSQL if DATABASE_URL environment variable is set, otherwise SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL (production)
    logger.info(f"Using PostgreSQL database")
else:
    # SQLite (local development)
    DATABASE_DIR = Path(__file__).parent.parent.parent / "data"
    DATABASE_PATH = DATABASE_DIR / "advisor.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    logger.info(f"Using SQLite database: {DATABASE_PATH}")
```

#### 4. Set Environment Variable on Render

1. Go to your service on Render
2. Environment → Add Environment Variable
3. Key: `DATABASE_URL`
4. Value: Your PostgreSQL Internal Database URL from step 1

#### 5. Deploy

Commit and push changes. Render will automatically deploy with the PostgreSQL database, and your data will persist across deployments.

---

## Current Workaround (Without PostgreSQL)

If you want to continue using SQLite on Render's free tier:

1. **Accept data loss** on each deployment
2. **Generate recommendations** after each deployment to populate the database:
   ```bash
   curl -X POST https://your-app.onrender.com/api/recommendation \
     -H "Content-Type: application/json" \
     -d '{"days": 100, "news_days": 7}'
   ```
3. The system will work during runtime, but will reset on redeploy

---

## Testing Locally

Local development uses SQLite and works perfectly:
```bash
# Start local server
python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# Generate recommendations
curl -X POST http://localhost:8000/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"days": 100, "news_days": 7}'

# View dashboard
open http://localhost:8000/dashboard
```

Data persists locally in `data/advisor.db` (not tracked in git per `.gitignore`).
