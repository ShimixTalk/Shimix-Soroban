"""Forward-only profit reserve experiment. Decimal accounting, no network or writes."""
import argparse
import copy
import hashlib
import json
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from engine import digest, finite
from journal import timestamp
from rigour import review
from shadow_compare import load_events, RISK

D = lambda value: Decimal(str(value))
ZERO = D(0)
CAPITAL = D(1600)
STEP = D(5)


def validate_plan(plan):
    expected = dict(version=1,id='profit-reserve-forward-v1',frozenAt='2026-11-12T08:41:23+00:00',
                    capital=1600,transferStepEUR=5,allocations=[[0,1600],[800,800],[400,1200]],
                    mode='offline_shadow_only',automaticPromotion=False)
    if digest(plan) != digest(expected):
        raise ValueError('Protocole de réserve différent du plan gelé')


def fresh(harvest, growth):
    if harvest+growth != 1600 or min(harvest,growth)<0:
        raise ValueError('Répartition invalide')
    return dict(pockets={name:dict(initial=D(amount),cash=D(amount),holdings={},basis={},realized=ZERO,
                                  transferred=ZERO,fees=ZERO)
                         for name,amount in [('harvest',harvest),('growth',growth)] if amount},
                reserve=ZERO,lastBuy={},trades=[],transfers=[],curve=[],paused=False)


def pocket_value(pocket,prices,liquidate=True):
    factor=D('.998')*D('.999') if liquidate else D(1)
    return pocket['cash']+sum((q*D(prices[a])*factor for a,q in pocket['holdings'].items()),ZERO)


def trading_value(account,prices,liquidate=True):
    return sum((pocket_value(p,prices,liquidate) for p in account['pockets'].values()),ZERO)


def transfer_profit(account,prices,at):
    """Internal transfer, never income. Recover realized losses and preserve base at transfer time."""
    harvest=account['pockets'].get('harvest')
    if harvest is None:
        return ZERO
    eligible=min(harvest['realized']-harvest['transferred'],harvest['cash'],
                 trading_value(account,prices)-CAPITAL)
    amount=max(ZERO,(eligible/STEP).to_integral_value(rounding=ROUND_FLOOR)*STEP)
    if amount:
        before=trading_value(account,prices)+account['reserve']
        harvest['cash']-=amount;harvest['transferred']+=amount;account['reserve']+=amount
        account['transfers'].append(dict(id='reserve:'+str(len(account['transfers'])+1)+':'+at,
                                       at=at,fromPocket='harvest',toPocket='reserve',amount=amount,
                                       harvestCashDelta=-amount,reserveCashDelta=amount))
        if trading_value(account,prices)+account['reserve'] != before:
            raise ArithmeticError('Un transfert interne a changé la richesse totale')
    return amount


def buy(account,name,asset,amount,price,at,signal_at):
    p=account['pockets'][name];amount=D(amount);price=D(price)
    if not amount.is_finite() or not price.is_finite() or price<=0 or amount<1 or amount>120 or amount>p['cash']:
        raise ValueError('Montant fictif invalide')
    q=amount*D('.999')/(price*D('1.002'))
    p['cash']-=amount;p['holdings'][asset]=p['holdings'].get(asset,ZERO)+q
    p['basis'][asset]=p['basis'].get(asset,ZERO)+amount;p['fees']+=amount*D('.001')
    account['lastBuy'][asset]=at
    account['trades'].append(dict(at=at,signalAt=signal_at,pocket=name,asset=asset,
                                  action='Achat',amount=amount,quantity=q,fee=amount*D('.001')))


def sell(account,name,asset,price,at,signal_at,reason):
    p=account['pockets'][name];price=D(price)
    if not price.is_finite() or price<=0:raise ValueError('Prix fictif invalide')
    q=p['holdings'][asset];cost=p['basis'][asset]
    gross=q*D(price)*D('.998');fee=gross*D('.001');proceeds=gross-fee
    profit=proceeds-cost;p['cash']+=proceeds;p['realized']+=profit;p['fees']+=fee
    del p['holdings'][asset];del p['basis'][asset]
    account['trades'].append(dict(at=at,signalAt=signal_at,pocket=name,asset=asset,
                                  action='Vente',quantity=q,fee=fee,netRealizedPnl=profit,reason=reason))
    return profit


def step(account,current,previous):
    prices=current['prices'];at=current['at']
    # Reserve is excluded from the stop test: it cannot subsidize a losing trading base.
    if trading_value(account,prices,False)<=800:
        account['paused']=True
    if account['paused']:
        return
    signals={s['asset']:s for s in previous.get('signals',[])};sold=set()
    for name,p in account['pockets'].items():
        for asset,q in list(p['holdings'].items()):
            price=D(prices[asset]);entry=p['basis'][asset]/q
            net_if_sold=q*price*D('.998')*D('.999')-p['basis'][asset]
            reason='stop_loss' if price<=entry*D('.96') else 'take_profit' if price>=entry*D('1.08') else 'previous_sell_signal' if signals.get(asset,{}).get('action')=='Vente' else None
            if reason is None and name=='harvest' and net_if_sold>=STEP and p['realized']-p['transferred']+net_if_sold>=STEP:
                reason='harvest_five_eur_net'
            if reason:
                sell(account,name,asset,price,at,previous['at'],reason);sold.add(asset)
    transfer_profit(account,prices,at)
    candidates=[]
    for asset,signal in signals.items():
        values=signal.get('indicators',{});rsi=values.get('rsi');short=values.get('sma7');long=values.get('sma21')
        if signal.get('action')=='Achat' and all(finite(v) for v in [rsi,short,long]) and rsi<35 and short>long:
            candidates.append((rsi,asset))
    active={a for p in account['pockets'].values() for a in p['holdings']}
    if len(active)>=8:
        return
    # Least deployed relative to its allocated capital, deterministic ties; no cash crosses pockets.
    pockets=sorted(account['pockets'],key=lambda n:(sum(account['pockets'][n]['basis'].values(),ZERO)/account['pockets'][n]['initial'],0 if n=='harvest' else 1))
    for _,asset in sorted(candidates):
        if asset not in prices or asset in sold:
            continue  # Never sell then rebuy the same asset in one observation.
        if asset in account['lastBuy'] and (timestamp(at)-timestamp(account['lastBuy'][asset])).total_seconds()<86400:
            continue
        total_position=sum((p['holdings'].get(asset,ZERO)*D(prices[asset]) for p in account['pockets'].values()),ZERO)
        for name in pockets:
            p=account['pockets'][name]
            amount=min(D(120),p['cash'],max(ZERO,D(320)-total_position),
                       max(ZERO,p['initial']*D('.2')-p['holdings'].get(asset,ZERO)*D(prices[asset])))
            if amount>=1:
                buy(account,name,asset,amount,prices[asset],at,previous['at']);return


def snapshot(account,event):
    prices=event['prices'];trading=trading_value(account,prices);total=trading+account['reserve']
    marked=trading_value(account,prices,False)
    cash=sum((p['cash'] for p in account['pockets'].values()),ZERO)
    account['curve'].append(dict(at=event['at'],tradingLiquidation=trading,reserve=account['reserve'],
                                 combinedLiquidation=total,exposurePercent=(marked-cash)/(marked+account['reserve'])*100 if marked+account['reserve'] else ZERO))


def serializable(value):
    if isinstance(value,Decimal):return float(value.quantize(D('.000001')))
    if isinstance(value,dict):return {k:serializable(v) for k,v in value.items()}
    if isinstance(value,list):return [serializable(v) for v in value]
    return value


def metrics(account):
    if not account['curve']:return None
    peak=CAPITAL;drawdown=ZERO
    for point in account['curve']:
        peak=max(peak,point['combinedLiquidation']);drawdown=max(drawdown,1-point['combinedLiquidation']/peak)
    last=account['curve'][-1];realized=sum((p['realized'] for p in account['pockets'].values()),ZERO)
    return serializable(dict(reserve=account['reserve'],tradingLiquidation=last['tradingLiquidation'],
        combinedLiquidation=last['combinedLiquidation'],netChange=last['combinedLiquidation']-CAPITAL,
        netReturnPercent=(last['combinedLiquidation']/CAPITAL-1)*100,
        maxObservedDrawdownPercent=drawdown*100,realizedPnl=realized,
        latentAfterExitCosts=last['combinedLiquidation']-CAPITAL-realized,
        paidFees=sum((p['fees'] for p in account['pockets'].values()),ZERO),
        maxExposurePercent=max(p['exposurePercent'] for p in account['curve']),
        meanExposurePercent=sum((p['exposurePercent'] for p in account['curve']),ZERO)/len(account['curve']),
        paused=account['paused'],trades=account['trades'],transfers=account['transfers'],curve=account['curve']))


def compare(events,plan):
    validate_plan(plan);cutoff=timestamp(plan['frozenAt'])
    variants={str(h)+'/'+str(g):fresh(h,g) for h,g in plan['allocations']}
    rows=sorted([e for e in events if e.get('source')=='robot-state.json' and timestamp(e['at'])>cutoff and timestamp(e['observedAt'])>cutoff],key=lambda e:(timestamp(e['at']),e['id']))
    accepted=[];seen=set();issues=[];robot=[]
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
        if any(a not in prices for acc in variants.values() for p in acc['pockets'].values() for a in p['holdings']):
            issues.append(dict(event=event['id'],reason='missing_shadow_holding_quote'));break
        if accepted and timestamp(event['at'])==timestamp(accepted[-1]['at']):continue
        available=[e for e in accepted if timestamp(e['observedAt'])<=timestamp(event['at'])]
        if available:
            previous=available[-1]
            if (timestamp(event['at'])-timestamp(previous['at'])).total_seconds()<=7200:
                for acc in variants.values():step(acc,event,previous)
            else:issues.append(dict(event=event['id'],reason='signal_gap_no_fill'))
        for acc in variants.values():snapshot(acc,event)
        robot.append(dict(at=event['at'],sourceCommit=event.get('sourceCommit'),estimatedLiquidationEquity=checked['estimatedLiquidationEquity']))
        accepted.append(event)
    blocked=any(e['reason']!='signal_gap_no_fill' for e in issues)
    return dict(version=1,plan=copy.deepcopy(plan),planHash=digest(plan),
        inputDigest=digest([e.get('recordHash') or digest(e) for e in events]),
        evaluatorCodeHash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        dependencyHashes={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['shadow_compare.py','rigour.py','journal.py','engine.py']},
        status='blocked_partial_data' if blocked else 'waiting_for_new_observations' if len(accepted)<2 else 'forward_reserve_observation',
        evidence='insufficient',automaticPromotion=False,acceptedObservations=len(accepted),issues=issues,
        variants={name:metrics(acc) for name,acc in variants.items()},observedRobot=robot,
        limitations=[
            'Réserve fictive en euros, sans rendement et exclue du trading ; aucun argent réel protégé.',
            'Transferts internes : aucune création de gain ou de capital. Réserve + capital liquidable restant est le critère de comparaison.',
            'Transfert par tranche de 5 EUR après récupération des pertes réalisées et uniquement si le capital de trading liquidable reste au moins 1600 EUR à cet instant ; ce niveau n’est pas garanti ensuite.',
            'Trois comptes de test repartent chacun de 1600 EUR ; le robot observé conserve ses positions antérieures. Les expositions peuvent différer ; aucun gagnant automatique.',
            'Les deux poches suivent le filtre strict de recherche, pas une reproduction du moteur courant ; la récolte ajoute une sortie sur gain net de position au moins égal à 5 EUR.',
            'Cours indicatifs, coûts simulés, avant impôts ; les gaps peuvent masquer des variations. Aucun rendement mensuel garanti.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    plan=json.loads(Path(__file__).with_name('reserve-plan-v1.json').read_text())
    print(json.dumps(compare(load_events(args.root),plan),ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
