from typing import Callable, Awaitable, TypeVar
from collections import deque
from asyncio import sleep
import time
from logs import log
from .responses import APIResponse

T = TypeVar('T')


def handle_rate_limit(max_calls: int, time_window: float, header_order: int, verbose: bool = False):
    '''
    Sliding-window rate limiter. Tracks the start time of each accepted call
    and holds new callers until fewer than max_calls have started within the
    past time_window seconds.
    '''
    def decorator(func: Callable[..., Awaitable[APIResponse[T]]]) -> Callable[..., Awaitable[APIResponse[T]]]:
        call_times: deque[float] = deque()

        async def wrapper(*args, **kwargs):
            while True:
                # Rate gate: wait until a slot is free in the sliding window
                while True:
                    now = time.monotonic()
                    while call_times and now - call_times[0] >= time_window:
                        call_times.popleft()

                    if len(call_times) < max_calls:
                        call_times.append(now)
                        break

                    wait = time_window - (now - call_times[0])
                    await sleep(max(wait, 0))

                resobj = await func(*args, **kwargs)

                # Adopt the server's count when it exceeds ours (bot restarted mid-window)
                server_count = resobj.rate_limit_count(header_order)
                if server_count > len(call_times):
                    now = time.monotonic()
                    for _ in range(server_count - len(call_times)):
                        call_times.appendleft(now)

                if resobj.error() == 'rate-limit':
                    # Saturate the window so other callers queue while we back off
                    now = time.monotonic()
                    while len(call_times) < max_calls:
                        call_times.appendleft(now)
                    log('Surpassed rate limit — retrying after 5 s', 'WARNING', 'riot.rate_limit')
                    await sleep(5)
                    continue  # retry via the outer loop — no recursion

                if verbose:
                    log(f'Rate-limit: {len(call_times)}/{max_calls} in window', 'INFO', 'riot.rate_limit')

                return resobj

        return wrapper
    return decorator
