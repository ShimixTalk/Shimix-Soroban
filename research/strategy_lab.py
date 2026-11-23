"""Local daily-model research; no engine imports, network, orders or writes."""
import argparse, datetime as dt, hashlib, json, math
from pathlib import Path
ASSETS=('bitcoin','ethereum','solana')
VARIANTS=('current_daily_proxy','early_rebound','trend_following','cash','buy_hold')
FEE=SPREAD=SLIPPAGE=.001
EXIT=(1-SPREAD-SLIPPAGE)*(1-FEE)
FREEZE='2026-11-17T21:22:44+00:00'

def sma(p,n):return sum(p[-n:])/n

def rsi(p):
 changes=[b-a for a,b in zip(p[-15:-1],p[-14:])]
 gain=sum(max(x,0) for x in changes)/14;loss=sum(max(-x,0) for x in changes)/14
 return 100-100/(1+gain/loss) if loss else 100 if gain else 50

def signal(p,variant):
 if len(p)<22:return False
 a,b=sma(p,7),sma(p,21);r=rsi(p);rising=p[-1]>p[-2]
 if variant=='current_daily_proxy':
  raw=(r<35 and a>b and p[-1]>sma(p[:-1],21)) or (r<45 and rising and a>=.97*b)
  return raw and a>b and rising
 if variant=='early_rebound':return r<45 and rising and sma(p,3)>a and a>=.97*b
 if variant=='trend_following':return a>b and p[-1]>max(p[-21:-1]) and r<70
 return False

def replay(rows,variant,start,end):
 """Past-only signals; execution at next observed daily price, with gap risk."""
 if variant not in VARIANTS:raise ValueError('Unknown variant')
 cash=1600.;positions={};ledger=[];peak=1600.;dd=0.;latched=False;exposures=[];fees=0.;realized=0.
 def liquidation(prices):return cash+sum(q*prices[a]*EXIT for a,(q,basis) in positions.items())
 def sell(a,prices,day,reason):
  nonlocal cash,fees,realized
  q,basis=positions.pop(a);gross=q*prices[a]*(1-SPREAD-SLIPPAGE);fee=gross*FEE
  cash+=gross-fee;fees+=fee;realized+=gross-fee-basis
  ledger.append(dict(date=day,asset=a,action='sell',reason=reason,net=gross-fee))
 for i in range(start,end):
  prices=rows[i]['prices'];day=rows[i]['date'];exited=set();liq=liquidation(prices)
  peak=max(peak,liq);dd=max(dd,1-liq/peak)
  if variant not in ('cash','buy_hold') and liq<=1440:
   latched=True
   for a in list(positions):sell(a,prices,day,'global_10_percent')
  for a,(q,basis) in list(positions.items()):
   p=[x['prices'][a] for x in rows[:i]];unit=basis/q
   reason='stop' if prices[a]<=unit*.96 else 'target' if prices[a]>=unit*1.08 else 'signal' if rsi(p)>65 and sma(p,7)<sma(p,21) else None
   if reason and variant!='buy_hold':sell(a,prices,day,reason);exited.add(a)
  paused=liquidation(prices)<=1520 or latched
  candidates=[]
  if variant=='buy_hold' and i==start:candidates=list(ASSETS)
  elif variant!='cash' and not paused:
   candidates=[a for a in ASSETS if a not in exited and signal([x['prices'][a] for x in rows[:i]],variant) and prices[a]>=rows[i-1]['prices'][a]]
  for a in candidates[:len(ASSETS) if variant=='buy_hold' else 1]:
   cap=1600/len(ASSETS) if variant=='buy_hold' else 320
   budget=min(cash,cap-positions.get(a,(0,0))[0]*prices[a],1600/len(ASSETS) if variant=='buy_hold' else 60 if variant=='early_rebound' else 120)
   if budget<1:continue
   fee=budget*FEE;q=(budget-fee)/(prices[a]*(1+SPREAD+SLIPPAGE));oldq,oldbasis=positions.get(a,(0,0))
   positions[a]=(oldq+q,oldbasis+budget);cash-=budget;fees+=fee
   ledger.append(dict(date=day,signalThrough=rows[i-1]['date'],asset=a,action='buy',budget=budget,quantity=q))
  equity=cash+sum(q*prices[a] for a,(q,_) in positions.items());liq=liquidation(prices)
  exposures.append((equity-cash)/equity if equity else 0);peak=max(peak,liq);dd=max(dd,1-liq/peak)
 last=rows[end-1]['prices'];terminal=liquidation(last)
 return dict(variant=variant,terminalLiquidation=terminal,netPnl=terminal-1600,realized=realized,
  latentAfterEstimatedExit=terminal-cash-sum(b for _,b in positions.values()),maxDrawdownPercent=dd*100,
  averageExposurePercent=sum(exposures)/len(exposures)*100,feesPaid=fees,
  estimatedTerminalExitFees=sum(q*last[a]*(1-SPREAD-SLIPPAGE)*FEE for a,(q,_) in positions.items()),
  tradeCount=len(ledger),liquidationLatched=latched,ledger=ledger)

def load_rows(directory,freeze):
 data={};hashes={};late=0
 for a in ASSETS:
  raw=(directory/(a+'.json')).read_bytes();hashes[a]=hashlib.sha256(raw).hexdigest();d=json.loads(raw)
  if d.get('currency')!='EUR':raise ValueError('EUR required')
  values={};previous=None
  for row in d['prices']:
   day=dt.date.fromisoformat(row['date']);price=row['price']
   if previous and (day-previous).days!=1:raise ValueError('Missing, unordered or duplicated dates')
   previous=day
   if type(price) not in (int,float) or not math.isfinite(price) or price<=0:raise ValueError('Invalid price')
   seen=dt.datetime.fromisoformat(d.get('firstSeen',{}).get(row['date'],'').replace('Z','+00:00'))
   if seen.tzinfo is None:raise ValueError('Unknown observation time')
   if day<freeze.date() and seen<=freeze:
    values[row['date']]=price
    late+=seen.date()>day
  data[a]=values
 common=sorted(set.intersection(*(set(v) for v in data.values())))
 if len(common)<142:raise ValueError('At least 142 common daily observations required')
 if any((dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days!=1 for a,b in zip(common,common[1:])):raise ValueError('Common dates discontinuous')
 return [dict(date=d,prices={a:data[a][d] for a in ASSETS}) for d in common],hashes,late

def study(directory):
 freeze=dt.datetime.fromisoformat(FREEZE);rows,hashes,late=load_rows(directory,freeze)
 # Fixed last 120 sessions, two disjoint 60-session windows, fresh capital each.
 windows={'historical_A':(len(rows)-120,len(rows)-60),'historical_B':(len(rows)-60,len(rows))}
 results={name:[replay(rows,v,start,end) for v in VARIANTS] for name,(start,end) in windows.items()}
 dates={name:dict(first=rows[start]['date'],last=rows[end-1]['date']) for name,(start,end) in windows.items()}
 return dict(version=1,freeze=FREEZE,sourceHashes=hashes,backfilledObservations=late,
  commonDays=len(rows),first=rows[0]['date'],last=rows[-1]['date'],windows=dates,results=results,
  modelSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  costs=dict(feeRate=FEE,spreadRate=SPREAD,slippageRate=SLIPPAGE),
  prospectiveResult=None,automaticPromotion=False,
  limitations=['Retrospective daily model, not an exact replay of the live fictitious engine.',
   'All three strategies use BTC/ETH/SOL only, not the production scanner universe.',
   'Daily sampling misses intraday stops and actual fills; loss limits are not guarantees.',
   'Historical A/B are both retrospective, not an untouched prospective holdout.',
   'Early rebound deliberately changes the trend gate and halves order size; exposure differs.',
   'Buy-and-hold is fully invested and unprotected; a contextual benchmark, not matched risk.',
   'No future conclusion or monthly income extrapolation.'])

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--history-dir',type=Path,required=True)
 print(json.dumps(study(parser.parse_args().history_dir),indent=2,allow_nan=False))
