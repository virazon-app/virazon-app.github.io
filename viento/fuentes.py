"""Lectura de datos: Club Nautico (Windguru), Pilote Norden (CARP), AySA Palermo y pronostico Windguru.

Cada funcion devuelve un dict o None si la fuente falla (la app sigue con lo que tenga).
Todas las horas se devuelven como datetime con zona horaria de Buenos Aires.
"""
import json
import re
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import requests

TZ = timezone(timedelta(hours=-3))  # Argentina no usa horario de verano
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT = 25


def ahora():
    return datetime.now(TZ)


def _log(msg):
    print(f"[fuentes] {msg}", flush=True)


# ---------------------------------------------------------------- Windguru
WG = "https://www.windguru.cz/int/iapi.php"


def _wg(params):
    r = requests.get(WG, params=params, timeout=TIMEOUT,
                     headers={"User-Agent": UA, "Referer": "https://www.windguru.cz/"})
    r.raise_for_status()
    return r.json()


def club_nautico(id_estacion, horas=12):
    """Estacion Windguru del Club Nautico San Isidro: actual + historial cada 30 min."""
    try:
        cur = _wg({"q": "station_data_current", "id_station": id_estacion})
        fin = ahora()
        ini = fin - timedelta(hours=horas)
        f = "%Y-%m-%d %H:%M:%S"  # la estacion usa hora local
        h = _wg({"q": "station_data", "id_station": id_estacion,
                 "from": ini.strftime(f), "to": fin.strftime(f), "avg_minutes": 30})
        serie = []
        for i, ts in enumerate(h.get("unixtime", [])):
            serie.append({
                "t": datetime.fromtimestamp(ts, TZ),
                "kn": h["wind_avg"][i], "max": h["wind_max"][i], "dir": h["wind_direction"][i],
            })
        return {
            "t": datetime.fromtimestamp(cur["unixtime"], TZ),
            "kn": cur.get("wind_avg"), "max": cur.get("wind_max"),
            "dir": cur.get("wind_direction"), "temp": cur.get("temperature"),
            "serie": [s for s in serie if s["kn"] is not None],
        }
    except Exception as e:  # noqa: BLE001
        _log(f"club nautico fallo: {e}")
        return None


def pronostico_windguru(id_spot, id_modelo):
    """Pronostico horario (GFS 13 km por defecto) + temperatura del agua del spot."""
    try:
        fs = _wg({"q": "forecast_spot", "id_spot": id_spot})
        tab = fs["tabs"][0]
        m = next(x for x in tab["id_model_arr"] if int(x["id_model"]) == int(id_modelo))
        f = _wg({"q": "forecast", "id_model": id_modelo, "rundef": m["rundef"], "id_spot": id_spot,
                 "WGCACHEABLE": 21600, "cachefix": m["cachefix"]})["fcst"]
        sst = (fs.get("spots", {}).get(str(id_spot)) or {}).get("sst")
        horas = []
        for i, hh in enumerate(f["hours"]):
            def v(k):
                arr = f.get(k) or []
                return arr[i] if i < len(arr) else None
            horas.append({
                "t": datetime.fromtimestamp(f["initstamp"] + hh * 3600, TZ),
                "kn": v("WINDSPD"), "raf": v("GUST"), "dir": v("WINDDIR"),
                "temp": v("TMP"), "nubes": v("TCDC"),
            })
        return {"modelo": f.get("model_name", "GFS"), "init": f.get("initstr"),
                "sst": sst, "horas": horas}
    except Exception as e:  # noqa: BLE001
        _log(f"pronostico windguru fallo: {e}")
        return None


# ---------------------------------------------------------------- Pilote Norden (CARP)
CARP = "https://meteo.comisionriodelaplata.org"


def _carp_ts(ms):
    # La CARP manda la hora local como si fuera UTC
    return datetime.fromtimestamp(ms / 1000, timezone.utc).replace(tzinfo=TZ)


def _tabla_ultima(html):
    celdas = re.findall(r"<td[^>]*>(.*?)</td>", html, flags=re.S)
    return [re.sub(r"<[^>]+>", "", c).strip() for c in celdas]


def _ctx_viejo(ctx):
    """Acepta la configuracion TLS vieja del servidor de la CARP (clave DH chica, firmas SHA1).
    El certificado se sigue verificando contra las CAs."""
    import ssl
    ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
    return ctx


def _bundle_con_intermedio(host):
    """El servidor de la CARP no manda el certificado intermedio (los navegadores lo buscan solos).
    Lo bajamos de la direccion que indica su propio certificado (AIA) y armamos un bundle de CAs
    con certifi + ese intermedio. La verificacion SSL sigue activa."""
    import os
    import ssl
    import tempfile

    import certifi
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

    ctx = _ctx_viejo(ssl.create_default_context())
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # solo para leer el certificado y saber donde esta el intermedio
    import socket
    with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    hoja = x509.load_der_x509_certificate(der)
    aia = hoja.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    urls = [d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS]
    inter = []
    for u in urls:
        raw = requests.get(u, timeout=TIMEOUT).content
        try:
            c = x509.load_der_x509_certificate(raw)
        except ValueError:
            c = x509.load_pem_x509_certificate(raw)
        inter.append(c.public_bytes(Encoding.PEM).decode())
    ruta = os.path.join(tempfile.gettempdir(), f"ca_{host}.pem")
    with open(certifi.where()) as f, open(ruta, "w") as g:
        g.write(f.read() + "\n" + "\n".join(inter))
    return ruta


class _AdaptadorCARP(requests.adapters.HTTPAdapter):
    """El servidor de la CARP usa una clave DH chica: bajamos el nivel de seguridad de cifrado a 1,
    pero se sigue verificando el certificado con el bundle (certifi + intermedio)."""

    def __init__(self, cafile, **kw):
        import ssl
        self._ctx = _ctx_viejo(ssl.create_default_context(cafile=cafile))
        super().__init__(**kw)

    def init_poolmanager(self, *a, **kw):
        kw["ssl_context"] = self._ctx
        return super().init_poolmanager(*a, **kw)


def norden(id_estacion=2):
    """Viento (velocidad, rafaga, direccion) y marea de Pilote Norden."""
    try:
        s = requests.Session()
        s.mount(CARP, _AdaptadorCARP(_bundle_con_intermedio("meteo.comisionriodelaplata.org")))
        s.headers.update({"User-Agent": UA,
                          "Referer": "https://www.comisionriodelaplata.org/"})
        s.get(CARP + "/", params={"w": 900, "h": 450, "lang": "ES"}, timeout=TIMEOUT)
        url = CARP + "/ecsCommand.php"
        hdr = {"Content-Type": "application/x-www-form-urlencoded",
               "X-Requested-With": "XMLHttpRequest", "Referer": CARP + "/?w=900&h=450&lang=ES"}
        s.post(url, params={"c": "telemetry/updateTelemetry", "s": time.time() % 1},
               data="p=1", headers=hdr, timeout=TIMEOUT)
        r = s.post(url, params={"c": "telemetry/updateTelemetry", "s": time.time() % 1},
                   data=f"p=1&p1={id_estacion}&p2=3&p3=1", headers=hdr, timeout=TIMEOUT)
        txt = r.text
        if "JSON**" not in txt:
            raise ValueError("respuesta sin datos: " + txt[:120])
        j = json.loads(txt[txt.index("JSON**") + 6:])
        return _parse_norden(j)
    except Exception as e:  # noqa: BLE001
        _log(f"norden fallo: {e}")
        return None


def _dec(v):
    return urllib.parse.unquote(v) if isinstance(v, str) else v


def _parse_norden(j):
    wind, tide = j["wind"], j["tide"]
    chart = wind["chart"]
    if isinstance(chart, str):
        chart = json.loads(_dec(chart))
    ult = _tabla_ultima(_dec(wind["latest"]))  # fecha, vel, rafaga, unidad, dir, fuente
    gust = {s["name"]: s["data"] for s in chart["gust"]["series"]}
    serie = [{"t": _carp_ts(ts), "kn": float(v)} for ts, v in gust.get("Wind", [])]
    rafs = {ts: float(v) for ts, v in gust.get("Gust", [])}
    for (ts, _), p in zip(gust.get("Wind", []), serie):
        p["max"] = rafs.get(ts)
    tchart = tide["chart"]
    if isinstance(tchart, str):
        tchart = json.loads(_dec(tchart))
    marea = [{"t": _carp_ts(ts), "m": float(v)} for ts, v in tchart["series"][0]["data"]]
    return {
        "t": datetime.strptime(ult[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ),
        "kn": float(ult[1]), "max": float(ult[2]), "dir": float(ult[4]),
        "serie": serie, "marea": marea,
    }


# ---------------------------------------------------------------- AySA
AYSA = "https://www.aysa.com.ar/api/estaciones"


def aysa(id_estacion):
    """Ultimas 12 horas de AySA (Palermo): viento km/h -> kn, direccion, nivel del rio."""
    try:
        r = requests.get(f"{AYSA}/getVariablesEstacionesHistorico/{id_estacion}",
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return _parse_aysa(r.json())
    except Exception as e:  # noqa: BLE001
        _log(f"aysa fallo: {e}")
        return None


def _parse_aysa(j):
    v = j["variables"]
    # fechaMedicion viene marcada +00:00 pero es hora local
    fin = datetime.fromisoformat(j["fechaMedicion"][:19]).replace(tzinfo=TZ)
    n = len(v["VelocidadViento"])
    serie = []
    for i in range(n):
        def g(k):
            arr = v.get(k) or []
            try:
                return float(arr[i])
            except (IndexError, ValueError, TypeError):
                return None
        kmh, raf = g("VelocidadViento"), g("RafagaViento")
        serie.append({
            "t": fin - timedelta(hours=n - 1 - i),
            "kn": kmh / 1.852 if kmh is not None else None,
            "max": raf / 1.852 if raf is not None else None,
            "dir": g("DireccionViento"), "nivel": g("NivelRio"), "temp": g("Temperatura"),
        })
    return {"t": fin, "serie": serie, **{k: serie[-1][k] for k in ("kn", "max", "dir", "nivel", "temp")}}
