import re
from datetime import datetime, timezone
import yfinance as yf

# Specialized financial lexicon for headline polarity scoring
BULLISH_KEYWORDS = {
    'record', 'surge', 'surges', 'soar', 'soars', 'jump', 'jumps', 'beat', 'beats',
    'growth', 'profit', 'profits', 'bull', 'bullish', 'gain', 'gains', 'high', 'higher',
    'upgrade', 'upgrades', 'rally', 'rallies', 'outperform', 'outperforms', 'dividend',
    'breakthrough', 'expansion', 'buy', 'strong', 'optimistic', 'revenue', 'boost', 'boosts',
    'partnership', 'milestone', 'upside', 'win', 'wins', 'top'
}

BEARISH_KEYWORDS = {
    'fall', 'falls', 'drop', 'drops', 'plunge', 'plunges', 'slump', 'slumps', 'miss',
    'misses', 'loss', 'losses', 'bear', 'bearish', 'decline', 'declines', 'low', 'lower',
    'downgrade', 'downgrades', 'crash', 'selloff', 'warning', 'recession', 'inflation',
    'lawsuit', 'investigation', 'debt', 'risk', 'crisis', 'cut', 'cuts', 'down', 'weak',
    'struggle', 'struggles', 'downside', 'penalty', 'fine', 'layoff', 'layoffs'
}

class NewsService:
    @staticmethod
    def _calculate_headline_sentiment(title: str) -> dict:
        """Analyze headline text polarity using domain-specific financial lexicon."""
        words = re.findall(r'\b[a-z]+\b', title.lower())
        bull_count = sum(1 for w in words if w in BULLISH_KEYWORDS)
        bear_count = sum(1 for w in words if w in BEARISH_KEYWORDS)
        
        diff = bull_count - bear_count
        total = bull_count + bear_count
        
        if total == 0:
            score = 0.0
            label = "NEUTRAL"
        elif diff > 0:
            score = min(1.0, 0.3 + (diff * 0.2))
            label = "BULLISH"
        elif diff < 0:
            score = max(-1.0, -0.3 + (diff * 0.2))
            label = "BEARISH"
        else:
            score = 0.0
            label = "NEUTRAL"

        return {
            "score": round(score, 2),
            "label": label,
            "badge_class": "badge-bullish-subtle" if label == "BULLISH" else ("badge-bearish-subtle" if label == "BEARISH" else "badge bg-secondary bg-opacity-25 text-light")
        }

    @staticmethod
    def _format_time_ago(timestamp) -> str:
        """Convert unix timestamp to human-friendly relative time."""
        try:
            if isinstance(timestamp, (int, float)):
                published_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, str):
                published_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                return "Recent"

            now = datetime.now(timezone.utc)
            diff = now - published_dt
            seconds = int(diff.total_seconds())

            if seconds < 60:
                return "Just now"
            elif seconds < 3600:
                return f"{seconds // 60}m ago"
            elif seconds < 86400:
                return f"{seconds // 3600}h ago"
            else:
                return f"{seconds // 86400}d ago"
        except Exception:
            return "Recent"

    def get_stock_news(self, ticker: str, max_items: int = 6) -> dict:
        """
        Fetch real-time news articles from Yahoo Finance and score sentiment.
        """
        news_items = []
        try:
            t = yf.Ticker(ticker)
            raw_news = t.news or []
            
            for item in raw_news[:max_items]:
                # Handle varying Yahoo Finance payload structure
                content = item.get('content', item) if isinstance(item, dict) else {}
                title = content.get('title') or item.get('title', 'Market Update')
                publisher = content.get('provider', {}).get('displayName') or item.get('publisher', 'Financial Wire')
                
                # Extract URL
                url = content.get('canonicalUrl', {}).get('url') or item.get('link', '#')
                
                # Extract timestamp
                pub_time = content.get('pubDate') or item.get('providerPublishTime')
                time_ago = self._format_time_ago(pub_time)

                sentiment = self._calculate_headline_sentiment(title)

                news_items.append({
                    "title": title,
                    "publisher": publisher,
                    "url": url,
                    "time_ago": time_ago,
                    "sentiment": sentiment
                })
        except Exception as e:
            print(f"[NewsService] Error fetching news for {ticker}: {e}")

        # Compute aggregate sentiment
        if news_items:
            bull_pct = sum(1 for n in news_items if n['sentiment']['label'] == 'BULLISH') / len(news_items) * 100
            bear_pct = sum(1 for n in news_items if n['sentiment']['label'] == 'BEARISH') / len(news_items) * 100
            avg_score = sum(n['sentiment']['score'] for n in news_items) / len(news_items)
            
            if avg_score > 0.15:
                overall_label = "BULLISH"
                overall_badge = "badge-bullish-subtle"
            elif avg_score < -0.15:
                overall_label = "BEARISH"
                overall_badge = "badge-bearish-subtle"
            else:
                overall_label = "NEUTRAL"
                overall_badge = "badge bg-secondary bg-opacity-25 text-light"
        else:
            bull_pct, bear_pct, avg_score = 50.0, 50.0, 0.0
            overall_label = "NEUTRAL"
            overall_badge = "badge bg-secondary bg-opacity-25 text-light"

        return {
            "articles": news_items,
            "sentiment_summary": {
                "score": round(avg_score, 2),
                "label": overall_label,
                "badge_class": overall_badge,
                "bullish_pct": round(bull_pct, 1),
                "bearish_pct": round(bear_pct, 1)
            }
        }

news_service = NewsService()
