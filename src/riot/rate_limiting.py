from typing import Callable, Awaitable
from datetime import timedelta, datetime
from asyncio import sleep
from .responses import APIResponse


def handle_rate_limit(max_calls: int, time_window: int, header_order: int, verbose: bool = True):
    '''
    Uses a make-shift token bucket algorithm to prevent function from running more than a certain
    number of times in a given window of time.
    '''
    def decorator(func: Callable[..., Awaitable[APIResponse]]) -> Callable[..., Awaitable[APIResponse]]:
        info = {'timeout_start': None,
                'active_calls': 0,
                'completed_calls': 0,
                'waiting_calls': 0}

        async def wrapper(*args, **kwargs):
            while True:
                if info['timeout_start'] is None or datetime.now() > info['timeout_start'] + timedelta(seconds=time_window):
                    info['timeout_start'] = datetime.now()
                    info['active_calls'] = 0
                    info['completed_calls'] = 0

                if info['completed_calls'] + info['active_calls'] < max_calls:
                    info['active_calls'] += 1
                    break
                else:
                    info['waiting_calls'] += 1
                    await sleep((info['timeout_start'] + timedelta(seconds=time_window) - datetime.now()).total_seconds())
                    info['waiting_calls'] -= 1

            resobj = await func(*args, **kwargs)

            current = resobj.rate_limit_count(header_order)
            info['active_calls'] -= 1
            info['completed_calls'] += 1

            # Accounts for when the rate limit didn't start from 0 (When restarting bot)
            if current and current > info['completed_calls'] + info['active_calls']:
                info['completed_calls'] = current

            # Only prints once when the final call of the window completes
            elif current == max_calls:
                when = (info['timeout_start'] +
                        timedelta(seconds=time_window)).strftime('%H:%M:%S')
                print(f"Hit rate-limit ceiling: {info['waiting_calls']}",
                      f"calls will restart at {when}...")

            if resobj.error() == 'rate-limit':
                info['completed_calls'] = max(
                    info['completed_calls'], max_calls)
                print('ERROR: Surpassed rate limit - retrying after 5 seconds')
                await sleep(5)
                return await wrapper(*args, **kwargs)

            if verbose:
                print(f"Rate-limit({header_order}) update: <{current}T,",
                      f"{info['active_calls']}A, {info['completed_calls']}C>")
            return resobj

        return wrapper
    return decorator
