#!/usr/bin/env python3
"""Read local published snapshots only; never import/run the trading engine."""
import argparse, datetime as dt, hashlib, json, math
from pathlib import Path

UTC=dt.timezone.utc

def number(x):
    return type(x) in (int,float) and math.isfinite(x)

def timestamp(value):
    try:
        t=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return t if t.tzinfo is not None else None
    except (TypeError,ValueError,AttributeError):return None

def runtime_health(state, now, runs=None):
    """Snapshot freshness and scheduler evidence are separate from trading inactivity."""
    stamp=timestamp(state.get('updatedAt'))
    age=(now-stamp).total_seconds() if stamp else None
    freshness='unknown' if age is None or age<0 else 'stale' if age>1800 else 'recent'
    matching=[r for r in (runs or {}).get('workflow_runs',[])
              if r.get('path')=='.github/workflows/shimix-trading-simulation.yml']
    valid=[r for r in matching if timestamp(r.get('created_at')) and timestamp(r['created_at'])<=now]
    last=max(valid,key=lambda r:timestamp(r['created_at'])) if valid else None
    last_age=(now-timestamp(last['created_at'])).total_seconds() if last else None
    running=any(r.get('status')!='completed' for r in valid)
    scheduling=('not_observed' if runs is None else 'no_matching_run_in_supplied_page' if not last else
                'nonterminal_run_visible' if running else 'no_recent_run_visible' if last_age>1800 else 'recent_run_visible')
    return {'snapshotFreshness':freshness,'snapshotAgeSeconds':age,
        'snapshotWarningThresholdSeconds':1800,'robotEnabled':state.get('enabled'),
        'openPositionCount':sum(number(q) and q>0 for q in state.get('holdings',{}).values()),
        'publishedErrors':state.get('dataErrors',[]),'schedulerEvidence':scheduling,
        'lastVisibleRun':{k:last.get(k) for k in ('id','created_at','status','conclusion','html_url')} if last else None,
        'lastVisibleRunAgeSeconds':last_age,
        'cause':'unconfirmed','scope':'supplied_snapshot_and_optional_run_page_only',
        'note':'No new trades does not establish that the scheduler ran; a successful old run is not a heartbeat.'}

def explain_buy(decision):
    """Explain observed predicates, never classify a refusal as an economic mistake."""
    p=decision['buyPredicates']
    strict=['strictRsiBelow35','shortAverageAboveLong','lastCloseAbovePreviousLongAverage']
    rebound=['aggressiveRsiBelow45','lastCloseRising','shortAverageAtLeast97PercentOfLong']
    blocked=[]
    if decision['entryUniverse']!='allowed':
        blocked.append('entry_universe_excluded' if decision['entryUniverse']=='excluded' else 'entry_universe_unknown')
    if not decision['snapshotAligned']:blocked.append('scanner_snapshot_misaligned')
    age=decision['historyAgeSecondsAtDecision']
    if age is None or age<0:blocked.append('history_timestamp_unknown_or_future')
    elif age>=86400:blocked.append('history_stale')
    if p is None:
        status='not_assessable';failed_strict=None;failed_rebound=None
    else:
        failed_strict=[key for key in strict if not p[key]]
        failed_rebound=[key for key in rebound if not p[key]] if p['aggressiveMode'] else None
        passed=not failed_strict or (p['aggressiveMode'] and not failed_rebound)
        status='signal_predicates_pass' if passed else 'signal_predicates_fail'
    return {'signalAssessment':status,'dataAndUniverseBlockers':blocked,
        'strictConditionsFailed':failed_strict,'reboundConditionsFailed':failed_rebound,
        'orderEligibility':'not_reconstructed',
        'economicQualityOfRefusal':'undetermined',
        'evidenceNeeded':'Forward prices after the decision, identical horizons, all configured costs and exposure-matched benchmarks.'}

def diagnose(state, report, now, runs=None):
    updated=timestamp(state.get('updatedAt'))
    scanner=state.get('scanner',{})
    aligned=scanner.get('updatedAt')==state.get('updatedAt')
    policy=state.get('ownerAssetPolicy',{})
    universe=policy.get('allowedAssetIds')
    policy_known=policy.get('version')==1 and isinstance(universe,list)
    decisions=[]
    for row in scanner.get('shortlist',[]):
        sym=row.get('symbol');coin_id=state.get('assetIds',{}).get(sym)
        signal=state.get('signals',{}).get(sym,{})
        item={'symbol':sym,'coinId':coin_id,'publishedAction':signal.get('action'),
              'publishedReason':signal.get('reason'),
              'entryUniverse':('allowed' if coin_id in universe else 'excluded') if policy_known and coin_id else 'unknown',
              'snapshotAligned':aligned,'buyPredicates':None}
        p=state.get('dailyHistory',{}).get(coin_id,[])
        at=state.get('historyUpdated',{}).get(coin_id)
        history_age=updated.timestamp()-at if updated and number(at) else None
        item['historyAgeSecondsAtDecision']=history_age
        valid=aligned and history_age is not None and 0<=history_age<86400 and len(p)>=22 and all(number(x) and x>0 for x in p)
        rsi=signal.get('rsi');a=signal.get('sma7');b=signal.get('sma21')
        # Published indicators may be rounded: this is descriptive, not a replay.
        if valid and all(number(x) for x in (rsi,a,b)):
            prev=sum(p[-22:-1])/21
            item['buyPredicates']={
                'strictRsiBelow35':rsi<35,'shortAverageAboveLong':a>b,
                'lastCloseAbovePreviousLongAverage':p[-1]>prev,
                'aggressiveMode':state.get('experimentMode')=='aggressive_simulation',
                'aggressiveRsiBelow45':rsi<45,'lastCloseRising':p[-1]>p[-2],
                'shortAverageAtLeast97PercentOfLong':a>=b*.97}
        item['buyExplanation']=explain_buy(item)
        decisions.append(item)
    coverage=state.get('holdingQuoteCoverage',{})
    cache_at=state.get('marketCacheAt')
    return {'version':1,'readOnly':True,'runtimeHealth':runtime_health(state,now,runs),'snapshotAt':state.get('updatedAt'),
        'snapshotAgeSeconds':(now-updated).total_seconds() if updated else None,
        'historicalEstimateOnly':True,'decisions':decisions,
        'shortlistCount':len(decisions),
        'allowedSignalSummary':{status:sum(x['entryUniverse']=='allowed' and x['buyExplanation']['signalAssessment']==status for x in decisions) for status in ('not_assessable','signal_predicates_pass','signal_predicates_fail')},
        'excludedShortlistCount':sum(x['entryUniverse']=='excluded' for x in decisions),
        'unknownUniverseCount':sum(x['entryUniverse']=='unknown' for x in decisions),
        'unexplainedDecisionCount':sum(x['buyPredicates'] is None for x in decisions),
        'quoteEvidence':{'publishedErrors':state.get('dataErrors',[]),
            'valuationComplete':state.get('globalProtection',{}).get('valuationComplete'),
            'coverageAligned':coverage.get('checkedAt')==state.get('updatedAt'),
            'missingAssets':coverage.get('missingAssets'),
            'marketCacheAgeSecondsAtDecision':updated.timestamp()-cache_at if updated and number(cache_at) else None},
        'outcomeReportAt':report.get('generatedAt'),
        'attributableSalesOnly':report.get('observed',{}).get('outcomeQuality'),
        'limitations':['Rounded published indicators cannot exactly replay boundary decisions.',
            'No order, network access, strategy change or simulation engine execution.',
            'Shortlist exclusion is not a missed profitable trade.',
            'Unknown or stale evidence stays unknown; no zero costs or prices assumed.',
            'Closed attributable sales exclude open positions; correlated small samples cannot establish durable profitability.']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--runs',type=Path,help='Optional local GitHub Actions runs response; never fetched by this tool')
    parser.add_argument('--now',required=True,help='Timezone-aware observation time')
    args=parser.parse_args();now=timestamp(args.now)
    if now is None:parser.error('--now must include a timezone')
    raw=args.state.read_bytes();raw_report=args.report.read_bytes()
    raw_runs=args.runs.read_bytes() if args.runs else None
    result=diagnose(json.loads(raw),json.loads(raw_report),now,json.loads(raw_runs) if raw_runs else None)
    result['sourceHashes']={'state':hashlib.sha256(raw).hexdigest(),'report':hashlib.sha256(raw_report).hexdigest()}
    if raw_runs is not None:result['sourceHashes']['runs']=hashlib.sha256(raw_runs).hexdigest()
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))

if __name__=='__main__':main()
