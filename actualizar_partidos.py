#!/usr/bin/env python3
"""
Actualiza fixtures.json leyendo calendarios .ics públicos de Fixtur.es
(https://fixtur.es), que publica un calendario por equipo con todas sus
competencias, sin llave ni registro, y lo mantiene al día solo.

Cubre Boca Juniors, Inter Miami y FC Barcelona. Fixtur.es no incluye la Primera
División de Costa Rica, así que Alajuelense se intenta por ESPN a través de un
proxy y, si no responde, se queda con lo que haya en partidos.json.

Lo corre GitHub Actions cada lunes. También se puede correr a mano:
    python3 actualizar_partidos.py
"""

import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

try:
    from zoneinfo import ZoneInfo
    CR = ZoneInfo("America/Costa_Rica")
except Exception:                       # respaldo: Costa Rica es UTC-6 todo el año
    CR = timezone(timedelta(hours=-6))

SALIDA = "fixtures.json"
MESES = 6
UA = {"User-Agent": "Mozilla/5.0 (calendario-partidos)"}

# Un equipo puede tener varios nombres posibles en Fixtur.es: se prueban en orden.
EQUIPOS_ICS = [
    {
        "key": "boca",
        "slugs": ["boca-juniors"],
        "nombres": ["boca juniors", "boca"],
        "torneo_por_defecto": "Partido de Boca",
    },
    {
        "key": "miami",
        "slugs": ["inter-miami-cf", "inter-miami"],
        "nombres": ["inter miami cf", "inter miami"],
        "torneo_por_defecto": "Partido de Inter Miami",
    },
    {
        "key": "barca",
        "slugs": ["fc-barcelona"],
        "nombres": ["fc barcelona", "barcelona"],
        "torneo_por_defecto": "Partido del Barcelona",
    },
]


def pedir(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


# ---------------------------------------------------------------- iCalendar
def desdoblar(texto):
    """Une las líneas partidas del formato iCalendar (empiezan con espacio)."""
    lineas = []
    for linea in texto.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if linea[:1] in (" ", "\t") and lineas:
            lineas[-1] += linea[1:]
        else:
            lineas.append(linea)
    return lineas


def eventos_ics(texto):
    evento, dentro = {}, False
    for linea in desdoblar(texto):
        if linea.startswith("BEGIN:VEVENT"):
            evento, dentro = {}, True
            continue
        if linea.startswith("END:VEVENT"):
            if dentro:
                yield evento
            dentro = False
            continue
        if not dentro or ":" not in linea:
            continue
        izq, valor = linea.split(":", 1)
        clave = izq.split(";")[0].upper()
        params = izq.split(";")[1:]
        if clave in ("SUMMARY", "LOCATION", "DESCRIPTION", "CATEGORIES", "UID"):
            evento[clave] = valor.replace("\\,", ",").replace("\\n", " ").strip()
        elif clave == "DTSTART":
            evento["DTSTART"] = valor.strip()
            for p in params:
                if p.upper().startswith("TZID="):
                    evento["TZID"] = p.split("=", 1)[1].strip('"')


def a_fecha(valor, tzid):
    """Convierte el DTSTART del .ics a una fecha con zona horaria."""
    v = valor.strip()
    if v.endswith("Z"):
        return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    if "T" in v:
        base = datetime.strptime(v[:15], "%Y%m%dT%H%M%S")
        if tzid:
            try:
                return base.replace(tzinfo=ZoneInfo(tzid))
            except Exception:
                pass
        return base.replace(tzinfo=timezone.utc)
    return datetime.strptime(v[:8], "%Y%m%d").replace(tzinfo=timezone.utc)


def limpiar_marcador(nombre):
    return re.sub(r"\s*\(\d+\s*[-–]\s*\d+\)\s*$", "", nombre).strip()


def partido_de_evento(ev, equipo):
    titulo = limpiar_marcador(ev.get("SUMMARY", ""))
    if " - " not in titulo:
        return None
    local_txt, visita_txt = [t.strip() for t in titulo.split(" - ", 1)]

    def es_mio(txt):
        t = txt.lower()
        return any(n in t for n in equipo["nombres"])

    if es_mio(local_txt):
        soy_local, rival = True, visita_txt
    elif es_mio(visita_txt):
        soy_local, rival = False, local_txt
    else:
        return None

    cuando = a_fecha(ev["DTSTART"], ev.get("TZID")).astimezone(CR)
    ahora = datetime.now(CR)
    if cuando < ahora - timedelta(days=1) or cuando > ahora + timedelta(days=31 * MESES):
        return None

    torneo = (ev.get("CATEGORIES") or ev.get("DESCRIPTION") or "").strip()
    torneo = re.sub(r"https?://\S+", "", torneo).strip(" -–|")
    if not torneo or len(torneo) > 60:
        torneo = equipo["torneo_por_defecto"]

    return {
        "equipo": equipo["key"],
        "fecha": cuando.strftime("%Y-%m-%d"),
        "hora": cuando.strftime("%H:%M"),
        "rival": rival,
        "torneo": torneo,
        "local": soy_local,
        "sede": (ev.get("LOCATION") or "").strip(),
    }


def partidos_de_equipo(equipo):
    for slug in equipo["slugs"]:
        url = f"https://ics.fixtur.es/v2/{slug}.ics"
        try:
            texto = pedir(url)
        except Exception as e:
            print(f"    {slug}.ics no respondió ({e})")
            continue
        salida = [p for p in (partido_de_evento(ev, equipo) for ev in eventos_ics(texto)) if p]
        if salida:
            print(f"    {slug}.ics → {len(salida)} partidos")
            return salida
        print(f"    {slug}.ics no traía partidos futuros")
    return []


# ------------------------------------------------- Alajuelense (ESPN vía proxy)
ESPN = "site.api.espn.com/apis/site/v2/sports/soccer"
CAMINOS = [
    "https://{u}",                       # directo, por si el bloqueo desaparece
    "https://api.allorigins.win/raw?url=https%3A%2F%2F{e}",
    "https://r.jina.ai/https://{u}",
]
TORNEOS_LDA = [
    ("crc.1", "Primera División"),
    ("concacaf.champions", "Concacaf Champions Cup"),
]


def pedir_json(camino):
    for plantilla in CAMINOS:
        url = plantilla.format(u=camino, e=quote(camino, safe=""))
        try:
            return json.loads(pedir(url))
        except Exception:
            continue
    return None


def partidos_alajuelense():
    salida = []
    ahora = datetime.now(CR)
    for code, label in TORNEOS_LDA:
        datos = pedir_json(f"{ESPN}/{code}/teams/2057/schedule")
        if not datos:
            print(f"    {label}: ESPN no respondió por ningún camino")
            continue
        encontrados = 0
        for ev in datos.get("events") or []:
            comp = (ev.get("competitions") or [{}])[0]
            rivales = comp.get("competitors") or []
            yo = next((c for c in rivales if str(c.get("team", {}).get("id")) == "2057"), None)
            otro = next((c for c in rivales if c is not yo), None)
            iso = comp.get("date") or ev.get("date")
            if not (yo and otro and iso):
                continue
            try:
                cuando = datetime.strptime(iso.replace("Z", "+0000"), "%Y-%m-%dT%H:%M%z").astimezone(CR)
            except ValueError:
                continue
            if cuando < ahora - timedelta(days=1) or cuando > ahora + timedelta(days=31 * MESES):
                continue
            salida.append({
                "equipo": "lda",
                "fecha": cuando.strftime("%Y-%m-%d"),
                "hora": cuando.strftime("%H:%M"),
                "rival": otro["team"].get("displayName", "Rival por definir"),
                "torneo": label,
                "local": yo.get("homeAway") == "home",
                "sede": (comp.get("venue") or {}).get("fullName", ""),
            })
            encontrados += 1
        print(f"    {label}: {encontrados} partidos")
    return salida


# ------------------------------------------------------------------- programa
def main():
    todos, fuentes = [], []

    for equipo in EQUIPOS_ICS:
        print(f"  {equipo['key']}:")
        partidos = partidos_de_equipo(equipo)
        todos += partidos
        fuentes.append({"equipo": equipo["key"], "torneo": "Fixtur.es (todas sus competencias)",
                        "code": equipo["slugs"][0], "respondio": bool(partidos),
                        "encontrados": len(partidos)})

    print("  lda:")
    try:
        lda = partidos_alajuelense()
    except Exception as e:
        print(f"    error: {e}")
        lda = []
    todos += lda
    fuentes.append({"equipo": "lda", "torneo": "ESPN (Costa Rica y Concacaf)",
                    "code": "espn", "respondio": bool(lda), "encontrados": len(lda)})

    # un partido por equipo y día
    unicos = {}
    for p in todos:
        unicos.setdefault((p["equipo"], p["fecha"]), p)
    lista = sorted(unicos.values(), key=lambda p: (p["fecha"], p.get("hora", "")))

    if not lista:
        print("Ninguna fuente respondió; no se toca fixtures.json")
        return

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"actualizado": datetime.now(timezone.utc).isoformat(),
                   "fuentes": fuentes, "partidos": lista},
                  f, ensure_ascii=False, indent=1)
    print(f"{SALIDA} escrito con {len(lista)} partidos")


if __name__ == "__main__":
    main()
