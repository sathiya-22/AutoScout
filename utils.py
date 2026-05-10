"""Shared utilities for AutoScout."""
import time

INTER_CALL_DELAY = 5  # seconds between Gemini calls — keeps us under 15 RPM


def gemini_generate(client, model, contents, config=None, max_retries=3):
    """Wrapper around client.models.generate_content with:
    - A small delay before each call to stay under the per-minute limit
    - Exponential backoff retry on 429 RESOURCE_EXHAUSTED errors
    """
    time.sleep(INTER_CALL_DELAY)   # pace calls to ≤12/min
    for attempt in range(max_retries):
        try:
            kwargs = {"model": model, "contents": contents}
            if config:
                kwargs["config"] = config
            return client.models.generate_content(**kwargs)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = 60 * (attempt + 1)  # 60s, 120s, 180s
                print(f"  [RETRY] Rate limited. Waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Gemini rate limit: max retries exceeded.")
