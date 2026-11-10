"""Read-only research. Fixed universes/risk limits; decisions use observations strictly before execution."""
import copy, datetime as dt, hashlib, json, math
PROFILES={
 'prudent':dict(initial=640.,maxOrder=35.,exposure=.12,stop=.08,fee=.002,spread=.001,slippage=.001,assets=['bitcoin','ethereum']),
 'equilibre':dict(initial=560.,maxOrder=45.,exposure=.22,stop=.15,fee=.002,spread=.0015,slippage=.0015,assets=['bitcoin','ethereum','solana','chainlink']),
 'dynamique':dict(initial=400.,maxOrder=50.,exposure=.35,stop=.25,fee=.002,spread=.003,slippage=.003,assets=['bitcoin','ethereum','solana','chainlink','avalanche-2','dogecoin'])}
BASELINE=dict(lookback=14,threshold=.01)
CANDIDATES=[dict(lookback=n,threshold=t) for n in (7,14,21) for t in (0,.01,.02)]
def finite(n,minimum=0,maximum=1e15):return type(n) in (int,float) and math.isfinite(n) and minimum<=n<=maximum
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def policy_check(p):
 if p.get('version')!=1 or p.get('mode')!='shadow_simulation_only':raise ValueError('Mode observation requis')
 if any(p.get(k) is not False for k in ['automaticMerge','automaticRiskChanges','automaticLiveTrading']):raise ValueError('Automatismes sensibles interdits')
 if not isinstance(p.get('experimentId'),str) or not __import__('re').fullmatch(r'[a-z0-9-]{1,60}',p['experimentId']):raise ValueError('Identifiant expérience invalide')
 for name,low,high in [('minimumDailyPoints',120,2000),('futureMinimumPoints',20,365),('historyRequestsPerRun',0,2)]:
  if type(p.get(name)) is not int or not low<=p[name]<=high:raise ValueError('Limite invalide: '+name)
 ai=p.get('openai',{})
 if type(ai.get('enabled')) is not bool or not finite(ai.get('monthlyBudgetUsd'),0,10000) or not finite(ai.get('maxRequestUsd'),0,1000):raise ValueError('Budget invalide')
 if ai['maxRequestUsd']>ai['monthlyBudgetUsd']:raise ValueError('Budget par appel supérieur au budget mensuel')
 return p

def check_series(rows):
 if not isinstance(rows,list):raise ValueError('Série absente')
 last=None
 for row in rows:
  if not isinstance(row,dict) or set(row)!={'date','price'} or not finite(row['price'],1e-12):raise ValueError('Prix invalide')
  date=dt.date.fromisoformat(row['date'])
  if last is not None and (date-last).days!=1:raise ValueError('Jours manquants, répétés ou désordonnés')
  last=date
 return rows

def history_from_chart(chart,now):
 today=now.date();days={}
 if not isinstance(chart,dict) or not isinstance(chart.get('prices'),list):raise ValueError('Historique absent')
 for row in chart['prices']:
  if not isinstance(row,list) or len(row)!=2 or not finite(row[0]) or not finite(row[1],1e-12):raise ValueError('Point historique invalide')
  stamp=dt.datetime.fromtimestamp(row[0]/1000,dt.timezone.utc)
  # Daily points only; never label intraday samples as daily closes.
  if stamp.date()>=today:continue
  if stamp.hour or stamp.minute or stamp.second:raise ValueError('Point non journalier')
  day=stamp.date().isoformat()
  if day in days and days[day]!=row[1]:raise ValueError('Prix contradictoires pour un jour')
  days[day]=row[1]
 rows=[dict(date=d,price=p) for d,p in sorted(days.items())]
 check_series(rows)
 if not rows or rows[-1]['date']!=(today-dt.timedelta(days=1)).isoformat():raise ValueError('Historique périmé')
 return rows

def align(histories,assets):
 if any(a not in histories for a in assets):return []
 for a in assets:check_series(histories[a])
 maps={a:{r['date']:r['price'] for r in histories[a]} for a in assets}
 common=sorted(set.intersection(*(set(m) for m in maps.values())))
 if not common:return []
 if any((dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days!=1 for a,b in zip(common,common[1:])):raise ValueError('Dates communes discontinues')
 return [dict(date=d,prices={a:maps[a][d] for a in assets}) for d in common]

def action(past,params):
 n=params['lookback']
 if len(past)<max(n+1,21):return 'Attente'
 momentum=past[-1]/past[-1-n]-1
 short=sum(past[-7:])/7;long=sum(past[-21:])/21
 if momentum>params['threshold'] and short>long:return 'Achat'
 if momentum<-params['threshold'] or short<long:return 'Vente'
 return 'Attente'

def backtest(rows,profile,params,start=0,end=None):
 """Fresh capital per fold. Prior points warm indicators; each fill uses the next observed price."""
 p=PROFILES[profile];end=len(rows) if end is None else end
 cash=p['initial'];holdings={a:0. for a in p['assets']};peak=cash;worst=0.;fees=0.;orders=0;paused=False;ledger=[]
 for i in range(start,end):
  prices=rows[i]['prices'];equity=cash+sum(holdings[a]*prices[a] for a in holdings);peak=max(peak,equity)
  worst=max(worst,1-equity/peak)
  if equity<=peak*(1-p['stop']):paused=True
  # Stops suspend new decisions rather than promise a guaranteed liquidation price.
  for a in p['assets']:
   signal=action([r['prices'][a] for r in rows[:i]],params)
   if paused:signal='Attente'
   price=prices[a];quantity=0.;fee=0.;cost=0.
   if signal=='Vente' and holdings[a]>0:
    execution=price*(1-p['spread']/2-p['slippage']);quantity=min(holdings[a],p['maxOrder']/execution)
    cost=quantity*execution;fee=cost*p['fee'];cash+=cost-fee;holdings[a]-=quantity
   elif signal=='Achat':
    cost=min(p['maxOrder'],cash,max(0,p['initial']*p['exposure']-holdings[a]*price))
    if cost>=1:
     execution=price*(1+p['spread']/2+p['slippage']);fee=cost*p['fee'];quantity=(cost-fee)/execution;cash-=cost;holdings[a]+=quantity
   if quantity>0:
    orders+=1;fees+=fee;ledger.append(dict(date=rows[i]['date'],asset=a,action=signal,quantity=quantity,gross=cost,fee=fee,executionPrice=execution,signalThrough=rows[i-1]['date'] if i else None))
  equity=cash+sum(holdings[a]*prices[a] for a in holdings);peak=max(peak,equity);worst=max(worst,1-equity/peak)
 if start>=end:return dict(netReturnPercent=0,netPnl=0,fees=0,trades=0,maxDrawdownPercent=0,ledger=[])
 last=rows[end-1]['prices']
 # Comparable terminal liquidation valuation, with costs on still-open positions.
 terminal=sum(holdings[a]*last[a]*(1-p['spread']/2-p['slippage'])*(1-p['fee']) for a in holdings)
 terminal_fees=sum(holdings[a]*last[a]*(1-p['spread']/2-p['slippage'])*p['fee'] for a in holdings)
 net=cash+terminal-p['initial'];terminal_equity=cash+terminal
 worst=max(worst,1-terminal_equity/peak)
 return dict(netReturnPercent=round(net/p['initial']*100,6),netPnl=round(net,6),fees=round(fees+terminal_fees,6),trades=orders,maxDrawdownPercent=round(worst*100,6),terminalExitIncluded=True,ledger=ledger)

def compact(result):return {k:v for k,v in result.items() if k!='ledger'}
def splits(n):
 a=int(n*.6);b=int(n*.8)
 return dict(train=(21,a),validation=(a+1,b),test=(b+1,n))
def study(histories,profile,min_points):
 rows=align(histories,PROFILES[profile]['assets'])
 if len(rows)<min_points:return dict(status='insufficient_data',points=len(rows),required=min_points)
 windows=splits(len(rows))
 # Hyperparameters chosen using train only. Validation gates a hypothesis, test never selects it.
 train=windows['train'];score=lambda x:x['netReturnPercent']-.5*x['maxDrawdownPercent']
 ranked=[]
 for params in CANDIDATES:
  result=backtest(rows,profile,params,*train);ranked.append((score(result) if result['trades']>=3 else -1e9,params))
 _,candidate=max(ranked,key=lambda x:x[0]);folds={}
 for name,(start,end) in windows.items():
  folds[name]=dict(start=rows[start]['date'],end=rows[end-1]['date'],points=end-start,baseline=compact(backtest(rows,profile,BASELINE,start,end)),candidate=compact(backtest(rows,profile,candidate,start,end)))
 validation=folds['validation'];test=folds['test']
 supported=validation['candidate']['trades']>=3 and validation['candidate']['netReturnPercent']>validation['baseline']['netReturnPercent'] and validation['candidate']['maxDrawdownPercent']<=validation['baseline']['maxDrawdownPercent']
 test_supported=test['candidate']['trades']>=3 and test['candidate']['netReturnPercent']>test['baseline']['netReturnPercent'] and test['candidate']['maxDrawdownPercent']<=test['baseline']['maxDrawdownPercent']
 return dict(status='frozen_hypothesis' if supported and test_supported else 'not_supported',candidate=candidate,baseline=BASELINE,points=len(rows),cutoff=rows[-1]['date'],folds=folds,parameterTrials=len(CANDIDATES),validationSupportsCandidate=supported,testSupportsCandidate=test_supported,testUsedForSelection=False,selectionScope='train_only',riskLimits=copy.deepcopy(PROFILES[profile]),dataHash=digest(rows))

def future(histories,profile,frozen,min_points):
 rows=align(histories,PROFILES[profile]['assets']);cutoff=frozen.get('cutoff')
 frozen_at=dt.datetime.fromisoformat(frozen.get('frozenAt',str(cutoff)+'T23:59:59.999999+00:00')) if cutoff else None
 indices=[i for i,r in enumerate(rows) if cutoff and r['date']>cutoff and dt.datetime.fromisoformat(r['date']+'T00:00:00+00:00')>frozen_at]
 if len(indices)<min_points:return dict(status='waiting_for_new_data',points=len(indices),required=min_points,after=cutoff)
 start=indices[0]
 return dict(status='forward_observation',points=len(indices),start=rows[start]['date'],end=rows[-1]['date'],baseline=compact(backtest(rows,profile,frozen['baseline'],start)),candidate=compact(backtest(rows,profile,frozen['candidate'],start)),appliedToRobot=False)

def advisory_selection(study_result,forward_result):
 """Progressively recommend a frozen signal filter, without changing any running strategy."""
 candidate=forward_result.get('candidate',{});baseline=forward_result.get('baseline',{})
 supported=(study_result.get('validationSupportsCandidate') is True and study_result.get('testSupportsCandidate') is True and forward_result.get('status')=='forward_observation' and candidate.get('trades',0)>=3 and candidate.get('netReturnPercent',-1e9)>baseline.get('netReturnPercent',1e9) and candidate.get('maxDrawdownPercent',1e9)<=baseline.get('maxDrawdownPercent',0))
 params=study_result.get('candidate',BASELINE) if supported else study_result.get('baseline',BASELINE)
 return dict(selection='candidate' if supported else 'baseline',signalParameters={k:params[k] for k in ['lookback','threshold']},status='proposal_for_human_review' if supported else 'retain_reference_pending_evidence',appliedToRobot=False,riskChanges=False)
