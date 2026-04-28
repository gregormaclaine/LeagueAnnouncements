import asyncio
import os
import sys
import time
import unittest
from typing import Any
from unittest.mock import patch, MagicMock

# Ensure src/ is importable and stub external dependencies before any project import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.modules.setdefault('logs', MagicMock())

from riot.rate_limiting import handle_rate_limit  # noqa: E402


class FakeResponse:
    """Minimal stand-in for APIResponse, exposing only what rate_limiting.py uses."""

    def __init__(self, count: int = 1, is_rate_limited: bool = False):
        self._count = count
        self._rate_limited = is_rate_limited

    def error(self):
        return 'rate-limit' if self._rate_limited else None

    def rate_limit_count(self, which: int = 1) -> int:
        return self._count


def make_limiter(max_calls: int, time_window: float) -> Any:
    """Return a fresh @handle_rate_limit decorator with the given parameters."""
    return handle_rate_limit(max_calls=max_calls, time_window=time_window, header_order=0)


class TestRateLimiterWeakPressure(unittest.IsolatedAsyncioTestCase):
    """Calls well under the limit — should never queue or wait."""

    async def test_light_load_completes_quickly(self):
        """3 concurrent calls against a limit of 10 should finish without waiting."""
        call_count = 0

        @make_limiter(max_calls=10, time_window=0.5)
        async def api():
            nonlocal call_count
            call_count += 1
            return FakeResponse(count=call_count)

        start = time.monotonic()
        await asyncio.gather(api(), api(), api())
        elapsed = time.monotonic() - start

        self.assertEqual(call_count, 3)
        self.assertLess(elapsed, 0.3, "Light load must not wait for a new window")

    async def test_spaced_calls_never_trigger_queuing(self):
        """Calls arriving well apart in time should always find capacity."""
        call_count = 0

        @make_limiter(max_calls=3, time_window=0.2)
        async def api():
            nonlocal call_count
            call_count += 1
            return FakeResponse(count=call_count)

        # 4 calls spaced 0.25 s apart: each falls in its own window (limit 3/0.2 s)
        for _ in range(4):
            await api()
            await asyncio.sleep(0.25)

        self.assertEqual(call_count, 4)


class TestRateLimiterStrongPressure(unittest.IsolatedAsyncioTestCase):
    """Calls at or above the limit — overflow must wait for the next window."""

    async def test_exactly_at_limit_fits_in_one_window(self):
        """Exactly max_calls simultaneous requests should not queue."""
        max_calls = 5
        call_count = 0

        @make_limiter(max_calls=max_calls, time_window=0.5)
        async def api():
            nonlocal call_count
            call_count += 1
            return FakeResponse(count=call_count)

        start = time.monotonic()
        await asyncio.gather(*[api() for _ in range(max_calls)])
        elapsed = time.monotonic() - start

        self.assertEqual(call_count, max_calls)
        self.assertLess(elapsed, 0.4, "Exactly max_calls should not require waiting")

    async def test_overflow_waits_for_next_window(self):
        """max_calls + 3 concurrent requests: overflow batch must wait one window."""
        max_calls = 5
        overflow = 3
        call_times: list[float] = []

        @make_limiter(max_calls=max_calls, time_window=0.4)
        async def api():
            call_times.append(time.monotonic())
            return FakeResponse(count=len(call_times))

        start = time.monotonic()
        await asyncio.gather(*[api() for _ in range(max_calls + overflow)])
        elapsed = time.monotonic() - start

        self.assertEqual(len(call_times), max_calls + overflow)
        self.assertGreaterEqual(
            elapsed, 0.35,
            "Overflow calls must wait for the next window (~0.4 s)",
        )

    async def test_sustained_burst_spans_multiple_windows(self):
        """3 × max_calls requests should span roughly 3 windows."""
        max_calls = 5
        window = 0.3
        call_times: list[float] = []

        @make_limiter(max_calls=max_calls, time_window=window)
        async def api():
            call_times.append(time.monotonic())
            return FakeResponse(count=len(call_times))

        start = time.monotonic()
        await asyncio.gather(*[api() for _ in range(max_calls * 3)])
        elapsed = time.monotonic() - start

        self.assertEqual(len(call_times), max_calls * 3)
        # Windows 2 and 3 each add one full window of wait time
        self.assertGreaterEqual(elapsed, window * 1.8)

    async def test_call_order_is_preserved_under_pressure(self):
        """Each call should complete exactly once even under heavy concurrent load."""
        max_calls = 4
        completions: list[int] = []

        @make_limiter(max_calls=max_calls, time_window=0.3)
        async def api(n: int):
            completions.append(n)
            return FakeResponse(count=len(completions))

        total = max_calls * 2 + 1
        await asyncio.gather(*[api(i) for i in range(total)])

        self.assertEqual(len(completions), total)
        self.assertEqual(sorted(completions), list(range(total)))


class TestRateLimiterWindowBoundary(unittest.IsolatedAsyncioTestCase):
    """Behaviour at window boundaries — including known algorithm limitations."""

    async def test_calls_spanning_window_boundary_all_complete(self):
        """Calls that straddle a window reset must all eventually complete."""
        max_calls = 4
        window = 0.3
        call_times: list[float] = []

        @make_limiter(max_calls=max_calls, time_window=window)
        async def api():
            call_times.append(time.monotonic())
            return FakeResponse(count=len(call_times))

        # Fill the first window
        await asyncio.gather(*[api() for _ in range(max_calls)])

        # Fire another batch right after; these must wait for the next window
        await asyncio.gather(*[api() for _ in range(max_calls)])

        self.assertEqual(len(call_times), max_calls * 2)

    async def test_sliding_window_limits_call_rate(self):
        """
        With a sliding window, slots expire individually so the rate is correctly
        bounded even when slow in-flight calls span multiple windows. The limiter
        governs when calls START, not how many are concurrently open — so peak
        concurrent connections may exceed max_calls, but the RATE must not.
        """
        max_calls = 3
        window = 0.15
        start_times: list[float] = []

        @make_limiter(max_calls=max_calls, time_window=window)
        async def slow_api():
            start_times.append(time.monotonic())
            await asyncio.sleep(window + 0.05)  # outlasts the window
            return FakeResponse(count=len(start_times))

        await asyncio.gather(*[slow_api() for _ in range(max_calls * 2)])

        self.assertEqual(len(start_times), max_calls * 2)

        # No sliding window of length `window` should contain more than max_calls starts
        t0 = start_times[0]
        for t in start_times:
            starts_in_window = sum(1 for s in start_times if t <= s < t + window)
            self.assertLessEqual(
                starts_in_window, max_calls,
                f"Too many calls started in window [{t - t0:.3f}s, {t - t0 + window:.3f}s)",
            )


class TestRateLimiter429Handling(unittest.IsolatedAsyncioTestCase):
    """Retry behaviour when the server returns a 429 rate-limit response."""

    async def test_retries_once_after_429(self):
        """A single 429 should trigger one retry that returns successfully."""
        call_count = 0

        @make_limiter(max_calls=10, time_window=0.01)
        async def api():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FakeResponse(count=10, is_rate_limited=True)
            return FakeResponse(count=1)

        async def fast_sleep(duration):
            # Replace the hard-coded 5 s penalty with enough real time to reset
            # the tiny test window, avoiding an indefinite window-wait in the
            # recursive retry call.
            await asyncio.sleep(0.02)

        with patch('riot.rate_limiting.sleep', side_effect=fast_sleep):
            result = await api()

        self.assertIsNone(result.error())
        self.assertEqual(call_count, 2, "Underlying function must be called twice")

    async def test_retries_through_multiple_429s(self):
        """The decorator must keep retrying until it receives a non-429 response."""
        call_count = 0
        fail_times = 3

        @make_limiter(max_calls=10, time_window=0.01)
        async def api():
            nonlocal call_count
            call_count += 1
            if call_count <= fail_times:
                return FakeResponse(count=10, is_rate_limited=True)
            return FakeResponse(count=1)

        async def fast_sleep(_duration):
            await asyncio.sleep(0.02)

        with patch('riot.rate_limiting.sleep', side_effect=fast_sleep):
            result = await api()

        self.assertIsNone(result.error())
        self.assertEqual(call_count, fail_times + 1)

    async def test_429_triggers_sleep_before_retry(self):
        """The decorator must sleep before retrying, not immediately recurse."""
        call_count = 0
        sleep_durations: list[float] = []

        @make_limiter(max_calls=10, time_window=0.01)
        async def api():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FakeResponse(count=10, is_rate_limited=True)
            return FakeResponse(count=1)

        async def recording_sleep(duration):
            sleep_durations.append(duration)
            await asyncio.sleep(0.02)  # enough to reset the tiny window

        with patch('riot.rate_limiting.sleep', side_effect=recording_sleep):
            await api()

        self.assertTrue(
            any(d == 5 for d in sleep_durations),
            f"Expected a 5 s retry penalty sleep; got sleeps: {sleep_durations}",
        )


class TestRateLimiterServerCountSync(unittest.IsolatedAsyncioTestCase):
    """The decorator should trust the server's reported call count over its own."""

    async def test_adopts_higher_server_count_on_restart(self):
        """
        If the server reports more calls than the local counter knows about
        (e.g. the bot restarted mid-window), the limiter should adopt the higher
        value and start queuing sooner.
        """
        max_calls = 10
        server_reported_count = 8   # server already sees 8 calls this window
        call_count = 0

        @make_limiter(max_calls=max_calls, time_window=0.5)
        async def api():
            nonlocal call_count
            call_count += 1
            return FakeResponse(count=server_reported_count)

        start = time.monotonic()

        # First call: local counter says 1, server says 8 → limiter should adopt 8
        await api()

        # Only 2 more calls should fit before the window is considered full (8+2=10)
        await asyncio.gather(api(), api())

        # This call pushes over the adopted limit and must wait for the next window
        fourth_call_task = asyncio.create_task(api())
        elapsed_before_fourth = time.monotonic() - start

        await fourth_call_task
        total_elapsed = time.monotonic() - start

        self.assertEqual(call_count, 4)
        # The fourth call must have waited; if it was instant the adoption didn't work
        self.assertGreater(
            total_elapsed, elapsed_before_fourth + 0.1,
            "Fourth call should have queued after server-count was adopted",
        )


if __name__ == '__main__':
    unittest.main()
