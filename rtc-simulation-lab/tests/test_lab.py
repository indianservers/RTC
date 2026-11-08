import json
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import pytest
from hypothesis import given, strategies as st
from rtc_simulation.generator import generate, cases, trip, NOW, stamp
from rtc_simulation.reference_engine import evaluate, journeys, fare, active, dt
from rtc_simulation.event_replay import replay
from rtc_simulation.validators import validate
from rtc_simulation.benchmark import run

CASES,_=cases()
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_authored_gold(case):
    assert evaluate(case['fixture'],case['enquiry'],case['frozen_now'])==case['expected_result']

def test_reproducible_and_valid(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b'
    generate(a);generate(b)
    assert (a/'manifest.v1.json').read_bytes()==(b/'manifest.v1.json').read_bytes()
    assert validate(a)['passed']
    p=a/'fixtures/stations.v1.csv';p.write_bytes(p.read_bytes()+b'tamper')
    assert not validate(a)['passed']

def test_benchmark_adapter_failure(tmp_path,monkeypatch):
    import types,sys
    generate(tmp_path)
    assert run(tmp_path,category='C')['failed']==0
    module=types.ModuleType('test_adapter');module.respond=lambda payload: {'value':'wrong'}
    monkeypatch.setitem(sys.modules,'test_adapter',module)
    result=run(tmp_path,category='A',adapter='test_adapter:respond')
    assert result['failed']==result['total']
    with pytest.raises(ValueError):run(tmp_path,mode='nlp')

def test_replay_all_events(tmp_path):
    generate(tmp_path)
    state=json.loads((tmp_path/'fixtures/network.v1.json').read_text())
    events=json.loads((tmp_path/'fixtures/events.v1.json').read_text())['events']
    original=deepcopy(state)
    result=replay(state,events,'2026-11-08T08:07:00+05:30')
    assert state==original
    assert len(result['event_log'])==8
    assert result==replay(state,list(reversed(events)),'2026-11-08T08:07:00+05:30')
    ts=result['state']['trips']
    assert ts[0]['delay_minutes']==25
    assert ts[1]['operational_status']=='arrived'
    assert ts[2]['operational_status']=='departed'
    assert ts[3]['cancelled']
    assert ts[4]['platform']=='9'
    assert ts[5]['gps_stale']
    assert ts[6]['seat_snapshot']['available']==12
    assert 'bypass' in ts[7]['diversion']
    assert len(replay(state,events,NOW)['event_log'])==1
    with pytest.raises(ValueError):replay(state,events+events,NOW)

@given(st.integers(0,59),st.integers(0,30),st.booleans())
def test_transfer_allowance(minute,allowance,cancelled):
    a=trip('A',['O','M'],[(9,0),(10,0)])
    b=trip('B',['M','D'],[(10,minute),(12,0)]);b['cancelled']=cancelled
    paths=journeys({'trips':[a,b]},'O','D',NOW,transfer_minutes=allowance)
    assert bool(paths)==(minute>=allowance and not cancelled)
    for legs in paths:
        assert dt(legs[1]['departure'])>=dt(legs[0]['arrival'])+timedelta(minutes=allowance)
        assert all(dt(x['arrival'])>dt(x['departure']) for x in legs)
        assert all(x['source_label']=='SYNTHETIC' for x in legs)

@given(st.lists(st.integers(1,120),min_size=2,max_size=8))
def test_directed_sequence(gaps):
    start=dt(NOW);stops=[]
    for i,gap in enumerate(gaps):
        start+=timedelta(minutes=gap)
        stops.append(dict(station=str(i),arrival=start.isoformat(),departure=start.isoformat()))
    state={'trips':[dict(id='T',stops=stops,source_label='SYNTHETIC')]}
    for i in range(len(stops)):
        for j in range(len(stops)):
            assert bool(journeys(state,str(i),str(j),NOW))==(i<j)

@given(st.decimals(min_value='0',max_value='10000',places=2,allow_nan=False,allow_infinity=False))
def test_fare_nonnegative_expiry(amount):
    r=dict(mode='fixed',amount=str(amount),valid_from='2026-01-01',valid_to='2026-11-08')
    assert Decimal(fare(r,{'date':'2026-11-08'})['amount'])>=0
    assert fare(r,{'date':'2026-11-09'})['amount'] is None
    assert fare(r,{'date':'2025-12-31'})['amount'] is None

@given(st.integers(1,200),st.integers(0,60))
def test_capacity_and_freshness(capacity,age):
    t=trip('T',['A','B'],[(9,0),(10,0)]);t['capacity']=capacity
    q=dict(intent='seats',service_id='T')
    assert evaluate({'trips':[t]},q,NOW)['value'] is None
    t['seat_snapshot']={'available':0,'observed_at':(dt(NOW)-timedelta(minutes=age)).isoformat()}
    result=evaluate({'trips':[t]},q,NOW)
    assert result['value']==(0 if age<=15 else None)
    assert result['source_label']=='SYNTHETIC'

@given(st.booleans(),st.booleans())
def test_calendar_precedence(weekly,exception):
    t={'weekdays':[6] if weekly else [],'exceptions':{'2026-11-08':exception}}
    assert active(t,dt(NOW).date()) is exception

@given(st.integers(1,500),st.integers(1,500))
def test_past_and_unknown_price(a,b):
    t=trip('T',['A','B'],[(6,0),(7,0)])
    assert not evaluate({'trips':[t]},dict(intent='departure',service_id='T'),NOW)['value']
    state={'prices':[{'id':'unknown','amount':None},{'id':'a','amount':str(a)},{'id':'b','amount':str(b)}]}
    assert evaluate(state,dict(intent='cheapest'),NOW)['value']==('a' if a<=b else 'b')

def test_midnight_operating_day_and_delay():
    t=trip('T',['A','B'],[(23,50),(23,55)])
    t['stops'][-1].update(arrival=stamp(9,1),departure=stamp(9,1))
    t.update(weekdays=[6],delay_minutes=20)
    legs=journeys({'trips':[t]},'A','B',stamp(9,0))
    assert len(legs)==1
    assert legs[0][0]['departure']==stamp(9,0,10)
    assert legs[0][0]['arrival']==stamp(9,1,20)

def test_seed_configuration_and_csv(tmp_path):
    import csv
    a,b=tmp_path/'a',tmp_path/'b'
    generate(a,1,{'categories':['DEMO AC'],'operators':['DEMO A']})
    generate(b,2)
    net=json.loads((a/'fixtures/network.v1.json').read_text())
    assert net['random_seed']==1
    assert {t['category'] for t in net['trips']}=={'DEMO AC'}
    assert {t['operator'] for t in net['trips']}=={'DEMO A'}
    assert (a/'fixtures/network.v1.json').read_bytes()!=(b/'fixtures/network.v1.json').read_bytes()
    with (a/'fixtures/trips.v1.csv').open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==2400
    assert json.loads(rows[0]['stops'])==net['trips'][0]['stops']
    with (a/'scenarios/functional.v1.csv').open(newline='',encoding='utf-8') as f:
        assert len(list(csv.DictReader(f)))==540
    assert validate(a)['passed']

def test_decimal_rounding_and_effective_boundaries():
    rule=dict(mode='fixed',amount='0.01',valid_from='2026-11-08',valid_to='2026-11-08',concessions={'half':'0.5'})
    assert fare(rule,dict(date='2026-11-08',concession='half'))['amount']=='0.01'
    rule['amount']='-1'
    with pytest.raises(ValueError):fare(rule,dict(date='2026-11-08'))
