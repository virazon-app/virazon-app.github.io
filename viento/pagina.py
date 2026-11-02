"""Pagina web (GitHub Pages): tablero en HTML nativo, con SVG generados aca y un poco de JS
para mostrar "hace X min" y avisar si los datos quedaron viejos."""
import csv
import html
import json
import math
from datetime import timedelta
from pathlib import Path

from .analisis import punto, tendencia_txt

DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
E = html.escape


def horas_txt(desde, hasta):
    if desde.hour == hasta.hour:
        return f"a las {desde:%H} h"
    return f"de {desde:%H} a {hasta:%H} h"


# ------------------------------------------------------------------ SVG
def svg_brujula(deg, size=150):
    c = size / 2
    r = c - 14
    marcas = ""
    for d in range(0, 360, 30):
        a = math.radians(d)
        r1 = r - (9 if d % 90 == 0 else 5)
        marcas += (f'<line x1="{c + r1*math.sin(a):.1f}" y1="{c - r1*math.cos(a):.1f}" '
                   f'x2="{c + r*math.sin(a):.1f}" y2="{c - r*math.cos(a):.1f}" class="tick"/>')
    letras = "".join(
        f'<text x="{c + (r-20)*math.sin(math.radians(d)):.1f}" y="{c - (r-20)*math.cos(math.radians(d)) + 4:.1f}" '
        f'class="card-l">{l}</text>' for d, l in [(0, "N"), (90, "E"), (180, "S"), (270, "O")])
    flecha = ""
    if deg is not None:
        # la flecha apunta hacia donde va el viento
        flecha = (f'<g transform="rotate({deg + 180:.0f} {c} {c})">'
                  f'<line x1="{c}" y1="{c + r*0.62:.1f}" x2="{c}" y2="{c - r*0.45:.1f}" class="arrow"/>'
                  f'<polygon points="{c},{c - r*0.70:.1f} {c-9},{c - r*0.40:.1f} {c+9},{c - r*0.40:.1f}" class="arrowhead"/>'
                  f'</g>')
    return (f'<svg viewBox="0 0 {size} {size}" class="compass" role="img" aria-label="dirección {punto(deg)}">'
            f'<circle cx="{c}" cy="{c}" r="{r}" class="dial"/>{marcas}{letras}{flecha}</svg>')


def svg_grafico(t0, club, nor, ays, pron, ap, umbral, w=720, h=260):
    x0, x1 = t0 - timedelta(hours=6), t0 + timedelta(hours=10)
    padl, padr, padt, padb = 34, 10, 14, 26
    series = []
    vals = [umbral + 4]

    def add(nombre, pts, clase):
        pts = [(t, v) for t, v in pts if v is not None and x0 <= t <= x1]
        if pts:
            series.append((nombre, pts, clase))
            vals.extend(v for _, v in pts)

    if club:
        add("Club Náutico", [(p["t"], p["kn"]) for p in club["serie"]] + [(club["t"], club["kn"])], "s-club")
    if nor:
        add("Pilote Norden", [(p["t"], p["kn"]) for p in nor["serie"]], "s-norden")
    if ays:
        add("AySA Palermo", [(p["t"], p["kn"]) for p in ays["serie"]], "s-aysa")
    if pron:
        add("Windguru", [(x["t"], x["kn"]) for x in pron["horas"]], "s-wg")
    if ap:
        add("Nuestra apuesta", [(p["t"], p["kn"]) for p in ap], "s-ap")
    ymax = max(10, math.ceil(max(vals) / 5) * 5)

    def X(t):
        return padl + (t - x0).total_seconds() / (x1 - x0).total_seconds() * (w - padl - padr)

    def Y(v):
        return padt + (1 - v / ymax) * (h - padt - padb)

    g = []
    g.append(f'<rect x="{padl}" y="{Y(ymax):.1f}" width="{w-padl-padr}" height="{Y(umbral)-Y(ymax):.1f}" class="zone"/>')
    for v in range(0, ymax + 1, 5):
        g.append(f'<line x1="{padl}" x2="{w-padr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                 f'<text x="{padl-6}" y="{Y(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for k in range(-6, 11, 2):
        t = t0 + timedelta(hours=k)
        g.append(f'<text x="{X(t):.1f}" y="{h-6}" class="ax" text-anchor="middle">{t:%H}h</text>')
    g.append(f'<line x1="{X(t0):.1f}" x2="{X(t0):.1f}" y1="{padt}" y2="{h-padb}" class="now"/>'
             f'<text x="{X(t0)+4:.1f}" y="{padt+10}" class="ax">ahora</text>')
    if ap:
        up = " ".join(f"{X(p['t']):.1f},{Y(p['kn']+1.5):.1f}" for p in ap)
        dn = " ".join(f"{X(p['t']):.1f},{Y(max(0, p['kn']-1.5)):.1f}" for p in reversed(ap))
        g.append(f'<polygon points="{up} {dn}" class="band"/>')
    for _, pts, clase in series:
        g.append(f'<polyline points="{" ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in pts)}" class="{clase}"/>')
    if ap:
        for p in ap[2::2]:
            if p["t"] > x1:
                break
            g.append(f'<circle cx="{X(p["t"]):.1f}" cy="{Y(p["kn"]):.1f}" r="3.5" class="dot-ap"/>'
                     f'<text x="{X(p["t"]):.1f}" y="{Y(p["kn"])-8:.1f}" class="lbl-ap" text-anchor="middle">{p["kn"]:.0f}</text>')
    leyenda = "".join(f'<span class="lg"><i class="{c}"></i>{n}</span>' for n, _, c in series)
    return (f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="gráfico de viento">{"".join(g)}</svg>'
            f'<div class="legend">{leyenda}</div>')



NOMBRE_DIA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def nombre_dia(a):
    return "Mañana" if a["dias"] == 1 else NOMBRE_DIA[a["dia"].weekday()]


def svg_barras(horas, umbral, w=720, h=150):
    padl, padb, padt = 4, 22, 18
    n = len(horas)
    ymax = max(umbral + 4, max(p["kn"] for p in horas) * 1.15)
    bw = (w - padl * 2) / n
    g = [f'<line x1="0" x2="{w}" y1="{padt + (1-umbral/ymax)*(h-padt-padb):.1f}" '
         f'y2="{padt + (1-umbral/ymax)*(h-padt-padb):.1f}" class="umbral"/>']
    for i, p in enumerate(horas):
        x = padl + i * bw
        bh = p["kn"] / ymax * (h - padt - padb)
        y = h - padb - bh
        cls = "b-go" if p["kn"] >= umbral else ("b-maybe" if p["kn"] >= umbral - 3 else "b-no")
        wy = h - padb - p["wg"] / ymax * (h - padt - padb)
        g.append(f'<rect x="{x+3:.1f}" y="{y:.1f}" width="{bw-6:.1f}" height="{bh:.1f}" rx="4" class="{cls}"/>'
                 f'<line x1="{x+3:.1f}" x2="{x+bw-3:.1f}" y1="{wy:.1f}" y2="{wy:.1f}" class="b-wg"/>'
                 f'<text x="{x+bw/2:.1f}" y="{y-5:.1f}" class="b-v" text-anchor="middle">{p["kn"]:.0f}</text>'
                 f'<text x="{x+bw/2:.1f}" y="{h-6}" class="ax" text-anchor="middle">{p["t"]:%H}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="apuesta por hora">{"".join(g)}</svg>'


def html_manana(prox, umbral):
    if not prox:
        return ""
    a = prox[0]
    v = a["ventana"]
    wg = [p["wg"] for p in a["horas"] if v["desde"] <= p["t"] <= v["hasta"]]
    wg_txt = f"{min(wg):.0f}–{max(wg):.0f}" if wg and round(min(wg)) != round(max(wg)) else f"{wg[0]:.0f}" if wg else "–"
    return (f'<section class="tomorrow"><h2>Nuestra apuesta para navegar · {nombre_dia(a).lower()} {a["dia"].day}/{a["dia"].month}</h2>'
            f'<div class="tm-top"><div class="big">{v["kn"]}<span> kn</span></div><div>'
            f'<span class="pill {a["clase"]}">{a["veredicto"]}</span>'
            f'<div class="rng">{a["lo"]}–{a["hi"]} kn · {horas_txt(v["desde"], v["hasta"])} · del {punto(a["dir"])}</div>'
            f'<div class="wg">Windguru dice {wg_txt} kn · virazón {E(a["vir"]["nivel"])}'
            + (f' · <span class="rain-warn">con lluvia ({a["lluvia"]} mm)</span>' if a["lluvia"] >= 1 else "")
            + '</div></div></div>'
            f'{svg_barras(a["horas"], umbral)}'
            f'<div class="legend"><span class="lg"><i class="s-ap"></i>Nuestra apuesta por hora</span>'
            f'<span class="lg"><i class="s-wg"></i>Windguru</span><span class="lg"><i class="umb"></i>{umbral} kn para salir</span></div>'
            f'</section>')


def html_semana(prox, mejor):
    if not prox:
        return ""
    cards = ""
    for a in prox:
        v = a["ventana"]
        es_mejor = mejor is not None and a["dia"] == mejor["dia"] and v["kn"] >= 1
        cards += (f'<div class="day {a["clase"]}{" best" if es_mejor else ""}">'
                  + ('<div class="badge">Mejor día</div>' if es_mejor else "")
                  + f'<div class="d-n">{nombre_dia(a)}</div><div class="d-d">{a["dia"].day}/{a["dia"].month}</div>'
                  f'<div class="d-v">{v["kn"]}<span> kn</span></div>'
                  f'<div class="d-s">{horas_txt(v["desde"], v["hasta"])}</div><div class="d-s">{punto(a["dir"])}</div>'
                  + (f'<div class="d-r">☂ {a["lluvia_dia"]:.0f} mm</div>' if a["lluvia_dia"] >= 1 else "") + '</div>')
    return (f'<section><h2>¿Qué día está bueno para navegar?</h2><div class="week">{cards}</div>'
            f'<div class="muted" style="margin-top:8px">Cuanto más lejos el día, menos precisa la apuesta.</div></section>')


CAMARAS = [  # de norte a sur; id de Windy Webcams
    (1735938641, "Náutico San Isidro", "mirando al este"),
    (1793908523, "Acassuso · La Pocho Bay", "mirando al noreste"),
    (1601563134, "Martínez · Río de la Plata", "mirando al sudeste"),
    (1745449788, "La Lucila · Paseo del Viento", "mirando al noroeste"),
    (1577126865, "Olivos", "mirando al norte"),
]


def html_lluvia(serie, al, umbral_mm=0.5):
    radar = ('<div class="cam-f radar"><iframe src="https://www.rainviewer.com/map.html?loc=-34.47,-58.50,8'
             '&oFa=0&oC=1&oU=0&oCS=1&oF=0&oAP=1&c=3&o=83&lm=1&layer=radar&sm=1&sn=1" loading="lazy" '
             'title="Radar de lluvia" allowfullscreen></iframe></div>')
    barras = ""
    if serie:
        mx = max(3, max(p["mm"] for p in serie))
        for p in serie[:24]:
            h = 4 + p["mm"] / mx * 56
            cls = "r-hi" if p["mm"] >= 4 else ("r-on" if p["mm"] >= umbral_mm else "r-off")
            lbl = f"{p['mm']:.1f}" if p["mm"] >= umbral_mm else ""
            barras += (f'<div class="rb"><span class="rv">{lbl}</span><i class="{cls}" style="height:{h:.0f}px"></i>'
                       f'<span class="rh">{p["t"]:%H}</span></div>')
    total = sum(p["mm"] for p in serie[:24]) if serie else 0
    resumen = ("Sin lluvia en las próximas 24 h" if total < umbral_mm
               else f"{total:.1f} mm en las próximas 24 h")
    if al:
        resumen = (f'<b class="rain-warn">Se viene lluvia: {al["mm"]} mm {horas_txt(al["desde"], al["hasta"])}'
                   f'{" (fuerte)" if al["fuerte"] else ""}</b>')
    return (f'<section id="lluvia"><h2>Lluvia</h2><div class="muted" style="margin-bottom:10px">{resumen}</div>'
            f'<div class="rain">{barras}</div>'
            f'<div class="muted" style="margin:6px 0 12px">mm por hora según Windguru</div>{radar}'
            f'<div class="muted" style="margin-top:8px">Radar en vivo vía <a href="https://www.rainviewer.com" '
            f'target="_blank" rel="noopener">RainViewer</a>: tocá play para ver hacia dónde se mueve la lluvia.</div></section>')


def html_camaras():
    cams = "".join(
        f'<figure class="cam{" cam-main" if i == 0 else ""}"><div class="cam-f">'
        f'<iframe src="https://webcams.windy.com/webcams/public/embed/player/{cid}/day" loading="lazy" '
        f'title="Cámara {E(n)}" allowfullscreen></iframe></div>'
        f'<figcaption><b>{E(n)}</b> · {E(d)}</figcaption></figure>'
        for i, (cid, n, d) in enumerate(CAMARAS))
    return (f'<section id="camaras"><h2>Cámaras del río</h2><div class="cams">{cams}</div>'
            f'<div class="muted" style="margin-top:8px">Cámaras vía <a href="https://www.windy.com/-Webcams/webcams" '
            f'target="_blank" rel="noopener">Windy.com</a>. Muestran una foto cada pocos minutos y el timelapse de las últimas 24 h.</div></section>')


# ------------------------------------------------------------------ pagina
def _fuente(nombre, t, t0, max_min, detalle=""):
    if t is None:
        return {"n": nombre, "ok": False, "txt": "sin datos", "t": None, "d": detalle}
    edad = (t0 - t).total_seconds() / 60
    return {"n": nombre, "ok": edad <= max_min, "txt": f"{t:%H:%M}", "t": t.isoformat(), "d": detalle}


def armar(docs: Path, d, alertas, hist_csv: Path):
    docs.mkdir(exist_ok=True)
    t0, club, nor, ays, pron, ap = d["t0"], d["club"], d["nor"], d["ays"], d["pron"], d["ap"]
    ven, prob, items, vir, agua, umbral = d["ventana"], d["prob"], d["items"], d["vir"], d["agua"], d["umbral"]
    prox, mejor = d.get("prox") or [], d.get("mejor")
    if mejor and mejor["ventana"]["kn"] >= umbral - 3:
        mv = mejor["ventana"]
        mejor_txt = (f'<a class="bestline {mejor["clase"]}" href="#semana">Mejor día para navegar: <b>{nombre_dia(mejor).lower()} '
                     f'{mejor["dia"].day}/{mejor["dia"].month}</b> · {mv["kn"]} kn {horas_txt(mv["desde"], mv["hasta"])}</a>')
    elif prox:
        mejor_txt = '<div class="bestline nogo">Por ahora ningún día de la semana da para salir</div>'
    else:
        mejor_txt = ""

    # Apuesta
    if ven:
        sale = ven["kn"] >= umbral
        ap_big = f"{ven['kn']}"
        ap_rng = f"{ven['lo']}–{ven['hi']} kn · {horas_txt(ven['desde'], ven['hasta'])}"
        ap_wg = (f"Windguru: {ven['wg_lo']}–{ven['wg_hi']} kn" if ven["wg_lo"] is not None
                 and ven["wg_lo"] != ven["wg_hi"] else f"Windguru: {ven['wg_lo']} kn" if ven["wg_lo"] is not None else "")
        estado = "Da para salir" if sale else ("Justo" if ven["kn"] >= umbral - 3 else "No da para salir")
        clase_estado = "go" if sale else ("maybe" if ven["kn"] >= umbral - 3 else "nogo")
    else:
        ap_big, ap_rng, ap_wg, estado, clase_estado = "–", "sin datos", "", "Sin datos", "nogo"

    # Tarjetas de estaciones
    def estacion(nombre, src, sub):
        if not src or src.get("kn") is None:
            return (f'<div class="st"><div class="st-h">{nombre}</div>{svg_brujula(None)}'
                    f'<div class="st-v">–</div><div class="st-s">sin datos</div></div>')
        raf = f' <small>ráf {src["max"]:.0f}</small>' if src.get("max") is not None else ""
        return (f'<div class="st"><div class="st-h">{nombre}</div>{svg_brujula(src.get("dir"))}'
                f'<div class="st-v">{src["kn"]:.1f}<span> kn</span>{raf}</div>'
                f'<div class="st-s">{punto(src.get("dir"))} · {sub}</div></div>')

    est_html = (estacion("Club Náutico", club, f'{club["t"]:%H:%M}' if club else "")
                + estacion("Pilote Norden", nor, f'{nor["t"]:%H:%M}' if nor else "")
                + estacion("AySA Palermo", ays, f'{ays["t"]:%H:%M}' if ays else ""))

    # Por que
    razones = "".join(f'<li class="{"ok" if ok else "no"}">{E(t)}</li>' for ok, t in items)

    # Agua
    if agua:
        flecha = "↑" if agua["cmh"] > 0 else "↓"
        agua_html = (f'<div class="kv"><b>{agua["m"]:.2f} m</b><span class="{"up" if agua["cmh"] > 0 else "down"}">'
                     f'{flecha} {abs(agua["cmh"]):.0f} cm/h</span></div>'
                     f'<div class="muted">{tendencia_txt(agua["cmh"])} · {E(agua["fuente"])} {agua["t"]:%H:%M}</div>')
    else:
        agua_html = '<div class="kv"><b>–</b></div><div class="muted">sin datos</div>'
    vir_html = (f'<div class="kv"><b>{E(vir["nivel"].capitalize())}</b>'
                + (f'<span>{vir["pct"]}%</span>' if vir.get("pct") else "")
                + f'</div><div class="muted">{E(vir["detalle"])}</div>')

    # Pronostico Windguru
    pron_html = ""
    if pron:
        objetivo = [t0 + timedelta(hours=h) for h in (2, 4, 6, 8)]
        man = (t0 + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        objetivo += [man.replace(hour=h) for h in (10, 13, 16, 19)]
        for t in objetivo:
            x = min(pron["horas"], key=lambda p: abs((p["t"] - t).total_seconds()))
            dia = "hoy" if x["t"].date() == t0.date() else DIAS[x["t"].weekday()]
            pron_html += (f'<div class="fc{" good" if x["kn"] >= umbral else ""}"><div class="fc-h">{dia} {x["t"]:%H}h</div>'
                          f'<div class="fc-v">{x["kn"]:.0f}</div><div class="fc-s">ráf {x["raf"]:.0f} · {punto(x["dir"])}</div></div>')

    # Historial
    filas = []
    if hist_csv.exists():
        with hist_csv.open() as f:
            filas = list(csv.DictReader(f))[-96:]
    filas.reverse()

    def td(v):
        return f"<td>{E(v or '–')}</td>"
    tabla = "".join("<tr>" + td(r["hora"][11:]) + td(r["club_kn"]) + td(r["club_raf"]) + td(r["norden_kn"])
                    + td(r["agua_m"]) + td(r["windguru_kn_ahora"]) + td(r["apuesta_kn_en_3h"]) + td(r["prob_se"]) + "</tr>"
                    for r in filas)

    fuentes = [
        _fuente("Club Náutico (Windguru)", club and club["t"], t0, 40),
        _fuente("Pilote Norden (CARP)", nor and nor["t"], t0, 180, "publica con ~1,5 h de demora"),
        _fuente("AySA Palermo", ays and ays["t"], t0, 120),
        _fuente("Windguru GFS 13 km", t0 if pron else None, t0, 60, pron and f"corrida {pron.get('init', '')}"),
    ]
    fuentes_html = "".join(
        f'<li><span class="dotst {"ok" if f["ok"] else "bad"}"></span>{E(f["n"])}'
        f'<span class="muted"> · {E(f["txt"])}{(" · " + E(f["d"])) if f["d"] else ""}</span></li>' for f in fuentes)
    alertas = [a for a in alertas if not a.startswith("Se viene lluvia")]  # la lluvia tiene su propio cartel
    avisos_html = "".join(f"<li>{E(a)}</li>" for a in alertas)
    datos = {"actualizado": t0.isoformat(), "apuesta": ven and {"kn": ven["kn"], "lo": ven["lo"], "hi": ven["hi"],
             "desde": ven["desde"].isoformat(), "hasta": ven["hasta"].isoformat()}, "prob_se": prob, "fuentes": fuentes}
    (docs / "data.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1))
    (docs / "favicon.svg").write_text(FAVICON)
    (docs / "manifest.webmanifest").write_text(json.dumps(MANIFEST, ensure_ascii=False))

    page = PLANTILLA.format(
        css=CSS, favicon=FAVICON_URI, iso=t0.isoformat(), hora=f"{DIAS[t0.weekday()]} {t0.day}/{t0.month} · {t0:%H:%M}",
        clase_estado=clase_estado, estado=estado, ap_big=ap_big, ap_rng=E(ap_rng), ap_wg=E(ap_wg),
        avisos=(f'<section class="alert"><b>Aviso</b><ul>{avisos_html}</ul></section>' if alertas else ""),
        estaciones=est_html, prob=prob, prob_w=max(3, prob), razones=razones, umbral=umbral,
        grafico=svg_grafico(t0, club, nor, ays, pron, ap, umbral), agua=agua_html, vir=vir_html,
        lluvia_top=(f'<a class="bestline rainline" href="#lluvia">☂ Se viene lluvia: {d["al_lluvia"]["mm"]} mm '
                    f'{horas_txt(d["al_lluvia"]["desde"], d["al_lluvia"]["hasta"])}'
                    + (" · fuerte" if d["al_lluvia"]["fuerte"] else "") + '</a>') if d.get("al_lluvia") else "",
        lluvia=html_lluvia(d.get("lluvia") or [], d.get("al_lluvia")),
        camaras=html_camaras(), mejor=mejor_txt, manana=html_manana(prox, umbral), semana=html_semana(prox, mejor),
        pron=pron_html, modelo=E(pron["modelo"] if pron else "Windguru"), tabla=tabla, fuentes=fuentes_html)
    (docs / "index.html").write_text(page, encoding="utf-8")


FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0b2545"/>'
           '<path d="M12 24c8-6 16 6 24 0s12-4 16-2M12 34c8-6 16 6 24 0s12-4 16-2M12 44c8-6 16 6 24 0s12-4 16-2" '
           'fill="none" stroke="#5eead4" stroke-width="4" stroke-linecap="round"/></svg>')
FAVICON_URI = "favicon.svg"
MANIFEST = {"name": "Virazón", "short_name": "Virazón", "start_url": ".", "display": "standalone",
            "background_color": "#071426", "theme_color": "#071426",
            "icons": [{"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml"}]}

CSS = """
:root{--bg:#071426;--card:#0e1f38;--card2:#132a4a;--line:#1f3a60;--txt:#e6eef8;--muted:#8aa0bd;
--accent:#5eead4;--go:#22c55e;--maybe:#f5b301;--nogo:#64748b;--club:#38bdf8;--norden:#fb923c;--aysa:#a78bfa;--wg:#4ade80;--ap:#facc15}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:15px/1.45 Inter,-apple-system,system-ui,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:880px;margin:0 auto;padding:16px 16px 40px}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:4px 0 14px}
.brand{display:flex;align-items:center;gap:10px}.brand img{width:34px;height:34px;border-radius:9px}
.brand h1{font-size:20px;margin:0;letter-spacing:.2px}.brand small{display:block;color:var(--muted);font-size:12.5px}
.live{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--muted);white-space:nowrap}
.pulse{width:8px;height:8px;border-radius:50%;background:var(--go);box-shadow:0 0 0 0 rgba(34,197,94,.6);animation:p 2s infinite}
.live.stale .pulse{background:var(--maybe);animation:none}
@keyframes p{70%{box-shadow:0 0 0 8px rgba(34,197,94,0)}100%{box-shadow:0 0 0 0 rgba(34,197,94,0)}}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.9px;color:var(--muted);margin:0 0 12px;font-weight:600}
.hero{display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:center;background:linear-gradient(135deg,#0f2a4d,#0b1d36)}
.big{font-size:64px;font-weight:800;line-height:1;letter-spacing:-2px}.big span{font-size:20px;font-weight:600;letter-spacing:0;color:var(--muted)}
.pill{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:700;font-size:13px;margin-bottom:6px}
.pill.go{background:rgba(34,197,94,.15);color:var(--go)}.pill.maybe{background:rgba(245,179,1,.15);color:var(--maybe)}
.pill.nogo{background:rgba(100,116,139,.2);color:#b6c2d3}
.hero .rng{font-size:17px;font-weight:600}.hero .wg{color:var(--muted);font-size:14px}
.alert{border-color:#7c4a03;background:#2a1a03}.alert ul{margin:6px 0 0;padding-left:18px}
.stations{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.st{background:var(--card2);border-radius:12px;padding:12px;text-align:center}
.st-h{font-size:13px;color:var(--muted);font-weight:600}.st-v{font-size:26px;font-weight:800}.st-v span{font-size:14px;color:var(--muted);font-weight:600}
.st-v small{font-size:13px;color:var(--muted);font-weight:600}.st-s{font-size:12.5px;color:var(--muted)}
.compass{width:100%;max-width:130px;margin:4px auto;display:block}.dial{fill:#0a1830;stroke:var(--line);stroke-width:2}
.tick{stroke:#3b5a85;stroke-width:2}.card-l{fill:var(--muted);font-size:12px;font-weight:700;text-anchor:middle}
.arrow{stroke:var(--club);stroke-width:5;stroke-linecap:round}.arrowhead{fill:var(--club)}
.prob{display:grid;grid-template-columns:150px 1fr;gap:18px;align-items:center}
.pnum{font-size:44px;font-weight:800}.bar{height:8px;background:var(--card2);border-radius:9px;overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--nogo),var(--maybe),var(--go))}
ul.why{list-style:none;margin:0;padding:0}ul.why li{padding:3px 0 3px 24px;position:relative}
ul.why li:before{position:absolute;left:0;font-weight:800}ul.why li.ok:before{content:"✓";color:var(--go)}ul.why li.no:before{content:"✕";color:#f87171}
.chart{width:100%;height:auto;display:block}.grid{stroke:#1c3456;stroke-width:1}.ax{fill:var(--muted);font-size:11px}
.zone{fill:rgba(34,197,94,.07)}.now{stroke:#8aa0bd;stroke-dasharray:3 4}.band{fill:rgba(250,204,21,.13)}
polyline{fill:none;stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
.s-club{stroke:var(--club);stroke-width:3}.s-norden{stroke:var(--norden)}.s-aysa{stroke:var(--aysa);stroke-width:2}
.s-wg{stroke:var(--wg);stroke-dasharray:7 5}.s-ap{stroke:var(--ap);stroke-width:3.5}
.dot-ap{fill:var(--ap)}.lbl-ap{fill:var(--ap);font-size:12px;font-weight:800}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:8px;font-size:12.5px;color:var(--muted)}
.lg i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.lg i.s-club{background:var(--club)}.lg i.s-norden{background:var(--norden)}.lg i.s-aysa{background:var(--aysa)}
.lg i.s-wg{background:var(--wg)}.lg i.s-ap{background:var(--ap)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.two section{margin:0}
.kv{display:flex;align-items:baseline;gap:10px}.kv b{font-size:30px}.kv span{font-weight:700;font-size:16px;color:var(--muted)}
.kv .up{color:var(--go)}.kv .down{color:var(--norden)}
.fcs{display:grid;grid-template-columns:repeat(8,1fr);gap:6px}
.fc{background:var(--card2);border-radius:10px;padding:8px 4px;text-align:center}.fc.good{outline:1.5px solid var(--go)}
.fc-h{font-size:11.5px;color:var(--muted)}.fc-v{font-size:22px;font-weight:800}.fc-s{font-size:11px;color:var(--muted)}
.muted{color:var(--muted);font-size:13px}
details summary{cursor:pointer;color:var(--muted);font-weight:600}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap;margin-top:10px}
th,td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}
ul.src{list-style:none;padding:0;margin:0}ul.src li{padding:4px 0}
.dotst{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px}.dotst.ok{background:var(--go)}.dotst.bad{background:#f87171}
.bestline{display:block;text-decoration:none;color:var(--txt);border-radius:12px;padding:11px 14px;margin:12px 0;font-size:15px;
border:1px solid var(--line);background:var(--card)}.bestline.go{border-color:rgba(34,197,94,.5);background:rgba(34,197,94,.08)}
.bestline.maybe{border-color:rgba(245,179,1,.45);background:rgba(245,179,1,.07)}.bestline.nogo{color:var(--muted)}
.tomorrow{background:linear-gradient(135deg,#102c4f,#0b1d36)}.tm-top{display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:center;margin-bottom:8px}
.tomorrow .rng{font-size:16px;font-weight:600}.tomorrow .wg{color:var(--muted);font-size:14px}
.b-go{fill:var(--go)}.b-maybe{fill:var(--maybe)}.b-no{fill:#3b5578}.b-wg{stroke:var(--wg);stroke-width:2.5}
.b-v{fill:var(--txt);font-size:12px;font-weight:700}.umbral{stroke:var(--go);stroke-dasharray:5 5;opacity:.6}
.lg i.umb{background:var(--go);opacity:.6}
.week{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
.day{position:relative;background:var(--card2);border-radius:12px;padding:12px 6px 10px;text-align:center;border:1.5px solid transparent}
.day.go{border-color:rgba(34,197,94,.55)}.day.maybe{border-color:rgba(245,179,1,.45)}.day.best{box-shadow:0 0 0 2px var(--accent)}
.badge{position:absolute;top:-9px;left:50%;transform:translateX(-50%);background:var(--accent);color:#04201c;font-size:10.5px;
font-weight:800;padding:2px 7px;border-radius:999px;white-space:nowrap}
.d-n{font-weight:700;font-size:13px}.d-d{color:var(--muted);font-size:11.5px}.d-v{font-size:24px;font-weight:800;margin-top:4px}
.d-v span{font-size:12px;color:var(--muted)}.day.go .d-v{color:var(--go)}.day.maybe .d-v{color:var(--maybe)}.d-s{color:var(--muted);font-size:11.5px}
.cams{display:grid;grid-template-columns:1fr 1fr;gap:12px}.cam{margin:0}.cam-main{grid-column:1/-1}
.cam-f{position:relative;padding-top:56.25%;border-radius:12px;overflow:hidden;background:#0a1830}
.cam-f iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
figcaption{font-size:13px;color:var(--muted);margin-top:6px}figcaption b{color:var(--txt)}
section a{color:var(--accent)}
.rainline{border-color:rgba(96,165,250,.55);background:rgba(37,99,235,.12);color:#bfdbfe}
.rain{display:flex;align-items:flex-end;gap:3px;height:96px}
.rb{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:0}
.rb i{display:block;width:100%;border-radius:3px 3px 0 0}.r-off{background:#1c3456}.r-on{background:#60a5fa}.r-hi{background:#2563eb}
.rv{font-size:10px;color:#93c5fd;height:13px}.rh{font-size:10px;color:var(--muted);margin-top:3px}
.radar{padding-top:62%}.rain-warn{color:#93c5fd}.d-r{color:#93c5fd;font-size:11.5px;margin-top:2px}
footer{color:var(--muted);font-size:12.5px;margin-top:18px;line-height:1.6}
@media (max-width:640px){.big{font-size:52px}.stations{grid-template-columns:repeat(3,1fr);gap:6px}.st{padding:8px 4px}
.st-v{font-size:20px}.prob{grid-template-columns:1fr}.two{grid-template-columns:1fr}.fcs{grid-template-columns:repeat(4,1fr)}
.hero{grid-template-columns:1fr}.tm-top{grid-template-columns:1fr}
.week{grid-template-columns:repeat(4,1fr);gap:10px 6px}.cams{grid-template-columns:1fr}.radar{padding-top:110%}.rb:nth-child(even) .rh{visibility:hidden}.b-v{font-size:20px}.st-v small{display:block}
.ax{font-size:20px}.lbl-ap{font-size:22px}.live{font-size:12px}header{align-items:flex-start}}
"""

PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="refresh" content="300">
<title>Virazón · Viento en el Náutico San Isidro</title>
<meta name="description" content="Viento en vivo en el Club Náutico San Isidro, Pilote Norden y AySA, con pronóstico de Windguru y nuestra apuesta de nudos.">
<meta name="theme-color" content="#071426">
<meta property="og:title" content="Virazón · Viento en San Isidro">
<meta property="og:description" content="Viento en vivo, Pilote Norden, agua y pronóstico. Se actualiza cada 15 minutos.">
<link rel="icon" href="{favicon}" type="image/svg+xml"><link rel="apple-touch-icon" href="{favicon}">
<link rel="manifest" href="manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Virazón">
<style>{css}</style></head><body><main>
<header><div class="brand"><img src="{favicon}" alt=""><div><h1>Virazón</h1><small>Náutico San Isidro · Río de la Plata</small></div></div>
<div class="live" id="live"><span class="pulse"></span><span id="ago" data-t="{iso}">{hora}</span></div></header>

<section class="hero"><div class="big">{ap_big}<span> kn</span></div>
<div><span class="pill {clase_estado}">{estado}</span><div class="rng">Nuestra apuesta hoy: {ap_rng}</div><div class="wg">{ap_wg}</div></div></section>
{lluvia_top}
{mejor}
{avisos}
<section><h2>Ahora</h2><div class="stations">{estaciones}</div></section>

{camaras}

<section class="prob"><div><div class="pnum">{prob}%</div><div class="muted">chance de SE ≥{umbral} kn en las próximas 3 h</div>
<div class="bar"><i style="width:{prob_w}%"></i></div></div><ul class="why">{razones}</ul></section>

<section><h2>Viento (kn) · medido, Windguru y nuestra apuesta</h2>{grafico}</section>

{manana}
<div id="semana">{semana}</div>

{lluvia}

<div class="two"><section><h2>Agua</h2>{agua}</section><section><h2>Virazón esta tarde</h2>{vir}</section></div>

<section><h2>Pronóstico Windguru · {modelo}</h2><div class="fcs">{pron}</div></section>

<section><details><summary>Últimas 24 h</summary><div class="wrap"><table><tr><th>Hora</th><th>Club</th><th>Ráf</th><th>Norden</th>
<th>Agua m</th><th>Windguru</th><th>Apuesta +3h</th><th>Prob SE</th></tr>{tabla}</table></div></details></section>

<section><h2>Fuentes</h2><ul class="src">{fuentes}</ul></section>

<footer><b>Cómo calculamos la apuesta:</b> partimos del pronóstico de Windguru, le sumamos el viento del sur/sudeste que
entra por Pilote Norden (llega al club unas 2 h después) y el empuje de la virazón en las tardes de sol, y la pegamos al
viento medido en el club en las primeras horas. Es un modelo propio en calibración: cada medición queda guardada para ajustarlo.
<br>Datos de terceros, sin garantía. Ante la duda, mirá el río y las condiciones antes de salir.</footer>
</main>
<script>
(function(){{var el=document.getElementById('ago'),live=document.getElementById('live');
function f(){{var m=Math.round((Date.now()-new Date(el.dataset.t))/60000);
el.textContent=m<1?'actualizado recién':m<60?'actualizado hace '+m+' min':'actualizado hace '+Math.floor(m/60)+' h '+(m%60)+' min';
live.classList.toggle('stale',m>40);}}f();setInterval(f,30000);}})();
</script></body></html>"""
