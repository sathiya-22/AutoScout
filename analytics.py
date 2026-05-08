"""Project quality tracking for AutoScout.
Records per-run metadata to analytics.json so you can spot trends over time.
"""
import os
import json
import datetime

ANALYTICS_FILE = "analytics.json"


def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def record_run(project_name, project_title, connection_score,
               repo_url=None, fallback_used=False):
    """Append one run's metadata to analytics.json."""
    analytics = load_analytics()
    analytics.append({
        "date": str(datetime.date.today()),
        "project_name": project_name,
        "project_title": project_title,
        "connection_score": connection_score,
        "repo_url": repo_url,
        "fallback_used": fallback_used,
    })
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(analytics, f, indent=2)
    print(
        f"📊 Analytics recorded — score: {connection_score}/10, "
        f"fallback: {fallback_used}"
    )


def get_summary():
    """Return a one-line summary for logging/email."""
    analytics = load_analytics()
    if not analytics:
        return "No analytics data yet."
    scores = [a["connection_score"] for a in analytics if a.get("connection_score")]
    avg = sum(scores) / len(scores) if scores else 0
    fallbacks = sum(1 for a in analytics if a.get("fallback_used"))
    return (
        f"Total runs: {len(analytics)} | "
        f"Avg synthesis score: {avg:.1f}/10 | "
        f"Fallback builds: {fallbacks}"
    )
