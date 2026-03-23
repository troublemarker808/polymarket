# V1 Product Rules

This document captures the operator rules agreed before real exchange integration.

## Primary Goal

- Allow losing days.
- Target positive weekly and monthly equity growth.
- Prefer survival and consistency over trade frequency.

## Real-Money Scope

- Real money starts with `crypto` only.
- `sports` and `weather` remain in paper mode until the crypto path is stable.
- Only trade mainstream, high-clarity markets in V1.

## Capital Rules

- Starting real-money equity: `100 USD`
- Default order notional: `5 USD`
- Max concurrent positions: `4`
- Max positions per market: `1`
- No averaging down or adding to an existing V1 position.
- No direct flip from `YES` to `NO`; the current position must be closed first.

## Daily Order Discipline

- Soft limit: `10` orders per day
- Hard limit: `15` orders per day
- If trading is active but expectancy is weak, reduce frequency before changing automation.

## Global Halt Rules

- Halt after `5` consecutive realized losing trades.
- Halt after `5%` daily drawdown, measured on total equity:
  realized PnL + unrealized PnL.
- Halt on stale or broken data.
- Halt requires manual operator resume.

## Recovery Rules

- The system never auto-resumes in V1.
- The operator must inspect the halt reason and explicitly resume the system.

## Promotion Rules

- Paper gate before real money:
  - `7` paper days
  - no serious risk-control failures
  - at least `30` complete samples
- Increase order notional from `5 USD` to `10 USD` only after total equity reaches `150 USD`.

## Operator Dashboard V1

The first dashboard must show:

- total equity
- today PnL
- current positions
- current runtime status
- halt reason / latest alert
