"""
CurseBot — utils/retry.py
Exponential backoff decorator voor async API-aanroepen.
"""
import asyncio
import functools
from bot.utils.logger import get_logger

log = get_logger(__name__)


def async_retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator: herprobeert een async functie bij uitzonderingen.
    Wacht na elke poging exponentieel langer (delay * backoff^poging).
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == retries:
                        log.error(f"[RETRY] {fn.__name__} definitief mislukt na {retries} pogingen: {exc}")
                        raise
                    log.warning(
                        f"[RETRY] {fn.__name__} poging {attempt}/{retries} mislukt: {exc}. "
                        f"Opnieuw in {current_delay:.1f}s"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
