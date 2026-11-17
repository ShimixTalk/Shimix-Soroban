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

## Separate runtime freshness from trade inactivity

Optionally pass `--runs /path/to/actions-runs.json`, a local saved GitHub Actions
API response. Its SHA-256 is included. Only the principal simulation workflow
path is considered; comparative-profile runs are not a principal heartbeat.
A snapshot older than 30 minutes raises a diagnostic warning (not a trading
threshold or a scheduling SLA). Missing/future timestamps remain unknown.
The supplied page can be incomplete: no visible recent run does not establish
that no run exists. A nonterminal run is reported separately from snapshot age.
The root cause always remains unconfirmed by this offline tool.

Investigation on 16 November 2026 around 16:20 Europe/Paris found the simulation
workflow active, with its last visible scheduled run 43863795508 successful at
13:08 Europe/Paris. No later principal run was visible in the inspected pages.
The last state was enabled, with no positions and no published error. This
separates missing recent execution evidence from the last scan's lack of buy
signals. It does not prove why GitHub did not launch another run, nor fix its
scheduler. The existing quarter-hour cron has not been changed.

Validation: 95 trading tests and 75 learning tests pass locally.

## Explicit buy-refusal explanations

Each row separates data/universe blockers from failed strict and rebound
conditions. The rebound route is considered only when the snapshot enables it.
Missing, stale or misaligned history is not called a failed signal. Passing
signal predicates does not establish order eligibility: entry review, quote
freshness, protection, position sizing and cooldown still apply.

On source commit 645785b94fe77ad4ddcdf3e39baedaf47e35ac8c (state 17 November,
21:36 Europe/Paris), 16 of 20 shortlisted assets were excluded; BTC, ETH, SOL
and XRP had assessable history but all four failed the signal predicates.
Low RSI alone was insufficient: the strict trend condition and the rebound
trend floor failed. ETH also lacked a rising final close. This is consistent
with the rules, not proof that refusing was economically optimal.

No future outcome is inferred. Judging refusals requires prospectively recorded
decisions and later quotes, fixed horizons, all configured costs and matched
exposure benchmarks. This diagnostic does not retune the strategy or run
unverified comparisons on the journal. Validation with the current engine
including #25: 103 trading and 77 learning tests pass.
