#!/usr/bin/env python3
"""SHIMIX Trading: simulation only. No broker API or real orders."""
import base64, datetime, json, os, time, urllib.error, urllib.parse, urllib.request
API="https://api.coingecko.com/api/v3"
REPO=os.environ.get("GITHUB_REPOSITORY","ShimixTalk/Shimix-Soroban")
BRANCH=os.environ.get("SHIMIX_BRANCH","shimix-hub")
PATH="hub/trading/robot-state.json"
TOKEN=os.environ["GITHUB_TOKEN"]
def request(url,headers=None):
    req=urllib.request.Request(url,headers={"User-Agent":"ShimixTradingSimulation/1.0",**(headers or {})})
    with urllib.request.urlopen(req,timeout=35) as res:return json.load(res)
def gh(method,body=None):
    url="https://api.github.com/repos/"+REPO+"/contents/"+PATH+"?ref="+BRANCH if method=="GET" else "https://api.github.com/repos/"+REPO+"/contents/"+PATH
    h={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    if method=="PUT":
        req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={**h,"Content-Type":"application/json"},method="PUT")
        with urllib.request.urlopen(req,timeout=35) as res:return json.load(res)
    return request(url,h)
def sma(p,n):return sum(p[-n:])/n if len(p)>=n else None
def rsi(p):
    if len(p)<15:return None
    diff=[p[i]-p[i-1] for i in range(len(p)-14,len(p))]
    up=sum(max(0,x) for x in diff);down=sum(max(0,-x) for x in diff)
    return 100 if down==0 else 100-100/(1+up/down)
def main():
    file=gh("GET");state=json.loads(base64.b64decode(file["content"]).decode())
    if not state.get("enabled",False):print("Robot désactivé");return
    if state.get("realTradingEnabled") or state.get("exchangeApiConnected"):raise RuntimeError("Simulation uniquement : accès réel refusé")
    now=datetime.datetime.now(datetime.timezone.utc);stamp=now.isoformat()
    errors=[];logs=state.get("logs",[]);hist=state.get("dailyHistory",{})
    try:
        market=request(API+"/coins/markets?vs_currency=eur&order=market_cap_desc&per_page=100&page=1&sparkline=false&price_change_percentage=24h")
    except Exception as exc:
        state["dataErrors"]=[str(exc)];state["updatedAt"]=stamp
        save(state,file["sha"]);print("Marché indisponible, aucune opération");return
    eligible=[x for x in market if x.get("id") and x.get("symbol") and float(x.get("total_volume") or 0)>=2000000 and float(x.get("market_cap") or 0)>=50000000 and float(x.get("current_price") or 0)>0]
    ranked=sorted(eligible,key=lambda x:(__import__("math").log10(max(1,float(x.get("total_volume") or 1)))*2+min(12,abs(float(x.get("price_change_percentage_24h") or 0)))*0.6),reverse=True)
    selected=ranked[:20];prices=state.setdefault("prices",{})
    for x in market:
        if x.get("symbol") and x.get("current_price"):prices[x["symbol"].upper()]=float(x["current_price"])
    state["scanner"]={"updatedAt":stamp,"examined":len(market),"eligible":len(eligible),"shortlist":[{"symbol":x["symbol"].upper(),"name":x["name"],"volume":x.get("total_volume"),"change24h":x.get("price_change_percentage_24h")} for x in selected]}
    # Two historical requests per execution to limit rate limiting.
    due=[x for x in selected if len(hist.get(x["id"],[]))<22 or (now.timestamp()-float(state.get("historyUpdated",{}).get(x["id"],0)))>86400]
    for x in due[:2]:
        try:
            chart=request(API+"/coins/"+urllib.parse.quote(x["id"])+"/market_chart?vs_currency=eur&days=30&interval=daily")
            series=[float(a[1]) for a in chart.get("prices",[]) if float(a[1])>0]
            if len(series)>=22:
                hist[x["id"]]=series[-31:];state.setdefault("historyUpdated",{})[x["id"]]=now.timestamp()
        except Exception as exc:errors.append(x["symbol"]+": "+str(exc))
        time.sleep(2)
    state["dailyHistory"]=hist
    signals={};candidates=[]
    for x in selected:
        p=hist.get(x["id"],[]);sym=x["symbol"].upper()
        if len(p)<22:
            signals[sym]={"action":"Attente","reason":"Historique insuffisant"};continue
        rs=rsi(p);a=sma(p,7);b=sma(p,21);prev=sma(p[:-1],21)
        action="Achat" if rs<35 and a>b and p[-1]>prev else "Vente" if rs>65 and a<b else "Attente"
        signals[sym]={"action":action,"rsi":round(rs,2),"sma7":a,"sma21":b,"reason":"RSI et moyennes mobiles"}
        if action=="Achat":candidates.append((35-rs,sym))
    state["signals"]=signals
    holdings=state.setdefault("holdings",{});cash=float(state.get("cash",1600));capital=float(state.get("capital",1600))
    value=cash+sum(float(q)*float(prices.get(sym,0)) for sym,q in holdings.items())
    state["peak"]=max(float(state.get("peak",capital)),value)
    state["value"]=round(value,2)
    loss=float(state.get("maxLossPercent",5))
    if value<=capital*(1-loss/100):
        state["enabled"]=False;logs.insert(0,stamp+" : arrêt de sécurité, perte maximale atteinte (positions non liquidées)")
    else:
        last=state.setdefault("lastTrade",{})
        for _,sym in sorted(candidates,reverse=True):
            if len(state.get("trades",[]))>=1000:break
            if now.timestamp()-float(last.get(sym,0))<86400:continue
            price=float(prices.get(sym,0))
            if price<=0:continue
            amount=min(float(state.get("maxOrder",40)),cash,capital*0.30-float(holdings.get(sym,0))*price)
            if amount<1:continue
            # 0.1% fee, spread and slippage modeled conservatively.
            effective=price*(1+float(state.get("spreadRate",0.001))+float(state.get("slippageRate",0.001)))
            fee=amount*float(state.get("feeRate",0.001))
            qty=(amount-fee)/effective
            cash-=amount;holdings[sym]=float(holdings.get(sym,0))+qty
            last[sym]=now.timestamp()
            state.setdefault("trades",[]).insert(0,{"date":stamp,"asset":sym,"action":"Achat","amount":round(amount,2),"price":effective,"quantity":qty,"fee":fee,"simulation":True})
            logs.insert(0,stamp+" : achat FICTIF "+sym+" pour "+str(round(amount,2))+" EUR")
            # Only one simulated buy per run; evaluate further next time.
            break
    state["cash"]=round(cash,6);state["logs"]=logs[:100];state["trades"]=state.get("trades",[])[:1000]
    state["dataErrors"]=errors[:20];state["updatedAt"]=stamp
    state["realTradingEnabled"]=False;state["exchangeApiConnected"]=False
    state.setdefault("readiness",{})["simulationOnly"]=True;state["readiness"]["liveOrdersEnabled"]=False
    save(state,file["sha"]);print("Scan",len(market),"présélection",len(selected),"achats simulés",len(state["trades"]))
def save(state,sha):
    data=base64.b64encode((json.dumps(state,ensure_ascii=False,indent=2)+"\n").encode()).decode()
    gh("PUT",{"message":"chore(trading): update autonomous simulation state","content":data,"sha":sha,"branch":BRANCH})
if __name__=="__main__":main()
