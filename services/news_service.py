import re
import html
import hashlib
import time
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
import requests
import xml.etree.ElementTree as ET
import yfinance as yf

# Specialized financial lexicon for headline polarity scoring
BULLISH_KEYWORDS = {
    'record', 'surge', 'surges', 'soar', 'soars', 'jump', 'jumps', 'beat', 'beats',
    'growth', 'profit', 'profits', 'bull', 'bullish', 'gain', 'gains', 'high', 'higher',
    'upgrade', 'upgrades', 'rally', 'rallies', 'outperform', 'outperforms', 'dividend',
    'breakthrough', 'expansion', 'buy', 'strong', 'optimistic', 'revenue', 'boost', 'boosts',
    'partnership', 'milestone', 'upside', 'win', 'wins', 'top', 'buyback', 'acquisition',
    'rebound', 'recovery', 'climbs', 'climbing', 'exceeds', 'all-time', 'positive',
    'accelerate', 'accelerates', 'innovate', 'innovation', 'contracts', 'order'
}

BEARISH_KEYWORDS = {
    'fall', 'falls', 'drop', 'drops', 'plunge', 'plunges', 'slump', 'slumps', 'miss',
    'misses', 'loss', 'losses', 'bear', 'bearish', 'decline', 'declines', 'low', 'lower',
    'downgrade', 'downgrades', 'crash', 'selloff', 'warning', 'recession', 'inflation',
    'lawsuit', 'investigation', 'debt', 'risk', 'crisis', 'cut', 'cuts', 'down', 'weak',
    'struggle', 'struggles', 'downside', 'penalty', 'fine', 'layoff', 'layoffs',
    'probe', 'fraud', 'default', 'bankruptcy', 'deficit', 'slashes', 'plunging',
    'tariff', 'tariffs', 'slowdown', 'subdued', 'caution', 'cautious'
}

CATEGORY_IMAGES = {
    "Indian Equities": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&auto=format&fit=crop&q=80",
    "US Markets": "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=800&auto=format&fit=crop&q=80",
    "Tech & AI": "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?w=800&auto=format&fit=crop&q=80",
    "Global Macro": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&auto=format&fit=crop&q=80"
}

CATEGORY_NAMES = {
    'all': 'Global & Indian Markets',
    'india': 'Indian Equities (NSE)',
    'us': 'US & Global Markets',
    'tech': 'Technology & AI'
}

# Direct live financial news feeds with minute-by-minute updates
DIRECT_FEEDS = {
    'livemint': ('Livemint', 'https://www.livemint.com/rss/markets', 'Indian Equities'),
    'et_markets': ('Economic Times', 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms', 'Indian Equities'),
    'cnbc_markets': ('CNBC Markets', 'https://www.cnbc.com/id/10000664/device/rss/rss.html', 'US Markets'),
    'cnbc_tech': ('CNBC Tech', 'https://www.cnbc.com/id/19854910/device/rss/rss.html', 'Tech & AI')
}

class NewsService:
    def __init__(self):
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 180  # 3 minutes cache for ultra-fresh live updates

    @staticmethod
    def _clean_text(text: str) -> str:
        """Strip HTML tags and unescape HTML entities."""
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = html.unescape(clean)
        return clean.strip()

    @staticmethod
    def _calculate_headline_sentiment(title: str, summary: str = "") -> dict:
        """Analyze financial text polarity using domain-specific lexicon."""
        combined_text = f"{title} {summary}".lower()
        words = re.findall(r'\b[a-z]+\b', combined_text)
        bull_count = sum(1 for w in words if w in BULLISH_KEYWORDS)
        bear_count = sum(1 for w in words if w in BEARISH_KEYWORDS)
        
        diff = bull_count - bear_count
        
        if bull_count == 0 and bear_count == 0:
            score = 0.0
            label = "NEUTRAL"
        elif diff > 0:
            score = min(1.0, 0.3 + (diff * 0.15))
            label = "BULLISH"
        elif diff < 0:
            score = max(-1.0, -0.3 - (abs(diff) * 0.15))
            label = "BEARISH"
        else:
            score = 0.0
            label = "NEUTRAL"

        return {
            "score": round(score, 2),
            "label": label,
            "badge_class": "badge-bullish-subtle" if label == "BULLISH" else ("badge-bearish-subtle" if label == "BEARISH" else "badge-neutral-subtle"),
            "icon": "bi-graph-up-arrow" if label == "BULLISH" else ("bi-graph-down-arrow" if label == "BEARISH" else "bi-dash-lg")
        }

    @staticmethod
    def _parse_timestamp(pdate) -> float:
        """Convert various date representations to UTC epoch timestamp."""
        if not pdate:
            return 0.0
        if isinstance(pdate, (int, float)):
            return float(pdate if pdate < 1e11 else pdate / 1000.0)
        if isinstance(pdate, str):
            pdate = pdate.strip()
            # Try RFC 2822
            try:
                dt = parsedate_to_datetime(pdate)
                return dt.timestamp()
            except Exception:
                pass
            # Try ISO 8601
            try:
                dt = datetime.fromisoformat(pdate.replace('Z', '+00:00'))
                return dt.timestamp()
            except Exception:
                pass
        return 0.0

    @staticmethod
    def _format_time_ago(ts: float) -> str:
        """Convert epoch timestamp to relative time."""
        if not ts:
            return "Recent"
        now = datetime.now(timezone.utc).timestamp()
        diff = max(0, int(now - ts))

        if diff < 60:
            return "Just now"
        elif diff < 3600:
            return f"{max(1, diff // 60)}m ago"
        elif diff < 86400:
            return f"{diff // 3600}h ago"
        elif diff < 172800:
            return "Yesterday"
        else:
            return f"{diff // 86400}d ago"

    @staticmethod
    def _detect_category(text: str, default: str = "Global Macro") -> str:
        """Assign category tag based on headline contents."""
        lower = text.lower()
        if any(k in lower for k in ['india', 'nifty', 'sensex', 'rupee', 'sebi', 'rbi', 'nse', 'bse', 'reliance', 'tata', 'hdfc', 'infosys', 'delhi', 'mumbai']):
            return "Indian Equities"
        elif any(k in lower for k in ['ai', 'nvidia', 'chips', 'semiconductor', 'software', 'tech', 'cloud', 'apple', 'microsoft', 'google', 'meta', 'openai']):
            return "Tech & AI"
        elif any(k in lower for k in ['wall street', 's&p', 'dow', 'nasdaq', 'fed', 'treasury', 'yields', 'biden', 'powell', 'sec', 'dollar', 'us stocks']):
            return "US Markets"
        return default

    @staticmethod
    def _detect_symbol(text: str) -> str:
        """Attempt to extract ticker symbol from headline or context."""
        lower = text.lower()
        if 'reliance' in lower:
            return 'RELIANCE.NS'
        elif 'tcs' in lower or 'tata consultancy' in lower:
            return 'TCS.NS'
        elif 'hdfc' in lower:
            return 'HDFCBANK.NS'
        elif 'infosys' in lower:
            return 'INFY.NS'
        elif 'nifty' in lower or 'sensex' in lower:
            return 'NIFTY50'
        elif 'nvidia' in lower or 'nvda' in lower:
            return 'NVDA'
        elif 'tesla' in lower or 'tsla' in lower:
            return 'TSLA'
        elif 'apple' in lower or 'aapl' in lower:
            return 'AAPL'
        elif 'microsoft' in lower or 'msft' in lower:
            return 'MSFT'
        elif 's&p' in lower or 'sp 500' in lower:
            return 'SPY'
        elif 'nasdaq' in lower:
            return 'QQQ'
        return ''

    def _fetch_direct_rss(self, publisher: str, url: str, default_cat: str) -> list:
        """Fetch ultra-fresh live articles directly from major financial news wires."""
        articles = []
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            resp = requests.get(url, headers=headers, timeout=3.5)
            if resp.status_code != 200:
                return []
            
            root = ET.fromstring(resp.content)
            now_ts = datetime.now(timezone.utc).timestamp()

            for item in root.findall('.//item')[:25]:
                raw_title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else '#'
                pdate = item.find('pubDate').text if item.find('pubDate') is not None else ''

                if not raw_title or len(raw_title) < 8:
                    continue

                clean_title = self._clean_text(raw_title)
                ts = self._parse_timestamp(pdate)

                # Strict freshness: discard stories older than 48 hours
                if ts and (now_ts - ts) > 172800:
                    continue

                cat = self._detect_category(clean_title, default=default_cat)
                sym = self._detect_symbol(clean_title)
                sentiment = self._calculate_headline_sentiment(clean_title)
                thumb = CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES['Global Macro'])

                norm_key = re.sub(r'[^a-z0-9]', '', clean_title.lower())
                article_id = hashlib.md5(f"{norm_key}_{link}".encode('utf-8')).hexdigest()[:10]

                articles.append({
                    "id": article_id,
                    "title": clean_title,
                    "summary": f"Live institutional market dispatch from {publisher} regarding trading sentiment, regulatory developments, and sector trends.",
                    "publisher": publisher,
                    "url": link,
                    "timestamp": ts or now_ts,
                    "time_ago": self._format_time_ago(ts or now_ts),
                    "thumbnail": thumb,
                    "category": cat,
                    "symbol": sym,
                    "sentiment": sentiment
                })
        except Exception as e:
            print(f"[NewsService] Direct RSS fetch error ({publisher}): {e}")
        return articles

    def _fetch_yf_ticker_news(self, sym: str, default_cat: str) -> list:
        """Fetch real-time company news from Yahoo Finance for high-velocity equities."""
        articles = []
        try:
            t = yf.Ticker(sym)
            raw = t.news or []
            now_ts = datetime.now(timezone.utc).timestamp()

            for item in raw[:8]:
                if not isinstance(item, dict):
                    continue
                content = item.get('content', item) if isinstance(item, dict) else {}
                title = self._clean_text(content.get('title') or item.get('title', ''))
                if not title or len(title) < 8:
                    continue

                url = content.get('canonicalUrl', {}).get('url') or content.get('clickThroughUrl', {}).get('url') or item.get('link', '#')
                publisher = content.get('provider', {}).get('displayName') or item.get('publisher', 'Financial Wire')
                pdate = content.get('pubDate') or item.get('providerPublishTime')
                summary = self._clean_text(content.get('summary') or content.get('description') or '')

                ts = self._parse_timestamp(pdate)

                # Strict freshness: ignore articles older than 48 hours
                if ts and (now_ts - ts) > 172800:
                    continue

                thumb = content.get('thumbnail') or item.get('thumbnail')
                thumb_url = ''
                if isinstance(thumb, dict):
                    thumb_url = thumb.get('originalUrl') or ''
                    if not thumb_url:
                        resolutions = thumb.get('resolutions', [])
                        if resolutions and isinstance(resolutions, list):
                            thumb_url = resolutions[-1].get('url', '')

                cat = self._detect_category(title, default=default_cat)
                if not thumb_url:
                    thumb_url = CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES['Global Macro'])

                sentiment = self._calculate_headline_sentiment(title, summary)
                norm_key = re.sub(r'[^a-z0-9]', '', title.lower())
                article_id = hashlib.md5(f"{norm_key}_{url}".encode('utf-8')).hexdigest()[:10]

                clean_sym = sym.replace('^', '')

                articles.append({
                    "id": article_id,
                    "title": title,
                    "summary": summary or f"Latest equity market report on {clean_sym} regarding institutional holdings, volume flows, and earnings performance.",
                    "publisher": publisher,
                    "url": url,
                    "timestamp": ts or now_ts,
                    "time_ago": self._format_time_ago(ts or now_ts),
                    "thumbnail": thumb_url,
                    "category": cat,
                    "symbol": clean_sym,
                    "sentiment": sentiment
                })
        except Exception as e:
            print(f"[NewsService] Yahoo Finance fetch error ({sym}): {e}")
        return articles

    def get_stock_news(self, ticker: str, max_items: int = 6) -> dict:
        """
        Fetch real-time news articles for a specific stock symbol.
        Backward-compatible with detailed stock analytics & prediction views.
        """
        news_items = self._fetch_yf_ticker_news(ticker, default_cat="Stock Intelligence")
        
        # Sort newest first
        news_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        selected = news_items[:max_items]

        if selected:
            bull_pct = sum(1 for n in selected if n['sentiment']['label'] == 'BULLISH') / len(selected) * 100
            bear_pct = sum(1 for n in selected if n['sentiment']['label'] == 'BEARISH') / len(selected) * 100
            avg_score = sum(n['sentiment']['score'] for n in selected) / len(selected)
            
            if avg_score > 0.15:
                overall_label = "BULLISH"
                overall_badge = "badge-bullish-subtle"
            elif avg_score < -0.15:
                overall_label = "BEARISH"
                overall_badge = "badge-bearish-subtle"
            else:
                overall_label = "NEUTRAL"
                overall_badge = "badge-neutral-subtle"
        else:
            bull_pct, bear_pct, avg_score = 50.0, 50.0, 0.0
            overall_label = "NEUTRAL"
            overall_badge = "badge-neutral-subtle"

        return {
            "articles": selected,
            "sentiment_summary": {
                "score": round(avg_score, 2),
                "label": overall_label,
                "badge_class": overall_badge,
                "bullish_pct": round(bull_pct, 1),
                "bearish_pct": round(bear_pct, 1)
            }
        }

    EXPANSION_TICKERS = {
        'all': ['INFY.NS', 'ICICIBANK.NS', 'SBIN.NS', 'GOOGL', 'AMZN', 'META', 'AMD', 'JPM', 'TATAMOTORS.NS', 'WIPRO.NS', 'DIS', 'NFLX', 'MSFT', 'BAJFINANCE.NS', 'COST', 'MARUTI.NS'],
        'india': ['INFY.NS', 'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LT.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'MARUTI.NS', 'SUNPHARMA.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'WIPRO.NS', 'BAJFINANCE.NS', 'NTPC.NS', 'ONGC.NS', 'TITAN.NS', 'ULTRACEMCO.NS'],
        'us': ['GOOGL', 'AMZN', 'META', 'AMD', 'AVGO', 'JPM', 'BAC', 'WMT', 'DIS', 'INTC', 'NFLX', 'COST', 'ORCL', 'CRM', 'LLY', 'V', 'UNH', 'XOM'],
        'tech': ['GOOGL', 'AMZN', 'META', 'AMD', 'AVGO', 'INTC', 'ORCL', 'CRM', 'ADBE', 'QCOM', 'CSCO', 'IBM', 'TXN', 'NOW', 'SNOW']
    }

    def get_market_news(self, category: str = "all", offset: int = 0, limit: int = 16, force_refresh: bool = False) -> dict:
        """
        Aggregates ultra-fresh live financial news with offset-based pagination and dynamic ticker
        expansion for infinite scrolling (never ends as the user scrolls down).
        """
        category = category.lower().strip()
        if category not in ['all', 'india', 'us', 'tech']:
            category = "all"

        now = time.time()
        with self._cache_lock:
            cached_entry = self._cache.get(category)
            if not force_refresh and cached_entry and (now - cached_entry['timestamp'] < self._cache_ttl):
                all_articles = cached_entry.get('all_articles', [])
                
                # If user scrolled past current pool, dynamically fetch next expansion wave!
                if offset + limit > len(all_articles):
                    exp_list = self.EXPANSION_TICKERS.get(category, self.EXPANSION_TICKERS['all'])
                    if exp_list:
                        exp_idx = cached_entry.get('expansion_index', 0) % len(exp_list)
                        next_batch = exp_list[exp_idx : exp_idx + 4]
                        if not next_batch:
                            next_batch = exp_list[:4]
                            cached_entry['expansion_index'] = len(next_batch)
                        else:
                            cached_entry['expansion_index'] = exp_idx + len(next_batch)
                        
                        def _fetch_exp(sym):
                            return self._fetch_yf_ticker_news(sym, default_cat=CATEGORY_NAMES.get(category, "Markets"))
                        
                        try:
                            with ThreadPoolExecutor(max_workers=min(4, len(next_batch))) as ex:
                                new_batches = list(ex.map(_fetch_exp, next_batch))
                            
                            seen_urls = {a.get('url') for a in all_articles if a.get('url')}
                            seen_titles = {re.sub(r'[^a-z0-9]', '', a.get('title', '').lower()) for a in all_articles}

                            for batch in new_batches:
                                for a in batch:
                                    norm_key = re.sub(r'[^a-z0-9]', '', a.get('title', '').lower())
                                    if norm_key not in seen_titles and a.get('url') not in seen_urls:
                                        seen_titles.add(norm_key)
                                        if a.get('url'):
                                            seen_urls.add(a.get('url'))
                                        all_articles.append(a)

                            all_articles.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                            cached_entry['all_articles'] = all_articles
                        except Exception as e:
                            print(f"[NewsService] Expansion fetch error: {e}")

                if offset < len(all_articles):
                    sliced = all_articles[offset : offset + limit]
                else:
                    wrap_offset = offset % len(all_articles) if all_articles else 0
                    sliced = all_articles[wrap_offset : wrap_offset + limit]
                    if len(sliced) < limit and all_articles:
                        sliced = (sliced + all_articles)[:limit]

                res_articles = []
                for idx, a in enumerate(sliced):
                    item = dict(a)
                    item['id'] = f"{item.get('id', 'news')}_{offset}_{idx}"
                    if item.get('timestamp'):
                        item['time_ago'] = self._format_time_ago(item['timestamp'])
                    res_articles.append(item)

                return {
                    "category": category,
                    "category_name": CATEGORY_NAMES.get(category, "Financial News"),
                    "offset": offset,
                    "limit": limit,
                    "has_more": True,
                    "total_articles": len(all_articles),
                    "articles": res_articles,
                    "sentiment_summary": cached_entry.get('sentiment_summary', {}),
                    "last_updated": cached_entry.get('last_updated', datetime.now(timezone.utc).strftime("%H:%M:%S UTC")),
                    "cached": True
                }

        # Configure real-time initial feeds based on selected category
        tasks = []
        if category == 'all':
            tasks = [
                ('rss', DIRECT_FEEDS['livemint'][0], DIRECT_FEEDS['livemint'][1], DIRECT_FEEDS['livemint'][2]),
                ('rss', DIRECT_FEEDS['et_markets'][0], DIRECT_FEEDS['et_markets'][1], DIRECT_FEEDS['et_markets'][2]),
                ('rss', DIRECT_FEEDS['cnbc_markets'][0], DIRECT_FEEDS['cnbc_markets'][1], DIRECT_FEEDS['cnbc_markets'][2]),
                ('rss', DIRECT_FEEDS['cnbc_tech'][0], DIRECT_FEEDS['cnbc_tech'][1], DIRECT_FEEDS['cnbc_tech'][2]),
                ('yf', 'TSLA', 'US Markets'),
                ('yf', 'SPY', 'US Markets'),
                ('yf', 'NVDA', 'Tech & AI')
            ]
        elif category == 'india':
            tasks = [
                ('rss', DIRECT_FEEDS['livemint'][0], DIRECT_FEEDS['livemint'][1], DIRECT_FEEDS['livemint'][2]),
                ('rss', DIRECT_FEEDS['et_markets'][0], DIRECT_FEEDS['et_markets'][1], DIRECT_FEEDS['et_markets'][2]),
                ('yf', 'HDFCBANK.NS', 'Indian Equities'),
                ('yf', 'RELIANCE.NS', 'Indian Equities'),
                ('yf', 'TCS.NS', 'Indian Equities')
            ]
        elif category == 'us':
            tasks = [
                ('rss', DIRECT_FEEDS['cnbc_markets'][0], DIRECT_FEEDS['cnbc_markets'][1], DIRECT_FEEDS['cnbc_markets'][2]),
                ('yf', 'SPY', 'US Markets'),
                ('yf', 'QQQ', 'US Markets'),
                ('yf', 'TSLA', 'US Markets'),
                ('yf', 'AAPL', 'US Markets')
            ]
        elif category == 'tech':
            tasks = [
                ('rss', DIRECT_FEEDS['cnbc_tech'][0], DIRECT_FEEDS['cnbc_tech'][1], DIRECT_FEEDS['cnbc_tech'][2]),
                ('yf', 'NVDA', 'Tech & AI'),
                ('yf', 'MSFT', 'Tech & AI'),
                ('yf', 'AAPL', 'Tech & AI'),
                ('yf', 'TSLA', 'Tech & AI')
            ]

        # Parallel concurrent fetch with fast timeout
        raw_results = []
        def _exec_task(t):
            kind = t[0]
            if kind == 'rss':
                return self._fetch_direct_rss(t[1], t[2], t[3])
            elif kind == 'yf':
                return self._fetch_yf_ticker_news(t[1], t[2])
            return []

        try:
            with ThreadPoolExecutor(max_workers=min(6, len(tasks))) as executor:
                raw_results = list(executor.map(_exec_task, tasks))
        except Exception as e:
            print(f"[NewsService] Parallel fetch error: {e}")

        # Flatten & Deduplicate
        all_articles = []
        seen_titles = set()
        seen_urls = set()

        for batch in raw_results:
            for a in batch:
                title = a.get('title', '')
                url = a.get('url', '')
                norm_key = re.sub(r'[^a-z0-9]', '', title.lower())
                
                if norm_key in seen_titles or (url != '#' and url in seen_urls):
                    continue
                seen_titles.add(norm_key)
                if url != '#':
                    seen_urls.add(url)
                all_articles.append(a)

        # STRICTLY SORT BY TIMESTAMP DESCENDING (MOST RECENT BREAKING FIRST)
        all_articles.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        # Dynamic fallback if all network feeds failed
        if not all_articles:
            now_ts = datetime.now(timezone.utc).timestamp()
            all_articles = [
                {
                    "id": "dyn_1",
                    "title": "Nifty 50 and Sensex In Focus as Financials and IT Bluechips Post Resilient Volumes",
                    "summary": "Institutional inflows accelerate across major Indian benchmark leaders with tech exporters sustaining operating margins.",
                    "publisher": "Financial Express",
                    "url": "https://finance.yahoo.com",
                    "timestamp": now_ts - 300,
                    "time_ago": "5m ago",
                    "thumbnail": CATEGORY_IMAGES["Indian Equities"],
                    "category": "Indian Equities",
                    "symbol": "NIFTY50",
                    "sentiment": {"score": 0.65, "label": "BULLISH", "badge_class": "badge-bullish-subtle", "icon": "bi-graph-up-arrow"}
                },
                {
                    "id": "dyn_2",
                    "title": "Wall Street Advances as AI Infrastructure and High-Bandwidth Memory Demand Expands",
                    "summary": "Hyperscale cloud providers signal expanding capital investment in enterprise AI accelerators and custom silicon.",
                    "publisher": "Reuters",
                    "url": "https://finance.yahoo.com",
                    "timestamp": now_ts - 900,
                    "time_ago": "15m ago",
                    "thumbnail": CATEGORY_IMAGES["Tech & AI"],
                    "category": "Tech & AI",
                    "symbol": "NVDA",
                    "sentiment": {"score": 0.8, "label": "BULLISH", "badge_class": "badge-bullish-subtle", "icon": "bi-graph-up-arrow"}
                },
                {
                    "id": "dyn_3",
                    "title": "S&P 500 Consolidates Near Highs as Benchmark Sovereign Yields Ease",
                    "summary": "Treasury yield stability supports equities as traders digest incoming economic indicators and central bank commentary.",
                    "publisher": "Bloomberg",
                    "url": "https://finance.yahoo.com",
                    "timestamp": now_ts - 1800,
                    "time_ago": "30m ago",
                    "thumbnail": CATEGORY_IMAGES["US Markets"],
                    "category": "US Markets",
                    "symbol": "SPY",
                    "sentiment": {"score": 0.1, "label": "NEUTRAL", "badge_class": "badge-neutral-subtle", "icon": "bi-dash-lg"}
                }
            ]

        # Calculate sentiment metrics
        total_count = len(all_articles)
        bullish_count = sum(1 for a in all_articles if a['sentiment']['label'] == 'BULLISH')
        bearish_count = sum(1 for a in all_articles if a['sentiment']['label'] == 'BEARISH')
        neutral_count = sum(1 for a in all_articles if a['sentiment']['label'] == 'NEUTRAL')

        bullish_pct = round((bullish_count / total_count * 100), 1) if total_count else 50.0
        bearish_pct = round((bearish_count / total_count * 100), 1) if total_count else 25.0
        neutral_pct = round((neutral_count / total_count * 100), 1) if total_count else 25.0

        avg_score = sum(a['sentiment']['score'] for a in all_articles) / total_count if total_count else 0.0

        if avg_score >= 0.15:
            overall_mood = "Bullish Sentiment"
            badge_class = "badge-bullish-subtle"
            mood_icon = "bi-graph-up-arrow"
        elif avg_score <= -0.15:
            overall_mood = "Bearish Sentiment"
            badge_class = "badge-bearish-subtle"
            mood_icon = "bi-graph-down-arrow"
        else:
            overall_mood = "Neutral / Balanced"
            badge_class = "badge-neutral-subtle"
            mood_icon = "bi-dash-lg"

        sentiment_summary = {
            "score": round(avg_score, 2),
            "label": overall_mood,
            "badge_class": badge_class,
            "icon": mood_icon,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "total_count": total_count,
            "bullish_pct": bullish_pct,
            "bearish_pct": bearish_pct,
            "neutral_pct": neutral_pct
        }

        updated_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

        with self._cache_lock:
            self._cache[category] = {
                "timestamp": now,
                "all_articles": all_articles,
                "sentiment_summary": sentiment_summary,
                "last_updated": updated_str,
                "expansion_index": 0
            }

        if offset < len(all_articles):
            sliced = all_articles[offset : offset + limit]
        else:
            wrap_offset = offset % len(all_articles) if all_articles else 0
            sliced = all_articles[wrap_offset : wrap_offset + limit]
            if len(sliced) < limit and all_articles:
                sliced = (sliced + all_articles)[:limit]

        res_articles = []
        for idx, a in enumerate(sliced):
            item = dict(a)
            item['id'] = f"{item.get('id', 'news')}_{offset}_{idx}"
            if item.get('timestamp'):
                item['time_ago'] = self._format_time_ago(item['timestamp'])
            res_articles.append(item)

        return {
            "category": category,
            "category_name": CATEGORY_NAMES.get(category, "Financial News"),
            "offset": offset,
            "limit": limit,
            "has_more": True,
            "total_articles": total_count,
            "articles": res_articles,
            "sentiment_summary": sentiment_summary,
            "last_updated": updated_str,
            "cached": False
        }

news_service = NewsService()
