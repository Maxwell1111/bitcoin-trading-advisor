# Bitcoin Portfolio Advisor - API Documentation

## FastAPI REST API

The Bitcoin Portfolio Advisor now includes a RESTful API built with FastAPI, allowing you to integrate trading recommendations into your applications.

## 🚀 Quick Start

### Option 1: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python run_api.py

# Or use uvicorn directly
uvicorn src.api.app:app --reload
```

The API will be available at: **http://localhost:8000**

### Option 2: Run with Docker

```bash
# Build and run
docker-compose up --build

# Or use docker directly
docker build -t bitcoin-advisor .
docker run -p 8000:8000 bitcoin-advisor
```

### Option 3: Use Template Scripts

```bash
# Development mode
./dev

# Production mode
./prod

# Run with docker
./run_docker
```

## 📖 API Endpoints

### Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Available Endpoints

#### 1. **Root Endpoint**
```
GET /
```
Returns API information and available endpoints.

**Response:**
```json
{
  "message": "Bitcoin Portfolio Advisor API",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "docs": "/docs",
    "recommendation": "/api/recommendation",
    "price": "/api/price"
  }
}
```

#### 2. **Health Check**
```
GET /health
GET /api/health
```
Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "Bitcoin Trading Advisor API is running"
}
```

#### 3. **Get Current Bitcoin Price**
```
GET /api/price
```
Fetch the current Bitcoin price from CoinGecko.

**Response:**
```json
{
  "price": 65432.50,
  "currency": "USD",
  "symbol": "BTC"
}
```

#### 4. **Get Trading Recommendation** (Main Endpoint)
```
POST /api/recommendation
```
Get a comprehensive trading recommendation based on technical and sentiment analysis.

**Request Body:**
```json
{
  "days": 100,
  "news_days": 7,
  "max_articles": 50,
  "use_mock": false
}
```

**Parameters:**
- `days` (int, optional): Historical price data days (default: 100)
- `news_days` (int, optional): News lookback period (default: 7)
- `max_articles` (int, optional): Max news articles to analyze (default: 50)
- `use_mock` (bool, optional): Use mock news data (default: false)

**Response:**
```json
{
  "recommendation": "buy",
  "confidence": 0.72,
  "current_price": 65432.50,
  "signals": {
    "technical": {
      "recommendation": "buy",
      "confidence": 0.65,
      "score": 0.39,
      "weight": 0.6,
      "details": {
        "rsi": {
          "value": 58.2,
          "signal": "neutral",
          "recommendation": "hold"
        },
        "macd": {
          "macd_line": 125.5,
          "signal_line": 110.2,
          "histogram": 15.3,
          "signal": "bullish",
          "recommendation": "buy"
        }
      }
    },
    "sentiment": {
      "recommendation": "buy",
      "confidence": 0.72,
      "score": 0.288,
      "weight": 0.4,
      "details": {
        "overall": "positive",
        "compound": 0.245,
        "article_count": 50
      }
    }
  },
  "targets": {
    "entry": 65432.50,
    "target_1": 68704.13,
    "target_2": 71975.75,
    "stop_loss": 63569.93
  },
  "reasoning": "RSI at 58.2 is in neutral territory. MACD shows bullish, a strong signal. News sentiment is positive (score: 0.25 from 50 articles). Technical and sentiment analysis are in agreement.",
  "timestamp": "2025-12-20T22:15:30.123456"
}
```

#### 5. **Get Technical Analysis Only**
```
GET /api/technical?days=100
```
Get only the technical analysis (RSI and MACD).

**Query Parameters:**
- `days` (int, optional): Historical data days (default: 100)

**Response:**
```json
{
  "current_price": 65432.50,
  "technical_analysis": {
    "rsi": {
      "value": 58.2,
      "signal": "neutral",
      "recommendation": "hold"
    },
    "macd": {
      "macd_line": 125.5,
      "signal_line": 110.2,
      "histogram": 15.3,
      "signal": "bullish",
      "recommendation": "buy"
    },
    "overall": {
      "recommendation": "buy",
      "confidence": 0.65,
      "buy_signals": 1,
      "sell_signals": 0
    }
  }
}
```

#### 6. **Get Sentiment Analysis Only**
```
GET /api/sentiment?days=7&max_articles=50&use_mock=false
```
Get only the news sentiment analysis.

**Query Parameters:**
- `days` (int, optional): News lookback days (default: 7)
- `max_articles` (int, optional): Max articles (default: 50)
- `use_mock` (bool, optional): Use mock data (default: false)

**Response:**
```json
{
  "overall_sentiment": "positive",
  "recommendation": "buy",
  "confidence": 0.72,
  "average_compound": 0.245,
  "median_compound": 0.22,
  "article_count": 50,
  "positive_count": 35,
  "negative_count": 8,
  "neutral_count": 7,
  "positive_ratio": 0.70,
  "negative_ratio": 0.16,
  "neutral_ratio": 0.14
}
```

## 💻 Example Usage

### Python
```python
import requests

# Get recommendation
response = requests.post(
    "http://localhost:8000/api/recommendation",
    json={
        "days": 100,
        "news_days": 7,
        "max_articles": 50,
        "use_mock": False
    }
)
data = response.json()
print(f"Recommendation: {data['recommendation'].upper()}")
print(f"Confidence: {data['confidence'] * 100:.0f}%")
```

### cURL
```bash
# Get current price
curl http://localhost:8000/api/price

# Get recommendation
curl -X POST http://localhost:8000/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "days": 100,
    "news_days": 7,
    "max_articles": 50,
    "use_mock": false
  }'

# Get technical analysis only
curl "http://localhost:8000/api/technical?days=100"
```

### JavaScript/TypeScript
```javascript
// Get recommendation
const response = await fetch('http://localhost:8000/api/recommendation', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    days: 100,
    news_days: 7,
    max_articles: 50,
    use_mock: false
  })
});

const data = await response.json();
console.log(`Recommendation: ${data.recommendation}`);
console.log(`Confidence: ${(data.confidence * 100).toFixed(0)}%`);
```

## 🔧 Configuration

The API uses the same `config.yaml` file as the CLI tool. Make sure to:

1. Copy `config.example.yaml` to `config.yaml`
2. Add your NewsAPI key if you want real news analysis
3. Adjust weights and thresholds as needed

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t bitcoin-advisor-api .
```

### Run Container
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/data:/app/data \
  --name bitcoin-advisor \
  bitcoin-advisor-api
```

### Docker Compose
```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📊 CORS Configuration

The API has CORS enabled by default, allowing requests from any origin. For production, you should restrict this in `src/api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🔐 Production Considerations

For production deployment:

1. **Add Authentication**: Implement API keys or OAuth
2. **Rate Limiting**: Add rate limiting to prevent abuse
3. **HTTPS**: Use reverse proxy (nginx) with SSL
4. **Environment Variables**: Don't hardcode API keys
5. **Monitoring**: Add logging and monitoring
6. **Database**: Cache recommendations to reduce API calls
7. **Error Handling**: Improve error responses

## 🚀 Deploying to Cloud

### Render.com
1. Create a new Web Service
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn src.api.app:app --host 0.0.0.0 --port $PORT`

### Railway
1. Create new project from GitHub
2. Railway will auto-detect Dockerfile
3. Set port to 8000

### Heroku
```bash
# Create Procfile
echo "web: uvicorn src.api.app:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create bitcoin-advisor-api
git push heroku main
```

## 📝 Notes

- The API falls back to mock news data if no NewsAPI key is configured
- CoinGecko API (for price data) doesn't require an API key
- Default weights: 60% technical, 40% sentiment
- All endpoints return JSON responses
- The `/docs` endpoint provides interactive API testing

## 🆘 Troubleshooting

**Problem**: Port 8000 already in use
**Solution**: `lsof -ti:8000 | xargs kill` or use a different port

**Problem**: Import errors
**Solution**: Make sure you're running from the project root and have installed all requirements

**Problem**: No news data
**Solution**: Set `use_mock: true` in the request or add NewsAPI key to config.yaml

---

For more information, see the main [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md)
