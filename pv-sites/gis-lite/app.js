(()=>{
'use strict';
const $=s=>document.querySelector(s);
const MAX_FILE_BYTES=50*1024*1024;
const MAX_FEATURES=20000;
const MAX_COORDS=250000;
const MAX_HISTORY=40;
const FEATURE_LIST_LIMIT=500;
const R=6371008.8;
let lang=localStorage.getItem('gis-lite-language')||'ja';
let mode='marker';
let entries=[];
let nextId=1;
let history=[];
let future=[];
let drawPoints=[];
let drawLayer=null;
let searchAbort=null;
let lastMeasure='—';
let map,featureGroup,canvasRenderer;
const packs=window.GIS_LITE_I18N||{};
const t=k=>(packs[lang]||packs.en||{})[k]||k;
function setStatus(v){const e=$('#mapStatus');if(e)e.textContent=v}
function applyLanguage(){
  const p=packs[lang]||packs.en;if(!p)return;
  document.documentElement.lang=lang;document.title=p.title;
  document.querySelectorAll('[data-i18n]').forEach(e=>{if(p[e.dataset.i18n]!=null)e.textContent=p[e.dataset.i18n]});
  document.querySelectorAll('[data-i18n-html]').forEach(e=>{if(p[e.dataset.i18nHtml]!=null)e.innerHTML=p[e.dataset.i18nHtml]});
  document.querySelectorAll('[data-i18n-placeholder]').forEach(e=>{if(p[e.dataset.i18nPlaceholder]!=null)e.placeholder=p[e.dataset.i18nPlaceholder]});
  $('#languageSelect').value=lang;
  if(entries.length===0&&!drawPoints.length)setStatus(t('ready'));
  renderFeatureList();
}
function clone(v){return JSON.parse(JSON.stringify(v))}
function snapshot(){return entries.map(e=>clone(e.feature))}
function pushHistory(){history.push(snapshot());if(history.length>MAX_HISTORY)history.shift();future=[];updateHistoryButtons()}
function restore(features){entries=features.map(feature=>({id:nextId++,feature:clone(feature)}));rebuildLayers();updateStats();renderFeatureList()}
function undo(){if(!history.length)return;future.push(snapshot());restore(history.pop());updateHistoryButtons();setStatus(t('undo'))}
function redo(){if(!future.length)return;history.push(snapshot());restore(future.pop());updateHistoryButtons();setStatus(t('redo'))}
function updateHistoryButtons(){if($('#undoButton'))$('#undoButton').disabled=!history.length;if($('#redoButton'))$('#redoButton').disabled=!future.length}
function formatDistance(m){return m<1000?`${Math.round(m)} m`:`${(m/1000).toFixed(m<10000?2:1)} km`}
function formatArea(m2){return m2<1e6?`${Math.round(m2).toLocaleString()} m²`:`${(m2/1e6).toFixed(m2<1e7?2:1)} km²`}
function rad(v){return v*Math.PI/180}
function normalizeDeltaLon(v){while(v>Math.PI)v-=2*Math.PI;while(v< -Math.PI)v+=2*Math.PI;return v}
function sphericalArea(points){
  if(points.length<3)return 0;let sum=0;
  for(let i=0;i<points.length;i++){
    const a=points[i],b=points[(i+1)%points.length];
    const dLon=normalizeDeltaLon(rad(b.lng)-rad(a.lng));
    sum+=dLon*(2+Math.sin(rad(a.lat))+Math.sin(rad(b.lat)));
  }
  let area=Math.abs(sum)*R*R/2;
  const sphere=4*Math.PI*R*R;if(area>sphere/2)area=sphere-area;
  return Math.max(0,area);
}
function routeDistance(points){let m=0;for(let i=1;i<points.length;i++)m+=map.distance(points[i-1],points[i]);return m}
function geometryCoordCount(geometry){
  if(!geometry)return 0;
  if(geometry.type==='GeometryCollection')return geometry.geometries.reduce((n,g)=>n+geometryCoordCount(g),0);
  let n=0;const walk=v=>{if(!Array.isArray(v))throw new Error(t('invalidGeoJSON'));if(v.length>=2&&typeof v[0]==='number'&&typeof v[1]==='number'){if(!Number.isFinite(v[0])||!Number.isFinite(v[1]))throw new Error(t('invalidGeoJSON'));n++;return}v.forEach(walk)};walk(geometry.coordinates);return n;
}
function validateFeature(feature){
  if(!feature||feature.type!=='Feature'||!('geometry' in feature))throw new Error(t('invalidGeoJSON'));
  if(feature.geometry){const allowed=new Set(['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon','GeometryCollection']);if(!allowed.has(feature.geometry.type))throw new Error(t('invalidGeoJSON'));geometryCoordCount(feature.geometry)}
  if(feature.properties!=null&&(typeof feature.properties!=='object'||Array.isArray(feature.properties)))throw new Error(t('invalidGeoJSON'));
  return {type:'Feature',geometry:clone(feature.geometry),properties:clone(feature.properties||{})};
}
function normalizeGeoJSON(data){
  let fs=[];
  if(data?.type==='FeatureCollection')fs=data.features;
  else if(data?.type==='Feature')fs=[data];
  else if(['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon','GeometryCollection'].includes(data?.type))fs=[{type:'Feature',geometry:data,properties:{}}];
  else throw new Error(t('invalidGeoJSON'));
  if(!Array.isArray(fs)||fs.length>MAX_FEATURES)throw new Error(t('tooMany'));
  let coords=0;const out=fs.map(f=>{const v=validateFeature(f);coords+=geometryCoordCount(v.geometry);if(coords>MAX_COORDS)throw new Error(t('tooMany'));return v});
  return out;
}
function featureName(feature,index=0){const p=feature.properties||{};return String(p.name??p.title??p.label??`${feature.geometry?.type||'Feature'} ${index+1}`)}
function popupNode(feature){const d=document.createElement('div');const s=document.createElement('strong');s.textContent=featureName(feature);d.append(s);const type=document.createElement('div');type.textContent=feature.geometry?.type||'Feature';type.style.cssText='font-size:10px;opacity:.7;margin-top:3px';d.append(type);return d}
function layerFor(entry){
  const layer=L.geoJSON(entry.feature,{renderer:canvasRenderer,style:{color:'#147d66',weight:3,fillOpacity:.18},pointToLayer:(_f,ll)=>L.circleMarker(ll,{renderer:canvasRenderer,radius:6,color:'#147d66',weight:2,fillColor:'#fff',fillOpacity:1})});
  layer.eachLayer(l=>{if(l.bindPopup)l.bindPopup(popupNode(entry.feature))});
  layer.addTo(featureGroup);return layer;
}
function rebuildLayers(){featureGroup.clearLayers();entries.forEach(e=>{e.layer=layerFor(e)})}
function addFeatures(features,{record=true,fit=true}={}){
  if(!features.length)return;if(entries.length+features.length>MAX_FEATURES)throw new Error(t('tooMany'));if(record)pushHistory();
  const added=features.map(feature=>({id:nextId++,feature:clone(feature)}));added.forEach(e=>{e.layer=layerFor(e);entries.push(e)});updateStats();renderFeatureList();if(fit)fitEntries(added)
}
function removeEntry(id){const idx=entries.findIndex(e=>e.id===id);if(idx<0)return;pushHistory();featureGroup.removeLayer(entries[idx].layer);entries.splice(idx,1);updateStats();renderFeatureList();setStatus(t('ready'))}
function clearAll(){if(!entries.length)return;pushHistory();entries=[];featureGroup.clearLayers();resetMeasure();updateStats();renderFeatureList();setStatus(t('cleared'))}
function fitEntries(list=entries){if(!list.length)return;const group=L.featureGroup(list.map(e=>e.layer));const b=group.getBounds();if(b.isValid())map.fitBounds(b.pad(.12),{maxZoom:16})}
function updateStats(){
  const pts=entries.filter(e=>e.feature.geometry?.type==='Point').length;
  $('#pointCount').textContent=pts;$('#featureCount').textContent=entries.length;$('#measureValue').textContent=lastMeasure;
  $('#exportGeo').disabled=!entries.length;$('#exportCsv').disabled=!entries.some(e=>e.feature.geometry?.type==='Point');
}
function renderFeatureList(){
  const box=$('#featureList');if(!box)return;box.replaceChildren();
  if(!entries.length){const d=document.createElement('div');d.className='empty';d.textContent=t('emptyFeatures');box.append(d);return}
  const frag=document.createDocumentFragment();entries.slice(0,FEATURE_LIST_LIMIT).forEach((e,i)=>{
    const row=document.createElement('div');row.className='feature-item';
    const info=document.createElement('div');const strong=document.createElement('strong');strong.textContent=featureName(e.feature,i);const small=document.createElement('small');small.textContent=e.feature.geometry?.type||'Feature';info.append(strong,small);
    const acts=document.createElement('div');acts.className='feature-actions';
    const zoom=document.createElement('button');zoom.className='icon-button';zoom.type='button';zoom.textContent=t('zoom');zoom.onclick=()=>fitEntries([e]);
    const del=document.createElement('button');del.className='icon-button';del.type='button';del.textContent=t('remove');del.onclick=()=>removeEntry(e.id);acts.append(zoom,del);row.append(info,acts);frag.append(row)
  });
  if(entries.length>FEATURE_LIST_LIMIT){const more=document.createElement('div');more.className='empty';more.textContent=`${entries.length-FEATURE_LIST_LIMIT} more features`;frag.append(more)}box.append(frag)
}
function resetMeasure(){drawPoints=[];if(drawLayer){map.removeLayer(drawLayer);drawLayer=null}}
function setMode(next){mode=next;resetMeasure();document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===next));if(next==='marker')setStatus(t('markerMode'));if(next==='distance')setStatus(t('distanceMode'));if(next==='area')setStatus(t('areaMode'))}
function drawPreview(){
  if(drawLayer)map.removeLayer(drawLayer);if(!drawPoints.length)return;
  if(mode==='distance')drawLayer=L.polyline(drawPoints,{color:'#df744d',weight:4,dashArray:'8 5'}).addTo(map);
  if(mode==='area')drawLayer=L.polygon(drawPoints,{color:'#147d66',weight:3,fillOpacity:.18,dashArray:'8 5'}).addTo(map);
  if(mode==='distance'&&drawPoints.length>=2){lastMeasure=formatDistance(routeDistance(drawPoints));$('#measureValue').textContent=lastMeasure;setStatus(lastMeasure)}
  if(mode==='area'&&drawPoints.length>=3){lastMeasure=formatArea(sphericalArea(drawPoints));$('#measureValue').textContent=lastMeasure;setStatus(`${lastMeasure} · ${t('finish')}`)}
}
function finishMeasure(){
  if(mode==='distance'&&drawPoints.length>=2){const m=routeDistance(drawPoints),coords=drawPoints.map(p=>[p.lng,p.lat]);addFeatures([{type:'Feature',geometry:{type:'LineString',coordinates:coords},properties:{name:'Measured route',measurement_type:'distance',length_m:Number(m.toFixed(3))}}],{fit:false});lastMeasure=formatDistance(m);resetMeasure();updateStats();setStatus(lastMeasure);return}
  if(mode==='area'&&drawPoints.length>=3){const m=sphericalArea(drawPoints),ring=drawPoints.map(p=>[p.lng,p.lat]);ring.push([...ring[0]]);addFeatures([{type:'Feature',geometry:{type:'Polygon',coordinates:[ring]},properties:{name:'Measured area',measurement_type:'area',area_m2:Number(m.toFixed(3))}}],{fit:false});lastMeasure=formatArea(m);resetMeasure();updateStats();setStatus(lastMeasure)}
}
function parseCsv(text){
  text=text.replace(/^\uFEFF/,'');const rows=[];let row=[],field='',quoted=false;
  for(let i=0;i<text.length;i++){const c=text[i];if(quoted){if(c==='"'){if(text[i+1]==='"'){field+='"';i++}else quoted=false}else field+=c;continue}if(c==='"'&&field===''){quoted=true;continue}if(c===','){row.push(field);field='';continue}if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);field='';if(row.some(v=>v!==''))rows.push(row);row=[];continue}field+=c}
  if(quoted)throw new Error(t('invalidFile'));row.push(field);if(row.some(v=>v!==''))rows.push(row);if(rows.length<2)return [];
  const rawHead=rows.shift().map(v=>v.trim());const used=new Map();const head=rawHead.map((h,i)=>{let k=h||`column_${i+1}`;const n=used.get(k)||0;used.set(k,n+1);return n?`${k}_${n+1}`:k});
  const lower=head.map(h=>h.toLowerCase().trim());const latI=lower.findIndex(h=>['lat','latitude'].includes(h));const lonI=lower.findIndex(h=>['lon','lng','longitude'].includes(h));if(latI<0||lonI<0)throw new Error(t('invalidFile'));
  const out=[];for(const r of rows){const lat=Number(r[latI]),lon=Number(r[lonI]);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)continue;const props={};head.forEach((h,i)=>{if(i!==latI&&i!==lonI)props[h]=r[i]??''});out.push({type:'Feature',geometry:{type:'Point',coordinates:[lon,lat]},properties:props});if(out.length>MAX_FEATURES)throw new Error(t('tooMany'))}return out
}
async function importFile(file){
  if(!file)return;if(file.size>MAX_FILE_BYTES){setStatus(t('tooLarge'));return}setStatus('Reading…');
  try{const text=await file.text();let features;if(file.name.toLowerCase().endsWith('.csv'))features=parseCsv(text);else features=normalizeGeoJSON(JSON.parse(text));if(!features.length)throw new Error(t('invalidFile'));addFeatures(features);setStatus(`${features.length} ${t('loaded')}`)}catch(e){console.warn(e);setStatus(e?.message||t('invalidFile'))}finally{$('#fileInput').value=''}
}
function csvCell(value){let s=value==null?'':typeof value==='object'?JSON.stringify(value):String(value);if(/^[=+\-@]/.test(s))s="'"+s;return `"${s.replace(/"/g,'""')}"`}
function exportCsv(){const points=entries.filter(e=>e.feature.geometry?.type==='Point');if(!points.length){setStatus(t('nothingToExport'));return}const keys=[];const seen=new Set();points.forEach(e=>Object.keys(e.feature.properties||{}).forEach(k=>{if(!seen.has(k)){seen.add(k);keys.push(k)}}));const rows=[['latitude','longitude',...keys],...points.map(e=>[e.feature.geometry.coordinates[1],e.feature.geometry.coordinates[0],...keys.map(k=>e.feature.properties?.[k]??'')])];download('gis-lite.csv','\uFEFF'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n'),'text/csv;charset=utf-8')}
function exportGeoJSON(){if(!entries.length){setStatus(t('nothingToExport'));return}download('gis-lite.geojson',JSON.stringify({type:'FeatureCollection',features:entries.map(e=>e.feature)},null,2),'application/geo+json')}
function download(name,text,type){const u=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000)}
async function search(){
  const q=$('#searchInput').value.trim();if(!q)return;if(searchAbort)searchAbort.abort();searchAbort=new AbortController();setStatus(t('searching'));
  try{const url=`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=7&language=${encodeURIComponent(lang)}&format=json`;const r=await fetch(url,{signal:searchAbort.signal});if(!r.ok)throw new Error();const d=await r.json();const list=$('#resultList');list.replaceChildren();const results=Array.isArray(d.results)?d.results:[];if(!results.length){const x=document.createElement('div');x.className='empty';x.textContent=t('noResults');list.append(x)}results.forEach(x=>{const b=document.createElement('button');b.type='button';b.className='result';b.textContent=[x.name,x.admin1,x.country].filter(Boolean).join(', ');b.onclick=()=>{const ll=[Number(x.latitude),Number(x.longitude)];if(!ll.every(Number.isFinite))return;map.setView(ll,13);const node=document.createElement('div');node.textContent=b.textContent;L.popup().setLatLng(ll).setContent(node).openOn(map);setStatus(b.textContent)};list.append(b)});if(results.length)setStatus(`${results.length} results`)}catch(e){if(e.name!=='AbortError')setStatus(t('searchUnavailable'))}
}
function init(){
  applyLanguage();if(!window.L){setStatus(t('engineMissing'));document.querySelectorAll('button').forEach(b=>b.disabled=true);return}
  map=L.map('map',{preferCanvas:true}).setView([35.681,139.767],11);canvasRenderer=L.canvas({padding:.5});L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);featureGroup=L.featureGroup().addTo(map);
  map.on('click',e=>{if(mode==='marker'){addFeatures([{type:'Feature',geometry:{type:'Point',coordinates:[e.latlng.lng,e.latlng.lat]},properties:{source:'manual'}}],{fit:false});setStatus(t('markerMode'));return}drawPoints.push(e.latlng);drawPreview()});
  $('#searchButton').onclick=search;$('#searchInput').onkeydown=e=>{if(e.key==='Enter')search()};
  $('#fileInput').onchange=e=>importFile(e.target.files?.[0]);const dz=$('#dropZone');['dragenter','dragover'].forEach(n=>dz.addEventListener(n,e=>{e.preventDefault();dz.classList.add('drag')}));['dragleave','drop'].forEach(n=>dz.addEventListener(n,e=>{e.preventDefault();dz.classList.remove('drag')}));dz.addEventListener('drop',e=>importFile(e.dataTransfer.files?.[0]));
  document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));$('#finishMode').onclick=finishMeasure;$('#cancelMode').onclick=()=>{resetMeasure();setStatus(t('ready'))};
  $('#locateButton').onclick=()=>navigator.geolocation?.getCurrentPosition(p=>{addFeatures([{type:'Feature',geometry:{type:'Point',coordinates:[p.coords.longitude,p.coords.latitude]},properties:{source:'geolocation',accuracy_m:Math.round(p.coords.accuracy||0)}}]);map.setView([p.coords.latitude,p.coords.longitude],15);setStatus(t('locationAdded'))},()=>setStatus(t('locationUnavailable')),{enableHighAccuracy:false,timeout:10000,maximumAge:60000});
  $('#clearButton').onclick=clearAll;$('#exportGeo').onclick=exportGeoJSON;$('#exportCsv').onclick=exportCsv;$('#undoButton').onclick=undo;$('#redoButton').onclick=redo;
  $('#languageSelect').onchange=e=>{lang=e.target.value;localStorage.setItem('gis-lite-language',lang);applyLanguage()};
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?redo():undo()}else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();redo()}else if(e.key==='Escape'){resetMeasure();setStatus(t('ready'))}});
  updateHistoryButtons();updateStats();renderFeatureList();setMode('marker')
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();