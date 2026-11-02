"""Genera la pagina web (GitHub Pages) con el tablero y el historial."""
import csv
import html
from pathlib import Path


def armar(docs: Path, t0, ven, prob, alertas, hist_csv: Path, umbral):
    docs.mkdir(exist_ok=True)
    filas = []
    if hist_csv.exists():
        with hist_csv.open() as f:
            filas = list(csv.DictReader(f))[-96:]  # ultimas ~24 h
    filas.reverse()

    if ven:
        apuesta = (f"{ven['kn']} kn <small>({ven['lo']} a {ven['hi']})</small> de {ven['desde']:%H} a {ven['hasta']:%H} h")
        wg = f"Windguru dice {ven['wg_lo']}–{ven['wg_hi']} kn" if ven["wg_lo"] is not None else ""
        sale = ven["kn"] >= umbral
    else:
        apuesta, wg, sale = "sin datos", "", False
    avisos = "".join(f"<li>{a}</li>" for a in alertas) or "<li>Sin alertas ahora.</li>"

    def td(v):
        return f"<td>{html.escape(v or '–')}</td>"

    tabla = "".join(
        "<tr>" + td(r["hora"][11:]) + td(r["club_kn"]) + td(r["club_raf"]) + td(r["club_dir"])
        + td(r["norden_kn"]) + td(r["norden_dir"]) + td(r["agua_m"]) + td(r["agua_cmh"])
        + td(r["windguru_kn_ahora"]) + td(r["apuesta_kn_en_3h"]) + td(r["prob_se"]) + "</tr>"
        for r in filas)
    stamp = t0.strftime("%Y%m%d%H%M")
    page = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Viento San Isidro</title>
<style>
:root{{--bg:#0f172a;--card:#1e293b;--txt:#e2e8f0;--muted:#94a3b8;--yel:#eab308;--green:#22c55e}}
body{{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:16px}}
h1{{font-size:22px;margin:4px 0}} .muted{{color:var(--muted);font-size:14px}}
.apuesta{{background:{'var(--green)' if sale else 'var(--yel)'};color:#111;border-radius:14px;padding:14px 16px;margin:12px 0}}
.apuesta b{{font-size:24px}} .apuesta small{{font-size:15px}}
.card{{background:var(--card);border-radius:14px;padding:12px 16px;margin:12px 0}}
ul{{margin:6px 0;padding-left:20px}} img{{width:100%;border-radius:14px;display:block}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}}
th,td{{padding:5px 7px;text-align:right;border-bottom:1px solid #334155}} th{{color:var(--muted);font-weight:600}}
</style></head><body><main>
<h1>Viento · Náutico San Isidro</h1>
<div class="muted">Actualizado {t0:%d/%m %H:%M} · se refresca solo cada 5 min (los datos, cada 15)</div>
<div class="apuesta">Nuestra apuesta: <b>{apuesta}</b><br>{wg} · prob. SE ≥{umbral} kn próx. 3 h: {prob}%</div>
<div class="card"><b>Avisos</b><ul>{avisos}</ul></div>
<img src="tablero.png?v={stamp}" alt="Tablero de viento">
<div class="card"><b>Últimas 24 h</b> <span class="muted">(kn, grados, metros)</span>
<div class="wrap"><table><tr><th>Hora</th><th>Club</th><th>Ráf</th><th>Dir</th><th>Norden</th><th>Dir N</th>
<th>Agua</th><th>cm/h</th><th>Windguru</th><th>Apuesta +3h</th><th>Prob SE</th></tr>{tabla}</table></div></div>
<p class="muted">Fuentes: estación Windguru del Club Náutico San Isidro, Pilote Norden (CARP), AySA Palermo y Windguru GFS 13 km.
La apuesta y la probabilidad son una regla inicial, todavía sin calibrar.</p>
</main></body></html>"""
    (docs / "index.html").write_text(page, encoding="utf-8")
