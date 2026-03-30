import asyncio
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path
from types import SimpleNamespace

from pm_bot.adapters.in_memory import InMemoryMarketDataAdapter
from pm_bot.adapters.polymarket.user_ws_client import UserChannelAuth
from pm_bot.core.settings import RiskSettings, TradingSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderBookLevel, SignalSide, StrategySignal
from pm_bot.execution.paper_adapter import PaperExecutionAdapter
from pm_bot.execution.polymarket_live import PolymarketLiveExecutionAdapter
from pm_bot.orchestrator.event_router import EventRouter
from pm_bot.risk.manager import BasicRiskManager
from pm_bot.runtime.live_session import LiveSessionRunner
from pm_bot.runtime.state import PositionState
from pm_bot.runtime.sync_session import (
    SYNC_SHADOW_DUST_NOTIONAL,
    SYNC_SHADOW_DUST_SHARES,
    ShadowPaperCoordinator,
    SynchronizedLiveExecutionAdapter,
    _cleanup_size_from_balance_error,
    _cleanup_sync_shadow_session,
    _cleanup_exit_plan,
    _cleanup_position_candidates,
    _cleanup_position_shares,
    _cleanup_safe_position_shares,
    _filter_snapshots_by_crypto_barrier_distance,
    _filter_cleanup_runtime_positions,
    _is_runtime_position_dust,
    _load_required_cleanup_snapshots,
    _merge_snapshots_by_market_id,
    _prune_runtime_dust_positions,
    _prune_runtime_dust_pending_orders,
    _preflight_cancel_sync_shadow_open_orders,
    _refresh_cleanup_snapshots,
)
from pm_bot.storage.recorder import LiveRuntimeRecorder, PaperRuntimeRecorder


class FakeLiveClient:
    def __init__(self) -> None:
        self.open_orders = []
        self.cancelled_order_ids: list[str] = []

    def create_order(self, order_args, options=None):
        return order_args

    def post_order(self, order, orderType, post_only=False):
        return {"orderID": "live-1"}

    def cancel(self, order_id):
        self.cancelled_order_ids.append(order_id)
        return {"cancelled": order_id}

    def get_orders(self, params=None, next_cursor="MA=="):
        return list(self.open_orders)

    def get_trades(self, params=None, next_cursor="MA=="):
        return []

    def create_or_derive_api_creds(self, nonce=None):
        return {
            "api_key": "derived-key",
            "api_secret": "derived-secret",
            "api_passphrase": "derived-passphrase",
        }

    def set_api_creds(self, creds):
        return None


class SubmitOnceStrategy:
    strategy_id = "crypto.surface"

    def __init__(self) -> None:
        self._submitted = False

    async def evaluate(self, snapshot: MarketSnapshot, context) -> list[StrategySignal]:
        del context
        if self._submitted:
            return []
        self._submitted = True
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                category=Category.CRYPTO,
                market_id=snapshot.market_id,
                token_id=snapshot.token_id,
                fair_probability=0.61,
                side=SignalSide.BUY_YES,
                confidence=0.6,
                edge_bps=150.0,
                generated_at=snapshot.timestamp,
                target_price=0.5,
                target_size=5.0,
                quote_ttl_seconds=20,
            )
        ]


async def _market_stream(snapshot: MarketSnapshot):
    yield snapshot


async def _empty_user_stream():
    if False:
        yield


def test_sync_session_mirrors_same_intent_into_live_and_shadow(tmp_path: Path) -> None:
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.51,
        last_traded_price=0.495,
        metadata={"no_token_id": "no-token", "condition_id": "0xmarket"},
    )
    live_execution = PolymarketLiveExecutionAdapter(
        client=FakeLiveClient(),
        ttl_seconds=20,
        post_only=False,
        build_order_args=lambda intent: {
            "token_id": intent.token_id,
            "price": intent.price,
            "size": intent.size,
            "side": "BUY",
        },
        resolve_order_type=lambda tif: tif,
        user_channel_auth=UserChannelAuth(
            api_key="key",
            secret="secret",
            passphrase="passphrase",
        ),
    )
    shadow_execution = PaperExecutionAdapter(ttl_seconds=20, taker_slippage_bps=20.0)
    live_risk = BasicRiskManager(settings=RiskSettings(), trading_settings=TradingSettings())
    shadow_risk = BasicRiskManager(settings=RiskSettings(), trading_settings=TradingSettings())
    live_recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "live.events.jsonl",
        metrics_path=tmp_path / "live.metrics.json",
    )
    shadow_recorder = PaperRuntimeRecorder(
        event_path=tmp_path / "shadow.events.jsonl",
        metrics_path=tmp_path / "shadow.metrics.json",
    )
    shadow = ShadowPaperCoordinator(
        execution=shadow_execution,
        risk_manager=shadow_risk,
        recorder=shadow_recorder,
    )
    execution = SynchronizedLiveExecutionAdapter(
        live_execution=live_execution,
        shadow_coordinator=shadow,
    )
    router = EventRouter(
        market_data=InMemoryMarketDataAdapter([snapshot]),
        strategies=[SubmitOnceStrategy()],
        risk_manager=live_risk,
        execution=execution,
        recorder=live_recorder,
        default_order_size=1.1,
    )
    runner = LiveSessionRunner(
        router=router,
        execution=execution,
        risk_manager=live_risk,
        recorder=live_recorder,
        market_snapshots=(snapshot,),
        market_snapshot_stream=_market_stream(snapshot),
        user_event_stream=_empty_user_stream(),
        shadow_coordinator=shadow,
    )

    stats = asyncio.run(runner.run(max_market_snapshots=1, max_user_events=0))

    assert stats.market_snapshots_processed == 1
    assert live_recorder.metrics.orders_submitted == 1
    assert shadow_recorder.metrics.orders_submitted == 1

    live_events = [
        json.loads(line)
        for line in (tmp_path / "live.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    shadow_events = [
        json.loads(line)
        for line in (tmp_path / "shadow.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    live_submitted = next(event for event in live_events if event["event_type"] == "order.submitted")
    shadow_submitted = next(event for event in shadow_events if event["event_type"] == "order.submitted")

    assert live_submitted["payload"]["intent_id"] == "intent-00000001"
    assert shadow_submitted["payload"]["intent_id"] == "intent-00000001"
    assert shadow_submitted["payload"]["live_order_id"] == "live-1"
    assert shadow_submitted["payload"]["order_id"] == "paper-1"


def test_preflight_cancels_existing_open_orders_for_target_snapshots(tmp_path: Path) -> None:
    client = FakeLiveClient()
    client.open_orders = [
        {"id": "target-1", "market": "0xtarget-condition"},
        {"id": "other-1", "market": "0xother-condition"},
    ]
    live_execution = PolymarketLiveExecutionAdapter(
        client=client,
        ttl_seconds=20,
        post_only=False,
        build_order_args=lambda intent: {
            "token_id": intent.token_id,
            "price": intent.price,
            "size": intent.size,
            "side": "BUY",
        },
        resolve_order_type=lambda tif: tif,
        user_channel_auth=UserChannelAuth(
            api_key="key",
            secret="secret",
            passphrase="passphrase",
        ),
    )
    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "live.events.jsonl",
        metrics_path=tmp_path / "live.metrics.json",
    )
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.51,
        last_traded_price=0.495,
        metadata={"no_token_id": "no-token", "condition_id": "0xtarget-condition"},
    )

    asyncio.run(
        _preflight_cancel_sync_shadow_open_orders(
            execution=live_execution,
            snapshots=(snapshot,),
            recorder=recorder,
        )
    )

    assert client.cancelled_order_ids == ["target-1"]


def test_preflight_cancels_existing_open_orders_by_asset_id_match(tmp_path: Path) -> None:
    client = FakeLiveClient()
    client.open_orders = [
        {"id": "target-asset", "asset_id": "no-token"},
        {"id": "other-asset", "asset_id": "other-token"},
    ]
    live_execution = PolymarketLiveExecutionAdapter(
        client=client,
        ttl_seconds=20,
        post_only=False,
        build_order_args=lambda intent: {
            "token_id": intent.token_id,
            "price": intent.price,
            "size": intent.size,
            "side": "BUY",
        },
        resolve_order_type=lambda tif: tif,
        user_channel_auth=UserChannelAuth(
            api_key="key",
            secret="secret",
            passphrase="passphrase",
        ),
    )
    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "live2.events.jsonl",
        metrics_path=tmp_path / "live2.metrics.json",
    )
    snapshot = MarketSnapshot(
        market_id="m1",
        token_id="yes-token",
        slug="btc-above",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.49,
        best_ask_yes=0.5,
        best_bid_no=0.5,
        best_ask_no=0.51,
        last_traded_price=0.495,
        metadata={"no_token_id": "no-token", "condition_id": "0xtarget-condition"},
    )

    asyncio.run(
        _preflight_cancel_sync_shadow_open_orders(
            execution=live_execution,
            snapshots=(snapshot,),
            recorder=recorder,
        )
    )

    assert client.cancelled_order_ids == ["target-asset"]


def test_filter_snapshots_by_crypto_barrier_distance_excludes_far_short_horizon_barriers() -> None:
    near_snapshot = MarketSnapshot(
        market_id="btc-near",
        token_id="btc-near-yes",
        slug="bitcoin-above-68k-on-april-1",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=datetime(2026, 4, 1, 16, 0, tzinfo=UTC),
        metadata={
            "question": "Bitcoin above 68000 on April 1",
            "event_title": "Bitcoin above 68k on April 1",
            "no_token_id": "btc-near-no",
        },
    )
    far_snapshot = MarketSnapshot(
        market_id="btc-far",
        token_id="btc-far-yes",
        slug="will-bitcoin-hit-150k-by-march-31-2026",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=datetime(2026, 3, 31, 16, 0, tzinfo=UTC),
        metadata={
            "question": "Will Bitcoin hit 150000 by March 31, 2026?",
            "event_title": "Bitcoin 150k by March 31",
            "no_token_id": "btc-far-no",
        },
    )

    selected = _filter_snapshots_by_crypto_barrier_distance(
        snapshots=(near_snapshot, far_snapshot),
        underlying_states={"BTC": SimpleNamespace(spot_price=79_000.0)},
        min_distance_ratio=None,
        max_distance_ratio=0.35,
    )

    assert [snapshot.market_id for snapshot in selected] == ["btc-near"]


def test_merge_snapshots_by_market_id_keeps_seed_markets_and_prefers_latest_duplicates() -> None:
    seed_snapshot = MarketSnapshot(
        market_id="m-seed",
        token_id="seed-yes",
        slug="btc-seed",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.4,
        best_ask_yes=0.41,
        best_bid_no=0.59,
        best_ask_no=0.6,
        last_traded_price=0.405,
        metadata={"no_token_id": "seed-no"},
    )
    duplicate_old = MarketSnapshot(
        market_id="m-dup",
        token_id="dup-old-yes",
        slug="btc-dup-old",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.3,
        best_ask_yes=0.31,
        best_bid_no=0.69,
        best_ask_no=0.7,
        last_traded_price=0.305,
        metadata={"no_token_id": "dup-old-no"},
    )
    duplicate_new = MarketSnapshot(
        market_id="m-dup",
        token_id="dup-new-yes",
        slug="btc-dup-new",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 5, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.32,
        best_ask_yes=0.33,
        best_bid_no=0.67,
        best_ask_no=0.68,
        last_traded_price=0.325,
        metadata={"no_token_id": "dup-new-no"},
    )

    merged = _merge_snapshots_by_market_id((seed_snapshot, duplicate_old), (duplicate_new,))

    assert {snapshot.market_id for snapshot in merged} == {"m-seed", "m-dup"}
    merged_by_market = {snapshot.market_id: snapshot for snapshot in merged}
    assert merged_by_market["m-seed"].token_id == "seed-yes"
    assert merged_by_market["m-dup"].token_id == "dup-new-yes"


def test_cleanup_position_candidates_falls_back_to_runtime_positions() -> None:
    runtime_position = PositionState(
        market_id="m-runtime",
        token_id="runtime-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.04,
        shares=14.0,
        average_entry_price=0.36,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )

    merged = _cleanup_position_candidates(
        execution_positions=(),
        runtime_open_positions=(runtime_position,),
    )

    assert merged == (runtime_position,)


def test_cleanup_position_candidates_prefers_execution_positions_over_runtime_duplicates() -> None:
    execution_position = SimpleNamespace(
        market_id="m1",
        token_id="no-token",
        shares=12.5,
    )
    runtime_position = PositionState(
        market_id="m1",
        token_id="no-token",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=4.5,
        shares=10.0,
        average_entry_price=0.45,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )

    merged = _cleanup_position_candidates(
        execution_positions=(execution_position,),
        runtime_open_positions=(runtime_position,),
    )

    assert merged == (execution_position,)


def test_cleanup_position_shares_derives_from_notional_when_runtime_state_has_no_shares() -> None:
    runtime_position = PositionState(
        market_id="m-runtime",
        token_id="runtime-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.04,
        shares=None,
        average_entry_price=0.36,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )

    assert _cleanup_position_shares(runtime_position) == 14.0


def test_is_runtime_position_dust_flags_tiny_residual_position() -> None:
    position = PositionState(
        market_id="m-runtime",
        token_id="runtime-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=SYNC_SHADOW_DUST_NOTIONAL / 2,
        shares=SYNC_SHADOW_DUST_SHARES / 2,
        average_entry_price=0.45,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )

    assert _is_runtime_position_dust(position) is True


def test_filter_cleanup_runtime_positions_excludes_tiny_dust_positions() -> None:
    dust_position = PositionState(
        market_id="m-dust",
        token_id="dust-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=SYNC_SHADOW_DUST_NOTIONAL / 2,
        shares=SYNC_SHADOW_DUST_SHARES / 2,
        average_entry_price=0.45,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )
    normal_position = PositionState(
        market_id="m-normal",
        token_id="normal-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.5,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )

    filtered = _filter_cleanup_runtime_positions((dust_position, normal_position))

    assert filtered == (normal_position,)


def test_prune_runtime_dust_positions_clears_only_dust_from_runtime_state(tmp_path: Path) -> None:
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    dust_position = PositionState(
        market_id="m-dust",
        token_id="dust-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=SYNC_SHADOW_DUST_NOTIONAL / 2,
        shares=SYNC_SHADOW_DUST_SHARES / 2,
        average_entry_price=0.45,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )
    normal_position = PositionState(
        market_id="m-normal",
        token_id="normal-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.5,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )
    asyncio.run(risk_manager.sync_open_positions((dust_position, normal_position)))
    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "dust.events.jsonl",
        metrics_path=tmp_path / "dust.metrics.json",
    )

    asyncio.run(_prune_runtime_dust_positions(risk_manager=risk_manager, recorder=recorder))

    assert tuple(risk_manager.state.open_positions) == ("m-normal",)
    events = [
        json.loads(line)
        for line in (tmp_path / "dust.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dust_event = next(event for event in events if event["event_type"] == "cleanup.dust_position_ignored")
    assert dust_event["payload"]["market_id"] == "m-dust"


def test_prune_runtime_dust_pending_orders_clears_local_dust_remainder(tmp_path: Path) -> None:
    risk_manager = BasicRiskManager(
        settings=RiskSettings(),
        trading_settings=TradingSettings(),
    )
    risk_manager.state.pending_orders["dust-order"] = SimpleNamespace(
        order_id="dust-order",
        market_id="m-dust",
        token_id="dust-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side="sell",
        limit_price=0.35,
        requested_shares=13.809,
        requested_notional=4.83315,
        matched_shares=13.8,
        matched_notional=4.83,
        created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 1, tzinfo=UTC),
        quote_ttl_seconds=5,
        signal_edge_bps=None,
        exposure_group_id="exp",
        thesis_group_id="thesis",
        underlying_group_id="btc",
        intent_id=None,
        time_in_force="IOC",
    )
    risk_manager.state.pending_orders["normal-order"] = SimpleNamespace(
        order_id="normal-order",
        market_id="m-normal",
        token_id="normal-no",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        side="sell",
        limit_price=0.35,
        requested_shares=10.0,
        requested_notional=3.5,
        matched_shares=2.0,
        matched_notional=0.7,
        created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 1, tzinfo=UTC),
        quote_ttl_seconds=5,
        signal_edge_bps=None,
        exposure_group_id="exp",
        thesis_group_id="thesis",
        underlying_group_id="btc",
        intent_id=None,
        time_in_force="IOC",
    )

    class FakeTracker:
        def __init__(self) -> None:
            self.canceled: list[str] = []

        def mark_canceled(self, order_id: str, at=None):
            del at
            self.canceled.append(order_id)
            return None

    class FakeExecution:
        def __init__(self) -> None:
            self.tracker = FakeTracker()

        async def fetch_open_orders(self):
            return []

    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "dust-orders.events.jsonl",
        metrics_path=tmp_path / "dust-orders.metrics.json",
    )

    asyncio.run(
        _prune_runtime_dust_pending_orders(
            execution=FakeExecution(),
            risk_manager=risk_manager,
            recorder=recorder,
        )
    )

    assert tuple(risk_manager.state.pending_orders) == ("normal-order",)
    events = [
        json.loads(line)
        for line in (tmp_path / "dust-orders.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dust_event = next(event for event in events if event["event_type"] == "cleanup.dust_order_ignored")
    assert dust_event["payload"]["order_id"] == "dust-order"


def test_cleanup_safe_position_shares_applies_small_buffer_and_rounds_down() -> None:
    assert _cleanup_safe_position_shares(35.0) == 34.825
    assert _cleanup_safe_position_shares(12.5) == 12.4375


def test_cleanup_size_from_balance_error_resizes_to_available_shares() -> None:
    resized = _cleanup_size_from_balance_error(
        reason="not enough balance / allowance: the balance is not enough -> balance: 10293310, order amount: 11940000",
        requested_shares=11.94,
    )

    assert resized == 10.2418


def test_cleanup_size_from_balance_error_ignores_dust_residual() -> None:
    resized = _cleanup_size_from_balance_error(
        reason="not enough balance / allowance: the balance is not enough -> balance: 55980, order amount: 13430000",
        requested_shares=13.4325,
    )

    assert resized is None


def test_load_required_cleanup_snapshots_returns_only_requested_market_ids() -> None:
    requested = MarketSnapshot(
        market_id="m-requested",
        token_id="requested-yes",
        slug="btc-requested",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        metadata={"no_token_id": "requested-no"},
    )
    other = MarketSnapshot(
        market_id="m-other",
        token_id="other-yes",
        slug="btc-other",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        metadata={"no_token_id": "other-no"},
    )

    class FakeGammaClient:
        async def fetch_active_binary_market_snapshots(self, *, page_size: int, max_pages: int, tag_id: int | None):
            del page_size, max_pages, tag_id
            return [requested, other]

    class FakeClobEnricher:
        def __init__(self) -> None:
            self.received: list[str] = []

        async def enrich_snapshots(self, snapshots):
            self.received = [snapshot.market_id for snapshot in snapshots]
            return list(snapshots)

    enricher = FakeClobEnricher()
    matched = asyncio.run(
        _load_required_cleanup_snapshots(
            gamma_client=FakeGammaClient(),
            clob_enricher=enricher,
            required_market_ids={"m-requested"},
            page_size=100,
            max_pages=1,
            tag_id=21,
        )
    )

    assert [snapshot.market_id for snapshot in matched] == ["m-requested"]
    assert enricher.received == ["m-requested"]


def test_refresh_cleanup_snapshots_only_reenriches_runtime_open_position_markets() -> None:
    cleanup_snapshot = MarketSnapshot(
        market_id="m-cleanup",
        token_id="cleanup-yes",
        slug="btc-cleanup",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.25,
        metadata={"no_token_id": "cleanup-no"},
    )
    untouched_snapshot = MarketSnapshot(
        market_id="m-untouched",
        token_id="untouched-yes",
        slug="btc-untouched",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.4,
        metadata={"no_token_id": "untouched-no"},
    )
    runtime_position = PositionState(
        market_id="m-cleanup",
        token_id="cleanup-yes",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        notional=5.0,
        shares=10.0,
        average_entry_price=0.5,
        opened_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
    )

    class FakeClobEnricher:
        def __init__(self) -> None:
            self.received: list[str] = []

        async def enrich_snapshots(self, snapshots):
            self.received = [snapshot.market_id for snapshot in snapshots]
            return [replace(snapshot, best_bid_yes=0.21) for snapshot in snapshots]

    enricher = FakeClobEnricher()
    refreshed = asyncio.run(
        _refresh_cleanup_snapshots(
            snapshots=(cleanup_snapshot, untouched_snapshot),
            clob_enricher=enricher,
            runtime_open_positions=(runtime_position,),
        )
    )

    refreshed_by_market = {snapshot.market_id: snapshot for snapshot in refreshed}
    assert enricher.received == ["m-cleanup"]
    assert refreshed_by_market["m-cleanup"].best_bid_yes == 0.21
    assert refreshed_by_market["m-untouched"].best_bid_yes == 0.4


def test_cleanup_exit_plan_uses_cumulative_bid_depth_for_full_flatten() -> None:
    snapshot = MarketSnapshot(
        market_id="m-cleanup",
        token_id="yes-token",
        slug="btc-cleanup",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.25,
        best_bid_yes_size=5.0,
        tick_size=0.01,
        yes_bid_levels=(
            OrderBookLevel(price=0.26, size=5.0),
            OrderBookLevel(price=0.25, size=5.0),
            OrderBookLevel(price=0.24, size=100.0),
        ),
        metadata={"no_token_id": "no-token"},
    )

    side, price, size = _cleanup_exit_plan(
        snapshot=snapshot,
        token_id="yes-token",
        desired_shares=62.5,
    )

    assert side == SignalSide.SELL_YES
    assert price == 0.23
    assert size == 62.5


def test_cleanup_exit_plan_falls_back_to_partial_size_when_visible_depth_is_insufficient() -> None:
    snapshot = MarketSnapshot(
        market_id="m-cleanup",
        token_id="yes-token",
        slug="btc-cleanup",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.25,
        best_bid_yes_size=5.0,
        tick_size=0.01,
        yes_bid_levels=(
            OrderBookLevel(price=0.26, size=5.0),
            OrderBookLevel(price=0.25, size=5.0),
        ),
        metadata={"no_token_id": "no-token"},
    )

    side, price, size = _cleanup_exit_plan(
        snapshot=snapshot,
        token_id="yes-token",
        desired_shares=62.5,
    )

    assert side == SignalSide.SELL_YES
    assert price == 0.24
    assert size == 10.0


def test_cleanup_sync_shadow_session_submits_short_ttl_ioc_cleanup_orders(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def _fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("pm_bot.runtime.sync_session.asyncio.sleep", _fast_sleep)

    snapshot = MarketSnapshot(
        market_id="m-cleanup",
        token_id="yes-token",
        slug="btc-cleanup",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.25,
        best_bid_yes_size=25.0,
        tick_size=0.01,
        yes_bid_levels=(OrderBookLevel(price=0.25, size=25.0),),
        metadata={"no_token_id": "no-token"},
    )

    position = SimpleNamespace(
        market_id="m-cleanup",
        token_id="yes-token",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        shares=10.0,
        average_entry_price=0.3,
        exposure_group_id="exp",
        thesis_group_id="thesis",
        underlying_group_id="btc",
    )

    class FakeLiveExecution:
        def __init__(self) -> None:
            self.position_ledger = SimpleNamespace(snapshot=lambda: (position,))
            self.tracker = SimpleNamespace(snapshot=lambda: ())

        async def fetch_open_orders(self):
            return []

    class FakeSyncExecution:
        def __init__(self) -> None:
            self.live_execution = FakeLiveExecution()
            self.intents: list[object] = []

        async def submit(self, intent):
            self.intents.append(intent)
            return "cleanup-order"

        async def cancel_order(self, order_id: str, *, now=None):
            del order_id, now
            return None

    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "cleanup.events.jsonl",
        metrics_path=tmp_path / "cleanup.metrics.json",
    )
    execution = FakeSyncExecution()

    asyncio.run(
        _cleanup_sync_shadow_session(
            execution=execution,
            snapshots=(snapshot,),
            recorder=recorder,
        )
    )

    assert execution.intents
    cleanup_intent = execution.intents[0]
    assert cleanup_intent.time_in_force == "IOC"
    assert cleanup_intent.quote_ttl_seconds == 5
    assert cleanup_intent.size == 9.95


def test_cleanup_sync_shadow_session_records_submit_failures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def _fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("pm_bot.runtime.sync_session.asyncio.sleep", _fast_sleep)

    snapshot = MarketSnapshot(
        market_id="m-cleanup",
        token_id="yes-token",
        slug="btc-cleanup",
        category=Category.CRYPTO,
        timestamp=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        resolution_time=None,
        best_bid_yes=0.25,
        best_bid_yes_size=25.0,
        tick_size=0.01,
        yes_bid_levels=(OrderBookLevel(price=0.25, size=25.0),),
        metadata={"no_token_id": "no-token"},
    )

    position = SimpleNamespace(
        market_id="m-cleanup",
        token_id="yes-token",
        category=Category.CRYPTO,
        strategy_id="crypto.phase2",
        shares=10.0,
        average_entry_price=0.3,
        exposure_group_id="exp",
        thesis_group_id="thesis",
        underlying_group_id="btc",
    )

    class FakeLiveExecution:
        def __init__(self) -> None:
            self.position_ledger = SimpleNamespace(snapshot=lambda: (position,))
            self.tracker = SimpleNamespace(snapshot=lambda: ())

        async def fetch_open_orders(self):
            return []

    class FakeSyncExecution:
        def __init__(self) -> None:
            self.live_execution = FakeLiveExecution()

        async def submit(self, intent):
            del intent
            raise RuntimeError("cleanup submit failed")

        async def cancel_order(self, order_id: str, *, now=None):
            del order_id, now
            return None

    recorder = LiveRuntimeRecorder(
        event_path=tmp_path / "cleanup-fail.events.jsonl",
        metrics_path=tmp_path / "cleanup-fail.metrics.json",
    )

    asyncio.run(
        _cleanup_sync_shadow_session(
            execution=FakeSyncExecution(),
            snapshots=(snapshot,),
            recorder=recorder,
        )
    )

    events = [
        json.loads(line)
        for line in (tmp_path / "cleanup-fail.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cleanup_failure = next(event for event in events if event["event_type"] == "cleanup.order_submit_failed")
    assert cleanup_failure["payload"]["market_id"] == "m-cleanup"
    assert "cleanup submit failed" in cleanup_failure["payload"]["reason"]
