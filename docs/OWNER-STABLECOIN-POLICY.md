# Temporary owner instruction: no stablecoin entries

Owner confirmation on 15 November 2026 authorizes a change to the paper robot:
exclude new stablecoin purchases, exit the existing USD1 holding at a valid
quote after modeled exit costs, and retain EUR without forced reinvestment.
No claim of selling at a future maximum or preventing all losses is made.

Entries now require an exact reviewed provider ID and matching symbol from
BTC, ETH, SOL, ADA, XRP, DOGE, LINK, AVAX, DOT, LTC. Unknown identities are
excluded. This conservative universe is not an exhaustive stablecoin taxonomy.
The existing entry review, sizing, cooldown and risk checks still apply.

Only the recorded USD1 provider ID usd1-wlfi is targeted for the owner exit.
The quote must be finite and positive, identity verified, timezone aware,
no more than 900 seconds old and at most 60 seconds in the future. Configured
costs must be present and valid. Unavailable evidence leaves the exit pending;
no old total or zero quote is used. Sale proceeds use quantity * price *
(1 - spreadRate - slippageRate) * (1 - feeRate), without subtracting prior
purchase fees again. The position is removed and the trade is checkpointed
before history downloads; subsequent runs cannot sell that position twice.
No purchases occur in that execution. Subsequent entries remain subject to
all existing entry checks, and cash need not be invested.

Global 5% buy pause / 10% liquidation latch takes precedence and is unchanged;
no restart of a liquidated portfolio is authorized. Holding quote coverage,
exit priority, simulation-only flags, workflows, schedules, capital and
published journals are not edited by this change. The first official run
must be inspected for ownerAssetPolicy.version=1 and the exit trade (or a
pending exit). Until that evidence exists, do not report a completed sale.

Frozen #12/#14/#15 experiments must report a changed source regime. Their
protocols and the exact integration guard are not expanded to accept this
new engine silently. #15 remains a separate offline experiment, not the
implementation of this owner instruction.
