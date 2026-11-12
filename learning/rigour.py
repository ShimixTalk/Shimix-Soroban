"""Read-only performance checks. Never selects parameters or sends orders."""
from engine import finite
from journal import timestamp


def review(events, generated_at):
    """Estimate liquidation at the last observed quotes, never at a future price."""
    rows = [e for e in events if e.get('source') == 'robot-state.json']
    if not rows:
        return dict(status='no_observations', evidence='insufficient', issues=['no_observations'])
    rows = sorted(rows, key=lambda e: timestamp(e['at']))
    latest = rows[-1]
    issues = []
    cash, capital = latest.get('cash'), latest.get('capital')
    holdings, prices = latest.get('holdings', {}), latest.get('prices', {})
    valid = finite(cash) and finite(capital, 1e-12) and isinstance(holdings, dict) and isinstance(prices, dict)
    if not valid:
        issues.append('invalid_accounting')
    positions = {}
    if valid:
        for asset, quantity in holdings.items():
            if not finite(quantity) or (quantity > 0 and not finite(prices.get(asset), 1e-12)):
                issues.append('missing_or_invalid_holding_quote');valid = False;break
            if quantity > 0:
                positions[asset] = quantity * prices[asset]
    exposure = sum(positions.values()) if valid else None
    equity = cash + exposure if valid else None
    if equity is not None and finite(latest.get('equity')) and abs(equity-latest['equity']) > .02:
        issues.append('equity_mismatch');valid = False
    cache = latest.get('quotesFetchedAt')
    quote_age = timestamp(latest['at']).timestamp()-cache if finite(cache) else None
    source_age = (timestamp(generated_at)-timestamp(latest['at'])).total_seconds()
    if quote_age is None or not 0 <= quote_age <= 3600:
        issues.append('stale_or_unknown_execution_quotes')
    if source_age > 3600 or source_age < -60:
        issues.append('old_or_future_source')
    risk = latest.get('riskSnapshot', {})
    rates = [risk.get(k) for k in ('feeRate', 'spreadRate', 'slippageRate')]
    costs_valid = all(finite(v, 0, 1) for v in rates) and rates[1]+rates[2] < 1 and rates[0] < 1
    if exposure and not costs_valid:
        issues.append('unknown_or_invalid_exit_costs')
    critical = {'invalid_accounting', 'missing_or_invalid_holding_quote', 'equity_mismatch',
                'stale_or_unknown_execution_quotes', 'unknown_or_invalid_exit_costs'}
    liquidation = None
    if valid and not critical.intersection(issues):
        liquidation = cash if not exposure else cash+exposure*(1-rates[1]-rates[2])*(1-rates[0])
    trades = {}
    for row in rows:
        for trade in row.get('trades', []):
            trades.setdefault(trade['id'], trade)
    buys = sum(t.get('action') == 'Achat' for t in trades.values())
    sells = sum(t.get('action') == 'Vente' for t in trades.values())
    missing_fees = sum(not finite(t.get('fee')) for t in trades.values())
    if missing_fees:
        issues.append('incomplete_historical_fees')
    if any(t.get('reason') in (None, '', 'Non enregistrée') for t in trades.values()):
        issues.append('undocumented_trade_reasons')
    peak = None;max_drawdown = 0.;valued_samples = 0
    for row in rows:
        value = row.get('equity')
        if not finite(value, 1e-12):
            continue
        peak = max(peak or value, value)
        max_drawdown = max(max_drawdown, 1-value/peak);valued_samples += 1
    rounded = lambda v: round(v, 6) if v is not None else None
    return dict(status='checked' if not issues else 'needs_review', evidence='insufficient',
        asOf=latest['at'], sourceCommit=latest.get('sourceCommit'),
        quoteAgeAtExecutionSeconds=quote_age, sourceAgeAtReportSeconds=source_age,
        capital=capital, markedEquity=rounded(equity),
        markedChangeFromReference=rounded(equity-capital) if equity is not None else None,
        exposureEUR=rounded(exposure), exposurePercent=rounded(100*exposure/equity) if equity and exposure is not None else None,
        estimatedExitCosts=rounded(equity-liquidation) if liquidation is not None else None,
        estimatedLiquidationEquity=rounded(liquidation),
        estimatedLiquidationChangeFromReference=rounded(liquidation-capital) if liquidation is not None else None,
        estimatedLiquidationReturnPercent=rounded(100*(liquidation/capital-1)) if liquidation is not None else None,
        knownPaidFees=round(sum(t['fee'] for t in trades.values() if finite(t.get('fee'))),6),
        missingHistoricalFees=missing_fees, observedBuys=buys, observedSales=sells,
        recentDecisions=[dict(at=t.get('at'),asset=t.get('asset'),action=t.get('action'),reason=t.get('reason') or 'Non enregistrée',context=t.get('decision')) for t in sorted(trades.values(),key=lambda t:(t.get('at',''),t['id']))[-10:]],
        observations=len(rows), valuedSamples=valued_samples,
        observationDays=round((timestamp(latest['at'])-timestamp(rows[0]['at'])).total_seconds()/86400,6),
        observedMaxDrawdownPercent=rounded(100*max_drawdown) if valued_samples>=2 else None,
        riskSnapshot=risk, issues=issues,
        limitations=[
            'Estimation aux cours du relevé, pas un prix de vente garanti ; avant impôts.',
            'Les coûts de sortie sont déduits une fois ; les coûts d’achat sont déjà dans les soldes et quantités.',
            'Variation par rapport à la référence : les flux non journalisés ne peuvent pas être attribués au trading.',
            'Baisse maximale limitée aux relevés observés ; les mouvements entre relevés sont inconnus.',
            'Aucune rentabilité durable démontrée et aucune prévision mensuelle.',
            'Aucune stratégie ni limite de risque modifiée automatiquement.'])
