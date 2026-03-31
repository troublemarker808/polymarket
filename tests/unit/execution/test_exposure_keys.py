from datetime import datetime, timezone

from pm_bot.core.types import Category, MarketSnapshot, SignalSide
from pm_bot.execution.exposure_keys import derive_exposure_keys


def test_derive_exposure_keys_groups_btc_bullish_thesis_across_dip_no_and_reach_yes() -> None:
    now = datetime.now(tz=timezone.utc)
    dip_snapshot = MarketSnapshot(
        market_id="dip-50k",
        token_id="dip-yes",
        slug="will-bitcoin-dip-to-50000-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        metadata={"question": "Will Bitcoin dip to $50,000 by December 31, 2026?", "no_token_id": "dip-no"},
    )
    reach_snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        metadata={"question": "Will Bitcoin hit $150K by December 31, 2026?"},
    )

    dip_no_keys = derive_exposure_keys(dip_snapshot, side=SignalSide.BUY_NO)
    reach_yes_keys = derive_exposure_keys(reach_snapshot, side=SignalSide.BUY_YES)

    assert dip_no_keys.thesis_group_id == "crypto:btc:bullish"
    assert reach_yes_keys.thesis_group_id == "crypto:btc:bullish"
    assert dip_no_keys.underlying_group_id == "crypto:btc"
    assert reach_yes_keys.underlying_group_id == "crypto:btc"


def test_derive_exposure_keys_groups_btc_bearish_thesis_across_dip_yes_and_reach_no() -> None:
    now = datetime.now(tz=timezone.utc)
    dip_snapshot = MarketSnapshot(
        market_id="dip-50k",
        token_id="dip-yes",
        slug="will-bitcoin-dip-to-50000-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        metadata={"question": "Will Bitcoin dip to $50,000 by December 31, 2026?", "no_token_id": "dip-no"},
    )
    reach_snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="will-bitcoin-hit-150k-by-december-31-2026",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        metadata={"question": "Will Bitcoin hit $150K by December 31, 2026?", "no_token_id": "reach-no"},
    )

    dip_yes_keys = derive_exposure_keys(dip_snapshot, side=SignalSide.BUY_YES)
    reach_no_keys = derive_exposure_keys(reach_snapshot, side=SignalSide.BUY_NO)

    assert dip_yes_keys.thesis_group_id == "crypto:btc:bearish"
    assert reach_no_keys.thesis_group_id == "crypto:btc:bearish"


def test_derive_exposure_keys_does_not_misread_what_price_btc_titles() -> None:
    now = datetime.now(tz=timezone.utc)
    snapshot = MarketSnapshot(
        market_id="reach-150k",
        token_id="reach-yes",
        slug="what-price-will-bitcoin-hit-before-2027",
        category=Category.CRYPTO,
        timestamp=now,
        resolution_time=datetime(2027, 1, 1, tzinfo=timezone.utc),
        metadata={"question": "What price will Bitcoin hit before 2027?"},
    )

    keys = derive_exposure_keys(snapshot, side=SignalSide.BUY_YES)

    assert keys.underlying_group_id == "crypto:btc"
    assert keys.thesis_group_id == "crypto:btc:reach"
