from pm_bot.core.types import Category, SignalSide


def test_core_enums_exist() -> None:
    assert Category.SPORTS.value == "sports"
    assert SignalSide.BUY_YES.value == "buy_yes"
    assert SignalSide.SELL_NO.value == "sell_no"
