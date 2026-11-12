"""Isolated test of an entry exclusion policy. Never changes the running robot."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from engine import digest, finite
from journal import timestamp
from rigour import review
from shadow_compare import RISK, fresh, buy, liquidation, metrics, load_events

BLOCKED = ('USDT','USDC','USD1','DAI','USDS','USDE','USDF','USDG','USDD','PYUSD',
           'RLUSD','GHO','OUSD','BFUSD','FDUSD','TUSD','FRAX','LUSD','USD0','USDGO')
VARIANTS = ('recorded_buy_signals','recorded_buy_signals_no_stablecoins','strict_no_stablecoins')


def validate_plan(plan):
    expected=dict(version=1,id='stablecoin-entry-forward-v1',frozenAt='2026-11-12T13:48:35+00:00',
                  capital=1600,mode='offline_shadow_only',blockedSymbols=list(BLOCKED),
                  variants=list(VARIANTS),automaticPromotion=False)
    if digest(plan)!=digest(expected):raise ValueError('Politique différente du plan gelé')


def eligible(signals,exclude=False,strict=False):
    candidates=[];excluded=[]
    for signal in signals:
        asset=signal.get('asset');values=signal.get('indicators',{});rsi=values.get('rsi')
        if not isinstance(asset,str) or signal.get('action')!='Achat':continue
        if exclude and asset.upper() in BLOCKED:
            excluded.append(dict(asset=asset,reason='known_stablecoin_symbol'));continue
        if not finite(rsi,0,100):continue
        if strict:
            short,long=values.get('sma7'),values.get('sma21')
            if not (rsi<35 and finite(short,1e-12) and finite(long,1e-12) and short>long):continue
        candidates.append((45-rsi,asset))
    return sorted(candidates,reverse=True),excluded


def step(account,current,previous,variant):
    prices=current['prices'];at=current['at']
    marked=account['cash']+sum(q*prices[a] for a,q in account['holdings'].items())
    if marked<=800:account['paused']=True
    if account['paused']:return
    signals={s['asset']:s for s in previous.get('signals',[])}
    # Exclusion applies to entries only: existing positions retain ordinary exit rules.
    for asset,q in list(account['holdings'].items()):
        price=prices[asset];entry=account['entries'][asset]
        reason='stop_loss' if price<=entry*.96 else 'take_profit' if price>=entry*1.08 else 'previous_sell_signal' if signals.get(asset,{}).get('action')=='Vente' else None
        if not reason:continue
        gross=q*price*.998;fee=gross*.001
        account['cash']+=gross-fee;account['fees']+=fee
        del account['holdings'][asset];del account['entries'][asset]
        account['ledger'].append(dict(at=at,signalAt=previous['at'],asset=asset,action='Vente',quantity=q,fee=fee,reason=reason))
    candidates,excluded=eligible(previous.get('signals',[]),exclude=variant!='recorded_buy_signals',strict=variant=='strict_no_stablecoins')
    account['excludedEntries'].extend(dict(at=at,signalAt=previous['at'],**x) for x in excluded)
    for _,asset in candidates:
        if len(account['holdings'])>=8:break
        if asset not in prices:continue
        if asset in account['lastBuy'] and (timestamp(at)-timestamp(account['lastBuy'][asset])).total_seconds()<86400:continue
        amount=min(120,account['cash'],max(0,320-account['holdings'].get(asset,0)*prices[asset]))
        if amount>=1:
            buy(account,asset,amount,prices[asset],at,previous['at']);break


def compare(events,plan):
    validate_plan(plan);cutoff=timestamp(plan['frozenAt'])
    accounts={name:dict(fresh(),excludedEntries=[]) for name in VARIANTS}
    rows=sorted([e for e in events if e.get('source')=='robot-state.json' and timestamp(e['at'])>cutoff and timestamp(e['observedAt'])>cutoff],key=lambda e:(timestamp(e['at']),e['id']))
    accepted=[];seen=set();issues=[];observed=[]
    for event in rows:
        if event['id'] in seen:continue
        seen.add(event['id'])
        if event.get('capital')!=1600 or event.get('simulationOnly') is not True or event.get('riskSnapshot')!=RISK:
            issues.append(dict(event=event['id'],reason='source_configuration_changed'));break
        if timestamp(event['observedAt'])<timestamp(event['at']):
            issues.append(dict(event=event['id'],reason='invalid_collection_time'));break
        checked=review([event],event['observedAt']);prices=event.get('prices',{})
        if checked.get('estimatedLiquidationEquity') is None or not isinstance(prices,dict) or any(not finite(p,1e-12) for p in prices.values()):
            issues.append(dict(event=event['id'],reason='invalid_quote_or_costs'));break
        if any(a not in prices for account in accounts.values() for a in account['holdings']):
            issues.append(dict(event=event['id'],reason='missing_shadow_holding_quote'));break
        if accepted and timestamp(event['at'])==timestamp(accepted[-1]['at']):continue
        available=[e for e in accepted if timestamp(e['observedAt'])<=timestamp(event['at'])]
        if available:
            previous=available[-1]
            if (timestamp(event['at'])-timestamp(previous['at'])).total_seconds()<=7200:
                for name,account in accounts.items():step(account,event,previous,name)
            else:issues.append(dict(event=event['id'],reason='signal_gap_no_fill'))
        for account in accounts.values():
            marked=account['cash']+sum(q*prices[a] for a,q in account['holdings'].items())
            account['curve'].append(dict(at=event['at'],equity=liquidation(account,prices),exposurePercent=100*(marked-account['cash'])/marked if marked else 0))
        observed.append(dict(at=event['at'],sourceCommit=event.get('sourceCommit'),estimatedLiquidationEquity=checked['estimatedLiquidationEquity']))
        accepted.append(event)
    results={}
    for name,account in accounts.items():
        result=metrics(account)
        if result is not None:result['excludedEntrySignals']=account['excludedEntries']
        results[name]=result
    blocked=any(i['reason']!='signal_gap_no_fill' for i in issues)
    return dict(version=1,plan=copy.deepcopy(plan),planHash=digest(plan),
        inputDigest=digest([e.get('recordHash') or digest(e) for e in events]),
        evaluatorCodeHash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        dependencyHashes={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['shadow_compare.py','rigour.py','journal.py','engine.py']},
        status='blocked_partial_data' if blocked else 'waiting_for_new_observations' if len(accepted)<2 else 'forward_entry_policy_observation',
        evidence='insufficient',automaticPromotion=False,acceptedObservations=len(accepted),issues=issues,
        variants=results,observedRobot=observed,
        limitations=[
            'Liste bornée de symboles connus, pas une identification exhaustive ou certaine par contrat : collisions et nouveaux stablecoins restent possibles.',
            'Exclusion des nouveaux achats seulement ; aucune vente forcée d’un actif déjà détenu.',
            'Le témoin de recherche exploite les signaux Achat précédemment enregistrés, pas une reproduction complète du moteur ou du scanner.',
            'Le robot observé garde ses positions antérieures ; les trois comptes de test repartent chacun de 1600 EUR. Ne pas additionner ces capitaux.',
            'Comparer gain net après liquidation, pertes et exposition ; aucun gain mensuel promis et aucune stratégie promue automatiquement.',
            'Données postérieures au gel seulement ; signaux déjà collectés et exécutés au relevé suivant, coûts simulés avant impôts.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    plan=json.loads(Path(__file__).with_name('stablecoin-plan-v1.json').read_text())
    print(json.dumps(compare(load_events(args.root),plan),ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
