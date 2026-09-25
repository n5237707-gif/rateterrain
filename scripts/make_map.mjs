import fs from 'fs';
import * as topojson from 'topojson-client';
import { geoPath, geoIdentity } from 'd3-geo';
const us = JSON.parse(fs.readFileSync('node_modules/us-atlas/counties-10m.json'));
const counties = topojson.feature(us, us.objects.counties).features.filter(f=>f.id.startsWith('48'));
const data = JSON.parse(fs.readFileSync('src/data/counties.json'));
const byFips = Object.fromEntries(data.map(c=>[c.fips,c]));
const vals = data.filter(c=>c.min40).map(c=>c.min40);
const min=Math.min(...vals), max=Math.max(...vals);
// шкала: pine (дёшево) -> elev tan (дорого)
function lerp(a,b,t){return a+(b-a)*t}
function hex(r,g,b){return '#'+[r,g,b].map(x=>Math.round(x).toString(16).padStart(2,'0')).join('')}
const c1=[53,96,74], c2=[177,128,79];
const color=v=>{const t=(v-min)/(max-min);return hex(lerp(c1[0],c2[0],t),lerp(c1[1],c2[1],t),lerp(c1[2],c2[2],t))}
const proj = geoIdentity().reflectY(true).fitSize([900,860], {type:'FeatureCollection',features:counties});
const path = geoPath(proj);
let paths='';
for(const f of counties){
  const d=byFips[f.id];
  const fill = d&&d.min40 ? color(d.min40) : '#ddd';
  const tip = d? `${d.county} County — cheapest plan at 40: $${d.min40?.toFixed(2)} / mo, ${d.plans} plans, ${d.issuers} insurer${d.issuers>1?'s':''}` : f.id;
  paths+=`<path d="${path(f)}" fill="${fill}" stroke="#f7f8f4" stroke-width="0.6"><title>${tip}</title></path>`;
}
const legendStops=[0,.25,.5,.75,1].map(t=>`<stop offset="${t*100}%" stop-color="${color(min+(max-min)*t)}"/>`).join('');
const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 990" font-family="Georgia,serif">
<rect width="900" height="990" fill="#f7f8f4"/>
<text x="30" y="46" font-size="30" font-weight="bold" fill="#22301f">What the cheapest health plan costs across Texas</text>
<text x="30" y="72" font-size="16" fill="#5c6a58">Lowest available monthly premium for a 40-year-old, by county — ACA marketplace, plan year 2026</text>
<g transform="translate(0,90)">${paths}</g>
<defs><linearGradient id="lg" x1="0" x2="1">${legendStops}</linearGradient></defs>
<rect x="30" y="920" width="300" height="14" fill="url(#lg)"/>
<text x="30" y="952" font-size="14" fill="#22301f">$${min.toFixed(0)}</text>
<text x="330" y="952" font-size="14" fill="#22301f" text-anchor="end">$${max.toFixed(0)}</text>
<text x="870" y="976" font-size="13" fill="#5c6a58" text-anchor="end">Source: CMS Exchange Public Use Files · rateterrain.com · free to reuse with attribution</text>
</svg>`;
fs.mkdirSync('public/assets',{recursive:true});
fs.writeFileSync('public/assets/tx-cheapest-plan-map-2026.svg',svg);
console.log('SVG map:', (svg.length/1024).toFixed(0),'KB,', counties.length,'counties drawn');
