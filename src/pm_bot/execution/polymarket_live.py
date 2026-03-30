"""Safe-by-default Polymarket live execution adapter.

The adapter is intentionally isolated from strategies and defaults to disabled
unless the operator explicitly enables live orders and supplies credentials.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.util import find_spec
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from pm_bot.core.settings import PolymarketSettings
from pm_bot.core.types import Category, MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.order_tracker import OrderLifecycleTracker, TrackedOrder
from pm_bot.execution.position_ledger import LivePosition, PositionLedger
from pm_bot.adapters.polymarket.geoblock_client import GeoblockStatus, fetch_geoblock_status_sync
from pm_bot.adapters.polymarket.user_ws_client import (
    UserChannelAuth,
    UserMakerOrder,
    UserOrderEvent,
    UserTradeEvent,
)
from pm_bot.runtime.state import ClosedTrade


class SyncTradingClient(Protocol):
    """Subset of sync client methods required by the live adapter."""

    def create_order(self, order_args: object, options: object | None = None) -> object:
        ...

    def post_order(self, order: object, orderType: object, post_only: bool = False) -> object:
        ...

    def cancel(self, order_id: str) -> object:
        ...

    def get_orders(self, params: object | None = None, next_cursor: str = "MA==") -> object:
        ...

    def get_trades(self, params: object | None = None, next_cursor: str = "MA==") -> object:
        ...

    def create_or_derive_api_creds(self, nonce: int | None = None) -> object:
        ...

    def set_api_creds(self, creds: object) -> None:
        ...

    def get_balance_allowance(self, params: object) -> object:
        ...


@dataclass(slots=True, frozen=True)
class ResolvedPolymarketCredentials:
    private_key: str
    funder: str | None
    api_key: str | None
    api_secret: str | None
    api_passphrase: str | None
    account_addresses: frozenset[str]

    @property
    def has_api_credentials(self) -> bool:
        return all(
            value
            for value in (
                self.api_key,
                self.api_secret,
                self.api_passphrase,
            )
        )


def live_dependency_available() -> bool:
    """Return whether the optional py-clob-client package is importable."""

    return find_spec("py_clob_client.client") is not None and find_spec(
        "py_clob_client.clob_types"
    ) is not None


_PRICE_CENT = Decimal("0.01")
_SIZE_STEP = Decimal("0.0001")


def _round_size_for_live(intent: OrderIntent) -> float:
    """Normalize live sizes to Polymarket's buy-side amount precision rules."""

    size = Decimal(str(intent.size))
    price = Decimal(str(intent.price or 0.0))
    if price <= 0:
        return float(size.quantize(_SIZE_STEP, rounding=ROUND_HALF_UP))

    if intent.side in (SignalSide.BUY_YES, SignalSide.BUY_NO):
        target_notional = Decimal(str(intent.notional or 0.0))
        target_cents = max(
            int((target_notional.quantize(_PRICE_CENT, rounding=ROUND_HALF_UP) * 100)),
            1,
        )
        price_cents = int((price.quantize(_PRICE_CENT, rounding=ROUND_HALF_UP) * 100))
        for maker_cents in range(target_cents, target_cents + max(price_cents * 4, 500)):
            scaled = maker_cents * 10_000
            if scaled % price_cents != 0:
                continue
            normalized_size = Decimal(scaled // price_cents) / Decimal(10_000)
            return float(normalized_size.quantize(_SIZE_STEP, rounding=ROUND_HALF_UP))

    return float(size.quantize(_SIZE_STEP, rounding=ROUND_HALF_UP))


def _trade_event_fingerprint(event: UserTradeEvent) -> str:
    return "|".join(
        [
            str(event.trader_side or "").strip().upper(),
            str(event.taker_order_id or "").strip(),
            str(event.asset_id or "").strip(),
            str(event.side or "").strip().upper(),
            _canonical_trade_number(event.price),
            _canonical_trade_number(event.size),
        ]
    )


def canonical_trade_fingerprint(
    *,
    trader_side: object,
    taker_order_id: object,
    asset_id: object,
    side: object,
    price: object,
    size: object,
) -> str:
    return "|".join(
        [
            str(trader_side or "").strip().upper(),
            str(taker_order_id or "").strip(),
            str(asset_id or "").strip(),
            str(side or "").strip().upper(),
            _canonical_trade_number(price),
            _canonical_trade_number(size),
        ]
    )


def _canonical_trade_number(value: object) -> str:
    try:
        normalized = Decimal(str(value or "0"))
    except Exception:
        return str(value or "").strip()
    return format(normalized.quantize(Decimal("0.000001")), "f")


def resolve_polymarket_credentials(
    settings: PolymarketSettings,
    env: Mapping[str, str] | None = None,
) -> ResolvedPolymarketCredentials:
    """Resolve trading credentials from environment variables."""

    env_map = os.environ if env is None else env
    private_key = env_map.get(settings.private_key_env, "").strip()
    if not private_key:
        raise ValueError(f"Missing required env var: {settings.private_key_env}")

    api_key = env_map.get(settings.api_key_env, "").strip() or None
    api_secret = env_map.get(settings.api_secret_env, "").strip() or None
    api_passphrase = env_map.get(settings.api_passphrase_env, "").strip() or None
    funder = env_map.get(settings.funder_env, "").strip() or None

    provided_api_values = [api_key, api_secret, api_passphrase]
    if any(provided_api_values) and not all(provided_api_values):
        raise ValueError(
            "Polymarket API credentials must include api key, secret, and passphrase together"
        )

    return ResolvedPolymarketCredentials(
        private_key=private_key,
        funder=funder,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
        account_addresses=_resolve_account_addresses(
            private_key=private_key,
            funder=funder,
        ),
    )


def describe_live_execution_configuration(
    settings: PolymarketSettings,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Summarize whether live execution is configured safely enough to enable."""

    env_map = os.environ if env is None else env
    dependency_ok = live_dependency_available()
    private_key_present = bool(env_map.get(settings.private_key_env, "").strip())
    api_values = [
        env_map.get(settings.api_key_env, "").strip(),
        env_map.get(settings.api_secret_env, "").strip(),
        env_map.get(settings.api_passphrase_env, "").strip(),
    ]
    api_credentials_present = all(api_values)
    partial_api_credentials = any(api_values) and not api_credentials_present

    issues: list[str] = []
    if not settings.allow_live_orders:
        issues.append("allow_live_orders is false")
    if not dependency_ok:
        issues.append("py-clob-client is not installed")
    if not private_key_present:
        issues.append(f"missing {settings.private_key_env}")
    if partial_api_credentials:
        issues.append("partial api credentials present")
    if not api_credentials_present and not settings.derive_api_creds_if_missing:
        issues.append("api credentials missing and derivation disabled")

    return {
        "allow_live_orders": settings.allow_live_orders,
        "dependency_available": dependency_ok,
        "private_key_present": private_key_present,
        "api_credentials_present": api_credentials_present,
        "derive_api_creds_if_missing": settings.derive_api_creds_if_missing,
        "post_only_live_orders": settings.post_only_live_orders,
        "ready": not issues,
        "issues": tuple(issues),
    }


class PolymarketLiveExecutionAdapter:
    """Live execution adapter backed by the official py-clob-client package."""

    def __init__(
        self,
        *,
        client: SyncTradingClient,
        ttl_seconds: int,
        post_only: bool,
        signature_type: int = 0,
        build_order_args: Callable[[OrderIntent], object],
        resolve_order_type: Callable[[str], object],
        user_channel_auth: UserChannelAuth,
        parse_order_id: Callable[[object], str] | None = None,
        tracker: OrderLifecycleTracker | None = None,
        position_ledger: PositionLedger | None = None,
        account_addresses: frozenset[str] = frozenset(),
    ) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds
        self.post_only = post_only
        self.signature_type = signature_type
        self.build_order_args = build_order_args
        self.resolve_order_type = resolve_order_type
        self.user_channel_auth = user_channel_auth
        self.parse_order_id = _extract_order_id if parse_order_id is None else parse_order_id
        self.tracker = tracker or OrderLifecycleTracker()
        self.position_ledger = position_ledger or PositionLedger(
            allow_synthetic_complement_on_sell=False
        )
        self.processed_trade_ids: set[str] = set()
        self.account_addresses = frozenset(
            normalized
            for value in account_addresses
            if (normalized := _normalize_address(value))
        )

    @classmethod
    def from_settings(
        cls,
        *,
        settings: PolymarketSettings,
        ttl_seconds: int,
        env: Mapping[str, str] | None = None,
        client_factory: Callable[..., SyncTradingClient] | None = None,
        geoblock_status: GeoblockStatus | None = None,
    ) -> "PolymarketLiveExecutionAdapter":
        """Build a live adapter from config and env vars."""

        if not settings.allow_live_orders:
            raise ValueError("Live order submission is disabled in config")
        if not live_dependency_available() and client_factory is None:
            raise RuntimeError(
                "py-clob-client is not installed; install it before enabling live execution"
            )

        credentials = resolve_polymarket_credentials(settings=settings, env=env)
        if geoblock_status is None and client_factory is None:
            geoblock_status = fetch_geoblock_status_sync()
        if geoblock_status is not None and geoblock_status.blocked:
            raise ValueError(
                "Live trading blocked for current region "
                f"({geoblock_status.country}/{geoblock_status.region})"
            )

        if client_factory is None:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
        else:
            ClobClient = None
            ApiCreds = None
            OrderArgs = None
            OrderType = None

        user_channel_auth: UserChannelAuth | None = None
        if client_factory is None:
            creds = None
            if credentials.has_api_credentials:
                assert credentials.api_key is not None
                assert credentials.api_secret is not None
                assert credentials.api_passphrase is not None
                assert ApiCreds is not None
                creds = ApiCreds(
                    api_key=credentials.api_key,
                    api_secret=credentials.api_secret,
                    api_passphrase=credentials.api_passphrase,
                )
                user_channel_auth = UserChannelAuth(
                    api_key=credentials.api_key,
                    secret=credentials.api_secret,
                    passphrase=credentials.api_passphrase,
                )
            client = ClobClient(
                host=settings.api_url,
                chain_id=settings.chain_id,
                key=credentials.private_key,
                creds=creds,
                signature_type=settings.signature_type,
                funder=credentials.funder,
            )
            if creds is None:
                if not settings.derive_api_creds_if_missing:
                    raise ValueError("Live execution requires API credentials or credential derivation")
                derived_creds = client.create_or_derive_api_creds()
                client.set_api_creds(derived_creds)
                user_channel_auth = _coerce_user_channel_auth(derived_creds)
            resolved_signature_type = _resolve_signature_type_with_allowance_probe(
                client=client,
                preferred_signature_type=settings.signature_type,
            )
            builder = getattr(client, "builder", None)
            if builder is not None:
                setattr(builder, "sig_type", resolved_signature_type)

            assert OrderArgs is not None
            assert OrderType is not None
            if user_channel_auth is None:
                raise ValueError("Unable to resolve user-channel credentials for live execution")

            def live_build_order_args(intent: OrderIntent) -> object:
                if intent.action != OrderAction.PLACE:
                    raise ValueError("Only PLACE intents are supported for live trading")
                if intent.price is None:
                    raise ValueError("Live order intents require a limit price")
                return OrderArgs(
                    token_id=intent.token_id,
                    price=float(intent.price),
                    size=_round_size_for_live(intent),
                    side=_execution_side_for_signal(intent.side),
                )

            def live_resolve_order_type(time_in_force: str) -> object:
                normalized = time_in_force.upper()
                if normalized == "IOC":
                    normalized = "FOK"
                try:
                    return getattr(OrderType, normalized)
                except AttributeError as exc:
                    raise ValueError(f"Unsupported Polymarket time_in_force: {time_in_force}") from exc

            return cls(
                client=client,
                ttl_seconds=ttl_seconds,
                post_only=settings.post_only_live_orders,
                signature_type=resolved_signature_type,
                build_order_args=live_build_order_args,
                resolve_order_type=live_resolve_order_type,
                user_channel_auth=user_channel_auth,
                account_addresses=credentials.account_addresses,
            )

        client = client_factory(
            host=settings.api_url,
            chain_id=settings.chain_id,
            key=credentials.private_key,
            creds=None,
            signature_type=settings.signature_type,
            funder=credentials.funder,
        )
        if credentials.has_api_credentials:
            assert credentials.api_key is not None
            assert credentials.api_secret is not None
            assert credentials.api_passphrase is not None
            client.set_api_creds(
                {
                    "api_key": credentials.api_key,
                    "api_secret": credentials.api_secret,
                    "api_passphrase": credentials.api_passphrase,
                }
            )
            user_channel_auth = UserChannelAuth(
                api_key=credentials.api_key,
                secret=credentials.api_secret,
                passphrase=credentials.api_passphrase,
            )
        elif not settings.derive_api_creds_if_missing:
            raise ValueError("Live execution requires API credentials or credential derivation")
        elif settings.derive_api_creds_if_missing:
            derived_creds = client.create_or_derive_api_creds()
            client.set_api_creds(derived_creds)
            user_channel_auth = _coerce_user_channel_auth(derived_creds)

        def factory_build_order_args(intent: OrderIntent) -> object:
            return {
                "token_id": intent.token_id,
                "price": intent.price,
                "size": _round_size_for_live(intent),
                "side": _execution_side_for_signal(intent.side),
            }

        def factory_resolve_order_type(time_in_force: str) -> object:
            normalized = time_in_force.upper()
            if normalized == "IOC":
                normalized = "FOK"
            return normalized

        if user_channel_auth is None:
            raise ValueError("Unable to resolve user-channel credentials for live execution")

        resolved_signature_type = _resolve_signature_type_with_allowance_probe(
            client=client,
            preferred_signature_type=settings.signature_type,
        )
        builder = getattr(client, "builder", None)
        if builder is not None:
            setattr(builder, "sig_type", resolved_signature_type)

        return cls(
            client=client,
            ttl_seconds=ttl_seconds,
            post_only=settings.post_only_live_orders,
            signature_type=resolved_signature_type,
            build_order_args=factory_build_order_args,
            resolve_order_type=factory_resolve_order_type,
            user_channel_auth=user_channel_auth,
            account_addresses=credentials.account_addresses,
        )

    async def submit(self, intent: OrderIntent) -> str:
        order_args = self.build_order_args(intent)
        order_type = self.resolve_order_type(intent.time_in_force)
        response = await asyncio.to_thread(
            self._submit_sync,
            order_args,
            order_type,
        )
        order_id = self.parse_order_id(response)
        self.tracker.register_submission(order_id=order_id, intent=intent)
        return order_id

    async def cancel_order(
        self,
        order_id: str,
        *,
        now: datetime | None = None,
    ) -> TrackedOrder | None:
        try:
            await asyncio.to_thread(self.client.cancel, order_id)
        except Exception:
            return None
        return self.tracker.mark_canceled(order_id, at=now or datetime.now(tz=timezone.utc))

    async def cancel_stale(self) -> int:
        return len(await self.cancel_stale_orders())

    async def cancel_stale_orders(self) -> tuple[TrackedOrder, ...]:
        tracked_orders = self.tracker.snapshot()
        if not tracked_orders:
            return ()

        now = datetime.now(tz=timezone.utc)
        stale_order_ids = self.tracker.stale_order_ids(now=now, ttl_seconds=self.ttl_seconds)
        cancelled: list[TrackedOrder] = []
        for order_id in stale_order_ids:
            try:
                await asyncio.to_thread(self.client.cancel, order_id)
            except Exception:
                continue
            tracked = self.tracker.mark_canceled(order_id, at=now)
            if tracked is not None:
                cancelled.append(tracked)
        return tuple(cancelled)

    async def fetch_open_orders(self) -> list[dict[str, object]]:
        response = await asyncio.to_thread(self.client.get_orders)
        records = response if isinstance(response, (list, tuple)) else ()
        return [item for item in records if isinstance(item, dict)]

    async def fetch_trade_history(self) -> list[dict[str, object]]:
        response = await asyncio.to_thread(self.client.get_trades)
        records = response if isinstance(response, (list, tuple)) else ()
        return [item for item in records if isinstance(item, dict)]

    def apply_user_order_event(self, event: UserOrderEvent) -> TrackedOrder | None:
        return self.tracker.apply_order_event(event)

    def apply_user_trade_event(self, event: UserTradeEvent) -> tuple[LivePosition, ...]:
        trade_id = str(event.id or "").strip()
        trade_fingerprint = _trade_event_fingerprint(event)
        if (trade_id and trade_id in self.processed_trade_ids) or (
            trade_fingerprint and trade_fingerprint in self.processed_trade_ids
        ):
            return ()

        updated_positions: list[LivePosition] = []
        trader_side = str(event.trader_side or "").strip().upper()

        if trader_side != "MAKER" and event.taker_order_id:
            existing = self.tracker.get(event.taker_order_id)
            tracked_order = self.tracker.apply_fill(
                order_id=event.taker_order_id,
                market_id=event.market,
                token_id=event.asset_id,
                category=existing.category if existing is not None else Category.CRYPTO,
                strategy_id=existing.strategy_id if existing is not None else "recovered.live",
                trade_side=event.side,
                requested_shares=existing.requested_shares if existing is not None else event.size,
                limit_price=existing.limit_price if existing is not None else event.price,
                fill_shares=event.size,
                fill_price=event.price,
                fee_rate_bps=event.fee_rate_bps,
                event_time=event.timestamp or event.last_update,
                last_event="trade:taker",
            )
            position = self.position_ledger.apply_tracked_order(tracked_order)
            if position is not None:
                updated_positions.append(position)

        if trader_side == "MAKER":
            local_maker_orders = self._select_local_maker_orders(event.maker_orders)
            for maker_order in local_maker_orders:
                existing = self.tracker.get(maker_order.order_id)
                tracked_order = self.tracker.apply_fill(
                    order_id=maker_order.order_id,
                    market_id=event.market,
                    token_id=maker_order.asset_id,
                    category=existing.category if existing is not None else Category.CRYPTO,
                    strategy_id=existing.strategy_id if existing is not None else "recovered.live",
                    trade_side=maker_order.side,
                    requested_shares=(
                        existing.requested_shares if existing is not None else maker_order.matched_amount
                    ),
                    limit_price=existing.limit_price if existing is not None else maker_order.price,
                    fill_shares=maker_order.matched_amount,
                    fill_price=maker_order.price,
                    fee_rate_bps=maker_order.fee_rate_bps,
                    event_time=event.timestamp or event.last_update,
                    last_event="trade:maker",
                )
                position = self.position_ledger.apply_tracked_order(tracked_order)
                if position is not None:
                    updated_positions.append(position)
        if trade_id:
            self.processed_trade_ids.add(trade_id)
        if trade_fingerprint:
            self.processed_trade_ids.add(trade_fingerprint)
        return tuple(updated_positions)

    def tracked_order_ids_for_trade_event(
        self,
        event: UserTradeEvent,
    ) -> tuple[tuple[str, str], ...]:
        tracked_orders: list[tuple[str, str]] = []
        trader_side = str(event.trader_side or "").strip().upper()
        if trader_side != "MAKER" and event.taker_order_id:
            tracked_orders.append((event.taker_order_id, "taker"))
        if trader_side == "MAKER":
            tracked_orders.extend(
                (maker_order.order_id, "maker")
                for maker_order in self.local_maker_orders_for_trade_event(event)
            )
        return tuple(tracked_orders)

    def local_maker_orders_for_trade_event(
        self,
        event: UserTradeEvent,
    ) -> tuple[UserMakerOrder, ...]:
        return self._select_local_maker_orders(event.maker_orders)

    def matches_account_address(self, value: object) -> bool:
        normalized = _normalize_address(value)
        return bool(normalized) and normalized in self.account_addresses

    def has_processed_trade_id(self, trade_id: str) -> bool:
        normalized = str(trade_id).strip()
        return bool(normalized) and normalized in self.processed_trade_ids

    def mark_processed_trade_id(self, trade_id: str) -> None:
        normalized = str(trade_id).strip()
        if normalized:
            self.processed_trade_ids.add(normalized)

    def restore_processed_trade_ids(self, trade_ids: tuple[str, ...] | list[str]) -> None:
        for trade_id in trade_ids:
            normalized = str(trade_id).strip()
            if normalized:
                self.processed_trade_ids.add(normalized)

    def _select_local_maker_orders(
        self,
        maker_orders: tuple["UserMakerOrder", ...],
    ) -> tuple["UserMakerOrder", ...]:
        if not maker_orders:
            return ()
        if self.account_addresses:
            return tuple(
                maker_order
                for maker_order in maker_orders
                if self.matches_account_address(maker_order.maker_address)
            )
        if len(maker_orders) == 1:
            return maker_orders
        return ()

    def mark_positions_to_market(
        self,
        snapshots: list[MarketSnapshot] | tuple[MarketSnapshot, ...],
    ) -> tuple[LivePosition, ...]:
        return self.position_ledger.mark_to_market(snapshots)

    def total_unrealized_pnl(self) -> float:
        return self.position_ledger.total_unrealized_pnl()

    def drain_closed_trades(self) -> tuple[ClosedTrade, ...]:
        return self.position_ledger.drain_closed_trades()

    def _submit_sync(self, order_args: object, order_type: object) -> object:
        order = self.client.create_order(order_args)
        return self.client.post_order(order, orderType=order_type, post_only=self.post_only)


def _resolve_signature_type_with_allowance_probe(
    *,
    client: SyncTradingClient,
    preferred_signature_type: int,
) -> int:
    balance_reader = getattr(client, "get_balance_allowance", None)
    if not callable(balance_reader):
        return preferred_signature_type

    preferred_score = _signature_type_probe_score(
        _probe_balance_allowance(
            client=client,
            signature_type=preferred_signature_type,
        )
    )
    resolved_signature_type = preferred_signature_type
    best_score = preferred_score
    for candidate in (0, 1, 2):
        if candidate == preferred_signature_type:
            continue
        score = _signature_type_probe_score(
            _probe_balance_allowance(
                client=client,
                signature_type=candidate,
            )
        )
        if score > best_score:
            best_score = score
            resolved_signature_type = candidate
    return resolved_signature_type


def _probe_balance_allowance(
    *,
    client: SyncTradingClient,
    signature_type: int,
) -> Mapping[str, object] | None:
    try:
        from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
    except Exception:
        return None

    try:
        response = client.get_balance_allowance(
            BalanceAllowanceParams(
                asset_type=AssetType.COLLATERAL,
                signature_type=signature_type,
            )
        )
    except Exception:
        return None
    return response if isinstance(response, Mapping) else None


def _signature_type_probe_score(response: Mapping[str, object] | None) -> int:
    if response is None:
        return -1

    balance = int(str(response.get("balance") or "0"))
    allowances = response.get("allowances")
    max_allowance = 0
    if isinstance(allowances, Mapping):
        for value in allowances.values():
            try:
                max_allowance = max(max_allowance, int(str(value)))
            except ValueError:
                continue
    score = 0
    if balance > 0:
        score += 1
    if max_allowance > 0:
        score += 2
    return score


def _extract_order_id(response: object) -> str:
    if isinstance(response, str) and response:
        return response

    if isinstance(response, Mapping):
        for key in ("orderID", "orderId", "id"):
            value = response.get(key)
            if value:
                return str(value)

        nested = response.get("data")
        if isinstance(nested, Mapping):
            for key in ("orderID", "orderId", "id"):
                value = nested.get(key)
                if value:
                    return str(value)

    raise ValueError("Could not extract order id from live execution response")


def _coerce_user_channel_auth(raw_creds: object) -> UserChannelAuth:
    if isinstance(raw_creds, UserChannelAuth):
        return raw_creds

    if isinstance(raw_creds, Mapping):
        api_key = raw_creds.get("api_key") or raw_creds.get("apiKey")
        secret = raw_creds.get("api_secret") or raw_creds.get("secret")
        passphrase = raw_creds.get("api_passphrase") or raw_creds.get("passphrase")
        if api_key and secret and passphrase:
            return UserChannelAuth(
                api_key=str(api_key),
                secret=str(secret),
                passphrase=str(passphrase),
            )

    api_key = getattr(raw_creds, "api_key", None) or getattr(raw_creds, "apiKey", None)
    secret = getattr(raw_creds, "api_secret", None) or getattr(raw_creds, "secret", None)
    passphrase = getattr(raw_creds, "api_passphrase", None) or getattr(raw_creds, "passphrase", None)
    if api_key and secret and passphrase:
        return UserChannelAuth(
            api_key=str(api_key),
            secret=str(secret),
            passphrase=str(passphrase),
        )

    raise ValueError("Could not resolve user-channel auth from API credentials")


def _execution_side_for_signal(side: SignalSide) -> str:
    if side in {SignalSide.BUY_YES, SignalSide.BUY_NO}:
        return "BUY"
    if side in {SignalSide.SELL_YES, SignalSide.SELL_NO}:
        return "SELL"
    raise ValueError(f"Unsupported live execution side: {side.value}")


def _normalize_address(value: object) -> str:
    return str(value or "").strip().lower()


def _resolve_account_addresses(
    *,
    private_key: str,
    funder: str | None,
) -> frozenset[str]:
    addresses: set[str] = set()

    normalized_funder = _normalize_address(funder)
    if normalized_funder:
        addresses.add(normalized_funder)

    try:
        from eth_account import Account

        signer_address = _normalize_address(Account.from_key(private_key).address)
        if signer_address:
            addresses.add(signer_address)
    except Exception:
        pass

    return frozenset(addresses)
