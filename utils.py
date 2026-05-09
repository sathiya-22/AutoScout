"""Shared utilities for AutoScout."""
import time


def gemini_generate(client, model, contents, config=None, max_retries=4):
    """Wrapper around client.models.generate_content with exponential backoff
    for 429 RESOURCE_EXHAUSTED errors."""
    for attempt in range(max_retries):
        try:
            kwargs = {"model": model, "contents": contents}
            if config:
                kwargs["config"] = config
            return client.models.generate_content(**kwargs)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = 60 * (2 ** attempt)   # 60s, 120s, 240s, 480s
                print(f"  [RETRY] Rate limited. Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Gemini rate limit: max retries exceeded.")
