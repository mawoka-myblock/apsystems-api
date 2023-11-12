import os
from unittest import IsolatedAsyncioTestCase

import apsystems


class TestApi(IsolatedAsyncioTestCase):
    async def test__init__(self):
        # Test with Username/Password
        api = await apsystems.Api.init(username=os.environ.get("USERNAME"), password=os.environ.get("PASSWORD"))
        # Test Wrong Username/Password
        # self.assertRaises(apsystems.WrongLogin, await apsystems.Api.init(username="jkgkabfxcsergvdnfyg", password="hgcasdhcgmdascgh"))
        inverters = await api.list_inverters()
        inverter_status = await api.get_inverter_status(inverter=inverters[0].inverter_dev_id)
        inverter_statistics = await api.get_inverter_statistics(inverter=inverters[0].inverter_dev_id)
        inverter_realtime = await api.get_inverter_realtime(inverter=inverters[0].inverter_dev_id)
        day_graph = await api.get_graph(inverters[0].inverter_dev_id, year=2023, month=11, day=12)
        month_graph = await api.get_graph(inverters[0].inverter_dev_id, year=2023, month=11)
        year_graph = await api.get_graph(inverters[0].inverter_dev_id, year=2023)
