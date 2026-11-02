"""Arma la imagen tipo tablero que se manda por Telegram."""
from datetime import timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Wedge  # noqa: E402

from .analisis import punto, tendencia_txt  # noqa: E402

BG = "#0f172a"; CARD = "#1e293b"; TXT = "#e2e8f0"; MUTED = "#94a3b8"
GREEN = "#22c55e"; YEL = "#eab308"; RED = "#ef4444"; BLUE = "#38bdf8"; ORG = "#f97316"; GRAY = "#64748b"; PUR = "#a78bfa"
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TXT})


def _hhmm(t):
    return t.strftime("%H:%M") if t else "--"


def _compass(ax, deg, kn, raf, titulo):
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.45, 1.3); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Circle((0, 0), 1, fc="#0b1220", ec=GRAY, lw=2))
    for d, l in [(0, "N"), (90, "E"), (180, "S"), (270, "O")]:
        r = np.radians(d); ax.text(1.15*np.sin(r), 1.15*np.cos(r), l, ha="center", va="center", fontsize=13, color=MUTED, weight="bold")
    for d in range(0, 360, 45):
        r = np.radians(d); ax.plot([0.88*np.sin(r), np.sin(r)], [0.88*np.cos(r), np.cos(r)], color=GRAY, lw=1.5)
    if deg is not None:
        r = np.radians(deg + 180); dx, dy = np.sin(r), np.cos(r)
        ax.annotate("", xy=(0.75*dx, 0.75*dy), xytext=(-0.75*dx, -0.75*dy),
                    arrowprops=dict(arrowstyle="-|>,head_width=0.6,head_length=1.0", lw=5, color=BLUE))
    ax.text(0, -1.36, titulo, ha="center", fontsize=12, color=MUTED)
    tit = "sin datos" if kn is None else f"{kn:.1f} kn" + (f" (ráf {raf:.0f})" if raf is not None else "")
    ax.set_title(tit, fontsize=19, weight="bold", color=TXT, pad=2)


def _gauge(ax, val, vmax, label, unit, bands, fmt="{:.0f}"):
    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.6, 1.15); ax.set_aspect("equal"); ax.axis("off")
    for a, b, c in bands:
        ax.add_patch(Wedge((0, 0), 1, 180-180*b/vmax, 180-180*a/vmax, width=0.25, fc=c, ec=BG, lw=2))
    v = 0 if val is None else val
    ang = np.radians(180 - 180*min(v, vmax)/vmax)
    ax.plot([0, 0.8*np.cos(ang)], [0, 0.8*np.sin(ang)], color=TXT, lw=5, solid_capstyle="round")
    ax.add_patch(Circle((0, 0), 0.07, fc=TXT))
    ax.text(0, -0.27, ("--" if val is None else fmt.format(val)) + unit, ha="center", fontsize=24, weight="bold")
    ax.text(0, -0.53, label, ha="center", fontsize=12, color=MUTED)


def armar(path, d):
    """d: dict con t0, club, nor, ays, pron, ap, ventana, prob, items, vir, agua, banner."""
    t0 = d["t0"]; club = d["club"]; nor = d["nor"]; ays = d["ays"]; ap = d["ap"]
    umbral = d["umbral"]
    fig = plt.figure(figsize=(10.8, 16.6), dpi=100, facecolor=BG)
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1)

    def card(x, y, w, h, c=CARD):
        bg.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012", fc=c, ec="none"))

    fig.text(0.05, 0.980, "VIENTO · Náutico San Isidro", fontsize=26, weight="bold", va="top")
    fig.text(0.05, 0.952, f"{DIAS[t0.weekday()]} {t0.day}/{t0.month} · {_hhmm(t0)}", fontsize=14, color=MUTED, va="top", weight="bold")

    # Banner con la apuesta
    v = d["ventana"]; alerta = d.get("banner")
    color = ORG if alerta else YEL
    card(0.05, 0.882, 0.90, 0.052, color)
    if v:
        tit = f"NUESTRA APUESTA: {v['kn']} kn  ({v['lo']} a {v['hi']})  de {v['desde']:%H} a {v['hasta']:%H} h"
        sub = (f"Windguru dice {v['wg_lo']}–{v['wg_hi']} kn" if v["wg_lo"] is not None else "Windguru sin datos")
    else:
        tit, sub = "NUESTRA APUESTA: sin datos", ""
    sub += "  ·  " + (alerta if alerta else ("da para salir" if v and v["kn"] >= umbral else "sin alerta"))
    fig.text(0.07, 0.918, tit, fontsize=19, weight="bold", va="center", color="#111")
    fig.text(0.07, 0.893, sub[:95], fontsize=13, va="center", color="#111")

    # Fila 1: brujulas + reloj
    card(0.04, 0.655, 0.92, 0.215)
    _compass(fig.add_axes([0.05, 0.665, 0.29, 0.19]), club and club["dir"], club and club["kn"], club and club["max"],
             f"Club Náutico · {punto(club and club['dir'])} · {_hhmm(club and club['t'])}")
    _gauge(fig.add_axes([0.355, 0.675, 0.29, 0.17]), club and club["kn"], 30, "velocidad club (kn)", "",
           [(0, umbral-4, GRAY), (umbral-4, umbral, YEL), (umbral, 25, GREEN), (25, 30, RED)], "{:.1f}")
    _compass(fig.add_axes([0.67, 0.665, 0.27, 0.19]), nor and nor["dir"], nor and nor["kn"], nor and nor["max"],
             f"Pilote Norden · {punto(nor and nor['dir'])} · {_hhmm(nor and nor['t'])}")

    # Fila 2: probabilidad SE
    card(0.04, 0.475, 0.92, 0.165)
    _gauge(fig.add_axes([0.05, 0.483, 0.36, 0.15]), d["prob"], 100, f"prob. SE ≥{umbral} kn (próx. 3 h)", "%",
           [(0, 30, GRAY), (30, 60, YEL), (60, 100, GREEN)])
    fig.text(0.44, 0.625, f"Por qué ~{d['prob']}%", fontsize=17, weight="bold", va="top")
    for i, (ok, t) in enumerate(d["items"]):
        y = 0.588 - i*0.027
        fig.text(0.44, y, "✔" if ok else "✖", fontsize=16, color=GREEN if ok else RED, va="center")
        fig.text(0.475, y, t[:42], fontsize=13.5, va="center")
    fig.text(0.44, 0.483, "Regla inicial, todavía sin calibrar con historial", fontsize=11, color=MUTED, style="italic")

    # Fila 3: grafico
    card(0.04, 0.235, 0.92, 0.225)
    fig.text(0.06, 0.447, "Viento (kn): medido · Windguru · nuestra apuesta", fontsize=15, weight="bold", va="center")
    ax = fig.add_axes([0.10, 0.285, 0.83, 0.135], facecolor=CARD)
    x0 = t0 - timedelta(hours=6); x1 = t0 + timedelta(hours=10)
    hx = lambda t: (t - t0).total_seconds() / 3600  # noqa: E731
    ymax = 10
    if club and club["serie"]:
        s = [p for p in club["serie"] if p["t"] >= x0]
        ax.fill_between([hx(p["t"]) for p in s], [p["kn"] for p in s], [p["max"] or p["kn"] for p in s], color=BLUE, alpha=0.2, lw=0)
        ax.plot([hx(p["t"]) for p in s], [p["kn"] for p in s], color=BLUE, lw=3, marker="o", ms=4, label="Club Náutico")
        ymax = max([ymax] + [p["max"] or p["kn"] for p in s])
    if nor and nor["serie"]:
        s = [p for p in nor["serie"] if p["t"] >= x0]
        ax.plot([hx(p["t"]) for p in s], [p["kn"] for p in s], color=ORG, lw=2.5, label="Pilote Norden")
        ymax = max([ymax] + [p["kn"] for p in s])
    if ays:
        s = [p for p in ays["serie"] if p["t"] >= x0 and p["kn"] is not None]
        ax.plot([hx(p["t"]) for p in s], [p["kn"] for p in s], color=PUR, lw=2, marker="s", ms=4, label="AySA Palermo")
    pron = d["pron"]
    if pron:
        s = [h for h in pron["horas"] if x0 <= h["t"] <= x1]
        ax.plot([hx(h["t"]) for h in s], [h["kn"] for h in s], color=GREEN, lw=3, ls="--", label="Windguru")
        ax.plot([hx(h["t"]) for h in s], [h["raf"] for h in s], color=GREEN, lw=1.2, ls=":", alpha=0.8)
        ymax = max([ymax] + [h["kn"] for h in s])
    if ap:
        xs = [hx(p["t"]) for p in ap]; ys = [p["kn"] for p in ap]
        ax.fill_between(xs, np.array(ys)-1.5, np.array(ys)+1.5, color=YEL, alpha=0.12, lw=0)
        ax.plot(xs, ys, color=YEL, lw=3.5, label="Nuestra apuesta")
        ymax = max([ymax] + ys)
        for p in ap[2::2]:
            if hx(p["t"]) > 10:
                break
            ax.plot(hx(p["t"]), p["kn"], "o", color=YEL, ms=7)
            ax.annotate(f"{p['kn']:.0f}", (hx(p["t"]), p["kn"]), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=12, weight="bold", color=YEL)
            if p["wg"] is not None:
                ax.annotate(f"{p['wg']:.0f}", (hx(p["t"]), p["wg"]), xytext=(0, -17), textcoords="offset points", ha="center", fontsize=11, weight="bold", color=GREEN)
    ax.axvline(0, color=MUTED, lw=1)
    ax.axhspan(umbral, 30, color=GREEN, alpha=0.06)
    ax.set_xlim(-6, 10); top = min(35, ymax * 1.45 + 2); ax.set_ylim(0, top)
    ax.text(0.1, top * 0.04, "ahora", color=MUTED, fontsize=11)
    ticks = list(range(-6, 11, 2))
    ax.set_xticks(ticks); ax.set_xticklabels([f"{(t0 + timedelta(hours=k)).hour}h" for k in ticks], color=MUTED, fontsize=11)
    ax.tick_params(colors=MUTED, labelsize=11)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(axis="y", color="#334155", lw=0.8)
    ax.legend(loc="upper right", ncol=2, frameon=False, fontsize=9.5, labelcolor=TXT)
    nota = "Norden llega con ~1,5 h de demora. Apuesta: regla inicial (Norden + Windguru + virazón), banda ±1,5 kn."
    fig.text(0.06, 0.247, nota, fontsize=10, color=MUTED)

    # Fila 4: agua + virazon
    card(0.04, 0.115, 0.445, 0.105); card(0.515, 0.115, 0.445, 0.105)
    ag = d["agua"]
    if ag:
        fig.text(0.07, 0.198, f"Agua ({ag['fuente']}, {_hhmm(ag['t'])})", fontsize=13, color=MUTED, va="center")
        fig.text(0.07, 0.158, f"{ag['m']:.2f} m".replace(".", ","), fontsize=28, weight="bold", va="center")
        flecha = "▲" if ag["cmh"] > 0 else "▼"
        fig.text(0.27, 0.158, f"{flecha} {ag['cmh']:+.0f} cm/h", fontsize=19, weight="bold",
                 color=GREEN if ag["cmh"] > 0 else ORG, va="center")
        fig.text(0.07, 0.128, tendencia_txt(ag["cmh"]), fontsize=11.5, color=MUTED, va="center")
    else:
        fig.text(0.07, 0.165, "Agua: sin datos", fontsize=16, va="center")
    vir = d["vir"]
    fig.text(0.545, 0.198, "Virazón esta tarde", fontsize=13, color=MUTED, va="center")
    col = {"alta": GREEN, "media": YEL}.get(vir["nivel"], GRAY)
    fig.text(0.545, 0.158, vir["nivel"] + (f" {vir['pct']}%" if vir.get("pct") else ""), fontsize=26, weight="bold", color=col, va="center")
    fig.text(0.545, 0.128, vir["detalle"][:48], fontsize=11, color=MUTED, va="center")

    # Fila 5: Windguru proximas horas / manana
    card(0.04, 0.012, 0.92, 0.09)
    modelo = pron["modelo"] if pron else "Windguru"
    fig.text(0.06, 0.088, f"Windguru ({modelo}) — lo que \"debería pasar\"", fontsize=14, weight="bold", va="center")
    if pron:
        objetivo = [t0 + timedelta(hours=h) for h in (2, 5, 8)]
        man = (t0 + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        objetivo += [man.replace(hour=h) for h in (10, 14, 18)]
        for i, t in enumerate(objetivo):
            h = min(pron["horas"], key=lambda x: abs((x["t"] - t).total_seconds()))
            x = 0.075 + i*0.148
            dia = "Hoy" if h["t"].date() == t0.date() else DIAS[h["t"].weekday()]
            fig.text(x, 0.064, f"{dia} {h['t']:%H}h", fontsize=11, color=MUTED, va="center")
            fig.text(x, 0.040, f"{h['kn']:.0f} kn", fontsize=17, weight="bold", color=GREEN if h["kn"] >= umbral else TXT, va="center")
            fig.text(x, 0.020, f"ráf {h['raf']:.0f} · {punto(h['dir'])}", fontsize=10.5, color=MUTED, va="center")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path
