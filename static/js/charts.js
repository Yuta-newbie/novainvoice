/**
 * NovaInvoice Chart.js Configurations
 * Custom dark warm mocha theme.
 * Strictly zero emojis.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Dashboard Mini Trend Chart
    const dashCanvas = document.getElementById('dashboardSalesChart');
    if (dashCanvas && window.dashboardChartData) {
        initDashboardChart(dashCanvas, window.dashboardChartData);
    }

    // 2. Full Analytics Charts
    const analyticsContainer = document.getElementById('analytics-charts-wrapper');
    if (analyticsContainer) {
        loadAnalyticsCharts();
    }
});

function initDashboardChart(canvas, data) {
    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Daily Sales (₹)',
                data: data.sales,
                borderColor: '#D97706',
                backgroundColor: 'rgba(217, 119, 6, 0.12)',
                fill: true,
                tension: 0.3,
                borderWidth: 2,
                pointBackgroundColor: '#D97706',
                pointRadius: 3,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1C1814',
                    titleColor: '#FAF7F2',
                    bodyColor: '#D4A373',
                    borderColor: '#382F27',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function (ctx) {
                            return ' Sales: ₹' + ctx.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 });
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: '#27201A' },
                    ticks: { color: '#84766A', font: { size: 11 } }
                },
                y: {
                    grid: { color: '#27201A' },
                    ticks: {
                        color: '#84766A',
                        font: { size: 11 },
                        callback: function (val) {
                            return '₹' + (val / 1000).toFixed(0) + 'k';
                        }
                    }
                }
            }
        }
    });
}

function loadAnalyticsCharts() {
    fetch('/analytics/api/chart-data')
        .then(response => response.json())
        .then(data => {
            // Chart 1: Historical Sales Trend
            const histCanvas = document.getElementById('historicalSalesChart');
            if (histCanvas && data.historical) {
                new Chart(histCanvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: data.historical.labels,
                        datasets: [{
                            label: 'Historical Taxable Sales (₹)',
                            data: data.historical.sales,
                            borderColor: '#D97706',
                            backgroundColor: 'rgba(217, 119, 6, 0.1)',
                            fill: true,
                            tension: 0.25,
                            borderWidth: 1.8,
                            pointRadius: 2.5
                        }]
                    },
                    options: getChartOptions('Sales (₹)')
                });
            }

            // Chart 2: Test Set Evaluation (Actual vs Predicted)
            const evalCanvas = document.getElementById('evalComparisonChart');
            if (evalCanvas && data.evaluation) {
                new Chart(evalCanvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: data.evaluation.labels,
                        datasets: [
                            {
                                label: 'Actual Sales (Unseen Test Data)',
                                data: data.evaluation.actual,
                                borderColor: '#10B981',
                                backgroundColor: 'transparent',
                                borderWidth: 2,
                                pointRadius: 3
                            },
                            {
                                label: 'Predicted Sales (Linear Regression)',
                                data: data.evaluation.predicted,
                                borderColor: '#D97706',
                                backgroundColor: 'transparent',
                                borderDash: [5, 5],
                                borderWidth: 2,
                                pointRadius: 3
                            }
                        ]
                    },
                    options: getChartOptions('Sales (₹)')
                });
            }

            // Chart 3: Future Forecast
            const forecastCanvas = document.getElementById('futureForecastChart');
            if (forecastCanvas && data.forecast) {
                new Chart(forecastCanvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: data.forecast.labels,
                        datasets: [{
                            label: 'Future Forecast (Estimate)',
                            data: data.forecast.sales,
                            borderColor: '#F59E0B',
                            backgroundColor: 'rgba(245, 158, 11, 0.15)',
                            fill: true,
                            borderDash: [4, 4],
                            borderWidth: 2.5,
                            pointRadius: 5,
                            pointBackgroundColor: '#F59E0B'
                        }]
                    },
                    options: getChartOptions('Predicted Daily Sales (₹)')
                });
            }
        })
        .catch(err => console.error('Error fetching analytics chart data:', err));
}

function getChartOptions(yLabel) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false
        },
        plugins: {
            legend: {
                labels: {
                    color: '#BAACA0',
                    font: { size: 12, weight: '500' },
                    boxWidth: 14
                }
            },
            tooltip: {
                backgroundColor: '#1C1814',
                titleColor: '#FAF7F2',
                bodyColor: '#D4A373',
                borderColor: '#382F27',
                borderWidth: 1,
                padding: 10,
                callbacks: {
                    label: function (ctx) {
                        return ' ' + ctx.dataset.label + ': ₹' + ctx.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 });
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { color: '#27201A' },
                ticks: { color: '#84766A', font: { size: 11 }, maxRotation: 45 }
            },
            y: {
                grid: { color: '#27201A' },
                ticks: {
                    color: '#84766A',
                    font: { size: 11 },
                    callback: function (val) {
                        return '₹' + (val / 1000).toFixed(0) + 'k';
                    }
                }
            }
        }
    };
}

