import asyncio
import unittest

class TestLogin(unittest.IsolatedAsyncioTestCase):
    async def test_my_func(self):
        r = await my_func()
        self.assertTrue(r)