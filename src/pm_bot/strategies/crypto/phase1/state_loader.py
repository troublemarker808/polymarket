"""Reusable loaders for crypto underlying-state payloads."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pm_bot.strategies.crypto.phase1.inputs import build_underlying_state
from pm_bot.strategies.crypto.phase1.models import CryptoUnderlyingState


def load_underlying_states(path: str | Path) -> dict[str, CryptoUnderlyingState]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_items = payload if isinstance(payload, list) else payload.get("states", [payload])
    states: dict[str, CryptoUnderlyingState] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        state = build_underlying_state(
            underlying=str(item["underlying"]),
            as_of=datetime.fromisoformat(str(item["as_of"]).replace("Z", "+00:00")),
            spot_price=float(item["spot_price"]),
            daily_return=float(item.get("daily_return", 0.0)),
            realized_volatility=float(item.get("realized_volatility", 0.0)),
            implied_volatility=(
                float(item["implied_volatility"])
                if item.get("implied_volatility") not in (None, "")
                else None
            ),
        )
        states[state.underlying] = state
    return states
