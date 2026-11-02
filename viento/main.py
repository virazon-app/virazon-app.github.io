"""Corre cada 15 minutos (GitHub Actions): lee datos, decide alertas y manda por Telegram."""
import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from . import analisis as A
from . import fuentes as F
from . import imagen, pagina, telegram

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
ESTADO = DATA / "estado.json"
HIST = DATA / "historial.csv"
DOCS = RAIZ / "docs"
IMG = DOCS / "tablero.png"

AYUDA = ("Comandos:\n/estado - te mando el tablero ahora\n/ayuda - esta ayuda\n\n"
         "Reviso cada 15 min el Club Náutico, Pilote Norden, AySA y Windguru, y te aviso cuando:\n"
         "• entra SE en Norden y viene subiendo\n• sopla fuerte en el club (o se corta)\n"
         "• rota el viento\n• cambia el agua (sube/baja)\n• nuestra apuesta da para salir\n"
         "Y todas las mañanas te mando el resumen del día.")


def cargar_json(p, defecto):
    try:
        return json.loads(Path(p).read_text())
    except Exception:  # noqa: BLE001
        return defecto


def guardar_estado(est):
    DATA.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(est, indent=1, ensure_ascii=False))


def en_silencio(t, cfg):
    a, b = cfg["horas_silencio"]
    return t.hour >= a or t.hour < b


def puede(est, tipo, t, horas):
    ult = est.setdefault("alertas", {}).get(tipo)
    if ult and t - datetime.fromisoformat(ult) < timedelta(hours=horas):
        return False
    return True


def marcar(est, tipo, t):
    est.setdefault("alertas", {})[tipo] = t.isoformat()


def f1(x):
    return "" if x is None else f"{x:.1f}"


def main():
    DATA.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    cfg = cargar_json(RAIZ / "config.json", {})
    est = cargar_json(ESTADO, {})
    t0 = F.ahora()
    print("Corrida", t0.isoformat())

    # ---- mensajes que le mandaron al bot
    chat = os.environ.get("TELEGRAM_CHAT_ID") or est.get("chat")
    pedidos = []
    if telegram.activo():
        try:
            msgs, est["offset"] = telegram.mensajes_nuevos(est.get("offset", 0))
            for m in msgs:
                if not chat and m["texto"].startswith("/start"):
                    chat = m["chat"]; est["chat"] = chat  # el primero que escribe queda como dueño
                if str(m["chat"]) != str(chat):
                    continue  # ignorar a cualquier otro
                pedidos.append(m["texto"])
        except Exception as e:  # noqa: BLE001
            print("telegram getUpdates fallo:", e)

    # ---- datos
    club = F.club_nautico(cfg["windguru_estacion_club"])
    nor = F.norden()
    ays = F.aysa(cfg["aysa_estacion"])
    pron = F.pronostico_windguru(cfg["windguru_spot_pronostico"], cfg["windguru_modelo"])
    if nor and t0 - nor["t"] > timedelta(hours=4):
        print("Norden viejo, lo ignoro:", nor["t"])
        nor = None

    ap = A.apuesta(club, nor, pron, cfg, t0)
    ven = A.ventana(ap, t0)
    prob, items = A.prob_se(club, nor, pron, cfg, t0, ap)
    vir = A.virazon(pron, cfg, t0.date())
    agua = A.agua(ays, nor)
    umbral = cfg["umbral_salir_kn"]

    # ---- alertas
    alertas = []
    espera = cfg["espera_entre_alertas_iguales_horas"]
    es_se, subiendo, cambio = A.norden_tendencia(nor, cfg)
    if nor and es_se and nor["kn"] >= cfg["norden"]["alerta_kn"] and puede(est, "norden_se", t0, espera):
        txt = (f"<b>Entró SE en Pilote Norden</b>: {nor['kn']:.0f} kn del {A.punto(nor['dir'])}"
               + (f" (subiendo +{cambio:.0f} en 1 h)" if subiendo else "")
               + f". Debería llegar al club en ~{cfg['norden']['demora_horas']} h.")
        alertas.append(("norden_se", txt))
    if club and club["kn"] is not None:
        if club["kn"] >= umbral and puede(est, "club_sopla", t0, espera):
            alertas.append(("club_sopla", f"<b>Está soplando en el club</b>: {club['kn']:.0f} kn "
                                          f"(ráf {club['max'] or 0:.0f}) del {A.punto(club['dir'])}."))
        ult_sopla = est.get("alertas", {}).get("club_sopla")
        if (ult_sopla and t0 - datetime.fromisoformat(ult_sopla) < timedelta(hours=8)
                and club["kn"] < cfg["umbral_bajo_kn"] and puede(est, "club_corto", t0, espera)
                and est.get("alertas", {}).get("club_corto", "") < ult_sopla):
            alertas.append(("club_corto", f"<b>Se cortó</b>: ahora {club['kn']:.0f} kn en el club."))
        s = club["serie"]
        if len(s) >= 5:
            d_ahora = A.media_angular([p["dir"] for p in s[-2:]])
            d_antes = A.media_angular([p["dir"] for p in s[-5:-3]])
            if (d_ahora is not None and d_antes is not None
                    and A.dif_angulo(d_ahora, d_antes) >= cfg["rotacion_grados"]
                    and club["kn"] >= cfg["rotacion_min_kn"] and puede(est, "rotacion", t0, 2)):
                alertas.append(("rotacion", f"<b>Rotó el viento en el club</b>: de {A.punto(d_antes)} a "
                                            f"{A.punto(d_ahora)} ({club['kn']:.0f} kn)."))
    if cfg.get("alertar_cambio_marea") and agua and agua["cmh_prev"] is not None:
        if (abs(agua["cmh"]) >= 2 and abs(agua["cmh_prev"]) >= 2 and (agua["cmh"] > 0) != (agua["cmh_prev"] > 0)
                and puede(est, "marea", t0, 4)):
            alertas.append(("marea", f"<b>Cambió el agua</b>: ahora {A.tendencia_txt(agua['cmh'])} "
                                     f"({agua['cmh']:+.0f} cm/h), nivel {agua['m']:.2f} m ({agua['fuente']})."))
    if ven and ven["kn"] >= umbral and ven["desde"] - t0 < timedelta(hours=6) and puede(est, "apuesta", t0, 6):
        alertas.append(("apuesta", f"<b>Nuestra apuesta da para salir</b>: {ven['kn']} kn "
                                   f"{pagina.horas_txt(ven['desde'], ven['hasta'])}."))

    silencio = en_silencio(t0, cfg)
    if silencio:
        alertas = []
    resumen = (not silencio and t0.hour >= cfg["resumen_diario_hora"]
               and est.get("resumen") != t0.date().isoformat())

    # ---- armar y mandar
    banner = alertas[0][1].split("</b>")[0].replace("<b>", "") if alertas else None
    datos_vista = {"t0": t0, "club": club, "nor": nor, "ays": ays, "pron": pron, "ap": ap,
                   "ventana": ven, "prob": prob, "items": items, "vir": vir, "agua": agua,
                   "banner": banner, "umbral": umbral}
    imagen.armar(IMG, datos_vista)  # la imagen es la que se manda por Telegram
    pie = ""
    if ven:
        pie = (f"\n\nApuesta: <b>{ven['kn']} kn</b> ({ven['lo']}–{ven['hi']}) {pagina.horas_txt(ven['desde'], ven['hasta'])}"
               + (f" · Windguru {ven['wg_lo']}–{ven['wg_hi']} kn" if ven["wg_lo"] is not None else "")
               + f"\nProb. SE ≥{umbral} kn próx. 3 h: {prob}%")
    if chat:
        try:
            for p in pedidos:
                if p.startswith("/start"):
                    telegram.texto(chat, "Listo, quedaste registrado. " + AYUDA)
                elif p.startswith("/ayuda") or p.startswith("/help"):
                    telegram.texto(chat, AYUDA)
            if alertas:
                telegram.foto(chat, IMG, "\n".join(a[1] for a in alertas) + pie)
                for tipo, _ in alertas:
                    marcar(est, tipo, t0)
            elif resumen:
                telegram.foto(chat, IMG, f"<b>Buen día.</b> Virazón: {vir['nivel']}." + pie)
            elif any(p.startswith(("/estado", "/start")) for p in pedidos):
                telegram.foto(chat, IMG, "Estado ahora." + pie)
            if resumen:
                est["resumen"] = t0.date().isoformat()
        except Exception as e:  # noqa: BLE001
            print("telegram envio fallo:", e)
    elif telegram.activo():
        print("Todavía no hay chat: mandale /start al bot.")

    # ---- historial (para calibrar la apuesta mas adelante)
    DATA.mkdir(exist_ok=True)
    nuevo = not HIST.exists()
    ap3 = ap[3]["kn"] if len(ap) > 3 else None
    with HIST.open("a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["hora", "club_kn", "club_raf", "club_dir", "norden_hora", "norden_kn", "norden_raf",
                        "norden_dir", "palermo_kn", "palermo_dir", "agua_m", "agua_cmh", "windguru_kn_ahora",
                        "apuesta_kn_en_3h", "prob_se", "alertas"])
        wg_now = A.pronostico_en(pron, t0)
        w.writerow([t0.strftime("%Y-%m-%d %H:%M"),
                    f1(club and club["kn"]), f1(club and club["max"]), f1(club and club["dir"]),
                    nor["t"].strftime("%H:%M") if nor else "", f1(nor and nor["kn"]), f1(nor and nor["max"]),
                    f1(nor and nor["dir"]), f1(ays and ays["kn"]), f1(ays and ays["dir"]),
                    f"{agua['m']:.2f}" if agua else "", f1(agua and agua["cmh"]),
                    f1(wg_now and wg_now["kn"]), f1(ap3), prob, "|".join(a[0] for a in alertas)])
    pagina.armar(DOCS, datos_vista, [a[1].replace("<b>", "").replace("</b>", "") for a in alertas], HIST)
    guardar_estado(est)
    print("Fuentes:", {"club": bool(club), "norden": bool(nor), "aysa": bool(ays), "windguru": bool(pron)},
          "| alertas:", [a[0] for a in alertas], "| prob", prob, "| ventana", ven and ven["kn"])


if __name__ == "__main__":
    main()
