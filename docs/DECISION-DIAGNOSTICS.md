# Read-only decision diagnostics

This tool explains an existing snapshot without executing the robot, requesting
quotes, modifying portfolios or changing thresholds. It is not a comparator or
an experiment, and does not replace the frozen #12/#14/#15 protocols.

Run against local copies pinned to one repository commit:

    python hub/trading/decision_diagnostics.py \
      --state hub/trading/robot-state.json \
      --report hub/trading/learning-data/report.json \
      --now 2026-11-16T05:10:00+01:00

Output goes to stdout only and includes SHA-256 fingerprints for both inputs.
The displayed predicates describe the current reviewed signal rules using
published, rounded indicators; they do not reconstruct exact boundary decisions,
assert that an order would have been placed, or estimate hypothetical profit.
Misaligned scanner timestamps, stale histories and missing data remain explicit.
The policy universe comes from the snapshot, never from an invented stablecoin
classification. Outcome quality is copied from the attributable closed-sales
report and is dated separately.

## Findings at source commit 8091361551e7f364e6eb8d92f3c958a0d354092d

Robot snapshot 16 November 2026, 04:37:12 Europe/Paris:

- 20 shortlisted symbols, 15 outside the published allowed entry universe.
  This counts exclusions, not missed trades or missed gains.
- BTC and ETH have low RSI, but lack the trend/rebound conditions; inactivity
  does not imply an execution failure.
- SOL and ADA have historical data older than the one-day eligibility limit.
  Their missing/stale history prevents reconstruction of eligible signals.
- Holding quote coverage is aligned, with no held asset and no published error.
  This single successful snapshot does not prove recovery during an outage.
- Outcome report: one winning sale among six attributable sales, costs covered;
  too few potentially correlated sales to establish sustainable profitability.

## Follow-up proposals, not activated

1. Prioritize history refresh within the allowed universe so excluded assets
   do not consume the two-request budget. Test prospectively without expanding
   the universe, changing signal predicates, or increasing request volume.
2. Reproduce quote outages offline: provider 429, stale/future timestamps,
   disappearing held IDs, identity collisions and pending exits. Keep missing
   values unknown and preserve exit priority and the 5%/10% protection.
3. Add structured published decision reasons covering signal, data, universe,
   entry review, cooldown, allocation and global protection. Do not infer order
   eligibility solely from the signal predicates in this diagnostic.

This PR adds only an offline diagnostic and tests/documentation. It makes no
runtime engine, state, workflow, schedule, capital, risk or strategy change.
