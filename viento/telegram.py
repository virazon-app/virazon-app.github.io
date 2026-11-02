"""Envio de mensajes y fotos por Telegram (bot gratis)."""
import os

import requests

API = "https://api.telegram.org/bot{token}/{metodo}"


def _url(metodo):
    return API.format(token=os.environ["TELEGRAM_TOKEN"], metodo=metodo)


def activo():
    return bool(os.environ.get("TELEGRAM_TOKEN")) and not os.environ.get("DRY_RUN")


def mensajes_nuevos(offset):
    """Lee lo que le escribieron al bot (/start, /estado). Devuelve (lista, nuevo_offset)."""
    r = requests.get(_url("getUpdates"), params={"offset": offset, "timeout": 0}, timeout=20)
    r.raise_for_status()
    res = r.json().get("result", [])
    out = []
    for u in res:
        offset = max(offset, u["update_id"] + 1)
        m = u.get("message") or u.get("edited_message")
        if m and "text" in m:
            out.append({"chat": m["chat"]["id"], "texto": m["text"].strip().lower()})
    return out, offset


def texto(chat, msg):
    if not activo():
        print("[telegram:dry]", msg)
        return
    requests.post(_url("sendMessage"), data={"chat_id": chat, "text": msg, "parse_mode": "HTML"},
                  timeout=20).raise_for_status()


def foto(chat, path, caption):
    if not activo():
        print("[telegram:dry] foto", path, "|", caption)
        return
    with open(path, "rb") as f:
        requests.post(_url("sendPhoto"), data={"chat_id": chat, "caption": caption[:1000], "parse_mode": "HTML"},
                      files={"photo": f}, timeout=60).raise_for_status()
