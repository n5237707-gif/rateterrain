#!/usr/bin/env python3
"""Data for batch-1 guide pages: turning-26, early-retirement, bronze-vs-silver."""
import pandas as pd, json, statistics, re
UP='/mnt/user-data/uploads'; OUT='/home/claude/site/src/data'

cols=['StateCode','PlanId','RatingAreaId','Age','IndividualRate']
tx=pd.concat([c[c['StateCode']=='TX'] for c in pd.read_csv(f'{UP}/Rate_PUF.csv',usecols=cols,dtype=str,chunksize=500_000)],ignore_index=True)
tx['rate']=pd.to_numeric(tx['IndividualRate'],errors='coerce'); tx['StdId']=tx['PlanId'].str[:14]
tx['ra']=tx['RatingAreaId'].str.extract(r'(\d+)').astype(int)

pcols=['StateCode','StandardComponentId','PlanId','MarketCoverage','DentalOnlyPlan','MetalLevel','CSRVariationType','TEHBDedInnTier1Individual','TEHBInnTier1IndividualMOOP']
pa=pd.read_csv(f'{UP}/plan_attributes_PUF.csv',usecols=pcols,dtype=str)
pa=pa[(pa['StateCode']=='TX')&(pa['MarketCoverage']=='Individual')&(pa['DentalOnlyPlan']=='No')]
std=pa[pa['PlanId'].str.endswith('-01')].drop_duplicates('StandardComponentId').set_index('StandardComponentId')
print('стандартных вариантов:',len(std),'| CSR-типы:',std['CSRVariationType'].value_counts().head(3).to_dict())
def num(s):
    if not isinstance(s,str): return None
    m=re.sub(r'[^0-9.]','',s)
    return float(m) if m else None
std['ded']=std['TEHBDedInnTier1Individual'].map(num)
std['moop']=std['TEHBInnTier1IndividualMOOP'].map(num)
txm=tx[tx['StdId'].isin(set(std.index))]
metal=std['MetalLevel'].to_dict()

METRO={'Houston':10,'Dallas':8,'Fort Worth':25,'San Antonio':18,'Austin':3}
def med_min(age,raid=None,mfil=None):
    s=txm[txm['Age']==age]
    if raid: s=s[s['ra']==raid]
    if mfil: s=s[s['StdId'].map(metal).isin(mfil)]
    g=s.groupby(['StdId','ra'])['rate'].first()
    return (round(float(g.median()),2), round(float(g.min()),2)) if len(g) else (None,None)

# 1) Turning 26
t26={'statewide':med_min('26'),'metros':{k:med_min('26',v) for k,v in METRO.items()},
     'bronze':med_min('26',mfil=['Bronze','Expanded Bronze'])[1],
     'silver_med':med_min('26',mfil=['Silver'])[0],
     'vs40': med_min('40')[0], 'vs60': med_min('60')[0]}

# 2) Early retirement 60-64
ret={'ages':{a: med_min(a) for a in ['60','62','64 and over']},
     'metros64':{k:med_min('64 and over',v) for k,v in METRO.items()}}
a62=txm[txm['Age']=='62'].groupby('ra')['rate'].median()
ret['gap62']={'min':round(float(a62.min()),2),'min_ra':int(a62.idxmin()),'max':round(float(a62.max()),2),'max_ra':int(a62.idxmax())}

# 3) Bronze vs Silver (+Gold context) — премия(40) + франшиза + MOOP по metal
mt={}
for m in ['Catastrophic','Bronze','Expanded Bronze','Silver','Gold']:
    ids=[i for i,v in metal.items() if v==m]
    if not ids: continue
    g=txm[(txm['Age']=='40')&(txm['StdId'].isin(ids))].groupby(['StdId','ra'])['rate'].first()
    ded=[std.loc[i,'ded'] for i in ids if std.loc[i,'ded'] is not None]
    mo=[std.loc[i,'moop'] for i in ids if std.loc[i,'moop'] is not None]
    mt[m]={'plans':len(ids),'prem40_med':round(float(g.median()),2),'prem40_min':round(float(g.min()),2),
           'ded_med':round(statistics.median(ded)) if ded else None,'moop_med':round(statistics.median(mo)) if mo else None}
gold_vs_silver = mt['Silver']['prem40_med'] - mt['Gold']['prem40_med']
print('Silver−Gold медианная премия (40):', round(gold_vs_silver,2))
json.dump({'t26':t26,'ret':ret,'metals':mt,'gold_cheaper_than_silver': bool(gold_vs_silver>0)}, open(f'{OUT}/guides.json','w'))
print('t26:',t26['statewide'],'| ret 64+:',ret['ages']['64 and over'],'| gap62:',ret['gap62'])
