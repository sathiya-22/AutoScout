"""Social Poster Agent: Posts a summary of the day's build to X (Twitter).
Gracefully skips if credentials are not configured.

Required env vars (add as GitHub Actions secrets):
    TWITTER_API_KEY
    TWITTER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_SECRET
"""
import os


def post_to_twitter(project_title, repo_url, unified_problem):
    """Compose and post a tweet about today's generated project."""
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("  [SOCIAL] Twitter credentials not set — skipping.")
        return None

    try:
        import tweepy
    except ImportError:
        print("  [SOCIAL] tweepy not installed — skipping Twitter post.")
        return None

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    # Keep tweet under 280 chars
    summary = unified_problem[:160].rstrip()
    if len(unified_problem) > 160:
        summary += "..."

    tweet = (
        f"🤖 AutoScout built today:\n\n"
        f"📦 {project_title}\n\n"
        f"{summary}\n\n"
        f"🔗 {repo_url}\n\n"
        f"#AI #MachineLearning #OpenSource"
    )
    tweet = tweet[:280]

    try:
        response = client.create_tweet(text=tweet)
        print(f"  [SOCIAL] ✅ Posted to X/Twitter: {tweet[:80]}...")
        return response
    except Exception as e:
        print(f"  [SOCIAL] Twitter post failed: {e}")
        return None
