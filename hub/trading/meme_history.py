#!/usr/bin/env python3
"""Historical SHIB/DOGE/BTC research. Read-only market data, never live orders."""
import base64,datetime,json,os,time,urllib.parse,urllib.request,math
REPO=os.environ.get("GITHUB_REPOSITORY","ShimixTalk/Shimix-Soroban")
TOKEN=os.environ["GITHUB_TOKEN"];BRANCH="shimix-hub";PATH="hub/trading/meme-history.json"
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"ShimixTradingResearch/1.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def history(symbol):
 # Public spot-market daily candles, no API key or account. Binance listing
 # dates limit the coverage: we NEVER pretend a complete 10-year history.
 # Fallback domains avoid dependence on a single API host.
 start=int(datetime.datetime(2015,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
 end=int(time.time()*1000)
 errors=[]
 for host in ("https://data-api.binance.vision","https://api.binance.com","https://api.binance.us"):
  seen={};cursor=start
  try:
   for page in range(6):
    params=urllib.parse.urlencode({"symbol":symbol+"USDT","interval":"1d","startTime":cursor,"endTime":end,"limit":1000})
    rows=fetch(host+"/api/v3/klines?"+params)
    if not isinstance(rows,list):raise ValueError("Format inattendu")
    if not rows:break
    for row in rows:
     stamp=int(row[0])//1000;price=float(row[4])
     if math.isfinite(price) and price>0 and stamp>=0 and stamp+86400<=int(time.time()):seen[stamp]=price
    next_cursor=int(rows[-1][0])+86400000
    if next_cursor<=cursor:break
    cursor=next_cursor
    if len(rows)<1000 or cursor>end:break
    time.sleep(.3)
   if len(seen)>=30:return sorted(seen.items()),[]
   errors.append(host+": historique insuffisant ("+str(len(seen))+" jours)")
  except Exception as exc:
   errors.append(host+": "+str(exc)[:150])
 return [],errors
def metrics(series,years):
 if not series:return {"status":"indisponible"}
 end=series[-1][0];cutoff=end-int(years*365.25*86400)
 subset=[(t,p) for t,p in series if t>=cutoff]
 if len(subset)<30:return {"status":"insuffisant","points":len(subset)}
 start,p0=subset[0];p1=subset[-1][1];peak=p0;maxdd=0
 for _,p in subset:
  peak=max(peak,p);maxdd=min(maxdd,(p/peak-1)*100)
 returns=[subset[i][1]/subset[i-1][1]-1 for i in range(1,len(subset)) if subset[i-1][1]>0]
 import math
 mean=sum(returns)/len(returns) if returns else 0
 std=math.sqrt(sum((v-mean)**2 for v in returns)/len(returns)) if returns else 0
 return {"status":"ok" if (end-start)>=int((years-0.15)*365.25*86400) else "partiel","start":datetime.datetime.fromtimestamp(start,datetime.timezone.utc).date().isoformat(),"end":datetime.datetime.fromtimestamp(subset[-1][0],datetime.timezone.utc).date().isoformat(),"points":len(subset),"startPriceUSDT":p0,"endPriceUSDT":p1,"buyHoldPercent":round((p1/p0-1)*100,2),"maxDrawdownPercent":round(maxdd,2),"annualizedVolatilityPercent":round(std*math.sqrt(365)*100,2),"coverageYears":round((subset[-1][0]-start)/86400/365.25,2)}
def backtest(series,years):
 """Fictitious long-only strategies, prior-day signals, trading costs."""
 if len(series)<130:return {"status":"insuffisant"}
 end=series[-1][0];target=end-int(years*365.25*86400)
 start=next((i for i,(t,p) in enumerate(series) if t>=target),None)
 if start is None or start<101:return {"status":"insuffisant"}
 fee=.001;slippage=.001;methods={}
 for method in ("buy_hold","sma20_100","momentum30"):
  cash=1000.;units=0.;peak=1000.;worst=0.;orders=0
  for i in range(start,len(series)):
   price=series[i][1];past=[p for _,p in series]
   if method=="buy_hold":buy=True
   elif method=="sma20_100":buy=sum(past[i-20:i])/20>sum(past[i-100:i])/100
   else:buy=past[i-1]>past[i-31]
   if buy and cash>0:
    units=cash/(price*(1+fee+slippage));cash=0;orders+=1
   elif not buy and units>0:
    cash=units*price*(1-fee-slippage);units=0;orders+=1
   equity=cash+units*price;peak=max(peak,equity);worst=min(worst,(equity/peak-1)*100)
  final=cash+units*series[-1][1]
  methods[method]={"returnPercent":round((final/1000-1)*100,2),"maxDrawdownPercent":round(worst,2),"orders":orders}
 return {"status":"ok","start":datetime.datetime.fromtimestamp(series[start][0],datetime.timezone.utc).date().isoformat(),"end":datetime.datetime.fromtimestamp(end,datetime.timezone.utc).date().isoformat(),"methods":methods,"feePercent":0.1,"slippagePercent":0.1,"warning":"Simulation indicative au cours de clôture, signaux sur données antérieures. Aucun ordre réel."}
def main():
 output={"updatedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"Binance public spot daily candles (USDT)","currency":"USDT","assets":{},"note":"Étude descriptive historique. Aucune prédiction ni transaction réelle. Couverture réelle indiquée par actif."}
 for sym in ("SHIB","DOGE","BTC"):
  series,errors=history(sym)
  output["assets"][sym]={"availableFrom":datetime.datetime.fromtimestamp(series[0][0],datetime.timezone.utc).date().isoformat() if series else None,"points":len(series),"fiveYears":metrics(series,5),"tenYears":metrics(series,10),"backtests":{"fiveYears":backtest(series,5),"tenYears":backtest(series,10)},"errors":errors,"monthly":[{"date":datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),"priceUSD":p} for t,p in series if datetime.datetime.fromtimestamp(t,datetime.timezone.utc).day==1][-125:]}
 # Never replace previous valid data with an empty result due to an API outage.
 url="https://api.github.com/repos/"+REPO+"/contents/"+PATH
 headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
 sha=None
 try:
  old=fetch_authenticated(url+"?ref="+BRANCH,headers);sha=old["sha"]
  previous=json.loads(base64.b64decode(old["content"]))
  for sym in ("SHIB","DOGE","BTC"):
   if not output["assets"][sym]["points"] and previous.get("assets",{}).get(sym,{}).get("points"):
    output["assets"][sym]=previous["assets"][sym];output["assets"][sym]["errors"].append("Dernières données conservées : source indisponible")
 except Exception:pass
 payload={"message":"data(trading): refresh long-term SHIB DOGE BTC research (closed candles)","branch":BRANCH,"content":base64.b64encode((json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode()).decode()}
 if sha:payload["sha"]=sha
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={**headers,"Content-Type":"application/json"},method="PUT")
 with urllib.request.urlopen(req,timeout=45) as r:print("Updated long-term research:",r.status)
def fetch_authenticated(url,headers):
 req=urllib.request.Request(url,headers=headers)
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
if __name__=="__main__":main()
