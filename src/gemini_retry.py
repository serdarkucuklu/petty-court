import time

def call_with_retry(fn, tries=4, base_delay=8, sleep=time.sleep):
    """Retry a Gemini call through transient 5xx ServerError spikes (e.g. 503 high demand).
    Does NOT catch ClientError (4xx incl. 429 quota) — those are not transient.
    `sleep` is injectable so tests run instantly."""
    from google.genai import errors
    last = None
    for i in range(tries):
        try:
            return fn()
        except errors.ServerError as e:
            last = e
            if i < tries - 1:
                sleep(base_delay * (i + 1))
    raise last
