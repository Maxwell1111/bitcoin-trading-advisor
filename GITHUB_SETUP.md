# GitHub Setup Guide

## 📤 Push Your Project to GitHub

### Option 1: Using GitHub Website (Easiest)

1. **Go to GitHub** and sign in
   - Visit: https://github.com

2. **Create a new repository**
   - Click the "+" icon in top right → "New repository"
   - Repository name: `bitcoin-trading-advisor`
   - Description: "Bitcoin portfolio advisor using sentiment analysis and technical indicators"
   - Make it **Public** (or Private if you prefer)
   - **Do NOT** initialize with README, .gitignore, or license (we already have these)
   - Click "Create repository"

3. **Push your local code**

   Copy and run these commands in your terminal:

   ```bash
   cd /Users/aardeshiri/bitcoin-trading-advisor

   # Add your GitHub repository as remote
   git remote add origin https://github.com/YOUR_USERNAME/bitcoin-trading-advisor.git

   # Push your code
   git branch -M main
   git push -u origin main
   ```

   Replace `YOUR_USERNAME` with your actual GitHub username!

### Option 2: Using GitHub CLI (If you have it installed)

```bash
cd /Users/aardeshiri/bitcoin-trading-advisor

# Create and push repo in one command
gh repo create bitcoin-trading-advisor --public --source=. --remote=origin --push

# Or for private repo
gh repo create bitcoin-trading-advisor --private --source=. --remote=origin --push
```

### Option 3: Manual Setup with Personal Access Token

If you get authentication errors, use a Personal Access Token:

1. Go to GitHub Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Copy the token
4. Use it when pushing:

```bash
git remote add origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/YOUR_USERNAME/bitcoin-trading-advisor.git
git push -u origin main
```

## ✅ Verify Upload

After pushing, visit:
```
https://github.com/YOUR_USERNAME/bitcoin-trading-advisor
```

You should see all your files!

## 🎨 Recommended: Add Topics to Your Repo

On your GitHub repo page:
1. Click the gear icon ⚙️ next to "About"
2. Add topics: `bitcoin`, `trading-bot`, `sentiment-analysis`, `python`, `cryptocurrency`, `rsi`, `macd`, `technical-analysis`
3. Save changes

## 📋 Recommended: Enable GitHub Actions (Optional)

Create `.github/workflows/test.yml` to run tests automatically:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python main.py --mock
```

## 🔄 Future Updates

When you make changes:

```bash
# Check what changed
git status

# Add files
git add .

# Commit with message
git commit -m "Add new feature"

# Push to GitHub
git push
```

## 🌟 Make it Popular!

- Add a nice project banner/logo
- Write detailed documentation
- Add screenshots of output
- Create example notebooks
- Star other similar projects
- Share on Reddit (r/algotrading, r/Bitcoin)
- Tweet about it with #Bitcoin #TradingBot

## 🤝 Collaboration

To accept contributions:
1. Add CONTRIBUTING.md with guidelines
2. Create issue templates
3. Set up branch protection rules
4. Add code of conduct

Your repository URL will be:
```
https://github.com/YOUR_USERNAME/bitcoin-trading-advisor
```

Good luck with your project! 🚀
