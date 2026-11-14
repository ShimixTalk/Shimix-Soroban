"""Descriptive evidence, never a trained strategy or an automatic promotion rule."""
import math


def outcome_quality(steps,unknown,fees_complete):
    pnls=[step['netRealizedPnl'] for step in steps]
    count=len(pnls);wins=sum(p>0 for p in pnls);losses=sum(p<0 for p in pnls)
    interval=None
    if count:
        p=wins/count;z=1.959963984540054;den=1+z*z/count
        center=(p+z*z/(2*count))/den
        radius=z*math.sqrt(p*(1-p)/count+z*z/(4*count*count))/den
        interval=[round(max(0,center-radius)*100,6),round(min(1,center+radius)*100,6)]
    positive=sum(p for p in pnls if p>0);negative=-sum(p for p in pnls if p<0)
    return dict(knownSaleOutcomes=count,knownWinningSales=wins,knownLosingSales=losses,
                knownBreakevenSales=count-wins-losses,
                knownSalesWinRatePercent=round(100*wins/count,6) if count else None,
                indicativeWilson95Percent=interval,
                meanKnownPnlPerSale=round(sum(pnls)/count,6) if count else None,
                knownProfitFactor=round(positive/negative,6) if negative else None,
                unattributableTrades=unknown,feeCoverageComplete=fees_complete,
                evidence='insufficient_for_automatic_promotion',automaticPromotion=False,
                limitations=[
                    'Statistiques sur ventes attribuables seulement ; les positions ouvertes ne sont pas des succès.',
                    'Ventes partielles ou corrélées ne sont pas des observations indépendantes. L’intervalle binomial est indicatif, pas une probabilité de gain future.',
                    'Historique incomplet ou frais manquants : ce sous-échantillon peut être biaisé.',
                    'Un taux de réussite élevé ne suffit pas : comparer montant net des gains, pertes, frais, exposition et référence.',
                    'Ces statistiques ne changent ni les paramètres, ni la stratégie, ni les limites de risque.'])
