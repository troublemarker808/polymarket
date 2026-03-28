import json
from pathlib import Path

from pm_bot.strategies.sports.phase1.validation import review_closing_line


FIXTURE_CASES = Path("tests/fixtures/sports_phase1/closing_line_cases.json")


def test_review_closing_line_reports_positive_clv_when_market_moves_toward_fair() -> None:
    payload = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))["pregame_moneyline"]

    review = review_closing_line(
        market_id="nba-1",
        open_probability=float(payload["open_probability"]),
        fair_probability=float(payload["fair_probability"]),
        close_probability=float(payload["close_probability"]),
    )

    assert review.market_id == "nba-1"
    assert round(review.clv_bps, 1) == 400.0
    assert review.moved_toward_fair is True
