"""
Interactive Benchmark Visualization Dashboard - Enhanced UI

Creates beautiful interactive graphs for Lucene search benchmark results.
"""

import os
import sys
from pathlib import Path

import pandas as pd

RESULTS_DIR = "results"


def load_summary():
    """Load the summary CSV."""
    summary_path = Path(RESULTS_DIR) / "summary.csv"
    if not summary_path.exists():
        print(f"Error: {summary_path} not found. Run the benchmark first.")
        sys.exit(1)
    return pd.read_csv(summary_path)


def load_all_benchmarks():
    """Load all individual benchmark CSVs."""
    results_dir = Path(RESULTS_DIR)
    all_data = []

    for csv_file in sorted(results_dir.glob("benchmark_*_pdfs.csv")):
        print(f"  Loading {csv_file.name}...")
        df = pd.read_csv(csv_file)
        pdf_count = int(csv_file.stem.split("_")[1])
        df["pdf_count"] = pdf_count
        all_data.append(df)

    if not all_data:
        print("Error: No benchmark CSV files found.")
        sys.exit(1)

    combined = pd.concat(all_data, ignore_index=True)
    return combined


def create_enhanced_dashboard(summary_df, benchmark_df):
    """Create a beautiful enhanced HTML dashboard."""

    # Filter valid data
    df = benchmark_df[(benchmark_df["success"] == True) & (benchmark_df["run"] > 2)].copy()

    # Get unique values for filters
    pdf_counts = sorted(df["pdf_count"].unique())
    queries = sorted(df["query"].unique())
    topk_values = sorted(df["top_k"].unique())

    # Convert to JSON
    df_json = df.to_json(orient='records')
    summary_json = summary_df.to_json(orient='records')

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucene Benchmark Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --bg-card-hover: #22222f;
            --accent-primary: #6366f1;
            --accent-secondary: #8b5cf6;
            --accent-tertiary: #06b6d4;
            --accent-success: #10b981;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #2d2d3a;
            --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            --shadow-glow: 0 0 40px rgba(99, 102, 241, 0.15);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }}

        /* Animated Background */
        .bg-gradient {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background:
                radial-gradient(ellipse at 20% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(6, 182, 212, 0.05) 0%, transparent 70%);
            z-index: -1;
            animation: gradientShift 15s ease infinite;
        }}

        @keyframes gradientShift {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}

        /* Container */
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 30px;
        }}

        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
        }}

        .header h1 {{
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary), var(--accent-tertiary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 15px;
            letter-spacing: -1px;
        }}

        .header p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 400;
        }}

        .header .badge {{
            display: inline-block;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            padding: 8px 20px;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 20px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }}

        /* Filter Panel */
        .filter-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: var(--shadow-lg);
        }}

        .filter-panel h3 {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .filter-panel h3 i {{
            color: var(--accent-primary);
        }}

        .filters {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: flex-end;
        }}

        .filter-group {{
            flex: 1;
            min-width: 200px;
        }}

        .filter-group label {{
            display: block;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        select {{
            width: 100%;
            padding: 12px 16px;
            border-radius: 12px;
            border: 2px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 0.95rem;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.3s ease;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            background-size: 20px;
        }}

        select:hover {{
            border-color: var(--accent-primary);
        }}

        select:focus {{
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }}

        .btn-group {{
            display: flex;
            gap: 12px;
        }}

        .btn {{
            padding: 12px 28px;
            border-radius: 12px;
            border: none;
            font-size: 0.95rem;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-primary {{
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }}

        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }}

        .btn-secondary {{
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border: 2px solid var(--border-color);
        }}

        .btn-secondary:hover {{
            border-color: var(--accent-primary);
            color: var(--text-primary);
        }}

        /* Stats Section */
        .stats-section {{
            margin-bottom: 30px;
        }}

        .section-label {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-label i {{
            color: var(--accent-primary);
        }}

        .section-label .hint {{
            font-weight: 400;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        .filter-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-left: 10px;
            transition: all 0.3s ease;
        }}

        .filter-badge.overall {{
            background: linear-gradient(135deg, var(--accent-success), #059669);
            color: white;
        }}

        .filter-badge.filtered {{
            background: linear-gradient(135deg, var(--accent-warning), #d97706);
            color: white;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
        }}

        .fixed-stats .stat-card {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.08));
        }}

        .stat-card.dynamic {{
            border-left: 3px solid var(--accent-tertiary);
        }}

        .stat-card.fixed {{
            border-left: 3px solid var(--accent-secondary);
            opacity: 0.9;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 28px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: var(--shadow-glow);
            border-color: var(--accent-primary);
        }}

        .stat-card:hover::before {{
            opacity: 1;
        }}

        .stat-card .icon {{
            width: 50px;
            height: 50px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            margin-bottom: 18px;
        }}

        .stat-card:nth-child(1) .icon {{ background: rgba(99, 102, 241, 0.15); color: var(--accent-primary); }}
        .stat-card:nth-child(2) .icon {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-success); }}
        .stat-card:nth-child(3) .icon {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-warning); }}
        .stat-card:nth-child(4) .icon {{ background: rgba(6, 182, 212, 0.15); color: var(--accent-tertiary); }}
        .stat-card:nth-child(5) .icon {{ background: rgba(139, 92, 246, 0.15); color: var(--accent-secondary); }}

        .stat-card .value {{
            font-size: 2.2rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 6px;
            background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .stat-card .label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Chart Card */
        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 28px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-lg);
            transition: all 0.3s ease;
        }}

        .chart-card:hover {{
            border-color: rgba(99, 102, 241, 0.3);
        }}

        .chart-card .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }}

        .chart-card .chart-title {{
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .chart-card .chart-title i {{
            color: var(--accent-primary);
            font-size: 1.1rem;
        }}

        .chart-card .chart-subtitle {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}

        .chart {{
            width: 100%;
            height: 400px;
        }}

        .chart-large {{
            height: 500px;
        }}

        .chart-xl {{
            height: 600px;
        }}

        /* Grid Layouts */
        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }}

        /* Summary Table */
        .table-container {{
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--border-color);
        }}

        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }}

        .summary-table th {{
            background: var(--bg-secondary);
            padding: 16px 20px;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
            border-bottom: 2px solid var(--border-color);
        }}

        .summary-table td {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
        }}

        .summary-table tr:hover td {{
            background: var(--bg-card-hover);
        }}

        .summary-table tr:last-child td {{
            border-bottom: none;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 40px 0;
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .footer a {{
            color: var(--accent-primary);
            text-decoration: none;
        }}

        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .chart-card, .stat-card, .filter-panel {{
            animation: fadeIn 0.5s ease forwards;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .container {{ padding: 15px; }}
            .header h1 {{ font-size: 2rem; }}
            .filters {{ flex-direction: column; }}
            .filter-group {{ min-width: 100%; }}
            .grid-2 {{ grid-template-columns: 1fr; }}
            .stat-card .value {{ font-size: 1.8rem; }}
        }}
    </style>
</head>
<body>
    <div class="bg-gradient"></div>

    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1><i class="fas fa-bolt"></i> Lucene Benchmark Dashboard</h1>
            <p>Performance analysis across {len(pdf_counts)} index sizes with {len(df):,} data points</p>
            <span class="badge"><i class="fas fa-database"></i> {df['pdf_count'].max():,} PDFs | {summary_df['chunk_count'].max():,} Chunks | {summary_df['token_count'].max()/1e6:.1f}M Tokens</span>
        </header>

        <!-- Filters -->
        <div class="filter-panel">
            <h3><i class="fas fa-sliders-h"></i> Filters & Controls</h3>
            <div class="filters">
                <div class="filter-group">
                    <label>PDF Count</label>
                    <select id="pdfFilter">
                        <option value="all">All Sizes</option>
                        {"".join(f'<option value="{p}">{p:,} PDFs</option>' for p in pdf_counts)}
                    </select>
                </div>
                <div class="filter-group">
                    <label>TopK Value</label>
                    <select id="topkFilter">
                        <option value="all">All TopK</option>
                        {"".join(f'<option value="{t}">TopK = {t}</option>' for t in topk_values)}
                    </select>
                </div>
                <div class="filter-group">
                    <label>Query</label>
                    <select id="queryFilter">
                        <option value="all">All Queries</option>
                        {"".join(f'<option value="{q}">{q}</option>' for q in queries)}
                    </select>
                </div>
                <div class="filter-group">
                    <label>&nbsp;</label>
                    <div class="btn-group">
                        <button class="btn btn-primary" onclick="applyFilters()">
                            <i class="fas fa-filter"></i> Apply
                        </button>
                        <button class="btn btn-secondary" onclick="resetFilters()">
                            <i class="fas fa-redo"></i> Reset
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Dynamic Stats (changes with filters) -->
        <div class="stats-section">
            <h3 class="section-label">
                <i class="fas fa-sync-alt"></i>
                <span id="statsTitle">Overall Stats</span>
                <span class="filter-badge" id="filterBadge"></span>
            </h3>
            <div class="stats-grid">
                <div class="stat-card dynamic">
                    <div class="icon"><i class="fas fa-search"></i></div>
                    <div class="value" id="totalQueries">0</div>
                    <div class="label">API Calls</div>
                </div>
                <div class="stat-card dynamic">
                    <div class="icon"><i class="fas fa-tachometer-alt"></i></div>
                    <div class="value" id="avgLatency">0 ms</div>
                    <div class="label">Avg Latency</div>
                </div>
                <div class="stat-card dynamic">
                    <div class="icon"><i class="fas fa-percentage"></i></div>
                    <div class="value" id="p50Latency">0 ms</div>
                    <div class="label">P50 (Median)</div>
                </div>
                <div class="stat-card dynamic">
                    <div class="icon"><i class="fas fa-chart-line"></i></div>
                    <div class="value" id="p95Latency">0 ms</div>
                    <div class="label">P95 Latency</div>
                </div>
                <div class="stat-card dynamic">
                    <div class="icon"><i class="fas fa-arrow-down"></i></div>
                    <div class="value" id="minLatency">0 ms</div>
                    <div class="label">Min Latency</div>
                </div>
                <div class="stat-card dynamic">
                    <div class="icon"><i class="fas fa-arrow-up"></i></div>
                    <div class="value" id="maxLatency">0 ms</div>
                    <div class="label">Max Latency</div>
                </div>
            </div>
        </div>

        <!-- Fixed Stats (overall metrics - never change) -->
        <div class="stats-section">
            <h3 class="section-label"><i class="fas fa-lock"></i> Overall Stats <span class="hint">(fixed - entire dataset)</span></h3>
            <div class="stats-grid fixed-stats">
                <div class="stat-card fixed">
                    <div class="icon"><i class="fas fa-database"></i></div>
                    <div class="value">{len(df):,}</div>
                    <div class="label">Total Records</div>
                </div>
                <div class="stat-card fixed">
                    <div class="icon"><i class="fas fa-cubes"></i></div>
                    <div class="value">{summary_df['chunk_count'].max():,}</div>
                    <div class="label">Max Chunks</div>
                </div>
                <div class="stat-card fixed">
                    <div class="icon"><i class="fas fa-coins"></i></div>
                    <div class="value">{summary_df['token_count'].max()/1e6:.1f}M</div>
                    <div class="label">Max Tokens</div>
                </div>
                <div class="stat-card fixed">
                    <div class="icon"><i class="fas fa-hdd"></i></div>
                    <div class="value">{summary_df['index_size_mb'].max():.1f} MB</div>
                    <div class="label">Max Index Size</div>
                </div>
                <div class="stat-card fixed">
                    <div class="icon"><i class="fas fa-rocket"></i></div>
                    <div class="value">{summary_df['throughput_qps'].mean():.1f}</div>
                    <div class="label">Avg QPS</div>
                </div>
            </div>
        </div>

        <!-- Summary Table -->
        <div class="chart-card">
            <div class="chart-header">
                <div>
                    <div class="chart-title"><i class="fas fa-table"></i> Benchmark Summary</div>
                    <div class="chart-subtitle">Performance metrics by index size</div>
                </div>
            </div>
            <div class="table-container">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>PDFs</th>
                            <th>Chunks</th>
                            <th>Tokens</th>
                            <th>Index Size</th>
                            <th>Avg Latency</th>
                            <th>P50</th>
                            <th>P95</th>
                            <th>P99</th>
                            <th>Throughput</th>
                        </tr>
                    </thead>
                    <tbody id="summaryTableBody"></tbody>
                </table>
            </div>
        </div>

        <!-- Charts Row 1 -->
        <div class="grid-2">
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title"><i class="fas fa-wave-square"></i> Latency Percentiles</div>
                        <div class="chart-subtitle">Response time distribution by index size</div>
                    </div>
                </div>
                <div id="latency-chart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title"><i class="fas fa-tachometer-alt"></i> Throughput</div>
                        <div class="chart-subtitle">Queries per second by index size</div>
                    </div>
                </div>
                <div id="throughput-chart" class="chart"></div>
            </div>
        </div>

        <!-- Charts Row 2 -->
        <div class="grid-2">
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title"><i class="fas fa-box"></i> Latency Distribution</div>
                        <div class="chart-subtitle">Box plot showing spread and outliers</div>
                    </div>
                </div>
                <div id="boxplot-chart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title"><i class="fas fa-layer-group"></i> TopK Impact</div>
                        <div class="chart-subtitle">Latency variation by result count</div>
                    </div>
                </div>
                <div id="topk-chart" class="chart"></div>
            </div>
        </div>

        <!-- Scatter Plot -->
        <div class="chart-card">
            <div class="chart-header">
                <div>
                    <div class="chart-title"><i class="fas fa-braille"></i> All Data Points</div>
                    <div class="chart-subtitle">Every query execution - hover for details</div>
                </div>
            </div>
            <div id="scatter-chart" class="chart-xl"></div>
        </div>

        <!-- Charts Row 3 -->
        <div class="grid-2">
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title"><i class="fas fa-chart-area"></i> Index Growth</div>
                        <div class="chart-subtitle">Chunks and size scaling</div>
                    </div>
                </div>
                <div id="growth-chart" class="chart"></div>
            </div>
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <div class="chart-title"><i class="fas fa-chart-bar"></i> Latency Histogram</div>
                        <div class="chart-subtitle">Frequency distribution of response times</div>
                    </div>
                </div>
                <div id="histogram-chart" class="chart"></div>
            </div>
        </div>

        <!-- Heatmap -->
        <div class="chart-card">
            <div class="chart-header">
                <div>
                    <div class="chart-title"><i class="fas fa-th"></i> Query Performance Heatmap</div>
                    <div class="chart-subtitle">Average latency by query and TopK value</div>
                </div>
            </div>
            <div id="heatmap-chart" class="chart-xl"></div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <p>Built with <i class="fas fa-heart" style="color: var(--accent-danger);"></i> using Plotly.js</p>
            <p style="margin-top: 8px;">Lucene Search Service Benchmark Suite</p>
        </footer>
    </div>

    <script>
        // Data
        const allData = {df_json};
        const summaryData = {summary_json};
        let filteredData = [...allData];

        // Enhanced color palette
        const colors = {{
            primary: '#6366f1',
            secondary: '#8b5cf6',
            tertiary: '#06b6d4',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            chart: ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6']
        }};

        // Chart layout defaults
        const layoutDefaults = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ family: 'Inter, sans-serif', color: '#f8fafc', size: 12 }},
            margin: {{ t: 20, r: 20, b: 50, l: 60 }},
            xaxis: {{
                gridcolor: 'rgba(255,255,255,0.06)',
                linecolor: 'rgba(255,255,255,0.1)',
                tickfont: {{ size: 11 }}
            }},
            yaxis: {{
                gridcolor: 'rgba(255,255,255,0.06)',
                linecolor: 'rgba(255,255,255,0.1)',
                tickfont: {{ size: 11 }}
            }},
            hoverlabel: {{
                bgcolor: '#1a1a25',
                bordercolor: '#6366f1',
                font: {{ family: 'Inter, sans-serif', size: 13 }}
            }}
        }};

        // Initialize
        function init() {{
            updateStats();
            updateSummaryTable();
            renderAllCharts();
        }}

        // Apply filters
        function applyFilters() {{
            const pdf = document.getElementById('pdfFilter').value;
            const topk = document.getElementById('topkFilter').value;
            const query = document.getElementById('queryFilter').value;

            filteredData = allData.filter(d => {{
                let match = true;
                if (pdf !== 'all') match = match && d.pdf_count === parseInt(pdf);
                if (topk !== 'all') match = match && d.top_k === parseInt(topk);
                if (query !== 'all') match = match && d.query === query;
                return match;
            }});

            updateStats();
            renderAllCharts();
        }}

        // Reset filters
        function resetFilters() {{
            document.getElementById('pdfFilter').value = 'all';
            document.getElementById('topkFilter').value = 'all';
            document.getElementById('queryFilter').value = 'all';
            filteredData = [...allData];
            updateStats();
            renderAllCharts();
        }}

        // Update dynamic stats (these change with filters)
        function updateStats() {{
            const titleEl = document.getElementById('statsTitle');
            const badgeEl = document.getElementById('filterBadge');
            const pdf = document.getElementById('pdfFilter').value;
            const topk = document.getElementById('topkFilter').value;
            const query = document.getElementById('queryFilter').value;

            // Check if all filters are set to "all"
            const isOverall = (pdf === 'all' && topk === 'all' && query === 'all');

            if (isOverall) {{
                titleEl.textContent = 'Overall Stats';
                badgeEl.textContent = 'All Data';
                badgeEl.className = 'filter-badge overall';
            }} else {{
                // Build filter description
                const filters = [];
                if (pdf !== 'all') filters.push(pdf + ' PDFs');
                if (topk !== 'all') filters.push('TopK=' + topk);
                if (query !== 'all') filters.push('"' + query.substring(0, 20) + '..."');

                titleEl.textContent = 'Filtered Stats';
                badgeEl.textContent = filters.join(' | ');
                badgeEl.className = 'filter-badge filtered';
            }}

            if (filteredData.length === 0) {{
                document.getElementById('totalQueries').textContent = '0';
                document.getElementById('avgLatency').textContent = '-';
                document.getElementById('p50Latency').textContent = '-';
                document.getElementById('p95Latency').textContent = '-';
                document.getElementById('minLatency').textContent = '-';
                document.getElementById('maxLatency').textContent = '-';
                return;
            }}

            const latencies = filteredData.map(d => d.api_latency_ms);
            const avg = latencies.reduce((a,b) => a+b, 0) / latencies.length;
            const sorted = [...latencies].sort((a,b) => a-b);
            const p50 = sorted[Math.floor(sorted.length * 0.50)];
            const p95 = sorted[Math.floor(sorted.length * 0.95)];
            const minLat = sorted[0];
            const maxLat = sorted[sorted.length - 1];

            // Update dynamic stat cards
            document.getElementById('totalQueries').textContent = filteredData.length.toLocaleString();
            document.getElementById('avgLatency').textContent = avg.toFixed(2) + ' ms';
            document.getElementById('p50Latency').textContent = p50.toFixed(2) + ' ms';
            document.getElementById('p95Latency').textContent = p95.toFixed(2) + ' ms';
            document.getElementById('minLatency').textContent = minLat.toFixed(2) + ' ms';
            document.getElementById('maxLatency').textContent = maxLat.toFixed(2) + ' ms';
        }}

        // Update table
        function updateSummaryTable() {{
            document.getElementById('summaryTableBody').innerHTML = summaryData.map(d => `
                <tr>
                    <td>${{d.pdf_count.toLocaleString()}}</td>
                    <td>${{d.chunk_count.toLocaleString()}}</td>
                    <td>${{(d.token_count/1e6).toFixed(1)}}M</td>
                    <td>${{d.index_size_mb.toFixed(1)}} MB</td>
                    <td>${{d.avg_latency_ms.toFixed(2)}} ms</td>
                    <td>${{d.p50_latency_ms.toFixed(2)}} ms</td>
                    <td>${{d.p95_latency_ms.toFixed(2)}} ms</td>
                    <td>${{d.p99_latency_ms.toFixed(2)}} ms</td>
                    <td>${{d.throughput_qps.toFixed(1)}} QPS</td>
                </tr>
            `).join('');
        }}

        // Render all charts
        function renderAllCharts() {{
            renderLatencyChart();
            renderThroughputChart();
            renderBoxPlot();
            renderTopKChart();
            renderScatterPlot();
            renderGrowthChart();
            renderHistogram();
            renderHeatmap();
        }}

        // Latency chart
        function renderLatencyChart() {{
            const traces = [
                {{ name: 'Average', y: summaryData.map(d => d.avg_latency_ms), line: {{ color: colors.chart[0], width: 3 }}, marker: {{ size: 10 }} }},
                {{ name: 'P50', y: summaryData.map(d => d.p50_latency_ms), line: {{ color: colors.chart[1], width: 2 }}, marker: {{ size: 8 }} }},
                {{ name: 'P95', y: summaryData.map(d => d.p95_latency_ms), line: {{ color: colors.chart[2], width: 2 }}, marker: {{ size: 8 }} }},
                {{ name: 'P99', y: summaryData.map(d => d.p99_latency_ms), line: {{ color: colors.chart[3], width: 2 }}, marker: {{ size: 8 }} }}
            ].map(t => ({{ ...t, x: summaryData.map(d => d.pdf_count), type: 'scatter', mode: 'lines+markers' }}));

            Plotly.newPlot('latency-chart', traces, {{
                ...layoutDefaults,
                xaxis: {{ ...layoutDefaults.xaxis, title: 'Number of PDFs' }},
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Latency (ms)' }},
                legend: {{ x: 0, y: 1, bgcolor: 'rgba(0,0,0,0)' }},
                hovermode: 'x unified'
            }});
        }}

        // Throughput chart
        function renderThroughputChart() {{
            Plotly.newPlot('throughput-chart', [{{
                x: summaryData.map(d => d.pdf_count + ' PDFs'),
                y: summaryData.map(d => d.throughput_qps),
                type: 'bar',
                marker: {{
                    color: colors.chart,
                    line: {{ color: 'rgba(255,255,255,0.2)', width: 1 }}
                }},
                text: summaryData.map(d => d.throughput_qps.toFixed(1) + ' QPS'),
                textposition: 'outside',
                textfont: {{ color: '#f8fafc', size: 12 }}
            }}], {{
                ...layoutDefaults,
                xaxis: {{ ...layoutDefaults.xaxis, title: 'Index Size' }},
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Throughput (QPS)' }}
            }});
        }}

        // Box plot
        function renderBoxPlot() {{
            const pdfCounts = [...new Set(filteredData.map(d => d.pdf_count))].sort((a,b) => a-b);
            const traces = pdfCounts.map((pdf, i) => ({{
                y: filteredData.filter(d => d.pdf_count === pdf).map(d => d.api_latency_ms),
                name: pdf + ' PDFs',
                type: 'box',
                marker: {{ color: colors.chart[i % colors.chart.length] }},
                boxpoints: 'outliers'
            }}));

            Plotly.newPlot('boxplot-chart', traces, {{
                ...layoutDefaults,
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Latency (ms)' }},
                showlegend: true,
                legend: {{ x: 0, y: 1, bgcolor: 'rgba(0,0,0,0)' }}
            }});
        }}

        // TopK chart
        function renderTopKChart() {{
            const pdfCounts = [...new Set(filteredData.map(d => d.pdf_count))].sort((a,b) => a-b);
            const topks = [...new Set(filteredData.map(d => d.top_k))].sort((a,b) => a-b);

            const traces = pdfCounts.map((pdf, i) => {{
                const pdfData = filteredData.filter(d => d.pdf_count === pdf);
                return {{
                    x: topks,
                    y: topks.map(tk => {{
                        const vals = pdfData.filter(d => d.top_k === tk).map(d => d.api_latency_ms);
                        return vals.length ? vals.reduce((a,b) => a+b) / vals.length : 0;
                    }}),
                    name: pdf + ' PDFs',
                    type: 'scatter',
                    mode: 'lines+markers',
                    line: {{ color: colors.chart[i % colors.chart.length], width: 2 }},
                    marker: {{ size: 8 }}
                }};
            }});

            Plotly.newPlot('topk-chart', traces, {{
                ...layoutDefaults,
                xaxis: {{ ...layoutDefaults.xaxis, title: 'TopK Value' }},
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Avg Latency (ms)' }},
                legend: {{ x: 0, y: 1, bgcolor: 'rgba(0,0,0,0)' }},
                hovermode: 'x unified'
            }});
        }}

        // Scatter plot
        function renderScatterPlot() {{
            Plotly.newPlot('scatter-chart', [{{
                x: filteredData.map((d, i) => i),
                y: filteredData.map(d => d.api_latency_ms),
                mode: 'markers',
                type: 'scatter',
                marker: {{
                    size: 4,
                    color: filteredData.map(d => d.pdf_count),
                    colorscale: [[0, '#6366f1'], [0.5, '#10b981'], [1, '#f59e0b']],
                    showscale: true,
                    colorbar: {{ title: 'PDFs', tickfont: {{ color: '#f8fafc' }}, titlefont: {{ color: '#f8fafc' }} }}
                }},
                text: filteredData.map(d =>
                    `<b>${{d.query}}</b><br>PDFs: ${{d.pdf_count}}<br>TopK: ${{d.top_k}}<br>Latency: ${{d.api_latency_ms.toFixed(2)}}ms`
                ),
                hoverinfo: 'text'
            }}], {{
                ...layoutDefaults,
                xaxis: {{ ...layoutDefaults.xaxis, title: 'Query Index' }},
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Latency (ms)' }}
            }});
        }}

        // Growth chart
        function renderGrowthChart() {{
            Plotly.newPlot('growth-chart', [
                {{
                    x: summaryData.map(d => d.pdf_count),
                    y: summaryData.map(d => d.chunk_count),
                    name: 'Chunks',
                    type: 'scatter',
                    mode: 'lines+markers',
                    line: {{ color: colors.primary, width: 3 }},
                    marker: {{ size: 10 }}
                }},
                {{
                    x: summaryData.map(d => d.pdf_count),
                    y: summaryData.map(d => d.index_size_mb),
                    name: 'Size (MB)',
                    type: 'scatter',
                    mode: 'lines+markers',
                    line: {{ color: colors.success, width: 3 }},
                    marker: {{ size: 10 }},
                    yaxis: 'y2'
                }}
            ], {{
                ...layoutDefaults,
                xaxis: {{ ...layoutDefaults.xaxis, title: 'Number of PDFs' }},
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Chunk Count', titlefont: {{ color: colors.primary }} }},
                yaxis2: {{
                    title: 'Index Size (MB)',
                    titlefont: {{ color: colors.success }},
                    tickfont: {{ color: colors.success }},
                    overlaying: 'y',
                    side: 'right',
                    gridcolor: 'rgba(255,255,255,0.03)'
                }},
                legend: {{ x: 0.1, y: 1, bgcolor: 'rgba(0,0,0,0)' }}
            }});
        }}

        // Histogram - manually computed bins for proper display
        function renderHistogram() {{
            const binSize = 5; // 5ms bins
            const maxBin = 80; // Cap at 80ms
            const binEdges = [];
            for (let i = 0; i <= maxBin; i += binSize) binEdges.push(i);
            const binLabels = binEdges.slice(0, -1).map((b, i) => b + '-' + binEdges[i+1]);

            const pdfCounts = [...new Set(filteredData.map(d => d.pdf_count))].sort((a,b) => a-b);
            const histColors = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6'];

            const traces = pdfCounts.map((pdf, idx) => {{
                const pdfLatencies = filteredData.filter(d => d.pdf_count === pdf).map(d => d.api_latency_ms);

                // Count values in each bin
                const counts = new Array(binEdges.length - 1).fill(0);
                pdfLatencies.forEach(lat => {{
                    const binIdx = Math.min(Math.floor(lat / binSize), counts.length - 1);
                    if (binIdx >= 0) counts[binIdx]++;
                }});

                return {{
                    x: binLabels,
                    y: counts,
                    type: 'bar',
                    name: pdf + ' PDFs',
                    marker: {{
                        color: histColors[idx % histColors.length],
                        line: {{ color: 'rgba(255,255,255,0.2)', width: 1 }}
                    }}
                }};
            }});

            Plotly.newPlot('histogram-chart', traces, {{
                ...layoutDefaults,
                xaxis: {{
                    ...layoutDefaults.xaxis,
                    title: 'Latency Range (ms)',
                    tickangle: -45
                }},
                yaxis: {{ ...layoutDefaults.yaxis, title: 'Count' }},
                barmode: 'stack',
                legend: {{ x: 0.75, y: 0.95, bgcolor: 'rgba(26,26,37,0.9)', font: {{ size: 11 }} }},
                bargap: 0.1
            }});
        }}

        // Heatmap
        function renderHeatmap() {{
            const queries = [...new Set(filteredData.map(d => d.query))];
            const topks = [...new Set(filteredData.map(d => d.top_k))].sort((a,b) => a-b);

            const z = queries.map(q => topks.map(tk => {{
                const vals = filteredData.filter(d => d.query === q && d.top_k === tk).map(d => d.api_latency_ms);
                return vals.length ? vals.reduce((a,b) => a+b) / vals.length : 0;
            }}));

            Plotly.newPlot('heatmap-chart', [{{
                z: z,
                x: topks.map(t => 'TopK=' + t),
                y: queries.map(q => q.length > 30 ? q.substring(0, 30) + '...' : q),
                type: 'heatmap',
                colorscale: [[0, '#10b981'], [0.5, '#f59e0b'], [1, '#ef4444']],
                colorbar: {{ title: 'Latency (ms)', tickfont: {{ color: '#f8fafc' }}, titlefont: {{ color: '#f8fafc' }} }}
            }}], {{
                ...layoutDefaults,
                xaxis: {{ ...layoutDefaults.xaxis, title: 'TopK Value', side: 'bottom' }},
                yaxis: {{ ...layoutDefaults.yaxis, title: '', tickfont: {{ size: 10 }}, automargin: true }},
                margin: {{ t: 20, r: 80, b: 60, l: 250 }}
            }});
        }}

        // Initialize on load
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>'''

    return html_content


def main():
    print("=" * 60)
    print("  Lucene Benchmark Dashboard Generator")
    print("=" * 60)

    print("\n[*] Loading benchmark data...")
    summary_df = load_summary()
    benchmark_df = load_all_benchmarks()

    print(f"\n[+] Loaded {len(summary_df)} index sizes")
    print(f"[+] Loaded {len(benchmark_df):,} benchmark records")

    print("\n[*] Generating enhanced dashboard...")
    html_content = create_enhanced_dashboard(summary_df, benchmark_df)

    output_path = Path(RESULTS_DIR) / "dashboard.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    size_kb = output_path.stat().st_size / 1024
    print(f"\n[+] Dashboard saved: {output_path}")
    print(f"[+] File size: {size_kb:.1f} KB")

    import webbrowser
    webbrowser.open(str(output_path.absolute()))
    print("\n[+] Opened in browser!")


if __name__ == "__main__":
    main()
