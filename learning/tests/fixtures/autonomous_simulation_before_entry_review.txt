#!/usr/bin/env python3
"""SHIMIX Trading: simulation only. No broker API or real orders."""
import base64, datetime, json, os, time, urllib.error, urllib.parse, urllib.request, math
API="https://api.coingecko.com/api/v3"
REPO=os.environ.get("GITHUB_REPOSITORY","ShimixTalk/Shimix-Soroban")
BRANCH=os.environ.get("SHIMIX_BRANCH","shimix-hub")
PATH="hub/trading/robot-state.json"
TOKEN=os.environ.get("GITHUB_TOKEN", "")
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
def valid_market_row(x):
    """Reject incomplete, negative or non-finite market data before any simulation decision."""
    if not isinstance(x,dict) or not isinstance(x.get("id"),str) or not x["id"] or not isinstance(x.get("symbol"),str) or not x["symbol"] or not isinstance(x.get("name"),str):return False
    for field in ("current_price","total_volume","market_cap"):
        value=x.get(field)
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0 or value>1e30:return False
    change=x.get("price_change_percentage_24h")
    return change is None or (type(change) in (int,float) and math.isfinite(change))
def validate_simulation_state(state):
    """Fail closed before market access, state mutation or simulated orders."""
    if not isinstance(state,dict) or state.get("realTradingEnabled") is not False or state.get("exchangeApiConnected") is not False:
        raise ValueError("Simulation uniquement")
    readiness=state.get("readiness")
    if not isinstance(readiness,dict) or readiness.get("simulationOnly") is not True or readiness.get("liveOrdersEnabled") is not False:
        raise ValueError("Mode simulation non confirme")
    def number(value,minimum=0,maximum=1e15):
        return type(value) in (int,float) and math.isfinite(value) and minimum<=value<=maximum
    for field in ("capital","cash","maxOrder"):
        if not number(state.get(field)):raise ValueError("Valeur financiere invalide : "+field)
    if state["capital"]<=0:raise ValueError("Capital nul")
    if not number(state.get("maxLossPercent",5),0,100):raise ValueError("Limite de perte invalide")
    if not number(state.get("maxPositionPercent",20),0,100):raise ValueError("Exposition invalide")
    if type(state.get("maxPositions",8)) is not int or not number(state.get("maxPositions",8),1,100):raise ValueError("Nombre de positions invalide")
    for field in ("feeRate","spreadRate","slippageRate"):
        if not number(state.get(field,0.001),0,0.1):raise ValueError("Frais ou glissement invalide : "+field)
    holdings=state.get("holdings")
    if not isinstance(holdings,dict) or len(holdings)>100:raise ValueError("Positions invalides")
    if any(not isinstance(symbol,str) or not symbol or not number(quantity) for symbol,quantity in holdings.items()):
        raise ValueError("Quantite de position invalide")
    for field in ("peak",):
        if field in state and not number(state[field]):raise ValueError("Valeur invalide : "+field)
    for field in ("entryPrices","lastTrade","historyUpdated"):
        values=state.get(field,{})
        if not isinstance(values,dict) or any(not number(v) for v in values.values()):raise ValueError("Historique invalide : "+field)
    history=state.get("dailyHistory",{})
    if not isinstance(history,dict) or any(not isinstance(v,list) or len(v)>10000 or any(not number(x,1e-300) for x in v) for v in history.values()):raise ValueError("Historique de prix invalide")
    for field in ("logs","trades","equityHistory"):
        if not isinstance(state.get(field,[]),list):raise ValueError("Journal invalide : "+field)
    protection=state.get("globalProtection",{})
    if not isinstance(protection,dict):raise ValueError("Protection globale invalide")
    for flag in ("liquidationLatched","requiresApprovalToResume","buyPaused","valuationComplete"):
        if flag in protection and type(protection[flag]) is not bool:raise ValueError("Etat de protection invalide")
    if protection.get("requiresApprovalToResume",False) and not protection.get("liquidationLatched",False):raise ValueError("Reprise non approuvée : état de protection incohérent")
    return True

def market_prices(market, known_ids):
    """Symbols are not unique. Never price a holding using another coin's quote."""
    defaults={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","ADA":"cardano","XRP":"ripple","DOGE":"dogecoin","LINK":"chainlink","AVAX":"avalanche-2","DOT":"polkadot","LTC":"litecoin"}
    for symbol,coin_id in defaults.items():known_ids.setdefault(symbol,coin_id)
    groups={}
    for row in market:
        if valid_market_row(row):groups.setdefault(row["symbol"].upper(),[]).append(row)
    prices={}
    for symbol,rows in groups.items():
        ids={row["id"] for row in rows}
        if len(ids)!=1:continue
        row=rows[0]
        if symbol in known_ids and known_ids[symbol]!=row["id"]:continue
        known_ids[symbol]=row["id"]
        prices[symbol]=float(row["current_price"])
    return prices

def closed_daily_prices(chart, now):
    rows=chart.get("prices") if isinstance(chart,dict) else None
    if not isinstance(rows,list):raise ValueError("Historique absent")
    days={}
    today=int(now.timestamp())//86400
    for row in rows:
        if not isinstance(row,list) or len(row)!=2:raise ValueError("Point invalide")
        stamp,price=row
        if type(stamp) not in (int,float) or not math.isfinite(stamp) or type(price) not in (int,float) or not math.isfinite(price) or price<=0:raise ValueError("Prix historique invalide")
        day=int(stamp/86400000)
        if day<today:days[day]=price
    ordered=sorted(days)
    if len(ordered)<22 or ordered[-1]!=today-1 or any(b-a!=1 for a,b in zip(ordered,ordered[1:])):raise ValueError("Historique incomplet ou périmé")
    return [days[d] for d in ordered][-31:]

def sma(p,n):return sum(p[-n:])/n if len(p)>=n else None
def rsi(p):
    if len(p)<15:return None
    diff=[p[i]-p[i-1] for i in range(len(p)-14,len(p))]
    up=sum(max(0,x) for x in diff);down=sum(max(0,-x) for x in diff)
    return (50 if up==0 else 100) if down==0 else 100-100/(1+up/down)
def usable_quote(prices,symbol):
    price=prices.get(symbol)
    return type(price) in (int,float) and math.isfinite(price) and price>0

def net_liquidation_value(state, prices):
    if any(q>0 and not usable_quote(prices,sym) for sym,q in state["holdings"].items()):return None
    factor=(1-float(state.get("spreadRate",0.001))-float(state.get("slippageRate",0.001)))*(1-float(state.get("feeRate",0.001)))
    return float(state["cash"])+sum(q*prices.get(sym,0)*factor for sym,q in state["holdings"].items())

def global_protection(state, prices, stamp):
    """Fixed 5% entry pause, 10% liquidation latch. Never resets capital or resumes a latch."""
    policy=state.setdefault("globalProtection",{})
    policy.update(version=1,pauseNewBuysAtLossPercent=5,liquidateAtLossPercent=10,
                  referenceCapital=state["capital"],lastCheckedAt=stamp)
    state["maxLossPercent"]=10
    state["buyPauseLossPercent"]=5
    net=net_liquidation_value(state,prices)
    policy["valuationComplete"]=net is not None
    policy["estimatedLiquidationBeforeActions"]=round(net,6) if net is not None else None
    if net is not None and net<=state["capital"]*.90:
        if not policy.get("liquidationLatched",False):
            policy["triggeredAt"]=stamp
            state.setdefault("logs",[]).insert(0,stamp+" : protection globale -10 %, liquidation FICTIVE et reprise sur accord explicite")
        policy["liquidationLatched"]=True
    latched=policy.get("liquidationLatched",False)
    policy["requiresApprovalToResume"]=latched
    policy["buyPaused"]=latched or net is None or net<=state["capital"]*.95
    if latched:
        state["enabled"]=False
        for sym,quantity in list(state["holdings"].items()):
            if quantity<=0 or not usable_quote(prices,sym):continue
            execution=prices[sym]*(1-float(state.get("spreadRate",0.001))-float(state.get("slippageRate",0.001)))
            gross=quantity*execution;fee=gross*float(state.get("feeRate",0.001));proceeds=gross-fee
            state["cash"]+=proceeds
            state["holdings"].pop(sym,None);state.setdefault("entryPrices",{}).pop(sym,None)
            state.setdefault("trades",[]).insert(0,dict(date=stamp,asset=sym,action="Vente",amount=round(proceeds,2),
                price=execution,quantity=quantity,fee=fee,reason="global-loss-liquidation",simulation=True))
            state.setdefault("logs",[]).insert(0,stamp+" : vente FICTIVE "+sym+" (protection globale)")
    policy["pendingAssets"]=sorted(sym for sym,q in state["holdings"].items() if q>0) if latched else []
    return not policy["buyPaused"],latched

def save_protection_state(state, prices, stamp, sha, quote_errors=None):
    missing=[sym for sym,q in state["holdings"].items() if q>0 and not usable_quote(prices,sym)]
    complete=not missing
    state["cash"]=round(state["cash"],6)
    value=state["cash"]+sum(q*prices.get(sym,0) for sym,q in state["holdings"].items()) if complete else None
    state["value"]=round(value,2) if value is not None else None
    state["updatedAt"]=stamp
    state["dataErrors"]=["Prix indisponible, liquidation/valorisation en attente : "+", ".join(missing)] if missing else []
    state["dataErrors"].extend((quote_errors or [])[:19])
    state["globalProtection"]["valuationComplete"]=complete
    state["performance"]={"initialCapital":state["capital"],"equity":state["value"],
        "netPnl":round(value-state["capital"],2) if value is not None else None,
        "returnPercent":round((value/state["capital"]-1)*100,3) if value is not None else None,
        "lastCalculatedAt":stamp,"simulated":True,"totalTrades":len(state.get("trades",[]))}
    state.setdefault("equityHistory",[]).append(dict(at=stamp,equity=state["value"],cash=state["cash"]))
    return save(state,sha)

def price_exits_before_history(state,prices,stamp):
    """Price-only exits need no RSI/history download. Persist before slow analysis."""
    exited=set()
    for sym,quantity in list(state["holdings"].items()):
        if quantity<=0 or not usable_quote(prices,sym):continue
        price=prices[sym];entry=float(state.get("entryPrices",{}).get(sym,price))
        reason="stop-loss" if price<=entry*.96 else "take-profit" if price>=entry*1.08 else None
        if reason is None:continue
        execution=price*(1-float(state.get("spreadRate",0.001))-float(state.get("slippageRate",0.001)))
        gross=quantity*execution;fee=gross*float(state.get("feeRate",0.001));proceeds=gross-fee
        state["cash"]+=proceeds
        state["holdings"].pop(sym,None);state.setdefault("entryPrices",{}).pop(sym,None)
        state.setdefault("trades",[]).insert(0,dict(date=stamp,asset=sym,action="Vente",amount=round(proceeds,2),price=execution,quantity=quantity,fee=fee,reason=reason,simulation=True))
        state.setdefault("logs",[]).insert(0,stamp+" : vente FICTIVE "+sym+" ("+reason+", avant téléchargement historique)")
        exited.add(sym)
    return exited

def supplement_holding_quotes(state,prices,now):
    """Quote held assets by recorded coin ID; the top-100 discovery list is not the portfolio."""
    out=dict(prices);errors=[];needed={}
    known=state.get("assetIds",{})
    if not isinstance(known,dict):known={}
    required=[sym for sym,q in state["holdings"].items() if q>0]
    for sym in required:
        if usable_quote(out,sym):continue
        coin_id=known.get(sym)
        if not isinstance(coin_id,str) or not coin_id or len(coin_id)>200:
            errors.append("Identifiant source absent/invalide pour "+sym);continue
        needed[sym]=coin_id
    evidence={}
    if needed:
        ids=sorted(set(needed.values()))
        url=API+"/coins/markets?"+urllib.parse.urlencode(dict(vs_currency="eur",ids=",".join(ids),per_page=100,page=1,sparkline="false"))
        try:
            rows=request(url)
            if not isinstance(rows,list):raise ValueError("Réponse de cotation invalide")
        except Exception as exc:
            errors.append("Cours complémentaires indisponibles : "+type(exc).__name__);rows=[]
        for sym,coin_id in needed.items():
            matches=[row for row in rows if isinstance(row,dict) and row.get("id")==coin_id]
            if len(matches)!=1:
                errors.append("Cours absent/ambigu pour "+sym);continue
            row=matches[0];price=row.get("current_price")
            if not isinstance(row.get("symbol"),str) or row["symbol"].upper()!=sym.upper() or type(price) not in (int,float) or not math.isfinite(price) or not 0<price<=1e15:
                errors.append("Identité ou cours invalide pour "+sym);continue
            try:
                stamp=datetime.datetime.fromisoformat(row.get("last_updated","").replace("Z","+00:00"))
                if stamp.tzinfo is None:raise ValueError("Fuseau manquant")
                age=now.timestamp()-stamp.timestamp()
                if not -60<=age<=3600:raise ValueError("Cours périmé/futur")
            except (ValueError,TypeError,AttributeError):
                errors.append("Fraîcheur du cours non confirmée pour "+sym);continue
            out[sym]=float(price)
            evidence[sym]=dict(coinId=coin_id,providerUpdatedAt=stamp.isoformat(),fetchedAt=now.isoformat())
    state["holdingQuoteCoverage"]=dict(version=1,checkedAt=now.isoformat(),requiredAssets=required,
        supplementalRequestedIds=sorted(set(needed.values())),supplementalQuotes=evidence,
        missingAssets=[sym for sym in required if not usable_quote(out,sym)])
    return out,errors

def main():
    file=gh("GET");state=json.loads(base64.b64decode(file["content"]).decode())
    validate_simulation_state(state)
    pending=state.get("globalProtection",{}).get("liquidationLatched",False) and any(q>0 for q in state["holdings"].values())
    if not state.get("enabled",False) and not pending:print("Robot désactivé ; reprise sur accord explicite");return
    now=datetime.datetime.now(datetime.timezone.utc);stamp=now.isoformat()
    errors=[];logs=state.setdefault("logs",[]);hist=state.get("dailyHistory",{})
    # Market quotes are reused for at most 15 minutes; schedule timing remains best effort.
    cache=state.get("marketCache",{})
    cache_age=now.timestamp()-float(state.get("marketCacheAt",0))
    try:
        market=cache if isinstance(cache,list) and cache and 0<=cache_age<900 and state.get("globalProtection",{}).get("valuationComplete",True) else request(API+"/coins/markets?vs_currency=eur&order=market_cap_desc&per_page=100&page=1&sparkline=false&price_change_percentage=24h")
        if not isinstance(market,list) or len(market)<30 or sum(valid_market_row(x) for x in market)<20:
            raise ValueError("Données de marché incomplètes ou corrompues : simulation suspendue")
        if market is not cache:
            state["marketCache"]=market
            state["marketCacheAt"]=now.timestamp()
    except Exception as exc:
        state["dataErrors"]=[str(exc)];state["updatedAt"]=stamp
        save(state,file["sha"]);print("Marché indisponible, aucune opération");return
    eligible=[x for x in market if valid_market_row(x) and x["total_volume"]>=2000000 and x["market_cap"]>=50000000]
    ranked=sorted(eligible,key=lambda x:(__import__("math").log10(max(1,float(x.get("total_volume") or 1)))*2+min(12,abs(float(x.get("price_change_percentage_24h") or 0)))*0.6),reverse=True)
    selected=ranked[:20];prices={}
    # Never reuse stale quotes from previous runs for valuation or orders.
    prices=market_prices(market,state.setdefault("assetIds",{}))
    selected=[x for x in selected if x["symbol"].upper() in prices]
    prices,holding_quote_errors=supplement_holding_quotes(state,prices,now)
    errors.extend(holding_quote_errors)
    state["prices"]=prices
    buys_allowed,liquidation_latched=global_protection(state,prices,stamp)
    if liquidation_latched or not state["globalProtection"]["valuationComplete"]:
        save_protection_state(state,prices,stamp,file["sha"],holding_quote_errors)
        print("Protection globale",state["globalProtection"])
        return
    exited_before_analysis=price_exits_before_history(state,prices,stamp)
    if exited_before_analysis:
        # Do not relabel previous-run signals as decisions at this new execution time.
        state["signals"]={}
        new_sha=save_protection_state(state,prices,stamp,file["sha"])
        if not isinstance(new_sha,str) or not new_sha:raise ValueError("Checkpoint des sorties non confirmé : analyse interrompue")
        file["sha"]=new_sha
    state["scanner"]={"updatedAt":stamp,"examined":len(market),"eligible":len(eligible),"shortlist":[{"symbol":x["symbol"].upper(),"name":x["name"],"volume":x.get("total_volume"),"change24h":x.get("price_change_percentage_24h")} for x in selected]}
    # Two historical requests per execution to limit rate limiting.
    due=[x for x in selected if len(hist.get(x["id"],[]))<22 or (now.timestamp()-float(state.get("historyUpdated",{}).get(x["id"],0)))>86400]
    for x in due[:2]:
        try:
            chart=request(API+"/coins/"+urllib.parse.quote(x["id"])+"/market_chart?vs_currency=eur&days=30&interval=daily")
            series=closed_daily_prices(chart,now)
            if len(series)>=22:
                hist[x["id"]]=series[-31:];state.setdefault("historyUpdated",{})[x["id"]]=now.timestamp()
        except Exception as exc:errors.append(x["symbol"]+": "+str(exc))
        time.sleep(2)
    state["dailyHistory"]=hist
    signals={};candidates=[]
    for x in selected:
        p=hist.get(x["id"],[]);sym=x["symbol"].upper()
        age=now.timestamp()-float(state.get("historyUpdated",{}).get(x["id"],0))
        if len(p)<22 or not 0<=age<86400:
            signals[sym]={"action":"Attente","reason":"Historique insuffisant"};continue
        rs=rsi(p);a=sma(p,7);b=sma(p,21);prev=sma(p[:-1],21)
        action=("Achat" if (rs<35 and a>b and p[-1]>prev) or (state.get("experimentMode")=="aggressive_simulation" and rs<45 and p[-1]>p[-2] and a>=b*0.97) else "Vente" if rs>65 and a<b else "Attente")
        signals[sym]={"action":action,"rsi":round(rs,2),"sma7":a,"sma21":b,"reason":"RSI et moyennes mobiles"}
        if action=="Achat":candidates.append((45-rs,sym))
    state["signals"]=signals
    holdings=state.setdefault("holdings",{});cash=float(state.get("cash",1600));capital=float(state.get("capital",1600))
    # Never value an existing holding at zero when its quote is unavailable.
    missing=[sym for sym,q in holdings.items() if float(q)>0 and float(prices.get(sym,0))<=0]
    if missing:
        state["dataErrors"]=["Prix indisponible: "+", ".join(missing)]
        state["updatedAt"]=stamp
        save(state,file["sha"])
        print("Simulation paused: missing holdings prices",missing)
        return
    value=cash+sum(float(q)*float(prices.get(sym,0)) for sym,q in holdings.items())
    state["peak"]=max(float(state.get("peak",capital)),value)
    state["value"]=round(value,2)
    # Simulated exits: take-profit, stop-loss and bearish signal.
    # Exit management continues while the 5% entry pause is active.
    entries=state.setdefault("entryPrices",{})
    for sym,quantity in list(holdings.items()):
        price=float(prices.get(sym,0));quantity=float(quantity)
        if quantity<=0 or price<=0:continue
        entry=float(entries.get(sym,price))
        reason=("stop-loss" if price<=entry*0.96 else
                "take-profit" if price>=entry*1.08 else
                "signal" if signals.get(sym,{}).get("action")=="Vente" else None)
        if not reason:continue
        exit_price=price*(1-float(state.get("spreadRate",0.001))-float(state.get("slippageRate",0.001)))
        gross=quantity*exit_price
        fee=gross*float(state.get("feeRate",0.001))
        proceeds=gross-fee
        cash+=proceeds
        holdings.pop(sym,None);entries.pop(sym,None)
        state.setdefault("trades",[]).insert(0,{"date":stamp,"asset":sym,"action":"Vente","amount":round(proceeds,2),"price":exit_price,"quantity":quantity,"fee":fee,"reason":reason,"simulation":True})
        logs.insert(0,stamp+" : vente FICTIVE "+sym+" ("+reason+")")
    last=state.setdefault("lastTrade",{})
    if not buys_allowed:
        for sym in [sym for _,sym in candidates]:signals[sym]["reason"]="Achats suspendus par la protection globale -5 % ; positions toujours gérées"
    for _,sym in sorted(candidates if buys_allowed else [],reverse=True):
        if sym in exited_before_analysis:continue  # Never immediately rebuy an early risk exit.
        if len(state.get("trades",[]))>=1000:break
        if len(holdings)>=int(state.get("maxPositions",8)):break
        if now.timestamp()-float(last.get(sym,0))<86400:continue
        price=float(prices.get(sym,0))
        if price<=0:continue
        amount=min(float(state.get("maxOrder",40)),cash,capital*float(state.get("maxPositionPercent",20))/100-float(holdings.get(sym,0))*price)
        if amount<1:continue
        # 0.1% fee, spread and slippage modeled conservatively.
        effective=price*(1+float(state.get("spreadRate",0.001))+float(state.get("slippageRate",0.001)))
        fee=amount*float(state.get("feeRate",0.001))
        qty=(amount-fee)/effective
        exit_factor=(1-float(state.get("spreadRate",0.001))-float(state.get("slippageRate",0.001)))*(1-float(state.get("feeRate",0.001)))
        projected=cash-amount+(sum(q*prices.get(a,0) for a,q in holdings.items())+qty*price)*exit_factor
        if projected<=capital*.95:
            state["globalProtection"]["buyPaused"]=True
            signals[sym]["reason"]="Achat refusé : les coûts franchiraient le seuil global -5 %"
            break
        cash-=amount;holdings[sym]=float(holdings.get(sym,0))+qty
        last[sym]=now.timestamp()
        entries[sym]=((float(entries.get(sym,0))*float(holdings[sym]-qty))+amount)/float(holdings[sym])
        state.setdefault("trades",[]).insert(0,{"date":stamp,"asset":sym,"action":"Achat","amount":round(amount,2),"price":effective,"quantity":qty,"fee":fee,"simulation":True})
        logs.insert(0,stamp+" : achat FICTIF "+sym+" pour "+str(round(amount,2))+" EUR")
        # Only one simulated buy per run; evaluate further next time.
        break
    state["value"]=round(cash+sum(float(q)*float(prices.get(sym,0)) for sym,q in holdings.items()),2)
    state["performance"]={"initialCapital":capital,"equity":state["value"],"netPnl":round(state["value"]-capital,2),"returnPercent":round((state["value"]/capital-1)*100,3) if capital else 0,"drawdownPercent":round((1-state["value"]/max(state["peak"],0.01))*100,3),"totalTrades":len(state.get("trades",[])),"lastCalculatedAt":stamp,"simulated":True}
    snapshots=state.setdefault("equityHistory",[])
    snapshots.append({"at":stamp,"equity":state["value"],"cash":round(cash,2)})
    state["equityHistory"]=snapshots
    state["cash"]=round(cash,6);state["logs"]=logs;state["trades"]=state.get("trades",[])
    state["dataErrors"]=errors[:20];state["updatedAt"]=stamp
    state["realTradingEnabled"]=False;state["exchangeApiConnected"]=False
    state.setdefault("readiness",{})["simulationOnly"]=True;state["readiness"]["liveOrdersEnabled"]=False
    save(state,file["sha"]);print("Scan",len(market),"présélection",len(selected),"achats simulés",len(state["trades"]))
def save(state,sha):
    validate_simulation_state(state)
    data=base64.b64encode((json.dumps(state,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode()).decode()
    result=gh("PUT",{"message":"chore(trading): update autonomous simulation state","content":data,"sha":sha,"branch":BRANCH})
    new_sha=result.get("content",{}).get("sha") if isinstance(result,dict) else None
    if not isinstance(new_sha,str) or not new_sha:raise ValueError("GitHub ne confirme pas le SHA du nouvel état")
    return new_sha
if __name__=="__main__":main()
