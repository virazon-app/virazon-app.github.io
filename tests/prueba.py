"""Prueba sin internet: simula las 4 fuentes con datos reales del 2/11/2026 ~11:50 y corre la app.

Uso:  DRY_RUN=1 python -m tests.prueba
"""
import json
import os
import shutil
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

TZ = timezone(timedelta(hours=-3))
T0 = datetime(2026, 11, 2, 11, 50, tzinfo=TZ)
UTC0 = datetime(2026, 11, 2, 11, 50, tzinfo=timezone.utc)  # CARP manda hora local como UTC


class R:
    def __init__(self, data, text=None):
        self._d = data; self.text = text if text is not None else json.dumps(data); self.status_code = 200

    def json(self):
        return self._d

    def raise_for_status(self):
        pass


def wg(params):
    q = params["q"]
    if q == "station_data_current":
        return R({"wind_avg": 4.47, "wind_max": 5.99, "wind_direction": 96, "temperature": 20.87,
                  "datetime": "2026-11-02 11:45:00 -03", "unixtime": int(T0.timestamp()) - 300})
    if q == "station_data":
        base = int(datetime(2026, 11, 2, 7, 0, tzinfo=TZ).timestamp())
        return R({"unixtime": [base + i*1800 for i in range(10)],
                  "wind_avg": [11.1, 5.2, 2.8, 4.4, 5.3, 4.1, 6.1, 4.5, 4.7, 5.2],
                  "wind_max": [13.1, 7.5, 4.4, 7.4, 9.2, 7.2, 9.6, 6.6, 5.9, 6.1],
                  "wind_direction": [105, 163, 219, 255, 257, 236, 207, 183, 117, 114]})
    if q == "forecast_spot":
        return R({"tabs": [{"id_model_arr": [{"id_model": 3, "rundef": "x", "cachefix": "y"}]}],
                  "spots": {"261": {"sst": 20}}})
    if q == "forecast":
        spd = [2.6,1,2.2,3.9,3.2,4.3,4.6,4.9,3.5,1.3,0.8,1.6,2.6,4.2,4.3,5.7,8,7.5,7,6.8,8,8.6,8.3,8.2,7.7,8.1,8.6,9.5,10.3,10.8,10.2,13,8.8,12.1,11.9,11.7,12,12,11.5,9.9]
        import itertools
        base = spd
        spd = [round(v * (0.7 + 0.12 * ((i // 24) % 5)), 1) for i, v in enumerate(itertools.islice(itertools.cycle(base), 192))]
        n = len(spd)
        return R({"fcst": {"initstamp": int(datetime(2026, 11, 2, 3, 0, tzinfo=TZ).timestamp()), "hours": list(range(n)),
                           "WINDSPD": spd, "GUST": [s*1.45 for s in spd],
                           "WINDDIR": (lambda L: (L * 6)[:n])([63,202,215,217,167,170,202,214,190,120,80,67,60,55,60,70,84,88,90,91,91,90,90,90,90,92,95,96,98,101,104,108,112,118,123,120,115,111,110,120]),
                           "TMP": (lambda L: (L * 6)[:n])([17,16.5,16.6,16.2,16.6,17.5,18,20,21,22,22.5,23,24,24,24,23.5,23,22,20,19,19,18,18,18,18,18,18,18,18,19,19,20,20,19,19,19,18,18,18,18]),
                           "TCDC": [20]*n, "APCP1": [0]*10 + [0.2, 1.5, 3, 0.8] + [0]*(n-14), "model_name": "GFS 13 km", "initstr": "2026110206"}})
    raise ValueError(q)


def carp_station():
    base = int(UTC0.replace(hour=8, minute=30).timestamp() * 1000)
    wind = [9.5, 12, 12.5, 13.5, 13, 14, 12, 10.2]
    gust = [w + 1.2 for w in wind]
    serie_w = [[base + i*15*60000, f"{w:.2f}"] for i, w in enumerate(wind)]
    serie_g = [[base + i*15*60000, f"{g:.2f}"] for i, g in enumerate(gust)]
    tbase = int(UTC0.replace(hour=0, minute=0).timestamp() * 1000)
    marea = [[tbase + i*360000, f"{0.3 + 0.5*__import__('math').sin(i/40):.3f}"] for i in range(119)]
    latest = ("<table><tr><th>Date/Time</th></tr><tr><td>2026-11-02 10:18:00</td><td>10.2</td><td>11.3</td>"
              "<td>knots</td><td>174.1</td><td>Colonia</td></tr></table>")
    j = {"stationID": "2", "wind": {"latest": urllib.parse.quote(latest),
                                    "chart": {"gust": {"series": [{"name": "Gust", "data": serie_g}, {"name": "Wind", "data": serie_w}]}}},
         "tide": {"latest": "", "chart": {"series": [{"name": "Norden", "data": marea}]}}}
    return "OKshowStationTelemetry|JSON**" + json.dumps(j)


AYSA = {"estacion": "x", "fechaMedicion": "2026-11-02T11:00:00+00:00", "variables": {
    "VelocidadViento": ["28","27.30","14.70","5.60","28.80","26.70","18.60","25","13.50","20.50","16.50","6.70"],
    "RafagaViento": ["38.30","34.10","18.20","9","45.80","39.90","26.40","28.90","18.80","24.90","24.10","11.40"],
    "NivelRio": ["0.95","1.01","0.96","0.86","0.71","0.49","0.34","0.28","0.23","0.18","0.29","0.63"],
    "DireccionViento": ["101.80","75.10","53.80","46.20","275.20","253.80","142.20","83.70","235.10","245.90","184.70","230.60"],
    "Temperatura": ["20.50"]*12}}


def fake_get(url, params=None, **kw):
    if "windguru" in url:
        return wg(params)
    if "aysa" in url:
        return R(AYSA)
    return R({}, text="<html>ok</html>")


class FakeSession:
    headers = {}

    def mount(self, *a, **k):
        pass

    def get(self, *a, **k):
        return R({}, text="<html>ok</html>")

    def post(self, url, params=None, data=None, **k):
        if data and "p1=" in data:
            return R({}, text=carp_station())
        return R({}, text="OKdoneLoadingTelemetry|JSON**{}")


def main():
    from viento import fuentes, main as app
    d = Path(app.DATA)
    for x in (d, Path(app.DOCS)):
        if x.exists():
            shutil.rmtree(x)
    os.environ["DRY_RUN"] = "1"
    with mock.patch.object(fuentes.requests, "get", fake_get), \
         mock.patch.object(fuentes.requests, "Session", FakeSession), \
         mock.patch.object(fuentes, "ahora", lambda: T0), \
         mock.patch.object(fuentes, "_bundle_con_intermedio", lambda host: None):
        app.main()
    print(open(d / "historial.csv").read())


if __name__ == "__main__":
    main()
