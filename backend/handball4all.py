"""Read-only Handball4all schedule for the one configured league.

Adapted from h4all-statistik/app/live.py and app/import_league.py.
No remote data is persisted or allowed to overwrite WURFBILD analysis.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from .main import current_user

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
def schedule(user=Depends(current_user)):
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
