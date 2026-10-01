// ==========================================================================
// AlphaPulse AI — Production Financial Terminal JavaScript
// Features: Theme Switcher (Light Default), Search, Plotly Charts, Watchlist
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSearchAutocomplete();
    initPredictionLoading();
    syncWatchlistBadge();
    initLiveNewsDashboard();
});

// ==========================================================================
// 0. Theme Management (Light by Default, with Dark Toggle)
// ==========================================================================
function getCurrentTheme() {
    // Default to 'light' for modern fintech light aesthetic
    const stored = localStorage.getItem('alphapulse_theme_v2');
    if (!stored) {
        localStorage.setItem('alphapulse_theme_v2', 'light');
        localStorage.removeItem('alphapulse_theme');
        return 'light';
    }
    return stored;
}

function initTheme() {
    const theme = getCurrentTheme();
    document.body.setAttribute('data-theme', theme);
    updateThemeButtonUI(theme);
}

function toggleTheme() {
    const current = document.body.getAttribute('data-theme') || 'light';
    const nextTheme = (current === 'light') ? 'dark' : 'light';
    document.body.setAttribute('data-theme', nextTheme);
    localStorage.setItem('alphapulse_theme_v2', nextTheme);
    updateThemeButtonUI(nextTheme);

    // Refresh charts if present
    if (window.renderCurrentStockChart) {
        window.renderCurrentStockChart();
    }
    if (window.renderCurrentPredictionChart) {
        window.renderCurrentPredictionChart();
    }
}

function updateThemeButtonUI(theme) {
    const btn = document.getElementById('themeToggleBtn');
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    if (!btn || !icon || !label) return;

    if (theme === 'light') {
        icon.className = 'bi bi-moon-stars';
        label.innerText = 'Dark';
        btn.title = 'Switch to Dark Mode';
    } else {
        icon.className = 'bi bi-sun';
        label.innerText = 'Light';
        btn.title = 'Switch to Light Mode';
    }
}

// ==========================================================================
// 1. Instant Real-Time Search Autocomplete
// ==========================================================================
function initSearchAutocomplete() {
    const searchInput = document.getElementById('globalSearchInput');
    const dropdown = document.getElementById('searchResultsDropdown');
    if (!searchInput || !dropdown) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 1) {
            dropdown.style.display = 'none';
            dropdown.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const data = await res.json();
                
                if (data.results && data.results.length > 0) {
                    dropdown.innerHTML = data.results.map(item => `
                        <a href="/stock/${encodeURIComponent(item.symbol)}" class="search-result-item">
                            <div>
                                <span class="fw-bold mono">${item.symbol}</span>
                                <div class="small text-muted">${item.name}</div>
                            </div>
                            <span class="badge bg-secondary bg-opacity-25 text-secondary small">${item.market}</span>
                        </a>
                    `).join('');
                    dropdown.style.display = 'block';
                } else {
                    dropdown.innerHTML = `
                        <div class="p-3 text-muted text-center small">
                            No match in catalog. Press Enter to view '${query.toUpperCase()}' directly.
                        </div>
                    `;
                    dropdown.style.display = 'block';
                }
            } catch (err) {
                console.error("Search error:", err);
            }
        }, 150);
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = searchInput.value.trim();
            if (val) {
                window.location.href = `/stock/${encodeURIComponent(val.toUpperCase())}`;
            }
        }
    });
}

// ==========================================================================
// 2. Training Progress Polling & Loading Overlay
// ==========================================================================
function initPredictionLoading() {
    const predictForms = document.querySelectorAll('.predict-form');
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;

    predictForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            overlay.style.display = 'flex';
            
            const tickerInput = form.querySelector('input[name="ticker"]');
            const ticker = tickerInput ? tickerInput.value.trim().toUpperCase() : '';

            if (ticker) {
                pollTrainingProgress(ticker);
            }
        });
    });
}

function pollTrainingProgress(ticker) {
    const pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/train-progress/${encodeURIComponent(ticker)}`);
            const data = await res.json();
            
            if (data.status === 'training') {
                const header = document.querySelector('#loadingOverlay h4');
                if (header) {
                    header.innerText = `Training LSTM Network (Epoch ${data.epoch}/${data.total_epochs} — ${data.progress_pct}%)`;
                }
            } else if (data.status === 'completed') {
                const header = document.querySelector('#loadingOverlay h4');
                if (header) {
                    header.innerText = `Forecasting Future Trajectory...`;
                }
                clearInterval(pollInterval);
            }
        } catch (err) {
            // Ignore polling errors
        }
    }, 800);
}

// ==========================================================================
// 3. Browser Watchlist (localStorage + Live Batch Quotes)
// ==========================================================================
function getWatchlist() {
    try {
        return JSON.parse(localStorage.getItem('alphapulse_watchlist')) || ['AAPL', 'RELIANCE.NS', 'NVDA'];
    } catch {
        return ['AAPL', 'RELIANCE.NS'];
    }
}

function saveWatchlist(list) {
    localStorage.setItem('alphapulse_watchlist', JSON.stringify(list));
    syncWatchlistBadge();
}

function syncWatchlistBadge() {
    const badge = document.getElementById('watchlistCount');
    if (badge) {
        badge.innerText = getWatchlist().length;
    }
}

function toggleWatchlist(sym) {
    let list = getWatchlist();
    sym = sym.toUpperCase().trim();
    if (list.includes(sym)) {
        list = list.filter(item => item !== sym);
    } else {
        list.push(sym);
    }
    saveWatchlist(list);
    updateWatchlistButtonState(sym);
}

function updateWatchlistButtonState(sym) {
    const btn = document.getElementById('watchlistToggleBtn');
    if (!btn) return;
    const list = getWatchlist();
    const isSaved = list.includes(sym.toUpperCase().trim());
    
    if (isSaved) {
        btn.innerHTML = `<i class="bi bi-star-fill text-warning"></i> <span class="text-warning">Saved</span>`;
        btn.classList.add('border-warning');
    } else {
        btn.innerHTML = `<i class="bi bi-star"></i> <span>Watchlist</span>`;
        btn.classList.remove('border-warning');
    }
}

async function openWatchlistModal() {
    const modalEl = document.getElementById('watchlistModal');
    const container = document.getElementById('watchlistContent');
    if (!modalEl || !container) return;

    const list = getWatchlist();
    
    if (list.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-star text-muted fs-1 mb-2"></i>
                <h6 class="fw-bold">Your Watchlist is Empty</h6>
                <p class="text-muted small">Click "Watchlist" on any stock detail page to monitor its live performance.</p>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary mb-2"></div>
                <div class="text-muted small">Fetching real-time quotes for monitored assets...</div>
            </div>
        `;

        try {
            const res = await fetch('/api/watchlist/quotes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers: list })
            });
            const data = await res.json();
            
            if (data.watchlist && data.watchlist.length > 0) {
                container.innerHTML = `
                    <div class="table-responsive">
                        <table class="table table-hover small mb-0">
                            <thead>
                                <tr class="text-muted border-bottom border-secondary border-opacity-25">
                                    <th>Asset</th>
                                    <th>Company</th>
                                    <th class="text-end">Spot Price</th>
                                    <th class="text-end">24h Change</th>
                                    <th class="text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.watchlist.map(item => `
                                    <tr class="align-middle">
                                        <td>
                                            <a href="/stock/${encodeURIComponent(item.symbol)}" class="fw-bold mono text-decoration-none">
                                                ${item.symbol}
                                            </a>
                                        </td>
                                        <td class="text-truncate" style="max-width: 180px;">${item.name}</td>
                                        <td class="text-end mono fw-bold">${item.currency_symbol}${item.price}</td>
                                        <td class="text-end mono fw-bold ${item.change >= 0 ? 'price-up' : 'price-down'}">
                                            ${item.change >= 0 ? '+' : ''}${item.change} (${item.change >= 0 ? '+' : ''}${item.change_percent}%)
                                        </td>
                                        <td class="text-end">
                                            <a href="/stock/${encodeURIComponent(item.symbol)}" class="btn btn-sm btn-pill-action py-1 px-2 me-1" title="View Chart">
                                                <i class="bi bi-graph-up"></i>
                                            </a>
                                            <button class="btn btn-sm btn-pill-action text-danger py-1 px-2" onclick="removeFromWatchlist('${item.symbol}')" title="Remove">
                                                <i class="bi bi-trash"></i>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            } else {
                container.innerHTML = `<p class="text-danger small">Could not retrieve quotes. Please check network connection.</p>`;
            }
        } catch (err) {
            container.innerHTML = `<p class="text-danger small">Error loading watchlist: ${err.message}</p>`;
        }
    }

    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

function removeFromWatchlist(sym) {
    let list = getWatchlist().filter(item => item !== sym);
    saveWatchlist(list);
    openWatchlistModal();
}

// ==========================================================================
// 4. Plotly Financial Chart for Stock Detail Page (Theme Aware)
// ==========================================================================
function renderStockDetailChart(containerId, chartPayload, currencySymbol, mode = 'candlestick') {
    if (!window.Plotly || !chartPayload) return;

    const isLight = (document.body.getAttribute('data-theme') || 'light') === 'light';
    const gridColor = isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)';
    const textColor = isLight ? '#0F172A' : '#F8FAFC';
    const subtextColor = '#64748B';
    const btnBg = isLight ? '#F1F5F9' : '#121824';
    const btnText = isLight ? '#0F172A' : '#FFFFFF';

    const dates = chartPayload.dates;
    const opens = chartPayload.opens;
    const highs = chartPayload.highs;
    const lows = chartPayload.lows;
    const closes = chartPayload.closes;
    const volumes = chartPayload.volumes;
    const sma20 = chartPayload.sma20;
    const sma50 = chartPayload.sma50;

    let mainTrace;
    if (mode === 'area') {
        mainTrace = {
            x: dates,
            y: closes,
            type: 'scatter',
            mode: 'lines',
            name: 'Close Price',
            fill: 'tozeroy',
            fillcolor: isLight ? 'rgba(37, 99, 235, 0.08)' : 'rgba(0, 240, 255, 0.08)',
            line: { color: isLight ? '#2563EB' : '#00F0FF', width: 2 },
            yaxis: 'y'
        };
    } else {
        mainTrace = {
            x: dates,
            open: opens,
            high: highs,
            low: lows,
            close: closes,
            type: 'candlestick',
            name: 'Price Action',
            increasing: { line: { color: isLight ? '#16A34A' : '#00E676', width: 1.5 } },
            decreasing: { line: { color: isLight ? '#DC2626' : '#FF3366', width: 1.5 } },
            yaxis: 'y'
        };
    }

    const sma20Trace = {
        x: dates,
        y: sma20,
        type: 'scatter',
        mode: 'lines',
        name: 'SMA 20 (Fast)',
        line: { color: isLight ? '#2563EB' : '#00F0FF', width: 1.5 },
        yaxis: 'y'
    };

    const sma50Trace = {
        x: dates,
        y: sma50,
        type: 'scatter',
        mode: 'lines',
        name: 'SMA 50 (Slow)',
        line: { color: '#F59E0B', width: 1.5 },
        yaxis: 'y'
    };

    const volumeColors = closes.map((c, i) => (i > 0 && c >= closes[i - 1]) 
        ? (isLight ? 'rgba(22, 163, 74, 0.35)' : 'rgba(0, 230, 118, 0.35)') 
        : (isLight ? 'rgba(220, 38, 38, 0.35)' : 'rgba(255, 51, 102, 0.35)'));

    const volumeTrace = {
        x: dates,
        y: volumes,
        type: 'bar',
        name: 'Trading Volume',
        marker: { color: volumeColors },
        yaxis: 'y2'
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Plus Jakarta Sans, sans-serif', color: subtextColor },
        margin: { l: 60, r: 25, t: 25, b: 35 },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            orientation: 'h',
            y: 1.12,
            x: 0,
            font: { color: textColor, size: 11 }
        },
        xaxis: {
            rangeslider: { visible: false },
            color: subtextColor,
            gridcolor: gridColor,
            rangeselector: {
                buttons: [
                    { count: 1, label: '1M', step: 'month', stepmode: 'backward' },
                    { count: 3, label: '3M', step: 'month', stepmode: 'backward' },
                    { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
                    { count: 1, label: '1Y', step: 'year', stepmode: 'backward' },
                    { step: 'all', label: 'ALL' }
                ],
                bgcolor: btnBg,
                activecolor: '#2563EB',
                font: { color: btnText, size: 10 }
            }
        },
        yaxis: {
            title: `Price (${currencySymbol})`,
            color: subtextColor,
            gridcolor: gridColor,
            domain: [0.28, 1]
        },
        yaxis2: {
            title: 'Volume',
            color: subtextColor,
            gridcolor: 'transparent',
            domain: [0, 0.22],
            showgrid: false
        }
    };

    const config = { responsive: true, displayModeBar: true, displaylogo: false };
    Plotly.newPlot(containerId, [mainTrace, sma20Trace, sma50Trace, volumeTrace], layout, config);
}

// ==========================================================================
// 5. Plotly Forecast Chart for Prediction Page (Theme Aware)
// ==========================================================================
function renderPredictionChart(containerId, payload, currencySymbol) {
    if (!window.Plotly || !payload) return;

    const isLight = (document.body.getAttribute('data-theme') || 'light') === 'light';
    const gridColor = isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)';
    const textColor = isLight ? '#0F172A' : '#F8FAFC';
    const subtextColor = '#64748B';
    const forecastColor = isLight ? '#2563EB' : '#00F0FF';
    const coneFill = isLight ? 'rgba(37, 99, 235, 0.12)' : 'rgba(0, 240, 255, 0.12)';

    const traces = [];

    // 1. Historical Actual Close
    traces.push({
        x: payload.history_dates,
        y: payload.history_prices,
        mode: 'lines',
        name: 'Historical Close',
        line: { color: isLight ? '#64748B' : '#94A3B8', width: 2 },
        hoverinfo: 'x+y'
    });

    // 2. Test Set Actual vs Predicted (Backtesting Fit)
    if (payload.test_dates && payload.test_dates.length > 0) {
        traces.push({
            x: payload.test_dates,
            y: payload.test_pred,
            mode: 'lines',
            name: 'Model Test Fit (Backtest)',
            line: { color: '#F59E0B', width: 2, dash: 'dot' },
            hoverinfo: 'x+y'
        });
    }

    // 3. Shaded Confidence Cone (Upper and Lower 95% Bounds)
    if (payload.upper_band && payload.lower_band) {
        traces.push({
            x: payload.future_dates,
            y: payload.upper_band,
            mode: 'lines',
            line: { color: 'rgba(0, 0, 0, 0)' },
            showlegend: false,
            hoverinfo: 'none'
        });

        traces.push({
            x: payload.future_dates,
            y: payload.lower_band,
            mode: 'lines',
            fill: 'tonexty',
            fillcolor: coneFill,
            line: { color: 'rgba(0, 0, 0, 0)' },
            name: '95% Confidence Cone',
            hoverinfo: 'none'
        });
    }

    // 4. Future Forecast Line
    const forecastDates = [payload.history_dates[payload.history_dates.length - 1], ...payload.future_dates];
    const forecastPrices = [payload.history_prices[payload.history_prices.length - 1], ...payload.future_prices];

    traces.push({
        x: forecastDates,
        y: forecastPrices,
        mode: 'lines+markers',
        name: 'LSTM Neural Forecast',
        line: { color: forecastColor, width: 3 },
        marker: { size: 5, color: forecastColor },
        hoverinfo: 'x+y'
    });

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Plus Jakarta Sans, sans-serif', color: subtextColor },
        margin: { l: 60, r: 25, t: 30, b: 35 },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            orientation: 'h',
            y: 1.12,
            x: 0,
            font: { color: textColor, size: 11 }
        },
        xaxis: {
            color: subtextColor,
            gridcolor: gridColor,
            title: 'Trading Date'
        },
        yaxis: {
            title: `Stock Price (${currencySymbol})`,
            color: subtextColor,
            gridcolor: gridColor
        }
    };

    const config = { responsive: true, displayModeBar: true, displaylogo: false };
    Plotly.newPlot(containerId, traces, layout, config);
}

// ==========================================================================
// 5. Production Live Market News Wire & Sentiment Radar
// ==========================================================================

let activeNewsCategory = 'all';
let activeNewsArticles = [];
let activeSentimentFilter = null;
let newsSearchQuery = '';
let autoRefreshCountdown = 60;
let isAutoRefreshActive = true;
let newsCountdownInterval = null;
let newsOffset = 16;
let isFetchingMoreNews = false;
let hasMoreNews = true;
let infiniteScrollObserver = null;
let scrollThrottleTimeout = null;

function initLiveNewsDashboard() {
    const root = document.getElementById('newsSectionRoot');
    if (!root) return; // Only active on dashboard page

    // Hydrate from SSR payload
    if (window.initialNewsArticles && Array.isArray(window.initialNewsArticles) && window.initialNewsArticles.length > 0) {
        activeNewsArticles = window.initialNewsArticles;
        newsOffset = activeNewsArticles.length;
    } else {
        newsOffset = 16;
    }

    startAutoRefreshCycle();
    setupInfiniteScroll();
}

function startAutoRefreshCycle() {
    clearInterval(newsCountdownInterval);
    autoRefreshCountdown = 60;
    updateCountdownUI();

    newsCountdownInterval = setInterval(() => {
        if (!isAutoRefreshActive) return;
        autoRefreshCountdown--;
        if (autoRefreshCountdown <= 0) {
            autoRefreshCountdown = 60;
            refreshLiveNews(true); // background silent refresh
        }
        updateCountdownUI();
    }, 1000);
}

function updateCountdownUI() {
    const label = document.getElementById('autoRefreshLabel');
    if (!label) return;
    if (isAutoRefreshActive) {
        label.innerText = `Auto-refresh (${autoRefreshCountdown}s)`;
    } else {
        label.innerText = 'Auto-refresh: Paused';
    }
}

function toggleAutoRefresh() {
    isAutoRefreshActive = !isAutoRefreshActive;
    const btn = document.getElementById('autoRefreshToggleBtn');
    const icon = document.getElementById('autoRefreshIcon');
    if (!btn || !icon) return;

    if (isAutoRefreshActive) {
        autoRefreshCountdown = 60;
        icon.className = 'bi bi-arrow-repeat text-primary';
        btn.classList.remove('opacity-75');
    } else {
        icon.className = 'bi bi-pause-circle text-muted';
        btn.classList.add('opacity-75');
    }
    updateCountdownUI();
}

async function switchNewsCategory(category) {
    activeNewsCategory = category;
    activeSentimentFilter = null;
    newsSearchQuery = '';
    newsOffset = 0;
    hasMoreNews = true;
    isFetchingMoreNews = false;

    const searchInput = document.getElementById('newsSearchInput');
    if (searchInput) searchInput.value = '';
    const searchClear = document.getElementById('newsSearchClear');
    if (searchClear) searchClear.style.display = 'none';

    // Update active category tab button
    document.querySelectorAll('#newsCategoryPills .news-cat-btn').forEach(btn => {
        if (btn.getAttribute('data-cat') === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Reset sentiment filter buttons
    document.querySelectorAll('#newsCategoryPills [data-sentiment]').forEach(b => b.classList.remove('active'));

    // Show loading skeleton
    const container = document.getElementById('newsArticlesContainer');
    if (container) {
        container.innerHTML = `
            <div class="p-5 text-center">
                <div class="spinner-border text-primary mb-3" role="status" style="width: 2.5rem; height: 2.5rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h6 class="fw-bold mb-1">Retrieving Live Financial Stream...</h6>
                <p class="text-muted small mb-0">Aggregating real-time market wires, filings, and sentiment indicators</p>
            </div>
        `;
    }

    try {
        const res = await fetch(`/api/market-news?category=${encodeURIComponent(category)}&offset=0&limit=16`);
        const data = await res.json();

        activeNewsArticles = data.articles || [];
        newsOffset = activeNewsArticles.length;
        updateSentimentBarUI(data.sentiment_summary, data.total_articles);
        renderNewsArticles(activeNewsArticles);

        const updatedBadge = document.getElementById('newsLastUpdated');
        if (updatedBadge) {
            updatedBadge.innerText = `Updated ${data.last_updated || 'just now'}`;
        }
        setupInfiniteScroll();
    } catch (err) {
        console.error('[LiveNews] Failed to load news:', err);
        if (container) {
            container.innerHTML = `
                <div class="news-empty-state">
                    <i class="bi bi-exclamation-triangle text-warning fs-2 mb-2"></i>
                    <h6 class="fw-bold mb-1">Temporary Stream Latency</h6>
                    <p class="text-muted small mb-3">Could not sync real-time news desk at this moment. Please retry.</p>
                    <button class="btn-pill-action justify-content-center" onclick="refreshLiveNews()">
                        <i class="bi bi-arrow-clockwise"></i> Retry Connection
                    </button>
                </div>
            `;
        }
    }
}

function filterBySentiment(sentiment) {
    const btn = document.querySelector(`[data-sentiment="${sentiment}"]`);
    if (activeSentimentFilter === sentiment) {
        // Toggle off
        activeSentimentFilter = null;
        if (btn) btn.classList.remove('active');
    } else {
        activeSentimentFilter = sentiment;
        document.querySelectorAll('#newsCategoryPills [data-sentiment]').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
    }

    applyActiveFilters();
}

function handleNewsSearch(val) {
    newsSearchQuery = (val || '').trim().toLowerCase();
    const clearBtn = document.getElementById('newsSearchClear');
    if (clearBtn) {
        clearBtn.style.display = newsSearchQuery.length > 0 ? 'block' : 'none';
    }
    applyActiveFilters();
}

function clearNewsSearch() {
    newsSearchQuery = '';
    const input = document.getElementById('newsSearchInput');
    if (input) input.value = '';
    const clearBtn = document.getElementById('newsSearchClear');
    if (clearBtn) clearBtn.style.display = 'none';
    applyActiveFilters();
}

function applyActiveFilters() {
    let filtered = [...activeNewsArticles];

    // Filter by sentiment
    if (activeSentimentFilter) {
        filtered = filtered.filter(a => a.sentiment && a.sentiment.label === activeSentimentFilter);
    }

    // Filter by search query
    if (newsSearchQuery) {
        filtered = filtered.filter(a => {
            const title = (a.title || '').toLowerCase();
            const summary = (a.summary || '').toLowerCase();
            const publisher = (a.publisher || '').toLowerCase();
            const cat = (a.category || '').toLowerCase();
            const sym = (a.symbol || '').toLowerCase();
            return title.includes(newsSearchQuery) ||
                   summary.includes(newsSearchQuery) ||
                   publisher.includes(newsSearchQuery) ||
                   cat.includes(newsSearchQuery) ||
                   sym.includes(newsSearchQuery);
        });
    }

    // Update count badge
    const badge = document.getElementById('newsArticleCountBadge');
    if (badge) {
        badge.innerText = `${filtered.length} Stories Indexed`;
    }

    renderNewsArticles(filtered);
}

async function refreshLiveNews(isSilent = false) {
    const refreshIcon = document.getElementById('newsRefreshIcon');
    if (refreshIcon && !isSilent) {
        refreshIcon.classList.add('spinning-icon');
    }

    try {
        const res = await fetch(`/api/market-news?category=${encodeURIComponent(activeNewsCategory)}&offset=0&limit=16&refresh=true`);
        const data = await res.json();

        activeNewsArticles = data.articles || [];
        newsOffset = activeNewsArticles.length;
        updateSentimentBarUI(data.sentiment_summary, data.total_articles);
        applyActiveFilters();

        const updatedBadge = document.getElementById('newsLastUpdated');
        if (updatedBadge) {
            updatedBadge.innerText = `Updated ${data.last_updated || 'just now'}`;
        }
        autoRefreshCountdown = 60;
        updateCountdownUI();
        setupInfiniteScroll();
    } catch (err) {
        console.error('[LiveNews] Refresh failed:', err);
    } finally {
        if (refreshIcon) {
            setTimeout(() => refreshIcon.classList.remove('spinning-icon'), 600);
        }
    }
}

function updateSentimentBarUI(summary, totalCount) {
    if (!summary) return;

    const moodBadge = document.getElementById('newsMoodBadge');
    const moodIcon = document.getElementById('newsMoodIcon');
    const moodText = document.getElementById('newsMoodText');

    if (moodBadge && summary.badge_class) {
        moodBadge.className = `${summary.badge_class} px-2 py-1`;
    }
    if (moodIcon && summary.icon) {
        moodIcon.className = `bi ${summary.icon} me-1`;
    }
    if (moodText && summary.label) {
        moodText.innerText = summary.label;
    }

    const bullCount = document.getElementById('newsBullishCount');
    const bullPct = document.getElementById('newsBullishPct');
    const neuCount = document.getElementById('newsNeutralCount');
    const neuPct = document.getElementById('newsNeutralPct');
    const bearCount = document.getElementById('newsBearishCount');
    const bearPct = document.getElementById('newsBearishPct');

    if (bullCount) bullCount.innerText = summary.bullish_count || 0;
    if (bullPct) bullPct.innerText = `${summary.bullish_pct || 0}%`;
    if (neuCount) neuCount.innerText = summary.neutral_count || 0;
    if (neuPct) neuPct.innerText = `${summary.neutral_pct || 0}%`;
    if (bearCount) bearCount.innerText = summary.bearish_count || 0;
    if (bearPct) bearPct.innerText = `${summary.bearish_pct || 0}%`;

    const barBull = document.getElementById('sentimentBarBullish');
    const barNeu = document.getElementById('sentimentBarNeutral');
    const barBear = document.getElementById('sentimentBarBearish');

    if (barBull) barBull.style.width = `${summary.bullish_pct || 33.3}%`;
    if (barNeu) barNeu.style.width = `${summary.neutral_pct || 33.3}%`;
    if (barBear) barBear.style.width = `${summary.bearish_pct || 33.3}%`;
}

function renderNewsArticles(articles) {
    const container = document.getElementById('newsArticlesContainer');
    if (!container) return;

    if (!articles || articles.length === 0) {
        container.innerHTML = `
            <div class="news-empty-state">
                <i class="bi bi-search text-muted fs-2 mb-2"></i>
                <h6 class="fw-bold mb-1">No Matching Headlines Located</h6>
                <p class="text-muted small mb-3">No live articles match your current search or filter criteria.</p>
                <button class="btn-pill-action justify-content-center" onclick="clearNewsSearch(); switchNewsCategory('all');">
                    <i class="bi bi-arrow-repeat"></i> Reset All Filters
                </button>
            </div>
        `;
        return;
    }

    const spotlight = articles[0];
    const trending = articles.slice(1, 4);
    const secondary = articles.slice(4);

    let html = '';

    // Top Stories Showcase Row
    html += `
        <div class="row g-4 mb-4">
            <!-- Lead Spotlight Story (Col 8) -->
            <div class="col-lg-8">
                <div class="news-spotlight-card h-100 d-flex flex-column justify-content-between" id="leadSpotlightCard">
                    <div class="news-spotlight-img-wrap" style="min-height: 280px; max-height: 340px;">
                        ${spotlight.thumbnail ? `
                            <img src="${escapeAttr(spotlight.thumbnail)}" alt="${escapeAttr(spotlight.title)}" class="news-spotlight-img" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'news-fallback-placeholder\\'><i class=\\'bi bi-newspaper\\'></i></div>';">
                        ` : `
                            <div class="news-fallback-placeholder">
                                <i class="bi bi-newspaper"></i>
                            </div>
                        `}
                        <div class="news-spotlight-badge-float d-flex gap-2">
                            <span class="badge bg-dark bg-opacity-75 text-light px-2 py-1 backdrop-blur small">
                                <i class="bi bi-star-fill text-warning me-1"></i> TOP STORY
                            </span>
                            <span class="${spotlight.sentiment ? spotlight.sentiment.badge_class : 'badge-neutral-subtle'} px-2 py-1">
                                <i class="bi ${spotlight.sentiment ? spotlight.sentiment.icon : 'bi-dash-lg'} me-1"></i>${spotlight.sentiment ? spotlight.sentiment.label : 'NEUTRAL'}
                            </span>
                        </div>
                    </div>
                    <div class="p-4 d-flex flex-column justify-content-between flex-grow-1">
                        <div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="news-publisher-tag">${escapeHtml(spotlight.publisher || 'Financial Wire')} • ${escapeHtml(spotlight.time_ago || 'Recent')}</span>
                                <span class="badge bg-secondary bg-opacity-25 text-secondary small">${escapeHtml(spotlight.category || 'Markets')}</span>
                            </div>
                            <h3 class="fw-bold mb-2 fs-5">
                                <a href="${escapeAttr(spotlight.url)}" target="_blank" rel="noopener noreferrer" class="text-decoration-none text-reset">
                                    ${escapeHtml(spotlight.title)}
                                </a>
                            </h3>
                            <p class="text-secondary small mb-3" style="line-height: 1.6;">
                                ${escapeHtml(spotlight.summary || 'Institutional market report on financial developments, macroeconomic trends, and equity earnings catalysts.')}
                            </p>
                        </div>
                        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 pt-3 border-top">
                            <div class="d-flex align-items-center gap-2">
                                ${spotlight.symbol && spotlight.symbol !== 'GSPC' && spotlight.symbol !== 'IXIC' ? `
                                    <a href="/stock/${encodeURIComponent(spotlight.symbol)}" class="news-ticker-link" title="Open ${escapeAttr(spotlight.symbol)} Technicals & Forecast">
                                        <i class="bi bi-graph-up text-primary me-1"></i> ${escapeHtml(spotlight.symbol)}
                                    </a>
                                ` : ''}
                                <span class="text-muted small"><i class="bi bi-shield-check text-success me-1"></i> Verified Wire</span>
                            </div>
                            <a href="${escapeAttr(spotlight.url)}" target="_blank" rel="noopener noreferrer" class="news-read-link">
                                Read Full Story <i class="bi bi-box-arrow-up-right"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Trending Highlights Column (Col 4) -->
            <div class="col-lg-4">
                <div class="d-flex flex-column gap-3 h-100 justify-content-between">
                    <div class="d-flex align-items-center gap-2 px-1">
                        <i class="bi bi-lightning-charge-fill text-warning"></i>
                        <h6 class="fw-bold mb-0 text-uppercase small text-muted" style="letter-spacing: 0.05em;">Market Catalysts</h6>
                    </div>

                    ${trending.map(tr => `
                        <div class="terminal-card p-3 d-flex flex-column justify-content-between flex-grow-1">
                            <div>
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <span class="news-publisher-tag text-truncate" style="max-width: 140px;">${escapeHtml(tr.publisher || 'Financial Wire')}</span>
                                    <span class="${tr.sentiment ? tr.sentiment.badge_class : 'badge-neutral-subtle'}" style="font-size: 0.68rem; padding: 0.15rem 0.45rem;">
                                        ${tr.sentiment ? tr.sentiment.label : 'NEUTRAL'}
                                    </span>
                                </div>
                                <h6 class="fw-bold mb-1" style="font-size: 0.88rem; line-height: 1.4;">
                                    <a href="${escapeAttr(tr.url)}" target="_blank" rel="noopener noreferrer" class="text-decoration-none text-reset">
                                        ${escapeHtml(tr.title)}
                                    </a>
                                </h6>
                            </div>
                            <div class="d-flex justify-content-between align-items-center pt-2 mt-2 border-top" style="font-size: 0.75rem;">
                                <span class="text-muted small">${escapeHtml(tr.time_ago || 'Recent')}</span>
                                <a href="${escapeAttr(tr.url)}" target="_blank" rel="noopener noreferrer" class="news-read-link" style="font-size: 0.75rem;">
                                    Read <i class="bi bi-arrow-right"></i>
                                </a>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    // Secondary Stories Grid (Col 4 / Col 6)
    if (secondary.length > 0) {
        html += `<div class="row g-3" id="secondaryNewsGrid">`;
        secondary.forEach(item => {
            html += `
                <div class="col-lg-4 col-md-6 news-card-col" data-title="${escapeAttr((item.title || '').toLowerCase())}" data-publisher="${escapeAttr((item.publisher || '').toLowerCase())}" data-sentiment="${escapeAttr(item.sentiment ? item.sentiment.label : '')}">
                    ${createNewsCardHtml(item)}
                </div>
            `;
        });
        html += `</div>`;
    }

    container.innerHTML = html;
}

function createNewsCardHtml(item) {
    const badgeClass = item.sentiment ? item.sentiment.badge_class : 'badge-neutral-subtle';
    const sentimentIcon = item.sentiment ? item.sentiment.icon : 'bi-dash-lg';
    const sentimentLabel = item.sentiment ? item.sentiment.label : 'NEUTRAL';
    const publisher = escapeHtml(item.publisher || 'Financial Wire');
    const timeAgo = escapeHtml(item.time_ago || 'Recent');
    const title = escapeHtml(item.title || 'Market Update');
    const summary = item.summary ? `<p class="news-card-summary">${escapeHtml(item.summary)}</p>` : '';
    const url = escapeAttr(item.url || '#');
    const symbol = item.symbol && item.symbol !== 'GSPC' && item.symbol !== 'IXIC'
        ? `<a href="/stock/${encodeURIComponent(item.symbol)}" class="news-ticker-link" title="Open ${escapeAttr(item.symbol)} Analysis">${escapeHtml(item.symbol)}</a>`
        : `<span class="badge bg-secondary bg-opacity-15 text-secondary" style="font-size: 0.68rem;">${escapeHtml(item.category || 'News')}</span>`;

    const imgMarkup = item.thumbnail ? `
        <img src="${escapeAttr(item.thumbnail)}" alt="${escapeAttr(item.title)}" class="news-card-img" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'news-fallback-placeholder\\'><i class=\\'bi bi-newspaper\\'></i></div>';">
    ` : `
        <div class="news-fallback-placeholder">
            <i class="bi bi-newspaper"></i>
        </div>
    `;

    return `
        <div class="news-grid-card">
            <div class="news-card-img-wrap">
                ${imgMarkup}
                <div class="position-absolute top-0 end-0 m-2">
                    <span class="${badgeClass}" style="font-size: 0.7rem; padding: 0.15rem 0.5rem;">
                        <i class="bi ${sentimentIcon} me-1"></i>${sentimentLabel}
                    </span>
                </div>
            </div>
            <div class="p-3 d-flex flex-column justify-content-between flex-grow-1">
                <div>
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="news-publisher-tag text-truncate" style="max-width: 160px;">${publisher}</span>
                        <span class="text-muted small" style="font-size: 0.72rem;">${timeAgo}</span>
                    </div>
                    <h6 class="news-card-title" title="${escapeAttr(item.title)}">
                        <a href="${url}" target="_blank" rel="noopener noreferrer" class="text-decoration-none text-reset">
                            ${title}
                        </a>
                    </h6>
                    ${summary}
                </div>
                <div class="news-card-footer mt-auto">
                    <div class="d-flex align-items-center gap-1">
                        ${symbol}
                    </div>
                    <a href="${url}" target="_blank" rel="noopener noreferrer" class="news-read-link">
                        Read <i class="bi bi-box-arrow-up-right"></i>
                    </a>
                </div>
            </div>
        </div>
    `;
}

function createNewsCardElement(item) {
    const col = document.createElement('div');
    col.className = 'col-lg-4 col-md-6 news-card-col news-fade-in';
    col.setAttribute('data-title', (item.title || '').toLowerCase());
    col.setAttribute('data-publisher', (item.publisher || '').toLowerCase());
    col.setAttribute('data-sentiment', item.sentiment ? item.sentiment.label : '');
    col.innerHTML = createNewsCardHtml(item);
    return col;
}

async function fetchMoreNewsStream() {
    if (isFetchingMoreNews || !hasMoreNews) return;
    isFetchingMoreNews = true;

    const loader = document.getElementById('infiniteScrollLoader');
    if (loader) loader.style.display = 'block';

    try {
        const url = `/api/market-news?category=${encodeURIComponent(activeNewsCategory)}&offset=${newsOffset}&limit=12`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const incoming = data.articles || [];
        if (incoming.length > 0) {
            let secondaryGrid = document.getElementById('secondaryNewsGrid');
            if (!secondaryGrid) {
                const container = document.getElementById('newsArticlesContainer');
                if (container) {
                    secondaryGrid = document.createElement('div');
                    secondaryGrid.className = 'row g-3';
                    secondaryGrid.id = 'secondaryNewsGrid';
                    container.appendChild(secondaryGrid);
                }
            }

            const existingUrls = new Set(activeNewsArticles.map(a => a.url).filter(Boolean));
            const existingTitles = new Set(activeNewsArticles.map(a => (a.title || '').trim().toLowerCase()).filter(Boolean));

            incoming.forEach(item => {
                const normTitle = (item.title || '').trim().toLowerCase();
                if (item.url && existingUrls.has(item.url)) return;
                if (normTitle && existingTitles.has(normTitle)) return;

                if (item.url) existingUrls.add(item.url);
                if (normTitle) existingTitles.add(normTitle);
                activeNewsArticles.push(item);

                if (secondaryGrid) {
                    const cardCol = createNewsCardElement(item);
                    if (activeSentimentFilter && item.sentiment && item.sentiment.label !== activeSentimentFilter) {
                        cardCol.style.display = 'none';
                    }
                    if (newsSearchQuery) {
                        const match = (item.title || '').toLowerCase().includes(newsSearchQuery) ||
                                      (item.publisher || '').toLowerCase().includes(newsSearchQuery) ||
                                      (item.symbol || '').toLowerCase().includes(newsSearchQuery);
                        if (!match) cardCol.style.display = 'none';
                    }
                    secondaryGrid.appendChild(cardCol);
                }
            });

            newsOffset += incoming.length;

            const badge = document.getElementById('newsArticleCountBadge');
            if (badge) {
                badge.innerText = `${activeNewsArticles.length} Stories Indexed`;
            }
        }
    } catch (err) {
        console.warn('[InfiniteScroll] Error streaming more market stories:', err);
    } finally {
        if (loader) loader.style.display = 'none';
        isFetchingMoreNews = false;
    }
}

function throttleScrollListener() {
    if (scrollThrottleTimeout) return;
    scrollThrottleTimeout = setTimeout(() => {
        scrollThrottleTimeout = null;
        const scrollPosition = window.innerHeight + window.scrollY;
        const documentHeight = document.documentElement.offsetHeight;
        if (documentHeight - scrollPosition < 800 && !isFetchingMoreNews && hasMoreNews) {
            fetchMoreNewsStream();
        }
    }, 200);
}

function setupInfiniteScroll() {
    const sentinel = document.getElementById('infiniteScrollSentinel');
    if (!sentinel) return;

    if (infiniteScrollObserver) {
        infiniteScrollObserver.disconnect();
    }

    if ('IntersectionObserver' in window) {
        infiniteScrollObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !isFetchingMoreNews && hasMoreNews) {
                    fetchMoreNewsStream();
                }
            });
        }, {
            root: null,
            rootMargin: '500px',
            threshold: 0.01
        });
        infiniteScrollObserver.observe(sentinel);
    }

    window.removeEventListener('scroll', throttleScrollListener);
    window.addEventListener('scroll', throttleScrollListener, { passive: true });
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function escapeAttr(text) {
    if (!text) return '';
    return String(text).replace(/"/g, '&quot;');
}

// Export functions to window
window.switchNewsCategory = switchNewsCategory;
window.filterBySentiment = filterBySentiment;
window.handleNewsSearch = handleNewsSearch;
window.clearNewsSearch = clearNewsSearch;
window.refreshLiveNews = refreshLiveNews;
window.toggleAutoRefresh = toggleAutoRefresh;
window.fetchMoreNewsStream = fetchMoreNewsStream;
window.setupInfiniteScroll = setupInfiniteScroll;

