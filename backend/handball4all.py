"""Read-only Handball4all schedule for the one configured league.

Adapted from h4all-statistik/app/live.py and app/import_league.py.
No remote data is persisted or allowed to overwrite WURFBILD analysis.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request

def authenticated_user(request: Request):
    # Resolve at request time to avoid circular imports during module loading.
    from .main import current_user
    return current_user(request)


router = APIRouter(prefix="/api/handball4all")
ORG = "216"
LEAGUE = "161291"
API = "https://spo.handball4all.de/service/if_g_json.php"
BERLIN = ZoneInfo("Europe/Berlin")


def parse_schedule(payload):
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise ValueError("Invalid provider response")
    root = payload[0]
    content = root.get("content", {})
    future = content.get("futureGames", {})
    if not isinstance(future, dict) or str(future.get("gClassID")) != LEAGUE:
        raise ValueError("Wrong league")
    games = {}
    def visit(value):
        if isinstance(value, dict):
            if value.get("gID") and value.get("gHomeTeam") and value.get("gGuestTeam"):
                games[str(value["gID"])] = value
            else:
                for child in value.values():
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(future.get("games", []))
    visit(content.get("actualGames", []))
    if not games:
        raise ValueError("No games found")
    return {
        "organization": ORG,
        "league": LEAGUE,
        "season": str(root.get("menu", {}).get("period", {}).get("selectedID") or ""),
        "games": [
            {"externalId": gid, "reportId": str(g.get("sGID") or ""), "home": str(g["gHomeTeam"]), "away": str(g["gGuestTeam"]),
             "date": str(g.get("gDate") or ""), "time": str(g.get("gTime") or ""),
             "homeGoals": g.get("gHomeGoals"), "awayGoals": g.get("gGuestGoals"),
             "venue": str(g.get("gGymnasiumName") or ""), "gameNumber": str(g.get("gNo") or "")}
            for gid, g in sorted(games.items())
        ],
    }


@router.get("/schedule")
def schedule(user=Depends(authenticated_user)):
    params = urllib.parse.urlencode({
        "cmd": "ps", "og": ORG, "cl": LEAGUE, "ca": "1",
        "do": datetime.now(BERLIN).strftime("%Y-%m-%d"),
    })
    request = urllib.request.Request(
        API + "?" + params, headers={"User-Agent": "Wurfbild/0.1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Provider response too large")
        return parse_schedule(json.loads(raw))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=502, detail="Handball4all schedule unavailable") from exc


REPORT_URL = "https://spo.handball4all.de/misc/sboPublicReports.php?sGID="


def parse_rosters(text):
    """Extract both lineups from the 'Mannschaftslisten' PDF page."""
    if "Mannschaftslisten" not in text:
        raise ValueError("No roster section")
    section = text.split("Mannschaftslisten", 1)[1].split("Spielverlauf", 1)[0]
    teams = {}
    side = None
    for line in section.splitlines():
        heading = re.match(r"^\\s*(Heim|Gast):\\s*(.+?)\\s*$", line)
        if heading:
            side = "home" if heading.group(1) == "Heim" else "away"
            teams[side] = {"name": heading.group(2), "players": []}
            continue
        if side is None:
            continue
        match = re.match(r"^\\s*(\\d{1,2})\\s+(.+?)\\s*$", line)
        if not match:
            continue
        number, rest = match.groups()
        # Only parse the initial name columns; trailing statistics start at
        # wide whitespace. Avoid treating staff rows A-E as players.
        name = re.split(r"\\s{2,}", rest.strip(), maxsplit=1)[0].strip()
        if not name or name.isdecimal() or len(name) > 100:
            continue
        teams[side]["players"].append({"number": int(number), "name": name})
    if set(teams) != {"home", "away"} or not all(teams[s]["players"] for s in teams):
        raise ValueError("Incomplete roster")
    for team in teams.values():
        numbers = [p["number"] for p in team["players"]]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Duplicate shirt numbers")
    return teams


@router.get("/report/{report_id}/rosters")
def report_rosters(report_id: str, user=Depends(authenticated_user)):
    if not re.fullmatch(r"[1-9]\\d{0,9}", report_id):
        raise HTTPException(422, "Invalid report ID")
    try:
        import pymupdf
    except ImportError as exc:
        raise HTTPException(503, "PyMuPDF not installed") from exc
    try:
        request = urllib.request.Request(
            REPORT_URL + report_id, headers={"User-Agent": "Wurfbild/0.1"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.headers.get_content_type() != "application/pdf":
                raise ValueError("Not a PDF")
            pdf = response.read(2_000_001)
        if len(pdf) > 2_000_000 or not pdf.startswith(b"%PDF"):
            raise ValueError("Invalid PDF")
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            if len(doc) > 20:
                raise ValueError("Unexpected PDF size")
            text = "\\n".join(page.get_text(sort=True) for page in doc)
        return {"reportId": report_id, "rosters": parse_rosters(text)}
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(502, "Handball4all report unavailable or unrecognized") from exc
