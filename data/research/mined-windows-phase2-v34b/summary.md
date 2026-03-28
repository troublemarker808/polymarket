# Window Mining Report

- generated_at: 2026-03-28T10:35:03.927155+00:00
- snapshot_path: data\runtime\phase2-paper-snapshots.long.v34.20260328.jsonl
- event_path: data\runtime\phase2-paper-events.long.v34.20260328.jsonl
- output_dir: data\research\mined-windows-phase2-v34b
- window_snapshot_count: 30
- windows_found: 3

## Windows

- window-01: score=16.00, labels=expiry-heavy, snapshots=30, window=2026-03-28T10:32:28+00:00 -> 2026-03-28T10:32:40.784000+00:00
  snapshot_path: data\research\mined-windows-phase2-v34b\window-01.snapshots.jsonl
  event_path: data\research\mined-windows-phase2-v34b\window-01.events.jsonl
  event_counts: order.expired:3,order.submitted:1
- window-02: score=12.00, labels=submission-heavy, snapshots=30, window=2026-03-28T10:32:50.903000+00:00 -> 2026-03-28T10:33:08.895000+00:00
  snapshot_path: data\research\mined-windows-phase2-v34b\window-02.snapshots.jsonl
  event_path: data\research\mined-windows-phase2-v34b\window-02.events.jsonl
  event_counts: order.canceled:1
- window-03: score=8.00, labels=submission-heavy, snapshots=30, window=2026-03-28T10:27:34.558000+00:00 -> 2026-03-28T10:29:56.455000+00:00
  snapshot_path: data\research\mined-windows-phase2-v34b\window-03.snapshots.jsonl
  event_path: data\research\mined-windows-phase2-v34b\window-03.events.jsonl
  event_counts: order.submitted:4