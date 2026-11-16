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

def diagnose(state, report, now):
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
        decisions.append(item)
    coverage=state.get('holdingQuoteCoverage',{})
    cache_at=state.get('marketCacheAt')
    return {'version':1,'readOnly':True,'snapshotAt':state.get('updatedAt'),
        'snapshotAgeSeconds':(now-updated).total_seconds() if updated else None,
        'historicalEstimateOnly':True,'decisions':decisions,
        'shortlistCount':len(decisions),
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
    parser.add_argument('--now',required=True,help='Timezone-aware observation time')
    args=parser.parse_args();now=timestamp(args.now)
    if now is None:parser.error('--now must include a timezone')
    raw=args.state.read_bytes();raw_report=args.report.read_bytes()
    result=diagnose(json.loads(raw),json.loads(raw_report),now)
    result['sourceHashes']={'state':hashlib.sha256(raw).hexdigest(),'report':hashlib.sha256(raw_report).hexdigest()}
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))

if __name__=='__main__':main()
