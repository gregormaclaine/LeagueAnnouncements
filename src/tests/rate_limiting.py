import unittest
import asyncio
import random
from riot.rate_limiting import handle_rate_limit
from riot.responses import APIResponse
from datetime import datetime


class TestRateLimiting(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    async def sample_api(i: int, start: datetime):
        await asyncio.sleep(random.random() / 2)
        print(f'{i}: {(datetime.now() - start).total_seconds():.2f}s')
        return APIResponse(data=i)

    async def test_two_groups(self):
        api = handle_rate_limit(5, 5, 0)(self.sample_api)

        start = datetime.now()
        result = await asyncio.gather(*[api(i, start) for i in range(10)])
        self.assertListEqual([r.data for r in result], list(range(10)))

    async def test_many_groups(self):
        api = handle_rate_limit(2, 3, 0)(self.sample_api)

        start = datetime.now()
        result = await asyncio.gather(*[api(i, start) for i in range(12)])
        self.assertListEqual([r.data for r in result], list(range(12)))


if __name__ == '__main__':
    unittest.main()
