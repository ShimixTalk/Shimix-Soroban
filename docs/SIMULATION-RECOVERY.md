# Recovery proposal — simulation only

The primary simulation is scheduled every fifteen minutes, but observed scheduled
runs on 18–19 November 2026 were sometimes eight hours apart despite succeeding.
The workflow is active; the available evidence does not establish why GitHub
omitted or delayed scheduled runs. A successful run is not evidence of a live heartbeat.

This proposal uses completion of the existing learning and comparative-paper
workflows as additional opportunities to check the primary simulation. It adds no
external service or paid API and does not modify either observer or portfolio.
It requests the existing simulation on `main` only when its snapshot is older
than 45 minutes, no attempt was created in the last 45 minutes, and no primary
run is queued, pending, requested, waiting or in progress. The mode must explicitly
disable real trading and exchange connectivity. Read errors stop recovery.
There is no unbounded loop or automatic retry of a failed recovery request.

The token requires Actions write permission to dispatch; checkout uses trusted
main code, not artifacts or code from a triggering pull request. Recovery has a
separate serialized concurrency group. The primary workflow retains its existing
serialization and risk validation. A manual dispatch by the owner racing the
check can still queue an extra serialized attempt; this is not an exactly-once system.

GitHub can delay all workflows: this is a conditional fallback, not a guarantee
of fifteen-minute execution. Dispatch acceptance does not establish completion
or a transaction. The learning report remains observation-only and can be old.

No entry thresholds, allowed assets, costs, capital, positions, protection limits,
or state files change. More executions cannot by themselves establish profitability.
Use the separately proposed decision diagnostics (#24) to explain entry refusals,
and the research model (#26) for exposure-aware comparisons. Neither is activated
by this proposal. The frozen experiments #12/#14/#15 remain separate.

Activation requires this workflow and helper on the default branch. A PR or
passing unit tests do not activate recovery or prove dispatch permissions.
