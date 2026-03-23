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
from typing import Any, Protocol

from pm_bot.core.settings import PolymarketSettings
from pm_bot.core.types import MarketSnapshot, OrderAction, OrderIntent, SignalSide
from pm_bot.execution.order_tracker import OrderLifecycleTracker
from pm_bot.execution.position_ledger import LivePosition, PositionLedger
from pm_bot.adapters.polymarket.geoblock_client import GeoblockStatus, fetch_geoblock_status_sync
from pm_bot.adapters.polymarket.user_ws_client import UserChannelAuth, UserOrderEvent, UserTradeEvent
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


@dataclass(slots=True, frozen=True)
class ResolvedPolymarketCredentials:
    private_key: str
    funder: str | None
    api_key: str | None
    api_secret: str | None
    api_passphrase: str | None

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


def resolve_polymarket_credentials(
    settings: PolymarketSettings,
    env: Mapping[str, str] | None = None,
) -> ResolvedPolymarketCredentials:
    """Resolve trading credentials from environment variables."""

    env_map = env or os.environ
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
    )


def describe_live_execution_configuration(
    settings: PolymarketSettings,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Summarize whether live execution is configured safely enough to enable."""

    env_map = env or os.environ
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
        build_order_args: Callable[[OrderIntent], object],
        resolve_order_type: Callable[[str], object],
        user_channel_auth: UserChannelAuth,
        parse_order_id: Callable[[object], str] = None,
        tracker: OrderLifecycleTracker | None = None,
        position_ledger: PositionLedger | None = None,
    ) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds
        self.post_only = post_only
        self.build_order_args = build_order_args
        self.resolve_order_type = resolve_order_type
        self.user_channel_auth = user_channel_auth
        self.parse_order_id = parse_order_id or _extract_order_id
        self.tracker = tracker or OrderLifecycleTracker()
        self.position_ledger = position_ledger or PositionLedger()

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

        if client_factory is None:
            creds = None
            user_channel_auth: UserChannelAuth | None = None
            if credentials.has_api_credentials:
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

            assert OrderArgs is not None
            assert OrderType is not None
            if user_channel_auth is None:
                raise ValueError("Unable to resolve user-channel credentials for live execution")

            def build_order_args(intent: OrderIntent) -> object:
                if intent.action != OrderAction.PLACE:
                    raise ValueError("Only PLACE intents are supported for live trading")
                if intent.price is None:
                    raise ValueError("Live order intents require a limit price")
                return OrderArgs(
                    token_id=intent.token_id,
                    price=float(intent.price),
                    size=float(intent.size),
                    side=_execution_side_for_signal(intent.side),
                )

            def resolve_order_type(time_in_force: str) -> object:
                normalized = time_in_force.upper()
                try:
                    return getattr(OrderType, normalized)
                except AttributeError as exc:
                    raise ValueError(f"Unsupported Polymarket time_in_force: {time_in_force}") from exc

            return cls(
                client=client,
                ttl_seconds=ttl_seconds,
                post_only=settings.post_only_live_orders,
                build_order_args=build_order_args,
                resolve_order_type=resolve_order_type,
                user_channel_auth=user_channel_auth,
            )

        client = client_factory(
            host=settings.api_url,
            chain_id=settings.chain_id,
            key=credentials.private_key,
            creds=None,
            signature_type=settings.signature_type,
            funder=credentials.funder,
        )
        user_channel_auth: UserChannelAuth | None = None
        if credentials.has_api_credentials:
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

        def build_order_args(intent: OrderIntent) -> object:
            return {
                "token_id": intent.token_id,
                "price": intent.price,
                "size": intent.size,
                "side": _execution_side_for_signal(intent.side),
            }

        def resolve_order_type(time_in_force: str) -> object:
            return time_in_force.upper()

        if user_channel_auth is None:
            raise ValueError("Unable to resolve user-channel credentials for live execution")

        return cls(
            client=client,
            ttl_seconds=ttl_seconds,
            post_only=settings.post_only_live_orders,
            build_order_args=build_order_args,
            resolve_order_type=resolve_order_type,
            user_channel_auth=user_channel_auth,
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

    async def cancel_stale(self) -> int:
        tracked_orders = self.tracker.snapshot()
        if not tracked_orders:
            return 0

        now = datetime.now(tz=timezone.utc)
        stale_order_ids = self.tracker.stale_order_ids(now=now, ttl_seconds=self.ttl_seconds)
        cancelled = 0
        for order_id in stale_order_ids:
            try:
                await asyncio.to_thread(self.client.cancel, order_id)
            except Exception:
                continue
            self.tracker.mark_canceled(order_id, at=now)
            cancelled += 1
        return cancelled

    async def fetch_open_orders(self) -> list[dict[str, object]]:
        response = await asyncio.to_thread(self.client.get_orders)
        return [item for item in response if isinstance(item, dict)]

    async def fetch_trade_history(self) -> list[dict[str, object]]:
        response = await asyncio.to_thread(self.client.get_trades)
        return [item for item in response if isinstance(item, dict)]

    def apply_user_order_event(self, event: UserOrderEvent) -> object | None:
        return self.tracker.apply_order_event(event)

    def apply_user_trade_event(self, event: UserTradeEvent) -> tuple[LivePosition, ...]:
        updated_positions: list[LivePosition] = []
        for tracked_order in self.tracker.apply_trade_event(event):
            position = self.position_ledger.apply_tracked_order(tracked_order)
            if position is not None:
                updated_positions.append(position)
        return tuple(updated_positions)

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
