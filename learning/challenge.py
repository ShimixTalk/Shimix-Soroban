"""Independent educational paper challenge. No broker, HTTP, or primary-state writes."""
import copy
from zoneinfo import ZoneInfo
from engine import finite
from journal import timestamp

RULES=dict(id='educational-parallel-v1',initial=1600,targetPercent=8,dailyLossPercent=3,
           totalLossPercent=6,maxOrder=120,maxPositions=4,fee=.001,spread=.001,slippage=.001,
           stopPercent=4,takeProfitPercent=8,minimumDays=5,timezone='Europe/Paris')

def net_value(s,prices):
 if any(not finite(prices.get(a),1e-12) for a in s['holdings']):return None
 return s['cash']+sum(q*prices[a]*(1-RULES['spread']-RULES['slippage'])*(1-RULES['fee']) for a,q in s['holdings'].items())

def initial(event):
 return dict(version=1,rules=copy.deepcopy(RULES),simulationOnly=True,appliedToRobot=False,
             startedAt=event['at'],lastAt=event['at'],cash=1600.,holdings={},entries={},lastBuy={},
             day=timestamp(event['at']).astimezone(ZoneInfo(RULES['timezone'])).date().isoformat(),
             dayStartNet=1600.,netEquity=1600.,status='running',trades=[],observations=0,
             pending=[],tradingDays=[],issues=[],lastSignalAt=None)

def advance(current,event,now):
 """Execute prior observation's intent at a later observed quote, never retrospectively."""
 if event.get('source')!='robot-state.json' or event.get('simulationOnly') is not True:raise ValueError('Source simulation requise')
 at=timestamp(event['at']);observed=timestamp(now)
 if at>observed:raise ValueError('Observation future')
 if current is not None:
  if current.get('rules')!=RULES or current.get('simulationOnly') is not True or current.get('appliedToRobot') is not False:raise ValueError('Règles du challenge modifiées')
  if not finite(current.get('cash')) or not isinstance(current.get('holdings'),dict) or any(not finite(q,1e-12) or not finite(current.get('entries',{}).get(a),1e-12) for a,q in current['holdings'].items()):raise ValueError('Comptabilité du challenge invalide')
  if current.get('status') not in ('running','failed_total_loss','failed_daily_loss','review_required','educational_target_reached'):raise ValueError('État du challenge invalide')
  if at<=timestamp(current['lastAt']):return copy.deepcopy(current)
  s=copy.deepcopy(current)
 else:s=initial(event)
 s['lastAt']=event['at'];s['observations']+=1;s['issues']=[]
 if s['status']!='running':return s
 prices=event.get('prices',{});cache=event.get('quotesFetchedAt')
 age=at.timestamp()-cache if finite(cache) else None
 value=net_value(s,prices)
 if age is None or not 0<=age<=3600 or (observed-at).total_seconds()>3600 or value is None:
  s['issues']=['Cours absents ou anciens : aucune opération ; limites non évaluables.']
  s['netEquity']=None;s['pending']=[];return s
 day=at.astimezone(ZoneInfo(RULES['timezone'])).date().isoformat()
 if day!=s['day']:
  # Previous observed close is a proxy, not an invented midnight quote.
  if s['netEquity'] is None:
   s['issues']=['Référence journalière inconnue : reprise sur revue.'];s['status']='review_required';return s
  s['day']=day;s['dayStartNet']=s['netEquity']
 def sell(a,reason):
  q=s['holdings'].pop(a);price=prices[a]*(1-RULES['spread']-RULES['slippage']);gross=q*price
  fee=gross*RULES['fee'];s['cash']+=gross-fee;s['entries'].pop(a)
  s['trades'].append(dict(at=event['at'],asset=a,action='Vente',quantity=q,amount=gross-fee,fee=fee,reason=reason,simulation=True))
 def check_limits():
  v=net_value(s,prices)
  if v<=RULES['initial']*(1-RULES['totalLossPercent']/100):return 'failed_total_loss'
  if v<=s['dayStartNet']-RULES['initial']*RULES['dailyLossPercent']/100:return 'failed_daily_loss'
  return None
 breach=check_limits()
 if breach:
  for a in list(s['holdings']):sell(a,breach)
  s['status']=breach;s['netEquity']=s['cash'];s['pending']=[];return s
 actions={x['asset']:x['action'] for x in s['pending']} if s['lastSignalAt'] and 0<(at-timestamp(s['lastSignalAt'])).total_seconds()<=3600 else {}
 exited=set()
 for a in list(s['holdings']):
  reason='stop' if prices[a]<=s['entries'][a]*.96 else 'target' if prices[a]>=s['entries'][a]*1.08 else 'signal' if actions.get(a)=='Vente' else None
  if reason:sell(a,reason);exited.add(a)
 for a,action in sorted(actions.items()):
  if action!='Achat' or a in exited or a in s['holdings'] or not finite(prices.get(a),1e-12):continue
  if len(s['holdings'])>=RULES['maxPositions']:break
  if at.timestamp()-s['lastBuy'].get(a,0)<86400:continue
  amount=min(s['cash'],RULES['maxOrder']);fee=amount*RULES['fee']
  if amount<1:continue
  q=(amount-fee)/(prices[a]*(1+RULES['spread']+RULES['slippage']))
  projected=net_value(s,prices)-amount+q*prices[a]*(1-RULES['spread']-RULES['slippage'])*(1-RULES['fee'])
  if projected<=max(RULES['initial']*.94,s['dayStartNet']-48):continue
  s['cash']-=amount;s['holdings'][a]=q;s['entries'][a]=prices[a]*(1+RULES['spread']+RULES['slippage']);s['lastBuy'][a]=at.timestamp()
  s['trades'].append(dict(at=event['at'],signalAt=s['lastSignalAt'],asset=a,action='Achat',quantity=q,amount=amount,fee=fee,simulation=True))
 if s['trades'] and s['trades'][-1]['at']==event['at'] and day not in s['tradingDays']:s['tradingDays'].append(day)
 s['netEquity']=net_value(s,prices)
 if s['netEquity']>=RULES['initial']*1.08 and len(s['tradingDays'])>=RULES['minimumDays']:
  for a in list(s['holdings']):sell(a,'educational_target')
  s['netEquity']=s['cash'];s['status']='educational_target_reached'
 s['pending']=[dict(asset=x['asset'],action=x['action']) for x in event.get('signals',[]) if isinstance(x,dict) and isinstance(x.get('asset'),str) and x.get('action') in ('Achat','Vente')]
 s['lastSignalAt']=event['at']
 return s

def update(current,events,now):
 ordered=sorted((e for e in events if e.get('source')=='robot-state.json'),key=lambda e:e['at'])
 if current is None:ordered=ordered[-1:]  # Prospective start: never replay old profits.
 for e in ordered:
  if current is not None and timestamp(e['at'])<=timestamp(current['lastAt']):continue
  current=advance(current,e,now)
 return current
