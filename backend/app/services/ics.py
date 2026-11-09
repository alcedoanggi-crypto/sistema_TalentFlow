"""Generación de invitaciones iCalendar (RFC 5545) sin dependencias externas.

- UID estable por entrevista y SEQUENCE incremental: al reprogramar, Google
  Calendar / Outlook actualizan el evento existente en vez de duplicarlo.
- METHOD:REQUEST para invitar y METHOD:CANCEL para cancelar.
- Las líneas se pliegan a 75 octetos y el texto se escapa según la norma.
"""
from datetime import datetime, timedelta, timezone


def _escapar(texto: str) -> str:
    return (texto or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


def _plegar(linea: str) -> str:
    """Pliega a 75 octetos sin partir caracteres UTF-8 multibyte."""
    salida, actual = [], b""
    for ch in linea:
        b = ch.encode("utf-8")
        if len(actual) + len(b) > 75:
            salida.append(actual.decode("utf-8"))
            actual = b" " + b
        else:
            actual += b
    salida.append(actual.decode("utf-8"))
    return "\r\n".join(salida)


def _utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generar_ics(*, uid: str, secuencia: int, inicio: datetime, duracion_min: int, titulo: str,
                descripcion: str, lugar: str | None, organizador: tuple[str, str],
                asistentes: list[tuple[str, str]], cancelar: bool = False) -> str:
    fin = inicio + timedelta(minutes=duracion_min)
    org_nombre, org_email = organizador
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TalentFlow//ATS//ES",
        "CALSCALE:GREGORIAN",
        f"METHOD:{'CANCEL' if cancelar else 'REQUEST'}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"SEQUENCE:{secuencia}",
        f"DTSTAMP:{_utc(datetime.now(timezone.utc))}",
        f"DTSTART:{_utc(inicio)}",
        f"DTEND:{_utc(fin)}",
        f"SUMMARY:{_escapar(titulo)}",
        f"DESCRIPTION:{_escapar(descripcion)}",
    ]
    if lugar:
        lineas.append(f"LOCATION:{_escapar(lugar)}")
        if lugar.startswith("http"):
            lineas.append(f"URL:{lugar}")
    lineas.append(f"ORGANIZER;CN={_escapar(org_nombre)}:mailto:{org_email}")
    for nombre, email in asistentes:
        lineas.append(f"ATTENDEE;CN={_escapar(nombre)};ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{email}")
    lineas.append(f"STATUS:{'CANCELLED' if cancelar else 'CONFIRMED'}")
    if not cancelar:
        lineas += ["BEGIN:VALARM", "TRIGGER:-PT30M", "ACTION:DISPLAY",
                   f"DESCRIPTION:{_escapar(titulo)}", "END:VALARM"]
    lineas += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_plegar(l) for l in lineas) + "\r\n"
