"""
Cryptocurrency news fetcher
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time


class NewsFetcher:
    """Fetch cryptocurrency news articles"""

    def __init__(self, api_key: str, provider: str = "newsapi"):
        """
        Initialize news fetcher

        Args:
            api_key: API key for news service
            provider: News provider ('newsapi', 'cryptocontrol', 'cryptopanic')
        """
        self.api_key = api_key
        self.provider = provider.lower()

    def fetch_news(self, keywords: List[str], days: int = 7, max_articles: int = 50) -> List[Dict]:
        """
        Fetch news articles

        Args:
            keywords: List of keywords to search for
            days: Number of days to look back
            max_articles: Maximum number of articles to return

        Returns:
            List of news articles with title, description, url, published_date
        """
        if self.provider == "newsapi":
            return self._fetch_newsapi(keywords, days, max_articles)
        elif self.provider == "cryptocontrol":
            return self._fetch_cryptocontrol(keywords, max_articles)
        elif self.provider == "cryptopanic":
            return self._fetch_cryptopanic(keywords, max_articles)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _fetch_newsapi(self, keywords: List[str], days: int, max_articles: int) -> List[Dict]:
        """
        Fetch news from NewsAPI.org

        Free tier: 100 requests/day, max 100 articles per request
        """
        url = "https://newsapi.org/v2/everything"

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        # Build query
        query = " OR ".join(keywords)

        params = {
            'q': query,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': min(max_articles, 100),  # API limit
            'apiKey': self.api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['status'] != 'ok':
                raise Exception(f"NewsAPI error: {data.get('message', 'Unknown error')}")

            # Parse articles
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'published_date': article.get('publishedAt', ''),
                    'author': article.get('author', '')
                })

            return articles[:max_articles]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching news from NewsAPI: {e}")

    def _fetch_cryptocontrol(self, keywords: List[str], max_articles: int) -> List[Dict]:
        """Fetch news from CryptoControl API"""
        url = "https://cryptocontrol.io/api/v1/public/news"

        headers = {
            'x-api-key': self.api_key
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse articles
            articles = []
            for article in data[:max_articles]:
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('description', ''),  # CryptoControl doesn't provide full content
                    'url': article.get('url', ''),
                    'source': article.get('source', ''),
                    'published_date': article.get('publishedAt', ''),
                    'author': ''
                })

            return articles

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching news from CryptoControl: {e}")

    def _fetch_cryptopanic(self, keywords: List[str], max_articles: int) -> List[Dict]:
        """
        Fetch news from CryptoPanic API

        Free tier doesn't require API key but has rate limits
        """
        url = "https://cryptopanic.com/api/v1/posts/"

        params = {
            'auth_token': self.api_key if self.api_key else None,
            'currencies': 'BTC',
            'kind': 'news',
            'filter': 'hot'
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse articles
            articles = []
            for post in data.get('results', [])[:max_articles]:
                articles.append({
                    'title': post.get('title', ''),
                    'description': post.get('title', ''),  # CryptoPanic doesn't provide description
                    'content': post.get('title', ''),
                    'url': post.get('url', ''),
                    'source': post.get('source', {}).get('title', ''),
                    'published_date': post.get('published_at', ''),
                    'author': ''
                })

            return articles

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching news from CryptoPanic: {e}")

    def get_article_text(self, article: Dict) -> str:
        """
        Get full text from article for sentiment analysis

        Args:
            article: Article dictionary

        Returns:
            Combined text of title and description
        """
        text_parts = []

        if article.get('title'):
            text_parts.append(article['title'])

        if article.get('description'):
            text_parts.append(article['description'])

        if article.get('content') and article['content'] not in text_parts:
            # Some APIs truncate content, only add if unique
            content = article['content']
            if content and len(content) > 50:
                text_parts.append(content)

        return " ".join(text_parts)


# Mock news fetcher for testing without API key
class MockNewsFetcher(NewsFetcher):
    """Mock news fetcher for testing"""

    def __init__(self):
        super().__init__(api_key="mock_key", provider="newsapi")

    def fetch_news(self, keywords: List[str], days: int = 7, max_articles: int = 50) -> List[Dict]:
        """Return mock news data"""
        mock_articles = [
            {
                'title': 'Bitcoin Reaches New All-Time High as Institutional Adoption Grows',
                'description': 'Major financial institutions continue to add Bitcoin to their portfolios.',
                'content': 'Bitcoin has reached a new milestone as institutional investors...',
                'url': 'https://example.com/article1',
                'source': 'Crypto News',
                'published_date': datetime.now().isoformat(),
                'author': 'John Doe'
            },
            {
                'title': 'Regulatory Concerns Cause Bitcoin Price Volatility',
                'description': 'New regulatory proposals create uncertainty in the crypto market.',
                'content': 'Government officials announced new cryptocurrency regulations...',
                'url': 'https://example.com/article2',
                'source': 'Financial Times',
                'published_date': (datetime.now() - timedelta(days=1)).isoformat(),
                'author': 'Jane Smith'
            },
            {
                'title': 'Bitcoin Mining Becomes More Sustainable with Renewable Energy',
                'description': 'Major mining operations transition to clean energy sources.',
                'content': 'Bitcoin miners are increasingly adopting renewable energy...',
                'url': 'https://example.com/article3',
                'source': 'Green Tech',
                'published_date': (datetime.now() - timedelta(days=2)).isoformat(),
                'author': 'Mike Johnson'
            }
        ]

        return mock_articles[:max_articles]


if __name__ == "__main__":
    # Test with mock fetcher
    print("Testing News Fetcher with mock data...\n")

    fetcher = MockNewsFetcher()
    articles = fetcher.fetch_news(keywords=["bitcoin", "btc"], max_articles=3)

    print(f"Fetched {len(articles)} articles:\n")
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   Date: {article['published_date']}")
        print(f"   URL: {article['url']}")
        print()
