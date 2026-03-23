# Program Workflow

This file defines the V1 operational workflow before live exchange integration.

## 1. End-to-End Runtime Flow

```text
external data
    |
    v
Gamma discovery
    |
    v
CLOB enrichment
    |
    v
normalized market snapshot
    |
    v
orchestrator / event router
    |
    +--> strategy evaluation
    |        |
    |        v
    |    standardized signals
    |        |
    |        v
    +--> risk review
             |
             +--> reject -> recorder -> dashboard / alert
             |
             v
        order intent
             |
             v
        execution adapter
             |
             +--> live mode preflight
             |        |
             |        +--> geoblock check
             |        +--> credential check
             |        +--> region blocked? reject
             |
             +--> post order
             |        |
             |        v
            |    user channel / order lifecycle tracker
            |        |
            |        v
            |    local position ledger
            |        |
            |        v
            |    mark-to-market / unrealized pnl
            |        |
            |        v
            |    reconnect supervisor
            |        |
            |        +--> ws disconnect / stream error
            |        +--> recover open orders + trade history
            |        +--> rebuild local state
            |        +--> resubscribe market/user streams
             |
             v
    runtime state update / execution state
             |
             v
    recorder + dashboard + alerting
```

## 2. V1 Rollout Workflow

```text
research
  |
  v
paper
  |
  +--> sports (paper only)
  +--> weather (paper only)
  |
  v
crypto small-live
  |
  v
expand only after stability
```

## 3. Trading Decision Workflow

```text
snapshot arrives
  |
  v
strategy emits signal?
  | \
  |  \-- no --> wait for next snapshot
  |
  v
signal clears edge floor?
  | \
  |  \-- no --> reject + record
  |
  v
system halted?
  | \
  |  \-- yes --> reject + record
  |
  v
position/order limits breached?
  | \
  |  \-- yes --> reject + record
  |
  v
submit paper/live order
  |
  v
track order lifecycle
  |
  v
update runtime state
```

## 4. Halt / Resume State Machine

```text
          +---------------------------+
          |         RUNNING           |
          +---------------------------+
             |       |        |     |
             |       |        |     |
             |       |        |     +--> stale/broken data
             |       |        +--------> daily drawdown >= 5%
             |       +-----------------> 5 consecutive realized losses
             +-------------------------> manual halt / future operator halt
                                   |
                                   v
                     +---------------------------+
                     |          HALTED           |
                     +---------------------------+
                                   |
                                   +--> operator review
                                   |
                                   v
                     +---------------------------+
                     |      MANUAL RESUME        |
                     +---------------------------+
                                   |
                                   v
                     +---------------------------+
                     |         RUNNING           |
                     +---------------------------+
```

## 5. Operator Workflow

```text
start session
  |
  v
watch dashboard
  |
  +--> normal: status=running, orders and pnl visible
  |
  +--> reconnect: session reloads snapshots, trade history, and open orders
  |              |
  |              v
  |          dashboard stays in sync with recovered state
  |
  +--> halt: inspect halt reason / last alert
               |
               v
           investigate
               |
               +--> fix config / strategy / data issue
               |
               v
           manual resume
```

## 6. V1 Dashboard Contract

The first operator dashboard must show:

- total equity
- today PnL
- pending orders
- current positions
- current runtime status
- halt reason / latest alert

## 7. Out of Scope for This Phase

- real push-notification provider
- graphical frontend UI
- fill-to-position PnL accounting
- user-channel driven position close automation
- multi-category live deployment
