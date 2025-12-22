"""
Cryptocurrency news fetcher - supports NewsAPI, Reddit, and Twitter/X
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time
import json


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


class RedditFetcher:
    """
    Fetch Bitcoin sentiment from Reddit

    Free API - no authentication needed for public data
    Subreddits: r/Bitcoin, r/CryptoCurrency
    """

    def __init__(self):
        """Initialize Reddit fetcher"""
        self.base_url = "https://www.reddit.com"
        # User agent required by Reddit API
        self.headers = {
            'User-Agent': 'BitcoinTradingAdvisor/1.0'
        }

    def fetch_posts(self, subreddits: List[str] = None, limit: int = 50,
                    time_filter: str = 'day') -> List[Dict]:
        """
        Fetch hot posts from Bitcoin-related subreddits

        Args:
            subreddits: List of subreddits to fetch from (default: ['Bitcoin', 'CryptoCurrency'])
            limit: Number of posts per subreddit (max 100)
            time_filter: Time filter - 'hour', 'day', 'week', 'month', 'year', 'all'

        Returns:
            List of posts with title, text, score, url, created_time
        """
        if subreddits is None:
            subreddits = ['Bitcoin', 'CryptoCurrency']

        all_posts = []

        for subreddit in subreddits:
            try:
                # Fetch hot posts from subreddit
                url = f"{self.base_url}/r/{subreddit}/hot.json"
                params = {
                    'limit': min(limit, 100),  # Reddit API limit
                    't': time_filter
                }

                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Parse posts
                for post in data.get('data', {}).get('children', []):
                    post_data = post.get('data', {})

                    # Only include posts that mention bitcoin/btc/crypto
                    title = post_data.get('title', '').lower()
                    selftext = post_data.get('selftext', '').lower()

                    if any(keyword in title or keyword in selftext
                           for keyword in ['bitcoin', 'btc', 'crypto']):

                        all_posts.append({
                            'title': post_data.get('title', ''),
                            'description': post_data.get('selftext', '')[:500],  # Limit length
                            'content': post_data.get('selftext', ''),
                            'url': f"https://reddit.com{post_data.get('permalink', '')}",
                            'source': f"r/{subreddit}",
                            'published_date': datetime.fromtimestamp(
                                post_data.get('created_utc', 0)
                            ).isoformat(),
                            'author': post_data.get('author', ''),
                            'score': post_data.get('score', 0),  # Reddit upvotes
                            'num_comments': post_data.get('num_comments', 0)
                        })

                # Respect Reddit rate limits
                time.sleep(1)

            except Exception as e:
                print(f"Warning: Error fetching from r/{subreddit}: {e}")
                continue

        # Sort by score (upvotes) to get most popular posts
        all_posts.sort(key=lambda x: x.get('score', 0), reverse=True)

        return all_posts[:limit]


class TwitterFetcher:
    """
    Fetch Bitcoin sentiment from Twitter/X

    REQUIRES: Twitter API v2 access ($100/month minimum)
    To enable: Get Bearer Token from https://developer.twitter.com/
    """

    def __init__(self, bearer_token: str = None):
        """
        Initialize Twitter fetcher

        Args:
            bearer_token: Twitter API v2 Bearer Token (required)
        """
        self.bearer_token = bearer_token
        self.enabled = bearer_token is not None and bearer_token != ""

        if not self.enabled:
            print("Twitter/X integration disabled - no API token provided")
            print("To enable: Get Bearer Token from https://developer.twitter.com/")
            print("Cost: $100/month for Basic tier")

    def fetch_tweets(self, keywords: List[str] = None, max_results: int = 50) -> List[Dict]:
        """
        Fetch recent tweets about Bitcoin

        Args:
            keywords: Keywords to search (default: ['bitcoin', 'btc'])
            max_results: Number of tweets (10-100)

        Returns:
            List of tweets with text, author, created_at, metrics
        """
        if not self.enabled:
            return []

        if keywords is None:
            keywords = ['bitcoin', 'btc']

        url = "https://api.twitter.com/2/tweets/search/recent"

        # Build query
        query = " OR ".join(keywords) + " -is:retweet lang:en"

        headers = {
            'Authorization': f'Bearer {self.bearer_token}'
        }

        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,public_metrics,author_id',
            'expansions': 'author_id',
            'user.fields': 'username,verified'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse tweets
            tweets = []
            users = {user['id']: user for user in data.get('includes', {}).get('users', [])}

            for tweet in data.get('data', []):
                author = users.get(tweet.get('author_id', ''), {})
                metrics = tweet.get('public_metrics', {})

                tweets.append({
                    'title': tweet.get('text', '')[:100],  # First 100 chars as title
                    'description': tweet.get('text', ''),
                    'content': tweet.get('text', ''),
                    'url': f"https://twitter.com/i/web/status/{tweet.get('id', '')}",
                    'source': 'Twitter',
                    'published_date': tweet.get('created_at', ''),
                    'author': author.get('username', ''),
                    'verified': author.get('verified', False),
                    'likes': metrics.get('like_count', 0),
                    'retweets': metrics.get('retweet_count', 0)
                })

            return tweets

        except Exception as e:
            print(f"Error fetching tweets: {e}")
            return []


class MultiSourceFetcher:
    """
    Fetch sentiment data from multiple sources

    Sources:
    - NewsAPI: Professional news articles
    - Reddit: Community sentiment (FREE)
    - Twitter: Real-time sentiment (requires API token)
    """

    def __init__(self, newsapi_key: str = None, twitter_bearer_token: str = None):
        """
        Initialize multi-source fetcher

        Args:
            newsapi_key: NewsAPI.org API key (optional, falls back to mock)
            twitter_bearer_token: Twitter API Bearer Token (optional)
        """
        # Initialize all sources
        self.news_fetcher = None
        if newsapi_key:
            try:
                self.news_fetcher = NewsFetcher(api_key=newsapi_key, provider='newsapi')
            except:
                pass

        self.reddit_fetcher = RedditFetcher()
        self.twitter_fetcher = TwitterFetcher(bearer_token=twitter_bearer_token)

    def fetch_all(self, max_per_source: int = 50) -> Dict[str, List[Dict]]:
        """
        Fetch from all available sources

        Args:
            max_per_source: Maximum items per source

        Returns:
            Dictionary with sources as keys and lists of items as values
        """
        results = {
            'news': [],
            'reddit': [],
            'twitter': []
        }

        # Fetch from NewsAPI
        if self.news_fetcher:
            try:
                results['news'] = self.news_fetcher.fetch_news(
                    keywords=['bitcoin', 'btc', 'cryptocurrency'],
                    days=7,
                    max_articles=max_per_source
                )
            except Exception as e:
                print(f"NewsAPI error: {e}")

        # Fetch from Reddit (always available - FREE)
        try:
            results['reddit'] = self.reddit_fetcher.fetch_posts(
                limit=max_per_source,
                time_filter='day'
            )
        except Exception as e:
            print(f"Reddit error: {e}")

        # Fetch from Twitter (if enabled)
        if self.twitter_fetcher.enabled:
            try:
                results['twitter'] = self.twitter_fetcher.fetch_tweets(
                    max_results=max_per_source
                )
            except Exception as e:
                print(f"Twitter error: {e}")

        return results

    def get_combined_items(self, max_per_source: int = 25) -> List[Dict]:
        """
        Get combined list of all items from all sources

        Args:
            max_per_source: Maximum items per source

        Returns:
            Combined list of all items
        """
        try:
            all_data = self.fetch_all(max_per_source=max_per_source)

            combined = []
            for source_type, items in all_data.items():
                if items:  # Only process if we have items
                    for item in items:
                        # Add source type tag
                        item['source_type'] = source_type
                        combined.append(item)

            return combined
        except Exception as e:
            print(f"Error in get_combined_items: {e}")
            return []  # Return empty list on error


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
