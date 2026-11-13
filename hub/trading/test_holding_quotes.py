"""Off-list holding quotes, identity/freshness checks and risk-management recovery."""
import base64,copy,datetime,json,unittest,urllib.parse
from unittest.mock import patch
import autonomous_simulation as robot
from test_robot_regressions import good_state,market
NOW=datetime.datetime(2026,11,13,12,tzinfo=datetime.timezone.utc)
class HoldingQuoteTests(unittest.TestCase):
 def state(self):return {**good_state(),'cash':1480,'holdings':{'PEARL':100},'entryPrices':{'PEARL':1.2},'assetIds':{'PEARL':'pearl-2'},'marketCacheAt':123}
 def row(self,**changes):return dict(id='pearl-2',symbol='pearl',current_price=1.2,last_updated=NOW.isoformat(),**changes) if not changes else {**dict(id='pearl-2',symbol='pearl',current_price=1.2,last_updated=NOW.isoformat()),**changes}
 def quote(self,rows,state=None,prices=None):
  state=self.state() if state is None else state
  with patch.object(robot,'request',return_value=rows) as request:
   result,errors=robot.supplement_holding_quotes(state,{} if prices is None else prices,NOW)
  return state,result,errors,request
 def test_off_list_holding_is_quoted_by_exact_id(self):
  s,p,e,call=self.quote([self.row()]);self.assertEqual(p['PEARL'],1.2);self.assertEqual(e,[])
  params=urllib.parse.parse_qs(urllib.parse.urlparse(call.call_args.args[0]).query)
  self.assertEqual(params['ids'],['pearl-2']);self.assertEqual(s['holdingQuoteCoverage']['missingAssets'],[])
 def test_does_not_modify_finances_prices_or_global_cache_age(self):
  s=self.state();before=copy.deepcopy(s);prices={'BTC':100};saved=copy.deepcopy(prices)
  self.quote([self.row()],s,prices)
  s.pop('holdingQuoteCoverage');self.assertEqual(s,before);self.assertEqual(prices,saved)
 def test_primary_quotes_require_no_extra_request(self):
  s,p,e,call=self.quote([],prices={'PEARL':1.2});call.assert_not_called();self.assertEqual(p['PEARL'],1.2)
 def test_empty_or_zero_holdings_require_no_request(self):
  s=self.state();s['holdings']={'PEARL':0}
  self.quote([],s)[3].assert_not_called()
 def test_missing_id_is_not_guessed_from_ticker(self):
  s=self.state();s['assetIds']={};s,p,e,call=self.quote([self.row()],s)
  call.assert_not_called();self.assertNotIn('PEARL',p);self.assertTrue(e)
 def test_wrong_coin_with_same_symbol_is_rejected(self):
  self.assertNotIn('PEARL',self.quote([self.row(id='unrelated-coin')])[1])
 def test_wrong_symbol_with_matching_id_is_rejected(self):
  self.assertNotIn('PEARL',self.quote([self.row(symbol='BTC')])[1])
 def test_duplicate_matching_ids_are_ambiguous(self):
  self.assertNotIn('PEARL',self.quote([self.row(),self.row()])[1])
 def test_invalid_prices_never_become_zero_valuation(self):
  for price in [None,0,-1,True,float('nan'),float('inf'),'1.2']:
   with self.subTest(price=price):self.assertNotIn('PEARL',self.quote([self.row(current_price=price)])[1])
 def test_timestamp_required_with_timezone(self):
  for stamp in [None,'','bad','2026-11-13T12:00:00']:
   self.assertNotIn('PEARL',self.quote([self.row(last_updated=stamp)])[1])
 def test_stale_and_future_quotes_rejected(self):
  for delta in [-3601,61]:
   row=self.row(last_updated=(NOW+datetime.timedelta(seconds=delta)).isoformat())
   self.assertNotIn('PEARL',self.quote([row])[1])
 def test_exact_one_hour_boundary_and_offset_timezone(self):
  stamp=(NOW-datetime.timedelta(hours=1)).astimezone(datetime.timezone(datetime.timedelta(hours=2))).isoformat()
  self.assertEqual(self.quote([self.row(last_updated=stamp)])[1]['PEARL'],1.2)
 def test_nonlist_response_and_network_error_fail_closed(self):
  self.assertNotIn('PEARL',self.quote({'error':'rate limit'})[1])
  with patch.object(robot,'request',side_effect=TimeoutError('fixture')) as request:
   prices,errors=robot.supplement_holding_quotes(self.state(),{},NOW)
  self.assertEqual(request.call_count,1);self.assertNotIn('PEARL',prices);self.assertTrue(errors)
 def test_one_batch_covers_all_missing_holdings(self):
  s=self.state();s['holdings']['ETH']=.01;s['assetIds']['ETH']='ethereum'
  rows=[self.row(),self.row(id='ethereum',symbol='eth',current_price=1700)]
  s,p,e,request=self.quote(rows,s);self.assertEqual(request.call_count,1)
  params=urllib.parse.parse_qs(urllib.parse.urlparse(request.call_args.args[0]).query)
  self.assertEqual(params['ids'],['ethereum,pearl-2']);self.assertEqual(set(p),{'PEARL','ETH'})
 def run_engine(self,state,valid_supplement=True):
  saved=[];requests=[];now=datetime.datetime.now(datetime.timezone.utc);start=int(now.timestamp())//86400-31
  quotes=market();quotes[0]={**quotes[0],'id':'ethereum','symbol':'ETH'}
  def get(method,body=None):
   self.assertEqual(method,'GET');return dict(sha='fixture',content=base64.b64encode(json.dumps(state).encode()).decode())
  def request(url,*a):
   requests.append(url)
   if '/coins/markets?' in url:
    if 'ids=' in url:return [self.row(last_updated=now.isoformat())] if valid_supplement else []
    return quotes
   return {'prices':[[(start+i)*86400000,100+i] for i in range(31)]}
  with patch.object(robot,'gh',side_effect=get),patch.object(robot,'request',side_effect=request),patch.object(robot,'save',side_effect=lambda value,sha:saved.append(copy.deepcopy(value))),patch.object(robot.time,'sleep'),patch.object(robot,'rsi',return_value=70):robot.main()
  return saved[-1],requests
 def test_real_engine_maintains_valuation_for_off_list_pearl(self):
  before=self.state();result,requests=self.run_engine(before)
  self.assertTrue(result['globalProtection']['valuationComplete']);self.assertFalse(result['globalProtection']['buyPaused'])
  self.assertEqual(result['holdings'],before['holdings']);self.assertEqual(result['cash'],before['cash'])
  self.assertEqual(result['value'],1600);self.assertEqual(result['dataErrors'],[])
  self.assertEqual(sum('ids=' in r for r in requests),1)
  self.assertEqual(result['scanner']['examined'],30);self.assertNotIn('PEARL',result['signals'])
 def test_off_list_quote_unblocks_other_position_stop(self):
  s=self.state();s.update(cash=1360,holdings={'ETH':1,'PEARL':100},entryPrices={'ETH':120,'PEARL':1.2});s['assetIds']['ETH']='ethereum'
  result,_=self.run_engine(s)
  self.assertNotIn('ETH',result['holdings']);self.assertEqual(result['trades'][0]['reason'],'stop-loss')
  self.assertEqual(result['trades'][0]['asset'],'ETH');self.assertAlmostEqual(result['cash'],1459.7002)
  self.assertEqual(result['globalProtection']['liquidateAtLossPercent'],10)
 def test_failed_supplement_keeps_pause_and_unknown_value(self):
  before=self.state();result,_=self.run_engine(before,False)
  self.assertTrue(result['globalProtection']['buyPaused']);self.assertIsNone(result['value'])
  self.assertEqual(result['holdings'],before['holdings']);self.assertEqual(result['trades'],[])
  self.assertTrue(any('PEARL' in error for error in result['dataErrors']))
