// ==========================================================================
// AlphaPulse AI — Production Financial Terminal JavaScript
// Features: Instant Search, Plotly Charts, Watchlist, Real-Time Progress
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initSearchAutocomplete();
    initPredictionLoading();
    syncWatchlistBadge();
});

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
                                <span class="fw-bold text-white mono">${item.symbol}</span>
                                <div class="small text-muted">${item.name}</div>
                            </div>
                            <span class="badge bg-dark border border-secondary border-opacity-50 text-light small">${item.market}</span>
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
            
            // Extract ticker from form to poll progress
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
                <h6 class="text-white fw-bold">Your Watchlist is Empty</h6>
                <p class="text-muted small">Click "Watchlist" on any stock detail page to monitor its live performance.</p>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-info mb-2"></div>
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
                        <table class="table table-dark table-hover small mb-0">
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
                                            <a href="/stock/${encodeURIComponent(item.symbol)}" class="text-white fw-bold mono text-decoration-none">
                                                ${item.symbol}
                                            </a>
                                        </td>
                                        <td class="text-truncate" style="max-width: 180px;">${item.name}</td>
                                        <td class="text-end mono fw-bold text-white">${item.currency_symbol}${item.price}</td>
                                        <td class="text-end mono fw-bold ${item.change >= 0 ? 'price-up' : 'price-down'}">
                                            ${item.change >= 0 ? '+' : ''}${item.change} (${item.change >= 0 ? '+' : ''}${item.change_percent}%)
                                        </td>
                                        <td class="text-end">
                                            <a href="/stock/${encodeURIComponent(item.symbol)}" class="btn btn-sm btn-ghost py-1 px-2 me-1" title="View Chart">
                                                <i class="bi bi-graph-up"></i>
                                            </a>
                                            <button class="btn btn-sm btn-ghost text-danger py-1 px-2" onclick="removeFromWatchlist('${item.symbol}')" title="Remove">
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
// 4. Plotly Financial Chart for Stock Detail Page
// ==========================================================================
function renderStockDetailChart(containerId, chartPayload, currencySymbol, mode = 'candlestick') {
    if (!window.Plotly || !chartPayload) return;

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
            fillcolor: 'rgba(0, 240, 255, 0.08)',
            line: { color: '#00F0FF', width: 2 },
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
            increasing: { line: { color: '#00E676', width: 1.5 } },
            decreasing: { line: { color: '#FF3366', width: 1.5 } },
            yaxis: 'y'
        };
    }

    const sma20Trace = {
        x: dates,
        y: sma20,
        type: 'scatter',
        mode: 'lines',
        name: 'SMA 20 (Fast)',
        line: { color: '#00F0FF', width: 1.5 },
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

    const volumeColors = closes.map((c, i) => (i > 0 && c >= closes[i - 1]) ? 'rgba(0, 230, 118, 0.35)' : 'rgba(255, 51, 102, 0.35)');
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
        font: { family: 'Plus Jakarta Sans, sans-serif', color: '#94A3B8' },
        margin: { l: 60, r: 25, t: 25, b: 35 },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            orientation: 'h',
            y: 1.12,
            x: 0,
            font: { color: '#94A3B8', size: 11 }
        },
        xaxis: {
            rangeslider: { visible: false },
            color: '#64748B',
            gridcolor: 'rgba(255, 255, 255, 0.05)',
            rangeselector: {
                buttons: [
                    { count: 1, label: '1M', step: 'month', stepmode: 'backward' },
                    { count: 3, label: '3M', step: 'month', stepmode: 'backward' },
                    { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
                    { count: 1, label: '1Y', step: 'year', stepmode: 'backward' },
                    { step: 'all', label: 'ALL' }
                ],
                bgcolor: '#121824',
                activecolor: '#2563EB',
                font: { color: '#FFFFFF', size: 10 }
            }
        },
        yaxis: {
            title: `Price (${currencySymbol})`,
            color: '#64748B',
            gridcolor: 'rgba(255, 255, 255, 0.05)',
            domain: [0.28, 1]
        },
        yaxis2: {
            title: 'Volume',
            color: '#64748B',
            gridcolor: 'rgba(255, 255, 255, 0.02)',
            domain: [0, 0.22],
            showgrid: false
        }
    };

    const config = { responsive: true, displayModeBar: true, displaylogo: false };
    Plotly.newPlot(containerId, [mainTrace, sma20Trace, sma50Trace, volumeTrace], layout, config);
}

// ==========================================================================
// 5. Plotly Forecast Chart for Prediction Page
// ==========================================================================
function renderPredictionChart(containerId, payload, currencySymbol) {
    if (!window.Plotly || !payload) return;

    const traces = [];

    // 1. Historical Actual Close
    traces.push({
        x: payload.history_dates,
        y: payload.history_prices,
        mode: 'lines',
        name: 'Historical Close',
        line: { color: '#94A3B8', width: 2 },
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
            line: { color: 'rgba(0, 240, 255, 0)' },
            showlegend: false,
            hoverinfo: 'none'
        });

        traces.push({
            x: payload.future_dates,
            y: payload.lower_band,
            mode: 'lines',
            fill: 'tonexty',
            fillcolor: 'rgba(0, 240, 255, 0.12)',
            line: { color: 'rgba(0, 240, 255, 0)' },
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
        line: { color: '#00F0FF', width: 3 },
        marker: { size: 5, color: '#00F0FF' },
        hoverinfo: 'x+y'
    });

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Plus Jakarta Sans, sans-serif', color: '#94A3B8' },
        margin: { l: 60, r: 25, t: 30, b: 35 },
        hovermode: 'x unified',
        showlegend: true,
        legend: {
            orientation: 'h',
            y: 1.12,
            x: 0,
            font: { color: '#94A3B8', size: 11 }
        },
        xaxis: {
            color: '#64748B',
            gridcolor: 'rgba(255, 255, 255, 0.05)',
            title: 'Trading Date'
        },
        yaxis: {
            title: `Stock Price (${currencySymbol})`,
            color: '#64748B',
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        }
    };

    const config = { responsive: true, displayModeBar: true, displaylogo: false };
    Plotly.newPlot(containerId, traces, layout, config);
}
