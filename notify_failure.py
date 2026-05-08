"""Sends a failure alert email when the GitHub Actions workflow crashes.
Called by the workflow's on-failure step.
"""
import os
import sys
import datetime
import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
RECIPIENT = "sendilnathsathiya@gmail.com"


def send_failure_alert(run_url=""):
    if not resend.api_key:
        print("RESEND_API_KEY not set — cannot send failure alert.")
        sys.exit(0)

    subject = f"⚠️ AutoScout Run FAILED — {datetime.date.today()}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; color: #333;">
        <h2 style="color: #e74c3c;">⚠️ AutoScout Daily Run Failed</h2>
        <p>The scheduled AutoScout run on <strong>{datetime.date.today()}</strong>
        did not complete successfully.</p>
        <p>No new repositories were generated today.</p>
        {"<p><a href='" + run_url + "'>View workflow logs</a></p>" if run_url else ""}
        <hr>
        <p style="font-size:12px; color:#888;">AutoScout Autonomous R&D Lab</p>
    </div>
    """
    try:
        resend.Emails.send({
            "from": "Scout <onboarding@resend.dev>",
            "to": [RECIPIENT],
            "subject": subject,
            "html": html,
        })
        print("Failure alert sent.")
    except Exception as e:
        print(f"Could not send failure alert: {e}")


if __name__ == "__main__":
    run_url = sys.argv[1] if len(sys.argv) > 1 else ""
    send_failure_alert(run_url)
