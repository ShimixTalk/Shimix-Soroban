#!/usr/bin/env python3
"""Historical SHIB/DOGE research. Read-only market data, never live orders."""
import base64,datetime,json,os,time,urllib.parse,urllib.request
REPO=os.environ.get("GITHUB_REPOSITORY","ShimixTalk/Shimix-Soroban")
TOKEN=os.environ["GITHUB_TOKEN"];BRANCH="shimix-hub";PATH="hub/trading/meme-history.json"
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"ShimixTradingResearch/1.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def history(symbol):
 # CryptoCompare histoday public endpoint: 2000 days per request, older pages by toTs.
 now=int(time.time());cursor=now;seen={};errors=[]
 for page in range(3):
  params=urllib.parse.urlencode({"fsym":symbol,"tsym":"USD","limit":2000,"toTs":cursor})
  try:
   data=fetch("https://min-api.cryptocompare.com/data/v2/histoday?"+params)
   if data.get("Response")!="Success":raise RuntimeError(str(data.get("Message","API error")))
   rows=data.get("Data",{}).get("Data",[])
   valid=[r for r in rows if r.get("time") and float(r.get("close") or 0)>0]
   for r in valid:seen[int(r["time"])]=float(r["close"])
   if not rows or not valid:break
   earliest=min(int(r["time"]) for r in rows)
   if earliest<=now-365.25*10*86400:break
   if earliest>=cursor:break
   cursor=earliest-86400
   time.sleep(2)
  except Exception as e:errors.append(str(e));break
 return sorted(seen.items()),errors
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
 return {"status":"ok","start":datetime.datetime.fromtimestamp(start,datetime.timezone.utc).date().isoformat(),"end":datetime.datetime.fromtimestamp(subset[-1][0],datetime.timezone.utc).date().isoformat(),"points":len(subset),"startPriceUSD":p0,"endPriceUSD":p1,"buyHoldPercent":round((p1/p0-1)*100,2),"maxDrawdownPercent":round(maxdd,2),"annualizedVolatilityPercent":round(std*math.sqrt(365)*100,2),"coverageYears":round((subset[-1][0]-start)/86400/365.25,2)}
def main():
 output={"updatedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"CryptoCompare histoday public API","currency":"USD","assets":{},"note":"Étude descriptive historique. Aucune prédiction ni transaction réelle. Couverture réelle indiquée par actif."}
 for sym in ("SHIB","DOGE"):
  series,errors=history(sym)
  output["assets"][sym]={"availableFrom":datetime.datetime.fromtimestamp(series[0][0],datetime.timezone.utc).date().isoformat() if series else None,"points":len(series),"fiveYears":metrics(series,5),"tenYears":metrics(series,10),"errors":errors,"monthly":[{"date":datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),"priceUSD":p} for t,p in series if datetime.datetime.fromtimestamp(t,datetime.timezone.utc).day==1][-125:]}
 # Never replace previous valid data with an empty result due to an API outage.
 url="https://api.github.com/repos/"+REPO+"/contents/"+PATH
 headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
 sha=None
 try:
  old=fetch_authenticated(url+"?ref="+BRANCH,headers);sha=old["sha"]
  previous=json.loads(base64.b64decode(old["content"]))
  for sym in ("SHIB","DOGE"):
   if not output["assets"][sym]["points"] and previous.get("assets",{}).get(sym,{}).get("points"):
    output["assets"][sym]=previous["assets"][sym];output["assets"][sym]["errors"].append("Dernières données conservées : source indisponible")
 except Exception:pass
 payload={"message":"data(trading): refresh long-term SHIB and DOGE research","branch":BRANCH,"content":base64.b64encode((json.dumps(output,ensure_ascii=False,indent=2)+"\n").encode()).decode()}
 if sha:payload["sha"]=sha
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={**headers,"Content-Type":"application/json"},method="PUT")
 with urllib.request.urlopen(req,timeout=45) as r:print("Updated long-term research:",r.status)
def fetch_authenticated(url,headers):
 req=urllib.request.Request(url,headers=headers)
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
if __name__=="__main__":main()
