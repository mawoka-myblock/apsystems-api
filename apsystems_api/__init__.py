import enum

from aiohttp import ClientSession, FormData, ClientResponse
from pydantic import BaseModel
from datetime import datetime


class WrongLogin(Exception):
    pass


class UnknownError(Exception):
    def __init__(self, http_code: int, code: int | None, body: dict | None):
        self.code = code
        self.http_code = http_code
        self.body = body
        super().__init__(f"UnknownError - Code: {code}, Body: {body}")


class DeviceOffline(Exception):
    pass


async def _process_response(resp: ClientResponse) -> dict:
    if not resp.ok:
        raise UnknownError(resp.status, None, None)
    data = await resp.json()
    if data["code"] == 2006:
        raise WrongLogin()
    elif data["code"] == 1001:
        raise DeviceOffline()
    elif data["code"] != 0:
        raise UnknownError(resp.status, data["code"], data)
    return data["data"]


class Api:
    refresh_token: str = None
    access_token: str = None
    user_id: str = None
    base_url: str = "https://app.api.apsystemsema.com:9223"
    language: str = "de_DE"
    app_id: str = "4029817264d4821d0164d4821dd80015"
    app_secret: str = "EZAd2023"

    @classmethod
    async def init(cls, username: str | None = None, password: str | None = None, access_token: str | None = None,
                   refresh_token: str | None = None):
        self = cls()
        if username is not None and password is not None:
            await self._log_user_in(username=username, password=password)
        elif access_token is not None and refresh_token is not None:
            # Initialization code for the second case
            self.access_token = access_token
            self.refresh_token = refresh_token
        else:
            raise ValueError("Invalid parameters provided")
        return self

    async def _log_user_in(self, username: str, password: str):
        formData = FormData(
            {"language": self.language, "password": password, "app_id": self.app_id, "app_secret": self.app_secret,
             "username": username})
        async with ClientSession() as c, c.post(
                f"{self.base_url}/api/token/generateToken/user/login?language={self.language}",
                data=formData, timeout=5) as resp:
            data = await _process_response(resp)
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.user_id = data["user_id"]
            return None

    class _ListInvertersResponse(BaseModel):
        device_name: str | None
        communicationStatus: int
        runningStatus: int
        system_id: str
        inverter_dev_id: str
        type: str

    async def list_inverters(self) -> list[_ListInvertersResponse]:
        async with ClientSession() as c, c.get(
                f"{self.base_url}/aps-api-web/api/v2/data/device/ezInverter/list/{self.user_id}?language={self.language}&systemId={self.user_id}",
                headers={"Authorization": f"Bearer {self.access_token}"}, timeout=5) as resp:
            data = await _process_response(resp)
            return_list = []
            for i in data["inverter"]:
                return_list.append(self._ListInvertersResponse.parse_obj(i))
            return return_list

    class _InverterStatus(BaseModel):
        communicationStatus: int
        communicationDelayStatus: int

    async def get_inverter_status(self, inverter: str) -> _InverterStatus:
        async with ClientSession() as c, c.get(
                f"{self.base_url}/aps-api-web/api/v2/data/device/ezInverter/status/{inverter}?language={self.language}",
                headers={"Authorization": f"Bearer {self.access_token}"}, timeout=5) as resp:
            data = await _process_response(resp)
            return self._InverterStatus.parse_obj(data)

    class _InverterStatistics(BaseModel):
        lastReportDatetime: datetime
        lastCommunicationStatus: int
        lastPower: str
        runningDuration: int
        monthEnergy: float
        lastRunningStatus: int | None
        lifetimeCo2: float
        lifetimeEnergy: float
        todayCo2: float
        todayEnergy: float
        monthCo2: float

    async def get_inverter_statistics(self, inverter: str):
        async with ClientSession() as c, c.get(
                f"{self.base_url}/aps-api-web/api/v2/data/device/ezInverter/statistic/{inverter}?language={self.language}",
                headers={"Authorization": f"Bearer {self.access_token}"}, timeout=5) as resp:
            i_data = await _process_response(resp)
            date_format = "%Y-%m-%d %H:%M:%S"
            return self._InverterStatistics(
                lastReportDatetime=datetime.strptime(i_data["lastReportDatetime"], date_format),
                lastCommunicationStatus=i_data["lastCommunicationStatus"], lastPower=i_data["lastPower"],
                runningDuration=i_data["runningDuration"], monthEnergy=float(i_data["monthEnergy"]),
                lastRunningStatus=i_data.get("lastRunningStatus", None), lifetimeCo2=float(i_data["lifetimeCo2"]),
                lifetimeEnergy=float(i_data["lifetimeEnergy"]), todayCo2=float(i_data["todayCo2"]),
                todayEnergy=float(i_data["todayEnergy"]), monthCo2=float(i_data["monthCo2"]))

    class _InverterRealtime(BaseModel):
        communicationStatus: int
        runningDuration: int
        runningStatus: int
        inverter_dev_id: str
        power: int
        type: str
        energy: float

    async def get_inverter_realtime(self, inverter: str):
        async with ClientSession() as c, c.get(
                f"{self.base_url}/aps-api-web/api/v2/data/device/ezInverter/realTime/{inverter}?language={self.language}",
                headers={"Authorization": f"Bearer {self.access_token}"}, timeout=5) as resp:
            d = await _process_response(resp)
            return self._InverterRealtime(communicationStatus=d["communicationStatus"],
                                          runningDuration=d["runningDuration"], runningStatus=d["runningStatus"],
                                          inverter_dev_id=d["inverter_dev_id"],
                                          power=d["power"], type=d["type"], energy=float(d["energy"]))

    class _Graph(BaseModel):
        peakPower: str
        totalEnergy: float
        power: list[str]
        time: list[str]
        energy: list[str]

    async def get_graph(self, inverter: str, year: int, month: int | None = None,
                        day: int | None = None):
        d_range = ""
        date_str = str(year)
        if day is not None and month is None:
            raise ValueError("Day can't be set if month is unset")
        if day is None and month is None:
            d_range = "year"
        elif day is None and month is not None:
            d_range = "month"
            date_str += str(month)
        elif day is not None and month is not None:
            d_range = "day"
            date_str += str(month) + str(day)
        async with ClientSession() as c, c.get(
                f"{self.base_url}/aps-api-web/api/v2/data/device/ezInverter/{d_range}/{inverter}/{date_str}?language={self.language}",
                headers={"Authorization": f"Bearer {self.access_token}"}, timeout=5) as resp:
            d = await _process_response(resp)
            return self._Graph(peakPower=d.get("peakPower", None), totalEnergy=float(d["totalEnergy"]),
                               power=d["power"],
                               time=d["time"], energy=d["energy"])

    class _LifetimeGraph(BaseModel):
        year: list[str]
        totalEnergy: float
        averageEnergy: float
        energy: list[str]

    async def get_lifetime_graph(self, inverter: str):
        async with ClientSession() as c, c.get(
                f"{self.base_url}/aps-api-web/api/v2/data/device/ezInverter/lifetime/{inverter}?language={self.language}",
                headers={"Authorization": f"Bearer {self.access_token}"}, timeout=5) as resp:
            d = await _process_response(resp)
            return self._LifetimeGraph(year=d["year"], totalEnergy=float(d["totalEnergy"]),
                                       averageEnergy=float(d["averageEnergy"]), energy=d["energy"])
