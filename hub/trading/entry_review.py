"""Fixed conservative entry checks, not a prediction or an auto-trained strategy."""
import math,datetime
VERSION='confirmed-entry-v1'
STABLE_IDS=frozenset(('tether','usd-coin','usd1-wlfi','dai','usds','ethena-usde','falcon-finance','global-dollar','usdd','paypal-usd','ripple-usd','gho','origin-dollar','bfusd','first-digital-usd','true-usd','frax','liquity-usd','usual-usd','usdgo','euro-coin'))
def finite(x):return type(x) in (int,float) and math.isfinite(x) and x>0

def review(coin_id,closes,current,short,long,fee,spread,slippage,*,quote_at,now):
 reasons=[]
 try:
  stamp=datetime.datetime.fromisoformat(quote_at.replace('Z','+00:00'))
  if stamp.tzinfo is None or not -60<=(now-stamp).total_seconds()<=900:raise ValueError('Cours ancien ou futur')
 except (ValueError,TypeError,AttributeError):reasons.append('Fraîcheur du cours fournisseur non confirmée')
 if len(closes)<22 or not all(finite(x) for x in closes) or not all(finite(x) for x in (current,short,long)):
  return dict(version=VERSION,allowed=False,reasons=['Données insuffisantes ou invalides'])
 if coin_id in STABLE_IDS:reasons.append('Stablecoin connu exclu des nouveaux achats spéculatifs')
 if short<=long:reasons.append('Tendance haussière non confirmée (SMA7 ≤ SMA21)')
 if closes[-1]<=closes[-2]:reasons.append('Dernière clôture sans reprise confirmée')
 if current<closes[-1]:reasons.append('Rebond invalidé : cours actuel sous la dernière clôture')
 if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=.1 for x in (fee,spread,slippage)):
  return dict(version=VERSION,allowed=False,reasons=reasons+['Coûts non confirmés'])
 exit_factor=(1-spread-slippage)*(1-fee)
 # The engine's exit thresholds use the fee-inclusive average entry cost.
 target_net=1.08*exit_factor-1;stop_net=.96*exit_factor-1
 ratio=target_net/abs(stop_net) if stop_net<0 else None
 if target_net<=0 or ratio is None or ratio<1.5:reasons.append('Objectif net insuffisant par rapport au risque net théorique')
 return dict(version=VERSION,allowed=not reasons,reasons=reasons or ['Tendance et reprise confirmées ; scénarios nets compatibles'],
             coinId=coin_id,lastClosedPrice=closes[-1],currentPrice=current,sma7=short,sma21=long,
             targetNetPercent=round(target_net*100,6),stopNetPercent=round(stop_net*100,6),
             theoreticalRewardRisk=round(ratio,6) if ratio is not None else None,
             prediction=False,limitation='Scénarios aux seuils, pas une probabilité ; gaps et retard possibles')

def exit_review(entry,quantity,proceeds,price):
 known=finite(entry)
 cost=entry*quantity if known else None
 return dict(entryCost=cost,netProceeds=proceeds,netPnl=proceeds-cost if known else None,
             priceAtDecision=price,basisKnown=known,simulation=True)
