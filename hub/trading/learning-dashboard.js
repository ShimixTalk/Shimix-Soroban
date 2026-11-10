/* Read-only learning dashboard. No keys, API calls to an AI, trading changes or automatic merges. */
(function(){
'use strict';
const panel=document.getElementById('robotLearningPanel');if(!panel)return;
const content=panel.querySelector('[data-learning-content]'),status=panel.querySelector('[data-learning-status]');
const bases=['https://raw.githubusercontent.com/ShimixTalk/Shimix-Soroban/shimix-hub/hub/trading/learning-data/','./learning-data/'];
const names={prudent:'Prudente',equilibre:'Équilibrée',dynamique:'Dynamique'};
const number=x=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('fr-FR',{maximumFractionDigits:3}):'Non calculable';
function element(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);return e;}
function table(headers,rows){const wrap=element('div');wrap.className='scroll';const t=element('table'),head=element('tr');for(const h of headers)head.append(element('th',h));t.append(head);for(const values of rows){const row=element('tr');for(const v of values)row.append(element('td',v));t.append(row);}wrap.append(t);return wrap;}
async function read(filename){let last;for(const base of bases){try{const r=await fetch(base+filename+'?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return await r.json();}catch(e){last=e;}}throw last;}
function render(report){
 if(report?.version!==1||report.mode!=='shadow_simulation_only'||report.referenceCapitalEUR!==1600||report.appliedToRobot!==false)throw Error('Rapport non confirmé en observation fictive.');
 content.replaceChildren();const obs=report.observed||{};
 if(report.preview)content.append(element('p','Prévisualisation : la collecte planifiée n’est pas encore activée.'));
 content.append(element('p','Capital de référence conservé : 1 600 € fictifs. Cette analyse n’ajoute ni ne retire aucun montant aux portefeuilles.'));
 content.append(element('p',number(obs.observations)+' observations · '+number(obs.decisions)+' signaux enregistrés · '+number(obs.uniqueTrades)+' opérations distinctes · frais connus : '+number(obs.knownFees)+' €.'));
 if(obs.latest){content.append(element('p','Valeur observée : '+number(obs.latest.equity)+' € · résultat par rapport à 1 600 € : '+number(typeof obs.latest.equity==='number'?obs.latest.equity-1600:null)+' € · seuil de perte enregistré : '+number(obs.latest.riskSnapshot?.maxLossPercent)+' % (inchangé).'));}
 content.append(element('h3','Performances publiées des trois simulations'));
 const actual=Array.isArray(report.observedPortfolios)?report.observedPortfolios.slice(0,3):[];
 content.append(table(['Profil','Capital initial fictif','Valeur publiée','Résultat publié','Frais publiés'],actual.map(p=>[names[p.id]||String(p.name),number(p.initial)+' €',number(p.value)+' €',number(p.netProfit)+' €',number(p.feesPaid)+' €'])));
 content.append(element('p','Le robot principal et les trois profils sont des simulations indépendantes : leurs capitaux ne s’additionnent pas.'));
 for(const p of report.profileJournal||[])content.append(element('p',(names[p.id]||p.id)+' : '+number(p.observations)+' observations, '+number(p.decisions)+' signaux et '+number(p.uniqueTrades)+' opérations conservées dans le journal.'));
 content.append(element('h3','Hypothèses et tests chronologiques'));
 content.append(element('p','Référence de recherche : filtre momentum 14 jours et moyennes 7/21, avec les risques fixes de chaque profil. Ce n’est pas une reproduction exacte des moteurs actuellement exécutés.'));
 const rows=[];
 for(const [id,label] of Object.entries(names)){
  const h=report.hypotheses?.[id];if(!h||h.status==='insufficient_data'){rows.push([label,'Données insuffisantes',String(h?.points||0)+' / '+String(h?.required||120)+' jours','—','—','—']);continue;}
  content.append(element('p',label+' : '+(h.status==='frozen_hypothesis'?'Hypothèse à suivre':'Amélioration non confirmée')+' · '+String(h.parameterTrials)+' variantes testées · sélection sur apprentissage seulement.'));
  for(const [key,phase] of [['train','Apprentissage'],['validation','Validation'],['test','Test final']]){const f=h.folds?.[key];if(f)rows.push([label,phase,f.start+' → '+f.end,number(f.baseline?.netReturnPercent)+' %',number(f.candidate?.netReturnPercent)+' %',number(f.candidate?.maxDrawdownPercent)+' %']);}
  const selection=report.shadowSelections?.[id];content.append(element('p','Sélection en observation : '+(selection?.selection==='candidate'?'candidat proposé à la revue humaine':'référence conservée, preuves supplémentaires attendues')+'. Aucun changement appliqué au robot.'));
  const forward=report.forward?.[id];content.append(element('p',label+' · nouvelles données après gel : '+(forward?.status==='forward_observation'?number(forward.points)+' jours ; candidat '+number(forward.candidate?.netReturnPercent)+' %, référence '+number(forward.baseline?.netReturnPercent)+' %.':number(forward?.points||0)+' jour(s), pas encore assez pour conclure.')));
 }
 content.append(table(['Profil','Période','Dates / couverture','Référence nette','Candidat net','Baisse maximale candidat'],rows));
 content.append(element('p','Tests de recherche séparés des résultats publiés : frais, spread, glissement et sortie finale fictive inclus ; hors fiscalité. Le test final ne choisit pas les paramètres. Aucune stratégie n’est appliquée automatiquement au robot.'));
 content.append(element('h3','Pourquoi des gains ou des pertes ?'));
 content.append(element('p','Résultat réalisé attribuable à des achats connus : '+number(obs.knownRealizedPnl)+' €. Opérations non attribuables : '+number(obs.unattributableTrades)+'. Les coûts d’acquisition manquants ne sont jamais inventés.'));
 const attributions=Array.isArray(obs.equityAttribution)?obs.equityAttribution.slice(-8):[];
 content.append(table(['Variation de valeur','Effet des cours','Exécutions, frais et flux fictifs'],attributions.map(x=>[number(x.equityChange)+' €',number(x.priceEffect)+' €',number(x.executionAndCashEffect)+' €'])));
 content.append(element('h3','Erreurs et limites détectées'));
 const errors=Array.isArray(report.errors)?report.errors:[];
 if(!errors.length)content.append(element('p','Aucune anomalie enregistrée dans cette collecte. Cela ne garantit pas l’absence d’erreur.'));
 for(const e of errors.slice(-50))content.append(element('p',String(e.code||'Erreur')+' : '+String(e.message||'').slice(0,500)));
 for(const text of [...(obs.limitations||[]),...(report.limitations||[])].slice(0,12))content.append(element('p',text));
 content.append(element('h3','Analyse IA et revue du code'));
 content.append(element('p','OpenAI : interface hors ligne · appels API désactivés · budget mensuel '+number(report.ai?.monthlyBudgetUsd)+' USD · dépense '+number(report.ai?.spentUsd)+' USD. Aucune fusion, modification des risques ni activation réelle automatique.'));
 const download=element('button','Préparer le dossier d’analyse IA (sans appel API)');download.type='button';download.onclick=async()=>{download.disabled=true;try{const r=await read('openai-review-input.json');const u=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'})),a=element('a');a.href=u;a.download='SHIMIX-analyse-hors-ligne.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),3000);status.textContent='Dossier préparé. Aucun appel API ni dépense.';}catch{status.textContent='Dossier indisponible. Aucun appel API effectué.';}finally{download.disabled=false;}};content.append(download);
 const review=element('p','Revue Codex : utiliser le dossier learning-data/codex-review.md dans une PR ; validation humaine obligatoire avant toute fusion ou publication.');content.append(review);
 status.textContent='Dernière collecte : '+new Date(report.generatedAt).toLocaleString('fr-FR')+(report.experiment?' · hypothèse gelée le '+new Date(report.experiment.frozenAt).toLocaleDateString('fr-FR'):' · aucune hypothèse gelée pour le moment.');
}
async function refresh(){status.textContent='Lecture du rapport…';try{render(await read('report.json'));}catch(e){status.textContent='Rapport indisponible : '+e.message+'. Aucune donnée de simulation modifiée.';}}
panel.querySelector('[data-learning-refresh]').addEventListener('click',refresh);refresh();
})();
