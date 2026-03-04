# app/scorecard.py
"""Scorecard prompt and JSON parsing for golf scorecard images."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

SCORECARD_PROMPT = """This image is a golf scorecard. Identify every player (columns or rows may be labeled A, B, C, or by name). For each player, list the score for each hole in order (holes 1 through 18, or 1 through 9 if it's a 9-hole card). Include each player's total score.

Reply with ONLY a single JSON object, no markdown and no other text. Use this exact shape:
{"players": [{"name": "A", "scores_by_hole": [{"hole": 1, "score": 4}, {"hole": 2, "score": 3}, ...], "total": 72}, {"name": "B", "scores_by_hole": [...], "total": ...}]}
- "name" is the player label (e.g. A, B, or the name on the card).
- "scores_by_hole" is an array of objects with "hole" (1-based) and "score" (integer).
- "total" is the sum of that player's hole scores.
If the card has fewer than 18 holes, only include the holes that exist. Output valid JSON only."""


def parse_scorecard_json(raw: str) -> Dict[str, Any]:
    """Strip optional markdown code fences and parse JSON."""
    text = raw.strip()
    m = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def normalize_players_response(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build response players list: name, scores_by_hole [{hole, score}], total."""
    players_in = parsed.get("players") or []
    out: List[Dict[str, Any]] = []
    for p in players_in:
        if not isinstance(p, dict):
            continue
        name = p.get("name") or p.get("player") or "?"
        if isinstance(name, (int, float)):
            name = str(name)
        scores_by_hole_in = p.get("scores_by_hole")
        if not isinstance(scores_by_hole_in, list):
            continue
        holes_out: List[Dict[str, Any]] = []
        for i, s in enumerate(scores_by_hole_in):
            if isinstance(s, dict) and "score" in s:
                hole = s.get("hole", i + 1)
                score = s.get("score")
                if score is not None:
                    try:
                        holes_out.append({"hole": int(hole) if isinstance(hole, (int, float)) else i + 1, "score": int(score)})
                    except (ValueError, TypeError):
                        pass
            elif isinstance(s, (int, float)):
                holes_out.append({"hole": i + 1, "score": int(s)})
        total_in = p.get("total")
        if total_in is not None:
            try:
                total = int(total_in)
            except (ValueError, TypeError):
                total = sum(h["score"] for h in holes_out)
        else:
            total = sum(h["score"] for h in holes_out)
        out.append({"name": name, "scores_by_hole": holes_out, "total": total})
    return out
