#!/usr/bin/env python3
"""RateTerrain production ETL v1: CMS PUF (PY2026) -> site JSON. QA per SPEC_ETL_rate_puf_TX.md"""
import pandas as pd, json, statistics
UP = '/mnt/user-data/uploads'
OUT = '/home/claude/site/src/data'

ra = json.load(open('/home/claude/health/tx_health_rating_areas.json'))
county_to_ra = {}
for a in ra['rating_areas']:
    for c in a['counties']:
        county_to_ra[c] = a['rating_area_id']

def fkey(n):
    k = n.lower().replace(' ','').replace('.','')
    return 'mac'+k[2:] if k.startswith('mc') else k
names = sorted(county_to_ra.keys(), key=fkey)
fips_of = {n: f"48{(2*i+1):03d}" for i,n in enumerate(names)}
for n,f in {'Harris':'48201','Dallas':'48113','Travis':'48453','Bexar':'48029','Tarrant':'48439'}.items():
    assert fips_of[n]==f, f"FIPS anchor failed: {n} -> {fips_of[n]} != {f}"

cols = ['StateCode','IssuerId','PlanId','RatingAreaId','Tobacco','Age','IndividualRate','ImportDate']
tx = pd.concat([c[c['StateCode']=='TX'] for c in pd.read_csv(f'{UP}/Rate_PUF.csv', usecols=cols, dtype=str, chunksize=500_000)], ignore_index=True)
tx['rate'] = pd.to_numeric(tx['IndividualRate'], errors='coerce')
tx['StdId'] = tx['PlanId'].str[:14]
tx['ra'] = tx['RatingAreaId'].str.extract(r'(\d+)').astype(int)

pa = pd.read_csv(f'{UP}/plan_attributes_PUF.csv', usecols=['StateCode','IssuerId','StandardComponentId','MarketCoverage','DentalOnlyPlan','MetalLevel','ServiceAreaId','IssuerMarketPlaceMarketingName','PlanMarketingName'], dtype=str)
med = pa[(pa['StateCode']=='TX')&(pa['MarketCoverage']=='Individual')&(pa['DentalOnlyPlan']=='No')].drop_duplicates('StandardComponentId')
sa = pd.read_csv(f'{UP}/service_area_PUF.csv', dtype=str)
sa = sa[(sa['StateCode']=='TX')&(sa['MarketCoverage']=='Individual')&(sa['DentalOnlyPlan']=='No')]

txm = tx[tx['StdId'].isin(set(med['StandardComponentId']))]
assert txm['ra'].nunique()==27, 'QA-1 fail'
assert txm[(txm['rate']<50)|(txm['rate']>5000)].empty, 'QA placeholder fail'
p21 = txm[txm['Age']=='21'].groupby(['StdId','ra'])['rate'].first()
p64 = txm[txm['Age']=='64 and over'].groupby(['StdId','ra'])['rate'].first()
assert (p64/p21).dropna().max() <= 3.001, 'QA-3 fail'

sa_counties = set(sa['County'].dropna())
assert sa_counties == set(fips_of.values()), f'QA-2/FIPS fail: {sorted(sa_counties ^ set(fips_of.values()))[:6]}'
print('FIPS mapping proven against Service Area PUF (254/254).')

sa_map = sa.groupby(['IssuerId','ServiceAreaId'])['County'].apply(set).to_dict()
plan_counties = {r.StandardComponentId: sa_map.get((r.IssuerId, r.ServiceAreaId), set()) for r in med.itertuples()}
metal = dict(zip(med['StandardComponentId'], med['MetalLevel']))
AGES = ['21','30','40','50','60']
r_by_age = {a: txm[txm['Age']==a].groupby(['StdId','ra'])['rate'].first() for a in AGES}

counties_out = []
for cname in names:
    f = fips_of[cname]; ra_id = county_to_ra[cname]
    plans = [p for p,cs in plan_counties.items() if f in cs]
    issuers = len(set(med[med['StandardComponentId'].isin(plans)]['IssuerId']))
    silver = [p for p in plans if metal.get(p)=='Silver']
    row = {'county':cname,'fips':f,'ra':ra_id,'plans':len(plans),'issuers':issuers}
    for a in AGES:
        s = r_by_age[a]
        vals = [s.get((p,ra_id)) for p in plans]; vals=[v for v in vals if v is not None and v==v]
        sv = [s.get((p,ra_id)) for p in silver]; sv=[v for v in sv if v is not None and v==v]
        row['min'+a] = round(min(vals),2) if vals else None
        row['med'+a] = round(statistics.median(vals),2) if vals else None
        if a=='40': row['medSilver40'] = round(statistics.median(sv),2) if sv else None
    counties_out.append(row)
assert all(c['plans']>0 for c in counties_out), 'county with 0 plans'
json.dump(counties_out, open(f'{OUT}/counties.json','w'))

age_order = ['21','25','30','35','40','45','50','55','60','63','64 and over']
curve = {'ages':[a.replace(' and over','+') for a in age_order], 'statewide':[], 'areas':{}}
metro = {'Houston (RA10)':10,'Dallas (RA8)':8,'Fort Worth (RA25)':25,'San Antonio (RA18)':18,'Austin (RA3)':3}
for a in age_order:
    s = txm[txm['Age']==a].groupby(['StdId','ra'])['rate'].first()
    curve['statewide'].append(round(float(s.median()),2))
    for label,raid in metro.items():
        curve['areas'].setdefault(label,[]).append(round(float(s[s.index.get_level_values('ra')==raid].median()),2))
json.dump(curve, open(f'{OUT}/age_curve.json','w'))

a40 = txm[txm['Age']=='40'].groupby('ra')['rate'].median()
meta = {'plan_year':2026,'import_latest':str(max(tx['ImportDate'])),'built':'2026-08-27',
 'plans':int(txm['StdId'].nunique()),'issuers':int(txm['IssuerId'].nunique()),
 'rating_areas':27,'counties':254,'spread_pct':round(100*(a40.max()/a40.min()-1),1),
 'min_med40':round(float(a40.min()),2),'max_med40':round(float(a40.max()),2)}
json.dump(meta, open(f'{OUT}/meta.json','w'))
print('ETL OK:', meta)
