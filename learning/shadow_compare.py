"""Offline forward-only strategy comparison. Reads a verified journal; prints JSON only."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from engine import digest, finite
from journal import timestamp
from rigour import review

RISK = dict(maxOrder=120, maxLossPercent=50, maxPositionPercent=20, maxPositions=8,
            feeRate=.001, spreadRate=.001, slippageRate=.001)


def validate_plan(plan):
    expected = dict(version=1, id='strict-signal-forward-v1',
                    frozenAt='2026-11-11T20:00:52+00:00', mode='offline_shadow_only',
                    capital=1600, riskSnapshot=RISK,
                    candidate='strict_rsi_sma_previous_observation',
                    benchmark='buy_hold_btc_eth_120_each', automaticPromotion=False)
    if digest(plan) != digest(expected):
        raise ValueError('Plan différent du protocole gelé : nouvelle version et revue requises')
    return plan


def load_events(root):
    base = Path(root)/'hub/trading/learning-data'
    index = json.loads((base/'index.json').read_text())
    events = []
    previous = None
    for name in index['segments']:
        if not re.fullmatch(r'events/\d{4}-\d{2}-\d{2}-\d{4}\.jsonl', name):
            raise ValueError('Segment de journal invalide')
        for line in (base/name).read_text().splitlines():
            event = json.loads(line)
            claimed = event.pop('recordHash')
            if digest(event) != claimed or event.get('previousHash') != previous:
                raise ValueError('Intégrité du journal non confirmée')
            event['recordHash'] = claimed
            previous = claimed
            events.append(event)
    return events


def fresh():
    return dict(cash=1600., holdings={}, entries={}, lastBuy={}, ledger=[],
                fees=0., curve=[], paused=False, benchmarkBought=[])


def liquidation(account, prices):
    return account['cash']+sum(q*prices[a]*.998*.999 for a,q in account['holdings'].items())


def buy(account, asset, amount, price, at, signal_at):
    if amount < 1:
        return
    qty = amount*.999/(price*1.002)
    prior = account['holdings'].get(asset, 0)
    account['entries'][asset] = (account['entries'].get(asset, 0)*prior+amount)/(prior+qty)
    account['holdings'][asset] = prior+qty
    account['cash'] -= amount
    account['fees'] += amount*.001
    account['lastBuy'][asset] = at
    account['ledger'].append(dict(at=at, signalAt=signal_at, asset=asset, action='Achat',
                                  amount=amount, quantity=qty, fee=amount*.001))


def step(account, current, previous, benchmark=False):
    """Previous *collected* signals only; fills at the next distinct source quote."""
    prices = current['prices'];at = current['at']
    marked = account['cash']+sum(q*prices[a] for a,q in account['holdings'].items())
    if marked <= 800:  # Same 50% global halt as the frozen source, never loosened.
        account['paused'] = True
    if account['paused']:
        return
    signals = {s['asset']: s for s in previous.get('signals', [])}
    if benchmark:
        for asset in ['BTC', 'ETH']:
            if asset in account['benchmarkBought'] or asset not in prices:
                continue
            buy(account, asset, min(120, account['cash']), prices[asset], at, previous['at'])
            account['benchmarkBought'].append(asset)
            break
        return
    for asset,qty in list(account['holdings'].items()):
        price = prices[asset];entry = account['entries'][asset]
        # Exit rules are kept identical in form: 4% position stop, 8% take-profit,
        # or the last *available* bearish signal. This is not a loss guarantee.
        if price <= entry*.96 or price >= entry*1.08 or signals.get(asset, {}).get('action') == 'Vente':
            gross = qty*price*.998;fee = gross*.001
            account['cash'] += gross-fee;account['fees'] += fee
            del account['holdings'][asset];del account['entries'][asset]
            account['ledger'].append(dict(at=at,signalAt=previous['at'],asset=asset,
                                          action='Vente',quantity=qty,fee=fee))
    eligible = []
    for asset,signal in signals.items():
        indicators = signal.get('indicators', {})
        rsi,short,long = [indicators.get(k) for k in ['rsi','sma7','sma21']]
        if signal.get('action') == 'Achat' and all(finite(v) for v in [rsi,short,long]) and rsi < 35 and short > long:
            eligible.append((rsi,asset))
    for _,asset in sorted(eligible):
        if asset not in prices or len(account['holdings']) >= 8:
            continue
        if asset in account['lastBuy'] and (timestamp(at)-timestamp(account['lastBuy'][asset])).total_seconds() < 86400:
            continue
        amount = min(120, account['cash'], max(0,320-account['holdings'].get(asset,0)*prices[asset]))
        if amount >= 1:
            buy(account,asset,amount,prices[asset],at,previous['at']);break


def metrics(account):
    curve = account['curve']
    if not curve:
        return None
    peak = 1600.;drawdown = 0.
    for point in curve:
        peak = max(peak, point['equity']);drawdown = max(drawdown, 1-point['equity']/peak)
    return dict(estimatedLiquidationEquity=round(curve[-1]['equity'],6),
                netChange=round(curve[-1]['equity']-1600,6),
                netReturnPercent=round((curve[-1]['equity']/1600-1)*100,6),
                maxObservedDrawdownPercent=round(drawdown*100,6),
                paidFees=round(account['fees'],6),
                observedBuys=sum(t['action']=='Achat' for t in account['ledger']),
                observedSales=sum(t['action']=='Vente' for t in account['ledger']),
                paused=account['paused'],
                maxObservedExposurePercent=round(max(p['exposurePercent'] for p in curve),6),
                meanObservedExposurePercent=round(sum(p['exposurePercent'] for p in curve)/len(curve),6),
                ledger=account['ledger'],curve=curve)


def compare(events, plan):
    validate_plan(plan)
    cutoff = timestamp(plan['frozenAt'])
    rows = sorted([e for e in events if e.get('source')=='robot-state.json'
                   and timestamp(e['at'])>cutoff and timestamp(e['observedAt'])>cutoff],
                  key=lambda e: (timestamp(e['at']), e['id']))
    candidate,benchmark = fresh(),fresh()
    accepted=[];seen=set();issues=[];robot=[]
    for event in rows:
        if event['id'] in seen:
            continue
        seen.add(event['id'])
        if timestamp(event['observedAt']) < timestamp(event['at']):
            issues.append(dict(event=event['id'],reason='collection_before_execution'));continue
        if event.get('capital')!=1600 or event.get('simulationOnly') is not True or event.get('riskSnapshot')!=RISK:
            issues.append(dict(event=event['id'],reason='source_configuration_changed'));break
        checked=review([event],event['observedAt'])
        if checked.get('estimatedLiquidationEquity') is None:
            issues.append(dict(event=event['id'],reason='unusable_quote_or_costs'));break
        prices=event.get('prices',{})
        if not isinstance(prices,dict) or any(not finite(p,1e-12) for p in prices.values()):
            issues.append(dict(event=event['id'],reason='invalid_prices'));break
        if any(a not in prices for acc in [candidate,benchmark] for a in acc['holdings']):
            issues.append(dict(event=event['id'],reason='missing_shadow_holding_quote'));break
        if accepted and timestamp(event['at'])==timestamp(accepted[-1]['at']):
            # A new commit at the same execution time is not a new fill opportunity.
            continue
        available=[e for e in accepted if timestamp(e['observedAt'])<=timestamp(event['at'])]
        if available:
            previous=available[-1]
            # Avoid using a delayed signal or executing a stale shadow quote.
            if (timestamp(event['at'])-timestamp(previous['at'])).total_seconds()<=7200:
                step(candidate,event,previous)
                step(benchmark,event,previous,benchmark=True)
            else:
                issues.append(dict(event=event['id'],reason='signal_gap_over_two_hours_no_fill'))
        for acc in [candidate,benchmark]:
            marked=acc['cash']+sum(q*prices[a] for a,q in acc['holdings'].items())
            acc['curve'].append(dict(at=event['at'],equity=liquidation(acc,prices),
                                     exposurePercent=100*(marked-acc['cash'])/marked if marked else 0))
        robot.append(dict(at=event['at'],sourceCommit=event.get('sourceCommit'),estimatedLiquidationEquity=checked['estimatedLiquidationEquity']))
        accepted.append(event)
    blocked=any(issue['reason']!='signal_gap_over_two_hours_no_fill' for issue in issues)
    return dict(version=1,plan=copy.deepcopy(plan),planHash=digest(plan),
                inputDigest=digest([e.get('recordHash') or digest(e) for e in events]),
                evaluatorCodeHash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                status='blocked_partial_data' if blocked else 'waiting_for_new_observations' if len(accepted)<2 else 'forward_shadow_observation',
                evidence='insufficient',automaticPromotion=False,
                acceptedObservations=len(accepted),issues=issues,
                candidate=metrics(candidate),buyHold=metrics(benchmark),observedRobot=robot,
                limitations=[
                    'Aucune donnée antérieure au gel utilisée pour calculer les résultats de cette expérience.',
                    'Les signaux doivent avoir été collectés avant le relevé servant à exécuter ; aucun signal observé après coup utilisé au même cours.',
                    'Prix de remplissage indicatifs, frais/spread/glissement simulés, avant impôts ; aucune garantie de vente à ces prix.',
                    'Le candidat repart avec 1 600 EUR fictifs ; le robot observé conserve ses positions et son historique. Ses valeurs sont un témoin distinct, pas une reproduction ou un départ identique.',
                    'Le benchmark BTC/ETH investit 120 EUR par actif, une acquisition par relevé admissible ; son exposition et son univers diffèrent du candidat et du robot.',
                    'Même capital de référence, coûts et plafonds gelés ; comparaison à lire avec les expositions et non sur le seul gain en euros.',
                    'Aucun gagnant sélectionné et aucune règle appliquée au robot. Les gaps et arrêts peuvent rendre la couverture partielle.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    plan=json.loads(Path(__file__).with_name('shadow-plan-v1.json').read_text())
    print(json.dumps(compare(load_events(args.root),plan),ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
