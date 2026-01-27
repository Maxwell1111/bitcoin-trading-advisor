# Deployment Guide

## PostgreSQL Migration for Render.com

### Why PostgreSQL?

Render's free tier uses **ephemeral file systems**, meaning SQLite databases are **lost on every deployment**. Your adaptive learning system needs persistent storage to:
- Accumulate recommendations over time
- Learn from historical performance
- Show meaningful weight evolution trends
- Reach 30+ recommendations for full metrics

**Solution:** Use PostgreSQL for persistent storage on Render.

---

## Step-by-Step Migration Guide

### Step 1: Create PostgreSQL Database on Render

1. **Login to Render Dashboard**
   - Go to https://dashboard.render.com

2. **Create New PostgreSQL Database**
   - Click **"New +"** in top right
   - Select **"PostgreSQL"**
   - Fill in details:
     - **Name:** `bitcoin-advisor-db` (or your preferred name)
     - **Database:** Leave default or use `advisor`
     - **User:** Leave default or use `advisor`
     - **Region:** Same as your web service (for best performance)
     - **PostgreSQL Version:** 16 (latest)
     - **Plan:** Free
   - Click **"Create Database"**

3. **Get Database URL**
   - Wait for database to be created (~1-2 minutes)
   - On the database page, find **"Internal Database URL"**
   - Copy this URL (looks like: `postgresql://user:pass@dpg-xxxxx/dbname`)
   - **Important:** Use the **Internal** URL, not External (faster and free)

### Step 2: Set Environment Variable on Your Web Service

1. **Go to Your Web Service**
   - In Render Dashboard, click on your web service (bitcoin-trading-advisor)

2. **Add Environment Variable**
   - Click **"Environment"** in left sidebar
   - Click **"Add Environment Variable"**
   - Add:
     - **Key:** `DATABASE_URL`
     - **Value:** Paste the Internal Database URL from Step 1
   - Click **"Save Changes"**

### Step 3: Deploy Updated Code

The code has already been updated to support PostgreSQL. Just deploy:

1. **Trigger Deployment**
   - Render will auto-deploy when you push to GitHub
   - Or click **"Manual Deploy"** → **"Deploy latest commit"**

2. **Monitor Deployment**
   - Watch the deployment logs
   - Look for: `"Using PostgreSQL database (production)"`
   - Wait for: `"Deploy live"`

### Step 4: Verify Migration

Once deployed, check that it's working:

1. **Generate a Test Recommendation**
   ```bash
   curl -X POST https://bitcoin-trading-advisor.onrender.com/api/recommendation \
     -H "Content-Type: application/json" \
     -d '{"days": 100, "news_days": 7}'
   ```

2. **Check Database**
   - Refresh your dashboard: https://bitcoin-trading-advisor.onrender.com/dashboard
   - Should show **"System is in learning phase (1/30 recommendations)"**
   - Generate a few more recommendations
   - Count should increase and **persist** even after redeployment

3. **Test Persistence**
   - Note the current recommendation count
   - Redeploy your service (Manual Deploy → Deploy latest commit)
   - After deployment, check dashboard again
   - **Count should remain the same** ✅

---

## Troubleshooting

### "Connection to database failed"

**Solution:** Check DATABASE_URL is set correctly:
- Go to Web Service → Environment
- Verify `DATABASE_URL` exists and starts with `postgresql://`
- Make sure you used **Internal Database URL**, not External

### "Database tables not found"

**Solution:** Tables are created automatically on startup. Check logs:
- Go to Web Service → Logs
- Look for `"Database tables created successfully"`
- If you see errors, the app will retry on next request

### "Still showing 0 recommendations after migration"

**Solution:** Data doesn't migrate automatically from old SQLite:
- Old SQLite data is lost (was ephemeral anyway)
- Start fresh by generating new recommendations
- System will begin learning from scratch

### Want to test PostgreSQL locally?

```bash
# Get your DATABASE_URL from Render
export DATABASE_URL="postgresql://user:pass@host/db"

# Test connection
python scripts/test_postgres_connection.py

# Run app with PostgreSQL
python -m uvicorn src.api.app:app --reload
```

---

## Local Development (SQLite)

Local development still uses SQLite for convenience:

```bash
# No DATABASE_URL = SQLite automatically
python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# Data persists in data/advisor.db
```

The app automatically detects the environment:
- **No DATABASE_URL** → SQLite (local development)
- **DATABASE_URL set** → PostgreSQL (production)

---

## Cost

✅ **Completely Free** on Render:
- PostgreSQL: Free tier (shared CPU, 1GB storage, 97 connection limit)
- Web Service: Free tier (512MB RAM, shared CPU)

Limitations:
- Database spins down after 90 days of inactivity
- Suitable for hobby projects and testing
- For production scale, consider paid tiers

---

## Summary

After migration:
- ✅ Data persists across deployments
- ✅ Adaptive learning works properly
- ✅ Weight evolution shows real trends
- ✅ System accumulates knowledge over time
- ✅ Dashboard shows accurate metrics

**Total setup time:** ~10-15 minutes
