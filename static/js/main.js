// ==========================================================================
// AlphaPulse AI — Production Financial Terminal JavaScript
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    initSearchAutocomplete();
    initPredictionLoading();
});

// Instant Real-Time Search Autocomplete
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

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });

    // Enter key navigation to custom ticker
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

// Show Neural Loading Overlay on Form Submit
function initPredictionLoading() {
    const predictForms = document.querySelectorAll('.predict-form');
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;

    predictForms.forEach(form => {
        form.addEventListener('submit', () => {
            overlay.style.display = 'flex';
        });
    });
}

// Plotly Financial Chart for Stock Detail Page (Candlestick / Area + Volume + Moving Averages)
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

// Plotly Forecast Chart for Prediction Page (Historical + Test Fit + AI Forecast + 95% Confidence Cone)
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
    // Connect smoothly to the last historical price
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
