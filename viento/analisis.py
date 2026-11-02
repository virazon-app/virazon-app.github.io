"""Reglas: apuesta de viento, probabilidad de SE, virazon, rotacion y marea.

Son reglas iniciales (sin calibrar). Los numeros se ajustan en config.json y,
con el historial que se va guardando en data/, se pueden recalibrar.
"""
from datetime import timedelta
import math

PUNTOS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def punto(deg):
    if deg is None:
        return "?"
    return PUNTOS[int((deg % 360) / 22.5 + 0.5) % 16]


def dif_angulo(a, b):
    d = abs((a - b) % 360)
    return min(d, 360 - d)


def media_angular(degs):
    degs = [d for d in degs if d is not None]
    if not degs:
        return None
    s = sum(math.sin(math.radians(d)) for d in degs)
    c = sum(math.cos(math.radians(d)) for d in degs)
    return math.degrees(math.atan2(s, c)) % 360


def en_sector(deg, desde, hasta):
    return deg is not None and desde <= deg % 360 <= hasta


def _valor_en(serie, t, clave="kn", tolerancia_min=45):
    mejor = None
    for p in serie or []:
        d = abs((p["t"] - t).total_seconds()) / 60
        if d <= tolerancia_min and (mejor is None or d < mejor[0]):
            mejor = (d, p.get(clave))
    return mejor[1] if mejor else None


def pronostico_en(pron, t):
    if not pron:
        return None
    return min(pron["horas"], key=lambda h: abs((h["t"] - t).total_seconds()))


# ------------------------------------------------------------------ Norden
def norden_tendencia(nor, cfg):
    """Devuelve (es_se, subiendo, cambio_kn_1h)."""
    if not nor:
        return False, False, 0.0
    c = cfg["norden"]
    es_se = en_sector(nor["dir"], c["sector_se_desde"], c["sector_se_hasta"])
    antes = _valor_en(nor["serie"], nor["t"] - timedelta(hours=1))
    cambio = (nor["kn"] - antes) if antes is not None else 0.0
    return es_se, cambio >= c["subida_kn_en_1h"], cambio


# ------------------------------------------------------------------ Virazon
def virazon(pron, cfg, hoy):
    """Chance de virazon de la tarde: sol + tierra mas caliente que el agua + viento general debil."""
    if not pron:
        return {"nivel": "sin datos", "pct": None, "detalle": "sin pronostico"}
    tarde = [h for h in pron["horas"] if h["t"].date() == hoy and 13 <= h["t"].hour <= 18]
    if not tarde:
        return {"nivel": "sin datos", "pct": None, "detalle": "fuera de horario"}
    tmax = max(h["temp"] for h in tarde if h["temp"] is not None)
    sst = pron.get("sst")
    dT = (tmax - sst) if sst is not None else None
    nubes = [h["nubes"] for h in tarde if h.get("nubes") is not None]
    nub = sum(nubes) / len(nubes) if nubes else None
    viento_gral = max(h["kn"] for h in tarde)
    pct = 5
    if dT is not None:
        pct += 25 if dT >= 5 else 15 if dT >= 3 else 5 if dT >= 1 else -10
    if nub is not None:
        pct += 20 if nub < 30 else 10 if nub < 60 else -10
    pct += 15 if viento_gral < 8 else 5 if viento_gral < 12 else -5
    dirs = [h["dir"] for h in tarde]
    if all(en_sector(d, 45, 180) for d in dirs if d is not None):
        pct += 10  # el viento general ya viene del rio
    pct = max(5, min(90, pct))
    nivel = "alta" if pct >= 60 else "media" if pct >= 35 else "floja"
    partes = []
    if dT is not None:
        partes.append(f"aire {tmax:.0f}° / agua {sst:.0f}°")
    if nub is not None:
        partes.append(f"nubes {nub:.0f}%")
    return {"nivel": nivel, "pct": pct, "detalle": " · ".join(partes), "dT": dT, "tmax": tmax, "sst": sst}


# ------------------------------------------------------------------ Apuesta
def apuesta(club, nor, pron, cfg, t0, horas=12):
    """Nuestra apuesta hora por hora: pronostico + lo que viene de Norden + virazon,
    pegado al dato real del club en las primeras horas."""
    c = cfg["norden"]
    vir = virazon(pron, cfg, t0.date())
    es_se_ish = nor is not None and en_sector(nor["dir"], 90, 200)
    out = []
    for k in range(horas + 1):
        t = (t0 + timedelta(hours=k)).replace(minute=0, second=0, microsecond=0)
        if k == 0:
            t = t0
        h = pronostico_en(pron, t)
        base = h["kn"] if h else (club["kn"] if club else 0)
        val = base
        # Norden: lo que hay ahi llega al club con demora; el efecto se apaga en ~6 h
        if es_se_ish:
            dt = (t - nor["t"]).total_seconds() / 3600
            if dt >= 0:
                peso = 1.0 if dt <= c["demora_horas"] + 2 else max(0.0, 1 - (dt - c["demora_horas"] - 2) / 3)
                val = max(val, c["factor_llega_al_club"] * nor["kn"] * peso + base * (1 - peso) * 0.5)
        # Virazon por la tarde
        if vir.get("pct") and 13 <= t.hour <= 18 and t.date() == t0.date():
            val += cfg["virazon_extra_kn"] * vir["pct"] / 100
        # Pegar al dato real al principio
        if club and club.get("kn") is not None:
            w = math.exp(-k / 2)
            val = w * club["kn"] + (1 - w) * val
        out.append({"t": t, "kn": round(val, 1), "wg": h["kn"] if h else None,
                    "wg_raf": h["raf"] if h else None, "dir": h["dir"] if h else None})
    return out


def ventana(ap, t0):
    """Resumen de la apuesta: mejor ventana de la tarde/proximas horas."""
    fut = [p for p in ap[1:] if 8 <= p["t"].hour <= 20]  # horas de luz
    if not fut:
        fut = ap[1:]
    if not fut:
        return None
    i = max(range(len(fut)), key=lambda k: fut[k]["kn"])
    mejor = fut[i]
    a = b = i  # bloque continuo alrededor del maximo
    while a > 0 and fut[a-1]["kn"] >= mejor["kn"] - 1 and (fut[a]["t"] - fut[a-1]["t"]).seconds <= 3600:
        a -= 1
    while b < len(fut) - 1 and fut[b+1]["kn"] >= mejor["kn"] - 1 and (fut[b+1]["t"] - fut[b]["t"]).seconds <= 3600:
        b += 1
    cerca = fut[a:b+1]
    ini, fin = cerca[0]["t"], cerca[-1]["t"]
    wg = [p["wg"] for p in cerca if p["wg"] is not None]
    return {"kn": round(mejor["kn"]), "lo": round(mejor["kn"] - 1.5), "hi": round(mejor["kn"] + 1.5),
            "desde": ini, "hasta": fin,
            "wg_lo": round(min(wg)) if wg else None, "wg_hi": round(max(wg)) if wg else None}


# ------------------------------------------------------------------ Probabilidad SE
def prob_se(club, nor, pron, cfg, t0, ap):
    """Probabilidad (regla inicial) de que entre SE >= umbral en el club en las proximas 3 h."""
    umbral = cfg["umbral_salir_kn"]
    items = []
    pts = 5
    es_se, subiendo, cambio = norden_tendencia(nor, cfg)
    if nor:
        if es_se:
            pts += 25
            items.append((True, f"Norden del {punto(nor['dir'])}: {nor['kn']:.0f} kn"))
        else:
            items.append((False, f"Norden del {punto(nor['dir'])} (no SE): {nor['kn']:.0f} kn"))
        if es_se and nor["kn"] >= cfg["norden"]["alerta_kn"]:
            pts += 15
        if subiendo:
            pts += 10
            items.append((True, f"Norden subiendo (+{cambio:.0f} kn en 1 h)"))
        elif cambio <= -2:
            items.append((False, f"Norden bajando ({cambio:.0f} kn en 1 h)"))
    else:
        items.append((False, "Norden sin datos"))
    if club and club["serie"]:
        d_ahora = media_angular([p["dir"] for p in club["serie"][-2:]])
        if en_sector(d_ahora, 70, 180):
            pts += 12
            d_antes = media_angular([p["dir"] for p in club["serie"][:-3]][-4:])
            txt = f"Club del {punto(d_ahora)}" + (f" (antes {punto(d_antes)})" if d_antes is not None and dif_angulo(d_antes, d_ahora) > 40 else "")
            items.append((True, txt))
        else:
            items.append((False, f"Club del {punto(d_ahora)}"))
    prox = [p for p in ap[1:4]]
    wgmax = max((p["wg"] for p in prox if p["wg"] is not None), default=None)
    if wgmax is not None:
        if wgmax >= umbral:
            pts += 25
            items.append((True, f"Windguru da {wgmax:.0f} kn"))
        elif wgmax >= umbral - 3:
            pts += 10
            items.append((False, f"Windguru da {wgmax:.0f} kn (justo)"))
        else:
            items.append((False, f"Windguru da solo {wgmax:.0f} kn"))
    vir = virazon(pron, cfg, t0.date())
    if vir.get("pct") and 10 <= t0.hour <= 16:
        if vir["pct"] >= 50:
            pts += 10
            items.append((True, f"Virazón {vir['nivel']} ({vir['pct']}%)"))
        else:
            items.append((False, f"Virazón {vir['nivel']}"))
    return max(5, min(95, pts)), items[:4]


# ------------------------------------------------------------------ Agua
def agua(ays, nor):
    """Nivel y tendencia (cm/h). Usa AySA Palermo; si no hay, la marea de Norden."""
    if ays and len(ays["serie"]) >= 2 and ays["serie"][-1]["nivel"] is not None:
        s = [p for p in ays["serie"] if p["nivel"] is not None]
        vel = (s[-1]["nivel"] - s[-2]["nivel"]) * 100
        prev = (s[-2]["nivel"] - s[-3]["nivel"]) * 100 if len(s) >= 3 else None
        return {"fuente": "AySA Palermo", "t": s[-1]["t"], "m": s[-1]["nivel"], "cmh": vel,
                "cmh_prev": prev, "serie": [(p["t"], p["nivel"]) for p in s]}
    if nor and len(nor["marea"]) >= 12:
        m = nor["marea"]
        vel = (m[-1]["m"] - m[-11]["m"]) * 100  # 10 pasos de 6 min = 1 h
        prev = (m[-11]["m"] - m[-21]["m"]) * 100 if len(m) >= 21 else None
        return {"fuente": "Pilote Norden", "t": m[-1]["t"], "m": m[-1]["m"], "cmh": vel,
                "cmh_prev": prev, "serie": [(p["t"], p["m"]) for p in m]}
    return None


def tendencia_txt(cmh):
    if cmh is None:
        return "?"
    if abs(cmh) < 2:
        return "quieta"
    return "subiendo" if cmh > 0 else "bajando"
