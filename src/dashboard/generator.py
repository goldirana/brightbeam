"""Dashboard generator — produces interactive HTML report."""

import json
from pathlib import Path


def generate_dashboard(results_path: Path, output_dir: Path) -> Path:
    """Generate an interactive HTML dashboard from results.json."""
    results = json.loads(results_path.read_text())

    html = _build_html(results)
    html_path = output_dir / "dashboard.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def _build_html(results: list[dict]) -> str:
    """Build the full HTML dashboard with Plotly.js charts."""
    # Aggregate stats
    total = len(results)
    passed = sum(1 for r in results if not r.get("needs_human_review", False))
    review = total - passed
    categories = {}
    confidences = []

    for r in results:
        cat = r.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        confidences.append(r.get("confidence", 0))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Build per-transcript table rows
    rows_html = ""
    for r in results:
        status = "⚠️ Review" if r.get("needs_human_review") else "✅ Pass"
        conf = r.get("confidence", 0)
        factual = r.get("factual_check", {}).get("factual_score", 0) if r.get("factual_check") else 0
        quality = r.get("quality_score", {}).get("overall_score", 0) if r.get("quality_score") else 0
        structural = 1.0 if r.get("structural_valid", False) else 0.0
        rows_html += f"""
        <tr>
            <td>{r.get('transcript_id', '')}</td>
            <td>{r.get('category', '')}</td>
            <td>{factual:.2f}</td>
            <td>{quality:.2f}</td>
            <td>{'✓' if structural else '✗'}</td>
            <td><strong>{conf:.2f}</strong></td>
            <td>{r.get('attempts', 1)}</td>
            <td>{status}</td>
        </tr>"""

    categories_json = json.dumps(list(categories.keys()))
    categories_values_json = json.dumps(list(categories.values()))
    confidences_json = json.dumps(confidences)
    ids_json = json.dumps([r.get("transcript_id", "") for r in results])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Call Summarisation Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; }}
        .header {{ background: #1a1a2e; color: white; padding: 2rem; text-align: center; }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
        .header p {{ opacity: 0.8; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card .value {{ font-size: 2rem; font-weight: bold; color: #1a1a2e; }}
        .stat-card .label {{ color: #666; margin-top: 0.5rem; }}
        .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem; }}
        .chart-card {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .chart-card h3 {{ margin-bottom: 1rem; color: #1a1a2e; }}
        .formula-panel {{ background: #1a1a2e; color: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
        .formula-panel h3 {{ color: #e9c46a; margin-bottom: 0.75rem; }}
        .formula-panel code {{ background: rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 4px; display: block; font-size: 1.1rem; margin-bottom: 0.75rem; font-family: 'Fira Code', monospace; }}
        .formula-panel .weights {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1rem; }}
        .formula-panel .weight-item {{ text-align: center; padding: 0.5rem; background: rgba(255,255,255,0.05); border-radius: 4px; }}
        .formula-panel .weight-item .pct {{ font-size: 1.4rem; font-weight: bold; color: #2a9d8f; }}
        .formula-panel .weight-item .desc {{ font-size: 0.8rem; opacity: 0.7; margin-top: 0.25rem; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #1a1a2e; color: white; }}
        tr:hover {{ background: #f8f9fa; }}
        @media (max-width: 768px) {{ .charts {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Call Summarisation Dashboard</h1>
        <p>Pipeline Results Overview</p>
    </div>
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="value">{total}</div>
                <div class="label">Total Transcripts</div>
            </div>
            <div class="stat-card">
                <div class="value">{passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="stat-card">
                <div class="value">{review}</div>
                <div class="label">Needs Review</div>
            </div>
            <div class="stat-card">
                <div class="value">{avg_confidence:.2f}</div>
                <div class="label">Avg Confidence</div>
            </div>
        </div>

        <div class="charts">
            <div class="chart-card">
                <h3>Category Distribution</h3>
                <div id="category-chart"></div>
            </div>
            <div class="chart-card">
                <h3>Confidence Scores</h3>
                <div id="confidence-chart"></div>
            </div>
        </div>

        <h3 style="margin-bottom: 1rem;">Per-Transcript Results</h3>
        <div class="formula-panel">
            <h3>Confidence Score Formula</h3>
            <code>confidence = factual_score &times; 0.5 + quality_score &times; 0.3 + structural &times; 0.2</code>
            <div class="weights">
                <div class="weight-item">
                    <div class="pct">50%</div>
                    <div class="desc">Factual Score<br>(NER entity cross-check)</div>
                </div>
                <div class="weight-item">
                    <div class="pct">30%</div>
                    <div class="desc">Quality Score<br>(LLM-as-judge)</div>
                </div>
                <div class="weight-item">
                    <div class="pct">20%</div>
                    <div class="desc">Structural Valid<br>(Pydantic + format)</div>
                </div>
            </div>
            <p style="margin-top: 1rem; font-size: 0.85rem; opacity: 0.7;">Pass threshold: 0.8 (applied to quality_score.overall_score for human review flag)</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Category</th>
                    <th>Factual (50%)</th>
                    <th>Quality (30%)</th>
                    <th>Structural (20%)</th>
                    <th>Confidence</th>
                    <th>Attempts</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>

    <script>
        // Category pie chart
        Plotly.newPlot('category-chart', [{{
            values: {categories_values_json},
            labels: {categories_json},
            type: 'pie',
            hole: 0.4,
            marker: {{ colors: ['#264653', '#2a9d8f', '#e9c46a', '#f4a261', '#e76f51', '#606c38'] }}
        }}], {{ margin: {{ t: 20, b: 20 }}, height: 300 }});

        // Confidence bar chart
        Plotly.newPlot('confidence-chart', [{{
            x: {ids_json},
            y: {confidences_json},
            type: 'bar',
            marker: {{
                color: {confidences_json},
                colorscale: [[0, '#e76f51'], [0.5, '#e9c46a'], [1, '#2a9d8f']],
                cmin: 0, cmax: 1
            }}
        }}], {{
            margin: {{ t: 20, b: 40 }},
            height: 300,
            yaxis: {{ range: [0, 1], title: 'Confidence' }},
            xaxis: {{ title: 'Transcript ID' }}
        }});
    </script>
</body>
</html>"""
