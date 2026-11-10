"""Append-only observation journal and conservative attribution, never an order engine."""
import datetime as dt
from engine import finite,digest

def timestamp(value):
 if not isinstance(value,str):raise ValueError('Horodatage absent')
 parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
 if parsed.tzinfo is None:raise ValueError('Fuseau horaire absent')
 return parsed.astimezone(dt.timezone.utc)

def observe(state,source_sha,observed_at):
 if state.get('realTradingEnabled') is not False or state.get('exchangeApiConnected') is not False or state.get('readiness',{}).get('simulationOnly') is not True or state.get('readiness',{}).get('liveOrdersEnabled') is not False:raise ValueError('Source non confirmée en simulation')
 if state.get('capital')!=1600:raise ValueError('Capital de référence différent de 1 600 EUR : aucune correction automatique')
 at=timestamp(state.get('updatedAt'));now=timestamp(observed_at)
 if at>now+dt.timedelta(seconds=60):raise ValueError('Observation future refusée')
 prices=state.get('prices',{});holdings=state.get('holdings',{})
 if not isinstance(prices,dict) or not isinstance(holdings,dict) or not finite(state.get('cash')) or any(not finite(q) for q in holdings.values()):raise ValueError('Comptabilité invalide')
 prices={str(k):v for k,v in prices.items() if finite(v,1e-12)}
 errors=[];missing=[a for a,q in holdings.items() if q>0 and a not in prices]
 if missing:errors.append(dict(code='missing_holding_quote',message='Cotation absente : '+', '.join(missing)))
 equity=None if missing else state['cash']+sum(q*prices.get(a,0) for a,q in holdings.items())
 if equity is not None and finite(state.get('value')) and abs(state['value']-equity)>.02:errors.append(dict(code='equity_mismatch',message='Valeur publiée différente du recalcul des positions.'))
 cache_at=state.get('marketCacheAt')
 age=now.timestamp()-cache_at if finite(cache_at) else None
 if age is None or age>3600 or age<0:errors.append(dict(code='stale_or_unknown_quotes',message='Fraîcheur des cours non confirmée.'))
 signals=[]
 for asset,signal in state.get('signals',{}).items():
  if not isinstance(signal,dict):continue
  signals.append(dict(asset=str(asset)[:40],action=str(signal.get('action','Attente'))[:30],reason=str(signal.get('reason','Non documentée par le moteur'))[:300],indicators={k:v for k,v in signal.items() if k in ('rsi','sma7','sma21') and finite(v)}))
 trades=[]
 for raw in state.get('trades',[]):
  if not isinstance(raw,dict):continue
  safe={k:v for k,v in raw.items() if k in ('date','asset','symbol','action','amount','price','executionPrice','quantity','fee','reason','simulation') and (isinstance(v,(str,bool)) or finite(v))}
  try:date=timestamp(safe.get('date')).isoformat()
  except ValueError:
   errors.append(dict(code='trade_time_unknown',message='Une opération ne possède pas de date ISO exploitable.'));continue
  asset=safe.get('asset',safe.get('symbol'))
  if not isinstance(asset,str) or safe.get('action') not in ('Achat','Vente'):continue
  trade=dict(id=digest(safe),at=date,asset=asset[:40],action=safe['action'],gross=safe.get('amount'),fee=safe.get('fee'),quantity=safe.get('quantity'),executionPrice=safe.get('executionPrice',safe.get('price')),reason=str(safe.get('reason','Non enregistrée'))[:300])
  if not finite(trade['quantity'],1e-15) or not finite(trade['fee']):errors.append(dict(code='incomplete_trade_cost',message='Quantité ou frais historiques absents : attribution réalisée non calculable.'))
  if any(t['id']==trade['id'] for t in trades):errors.append(dict(code='duplicate_trade_fingerprint',message='Opérations identiques sans identifiant source : attribution à vérifier.'))
  trades.append(trade)
 return dict(version=1,id='robot:'+source_sha,sourceCommit=source_sha,source='robot-state.json',at=at.isoformat(),observedAt=now.isoformat(),capital=1600,currency='EUR',simulationOnly=True,cash=state['cash'],holdings=holdings,prices=prices,quotesFetchedAt=cache_at,equity=round(equity,6) if equity is not None else None,signals=signals,trades=sorted(trades,key=lambda t:(t['at'],t['id'])),riskSnapshot={k:state.get(k) for k in ['maxOrder','maxLossPercent','maxPositionPercent','maxPositions','feeRate','spreadRate','slippageRate']},errors=errors,notes='Observation après exécution ; pas de reconstitution des décisions non journalisées.')

def append(events,new):
 if any(e['id']==new['id'] for e in events):return events
 previous=next((e for e in reversed(events) if e['source']==new['source']),None)
 if previous and timestamp(new['at'])<timestamp(previous['at']):raise ValueError('Observation antérieure : journal inchangé')
 return events+[new]

def summarize(events):
 errors=[];trades={};steps=[];lots={};realized=0.;unknown=0
 for e in events:
  errors.extend(dict(event=e['id'],**err) for err in e['errors'])
  for t in e['trades']:trades.setdefault(t['id'],t)
 for t in sorted(trades.values(),key=lambda t:(t['at'],t['id'])):
  q=t['quantity'];fee=t['fee'];price=t['executionPrice'];asset=t['asset']
  if not finite(q,1e-15) or not finite(fee) or not finite(price,1e-12):unknown+=1;continue
  if t['action']=='Achat':lots.setdefault(asset,[]).append([q,q*price+fee]);continue
  available=sum(qty for qty,_ in lots.get(asset,[]))
  if available+1e-10<q:unknown+=1;continue
  remaining=q;basis=0.
  while remaining>1e-12:
   qty,cost=lots[asset][0];take=min(qty,remaining);basis+=cost*take/qty;remaining-=take
   if take>=qty-1e-12:lots[asset].pop(0)
   else:lots[asset][0]=[qty-take,cost*(1-take/qty)]
  pnl=q*price-fee-basis;realized+=pnl
  steps.append(dict(trade=t['id'],asset=asset,at=t['at'],netRealizedPnl=round(pnl,6),explanation='Produit de vente moins frais et coût FIFO connu (frais d’achat inclus).'))
 attribution=[]
 for before,after in zip(events,events[1:]):
  if before['equity'] is None or after['equity'] is None:continue
  if any(q>0 and (a not in before['prices'] or a not in after['prices']) for a,q in before['holdings'].items()):continue
  market=sum(q*(after['prices'].get(a,0)-before['prices'].get(a,0)) for a,q in before['holdings'].items())
  delta=after['equity']-before['equity']
  attribution.append(dict(fromId=before['id'],toId=after['id'],equityChange=round(delta,6),priceEffect=round(market,6),executionAndCashEffect=round(delta-market,6),explanation='Effet des cours sur les positions précédentes ; le solde inclut exécutions, frais et éventuels flux fictifs.'))
 latest=events[-1] if events else None
 return dict(observations=len(events),decisions=sum(len(e['signals']) for e in events),uniqueTrades=len(trades),knownFees=round(sum(t['fee'] for t in trades.values() if finite(t['fee'])),6),feeCoverageComplete=all(finite(t['fee']) for t in trades.values()),knownRealizedPnl=round(realized,6),unattributableTrades=unknown,realizedExplanations=steps[-50:],equityAttribution=attribution[-50:],errors=errors[-100:],latest=({k:latest[k] for k in ['at','equity','cash','capital','currency','riskSnapshot']} if latest else None),limitations=['Les opérations supprimées de l’historique avant la première collecte ne peuvent pas être récupérées.','Les signaux observés après exécution ne prouvent pas leur disponibilité avant l’ordre.','Le journal conserve toutes ses lignes ; les vues détaillées sont limitées pour l’affichage.'])

def observe_portfolios(state,source_sha,observed_at):
 if state.get('simulationOnly') is not True or state.get('realOrdersEnabled') is not False:raise ValueError('Trois portefeuilles non confirmés en simulation')
 expected={'prudent':640,'equilibre':560,'dynamique':400};profiles=state.get('portfolios',[])
 if not isinstance(profiles,list) or {p.get('id'):p.get('initial') for p in profiles}!=expected or len(profiles)!=3:raise ValueError('Capitaux des profils différents de 640/560/400 EUR')
 at=timestamp(state.get('updatedAt'));now=timestamp(observed_at)
 if at>now+dt.timedelta(seconds=60):raise ValueError('Résultats futurs refusés')
 out=[];errors=[]
 for p in profiles:
  if not finite(p.get('cash')) or not isinstance(p.get('holdings'),dict) or any(not finite(q) for q in p['holdings'].values()):raise ValueError('Profil invalide')
  safe={k:p.get(k) for k in ['id','name','initial','cash','value','netProfit','feesPaid','paused','updatedAt','maxAllocation','maxTrade','stop','fee','spread','slippage']}
  safe['holdings']=p['holdings'];safe['prices']={k:v for k,v in p.get('lastPrices',{}).items() if finite(v,1e-12)}
  safe['signals']={str(k):{f:v for f,v in s.items() if f in ['action','reason','change24h','estimatedCosts'] and (isinstance(v,str) or finite(v,-1e15))} for k,s in p.get('signals',{}).items() if isinstance(s,dict)}
  safe['trades']=[]
  for t in p.get('trades',[]):
   if isinstance(t,dict):safe['trades'].append({k:v for k,v in t.items() if k in ['at','symbol','action','amount','quantity','executionPrice','fee','estimatedSpreadSlippage'] and (isinstance(v,str) or finite(v))})
  missing=[a for a,q in safe['holdings'].items() if q>0 and a not in safe['prices']]
  if missing:errors.append(dict(code='profile_quote_missing',message=p['id']+': prix manquant, résultat publié non reconstitué.'))
  safe['quoteFreshness']='not_provided_by_source';out.append(safe)
 return dict(version=1,id='profiles:'+source_sha,sourceCommit=source_sha,source='three-portfolios.json',at=at.isoformat(),observedAt=now.isoformat(),capital=1600,currency='EUR',simulationOnly=True,profiles=out,errors=errors)

def profiles_summary(events):
 result=[]
 for profile in ['prudent','equilibre','dynamique']:
  seen={};count=0;decisions=0;latest=None
  for e in events:
   for p in e.get('profiles',[]):
    if p['id']!=profile:continue
    count+=1;decisions+=len(p['signals']);latest=p
    for trade in p['trades']:seen.setdefault(digest(trade),trade)
  if latest:result.append(dict(id=profile,observations=count,decisions=decisions,uniqueTrades=len(seen),knownFees=round(sum(t['fee'] for t in seen.values() if finite(t.get('fee'))),6),latest={k:latest.get(k) for k in ['initial','value','netProfit','feesPaid','updatedAt']}))
 return result
