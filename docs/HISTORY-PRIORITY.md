# Historical request priority

Two historical requests per run are retained. Due histories for reviewed entry
identities and currently held identities are served before excluded assets.
Within each group, least recently attempted comes first, including failures.
Existing fresh histories remain fresh; attempts never count as successful data.
Fallback histories for other scanner assets are retained when priority assets
need no refresh, preserving the existing descriptive scanner.

The shortlist, entry universe, buy predicates, order sizing, costs, price-only
exits, checkpoint ordering and 5%/10% protection are unchanged. This can change
which eligible asset has timely history, so it creates a new observation regime;
it is not evidence of improved profit. The integration guard accepts only the exact old/new engine fingerprint pair
for this correction, with regression tests rejecting altered risk code. The
previous owner-policy exception cannot authorize this change. Historical
owner-policy transition tests use the exact previous engine fixture. Frozen
experiment protocols and their own source/journal checks remain unchanged;
this new regime must not be silently substituted for their baseline.

GitHub scheduling remains best effort. On 16 November a scheduled principal run
completed successfully at 16:28 Europe/Paris after an interval of about 3h20.
This patch does not fix or guarantee the external scheduler cadence and does not
create any additional trigger, request budget, service or paid dependency.
