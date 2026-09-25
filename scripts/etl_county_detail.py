#!/usr/bin/env python3
"""County detail pages data. Counties = top-25 TX by population [Г, 2020 census order]."""
import pandas as pd, json, statistics
UP='/mnt/user-data/uploads'; OUT='/home/claude/site/src/data'
TARGET=['Harris','Dallas','Tarrant','Bexar','Travis','Collin','Denton','Hidalgo','El Paso','Fort Bend',
'Montgomery','Williamson','Cameron','Nueces','Brazoria','Bell','Galveston','Lubbock','Webb','Jefferson',
'McLennan','Smith','Brazos','Hays','Ellis']
ra_json=json.load(open(f'{OUT}/tx_health_rating_areas.json')) if False else json.load(open('/home/claude/health/tx_health_rating_areas.json'))
county_ra={c:a['rating_area_id'] for a in ra_json['rating_areas'] for c in a['counties']}
def fkey(n):
    k=n.lower().replace(' ','').replace('.','')
    return 'mac'+k[2:] if k.startswith('mc') else k
names=sorted(county_ra.keys(), key=fkey)
fips_of={n:f"48{(2*i+1):03d}" for i,n in enumerate(names)}
slug_of=lambda n: n.lower().replace(' ','-')+'-county'

cols=['StateCode','IssuerId','PlanId','RatingAreaId','Age','IndividualRate']
tx=pd.concat([c[c['StateCode']=='TX'] for c in pd.read_csv(f'{UP}/Rate_PUF.csv',usecols=cols,dtype=str,chunksize=500_000)],ignore_index=True)
tx['rate']=pd.to_numeric(tx['IndividualRate'],errors='coerce'); tx['StdId']=tx['PlanId'].str[:14]
tx['ra']=tx['RatingAreaId'].str.extract(r'(\d+)').astype(int)
pa=pd.read_csv(f'{UP}/plan_attributes_PUF.csv',usecols=['StateCode','IssuerId','StandardComponentId','MarketCoverage','DentalOnlyPlan','MetalLevel','PlanType','ServiceAreaId','IssuerMarketPlaceMarketingName','PlanMarketingName'],dtype=str)
med=pa[(pa['StateCode']=='TX')&(pa['MarketCoverage']=='Individual')&(pa['DentalOnlyPlan']=='No')].drop_duplicates('StandardComponentId').set_index('StandardComponentId')
sa=pd.read_csv(f'{UP}/service_area_PUF.csv',dtype=str)
sa=sa[(sa['StateCode']=='TX')&(sa['MarketCoverage']=='Individual')&(sa['DentalOnlyPlan']=='No')]
sa_map=sa.groupby(['IssuerId','ServiceAreaId'])['County'].apply(set).to_dict()
plan_c={i:sa_map.get((r['IssuerId'],r['ServiceAreaId']),set()) for i,r in med.iterrows()}
txm=tx[tx['StdId'].isin(set(med.index))]
AGES=['21','30','40','50','60']
r_by={a:txm[txm['Age']==a].groupby(['StdId','ra'])['rate'].first() for a in AGES}
state_med40=float(r_by['40'].median())

out={}
for cname in TARGET:
    f=fips_of[cname]; raid=county_ra[cname]; slug=slug_of(cname)
    plans=[p for p,cs in plan_c.items() if f in cs]
    sub=med.loc[plans]
    ages={}
    for a in AGES:
        vals=[r_by[a].get((p,raid)) for p in plans]; vals=[v for v in vals if v is not None and v==v]
        ages[a]={'min':round(min(vals),2),'med':round(statistics.median(vals),2)}
    metals=[]
    for m in ['Catastrophic','Bronze','Expanded Bronze','Silver','Gold']:
        mp=[p for p in plans if med.loc[p,'MetalLevel']==m]
        if not mp: continue
        v=[r_by['40'].get((p,raid)) for p in mp]; v=[x for x in v if x is not None and x==x]
        metals.append({'metal':m,'count':len(mp),'min40':round(min(v),2),'med40':round(statistics.median(v),2)})
    r40=[(p,r_by['40'].get((p,raid))) for p in plans]
    r40=[(p,v) for p,v in r40 if v is not None and v==v]; r40.sort(key=lambda x:x[1])
    cheapest=[{'issuer':med.loc[p,'IssuerMarketPlaceMarketingName'],'plan':med.loc[p,'PlanMarketingName'][:70],'metal':med.loc[p,'MetalLevel'],'type':med.loc[p,'PlanType'],'rate':round(v,2)} for p,v in r40[:5]]
    iss=sub.groupby('IssuerMarketPlaceMarketingName').size().sort_values(ascending=False)
    out[slug]={'slug':slug,'county':cname,'fips':f,'ra':raid,'plans':len(plans),'issuers':int(sub['IssuerId'].nunique()),
      'ages':ages,'metals':metals,'cheapest':cheapest,'issuer_list':[{'name':k,'plans':int(v)} for k,v in iss.items()],'state_med40':round(state_med40,2)}
json.dump(out,open(f'{OUT}/county_detail.json','w'))
print(len(out),'counties; примеры:', [(s,d['plans']) for s,d in list(out.items())[5:9]])
