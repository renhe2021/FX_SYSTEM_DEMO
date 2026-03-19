// FX Markup Pricing — Offline Engine
// All data embedded, all computation client-side

const EMBEDDED_DATA = {"month_label":"2026年1月","summary":{"records":[{"business":"B TO B","ccy":"AUD","volume":189175.89},{"business":"B TO B","ccy":"CAD","volume":77573.17},{"business":"B TO B","ccy":"EUR","volume":1125226.31},{"business":"B TO B","ccy":"GBP","volume":6674.66},{"business":"B TO B","ccy":"HKD","volume":1199885},{"business":"B TO B","ccy":"SGD","volume":102749.79},{"business":"B TO B","ccy":"USD","volume":223089271.4},{"business":"标准收款","ccy":"AUD","volume":469335.237},{"business":"标准收款","ccy":"CAD","volume":821422.9664},{"business":"标准收款","ccy":"EUR","volume":3781369.922},{"business":"标准收款","ccy":"GBP","volume":1387607.226},{"business":"标准收款","ccy":"HKD","volume":1301969.515},{"business":"标准收款","ccy":"JPY","volume":318331.2812},{"business":"标准收款","ccy":"USD","volume":41650385.89},{"business":"纯汇兑","ccy":"AUD","volume":6303521.863},{"business":"纯汇兑","ccy":"CAD","volume":16492593.82},{"business":"纯汇兑","ccy":"EUR","volume":563037327.9},{"business":"纯汇兑","ccy":"GBP","volume":291457483.5},{"business":"纯汇兑","ccy":"HKD","volume":322302980.7},{"business":"纯汇兑","ccy":"JPY","volume":30492262.91},{"business":"纯汇兑","ccy":"SEK","volume":20069331.45},{"business":"纯汇兑","ccy":"SGD","volume":15242537.79},{"business":"纯汇兑","ccy":"USD","volume":2884671014},{"business":"港陆汇款","ccy":"HKD","volume":1493208242},{"business":"机酒商户","ccy":"AUD","volume":1722236.17},{"business":"机酒商户","ccy":"CAD","volume":35410.89},{"business":"机酒商户","ccy":"EUR","volume":56463018.62},{"business":"机酒商户","ccy":"GBP","volume":2762682.86},{"business":"机酒商户","ccy":"HKD","volume":66860242.9},{"business":"机酒商户","ccy":"JPY","volume":61773225.08},{"business":"机酒商户","ccy":"NZD","volume":65870.52},{"business":"机酒商户","ccy":"USD","volume":843461843.1},{"business":"境外收单","ccy":"EUR","volume":307766602.9},{"business":"境外收单","ccy":"GBP","volume":159170830.5},{"business":"境外收单","ccy":"MOP","volume":6964436.32},{"business":"境外收单","ccy":"SGD","volume":250427338.7},{"business":"境外收单","ccy":"THB","volume":58225812.78},{"business":"境外收单","ccy":"USD","volume":3554625.94},{"business":"留学缴费","ccy":"AUD","volume":10813793.17},{"business":"留学缴费","ccy":"CAD","volume":53476352.83},{"business":"留学缴费","ccy":"EUR","volume":1043044.66},{"business":"留学缴费","ccy":"GBP","volume":26367530.81},{"business":"留学缴费","ccy":"HKD","volume":6934094.92},{"business":"留学缴费","ccy":"JPY","volume":6067915.92},{"business":"留学缴费","ccy":"NZD","volume":2013712.78},{"business":"留学缴费","ccy":"SGD","volume":10258147.88},{"business":"留学缴费","ccy":"USD","volume":33243254.38},{"business":"钱包互联","ccy":"JPY","volume":326134.27},{"business":"钱包互联","ccy":"SGD","volume":124400.6},{"business":"钱包互联","ccy":"USD","volume":580251699.9},{"business":"融合三期","ccy":"GBP","volume":40236.08},{"business":"融合三期","ccy":"JPY","volume":18731670.56},{"business":"融合三期","ccy":"MOP","volume":421103025.7},{"business":"融合一期","ccy":"HKD","volume":2232.88},{"business":"收付通-智慧鹅","ccy":"AUD","volume":14524039.55},{"business":"收付通-智慧鹅","ccy":"CHF","volume":189640.78},{"business":"收付通-智慧鹅","ccy":"EUR","volume":5436303.23},{"business":"收付通-智慧鹅","ccy":"GBP","volume":23110425.07},{"business":"收付通-智慧鹅","ccy":"HKD","volume":15861502.5},{"business":"收付通-智慧鹅","ccy":"JPY","volume":1843387.63},{"business":"收付通-智慧鹅","ccy":"NZD","volume":466688.22},{"business":"收付通-智慧鹅","ccy":"SEK","volume":32672.85},{"business":"收付通-智慧鹅","ccy":"SGD","volume":309589.68},{"business":"收付通-智慧鹅","ccy":"THB","volume":33090.8},{"business":"收付通-智慧鹅","ccy":"USD","volume":77202240.51},{"business":"虾皮","ccy":"SGD","volume":120},{"business":"虾皮","ccy":"USD","volume":873716963.7}]},"mso":{"records":[{"business":"虾皮+标准收款+B2B","ccy":"AUD","volume":658511.127},{"business":"虾皮+标准收款+B2B","ccy":"CAD","volume":898996.1364},{"business":"虾皮+标准收款+B2B","ccy":"EUR","volume":4906596.232},{"business":"虾皮+标准收款+B2B","ccy":"GBP","volume":1394281.886},{"business":"虾皮+标准收款+B2B","ccy":"HKD","volume":2501854.515},{"business":"虾皮+标准收款+B2B","ccy":"JPY","volume":318331.2812},{"business":"虾皮+标准收款+B2B","ccy":"SGD","volume":102869.79},{"business":"虾皮+标准收款+B2B","ccy":"USD","volume":1138456620.99},{"business":"纯汇兑","ccy":"AUD","volume":6303521.863},{"business":"纯汇兑","ccy":"CAD","volume":16492593.82},{"business":"纯汇兑","ccy":"EUR","volume":563037327.9},{"business":"纯汇兑","ccy":"GBP","volume":291457483.5},{"business":"纯汇兑","ccy":"HKD","volume":322302980.7},{"business":"纯汇兑","ccy":"JPY","volume":30492262.91},{"business":"纯汇兑","ccy":"SEK","volume":20069331.45},{"business":"纯汇兑","ccy":"SGD","volume":15242537.79},{"business":"纯汇兑","ccy":"USD","volume":2884671014},{"business":"港陆汇款","ccy":"HKD","volume":1493208242},{"business":"留学缴费","ccy":"AUD","volume":10813793.17},{"business":"留学缴费","ccy":"CAD","volume":53476352.83},{"business":"留学缴费","ccy":"EUR","volume":1043044.66},{"business":"留学缴费","ccy":"GBP","volume":26367530.81},{"business":"留学缴费","ccy":"HKD","volume":6934094.92},{"business":"留学缴费","ccy":"JPY","volume":6067915.92},{"business":"留学缴费","ccy":"NZD","volume":2013712.78},{"business":"留学缴费","ccy":"SGD","volume":10258147.88},{"business":"留学缴费","ccy":"USD","volume":33243254.38},{"business":"钱包互联","ccy":"JPY","volume":326134.27},{"business":"钱包互联","ccy":"SGD","volume":124400.6},{"business":"钱包互联","ccy":"USD","volume":580251699.9},{"business":"收付通","ccy":"AUD","volume":16246275.72},{"business":"收付通","ccy":"CAD","volume":35410.89},{"business":"收付通","ccy":"CHF","volume":189640.78},{"business":"收付通","ccy":"EUR","volume":61899321.85},{"business":"收付通","ccy":"GBP","volume":25873107.93},{"business":"收付通","ccy":"HKD","volume":82721745.4},{"business":"收付通","ccy":"JPY","volume":63616612.71},{"business":"收付通","ccy":"NZD","volume":532558.74},{"business":"收付通","ccy":"SEK","volume":32672.85},{"business":"收付通","ccy":"SGD","volume":309589.68},{"business":"收付通","ccy":"THB","volume":33090.8},{"business":"收付通","ccy":"USD","volume":920664083.61},{"business":"跨境收单","ccy":"EUR","volume":307766602.9},{"business":"跨境收单","ccy":"GBP","volume":159211066.58},{"business":"跨境收单","ccy":"HKD","volume":2232.88},{"business":"跨境收单","ccy":"JPY","volume":18731670.56},{"business":"跨境收单","ccy":"MOP","volume":428067462.02},{"business":"跨境收单","ccy":"SGD","volume":250427338.7},{"business":"跨境收单","ccy":"THB","volume":58225812.78},{"business":"跨境收单","ccy":"USD","volume":3554625.94}]},"svf":{"records":[{"business":"跨境收单","ccy":"AED","volume":38837428.45},{"business":"跨境收单","ccy":"AUD","volume":195086171.1},{"business":"跨境收单","ccy":"CAD","volume":389299187},{"business":"跨境收单","ccy":"CHF","volume":46306766.01},{"business":"跨境收单","ccy":"DKK","volume":3086587.38},{"business":"跨境收单","ccy":"EUR","volume":35862541.1},{"business":"跨境收单","ccy":"GBP","volume":6741994.61},{"business":"跨境收单","ccy":"HKD","volume":6087986154},{"business":"跨境收单","ccy":"HUF","volume":21444.87},{"business":"跨境收单","ccy":"ISK","volume":14355.05},{"business":"跨境收单","ccy":"JPY","volume":2432707224},{"business":"跨境收单","ccy":"KRW","volume":612303564.7},{"business":"跨境收单","ccy":"KZT","volume":3739206.75},{"business":"跨境收单","ccy":"MNT","volume":4633450.74},{"business":"跨境收单","ccy":"MOP","volume":1662509965},{"business":"跨境收单","ccy":"MYR","volume":213221130.2},{"business":"跨境收单","ccy":"NOK","volume":387611.99},{"business":"跨境收单","ccy":"NZD","volume":100853534.9},{"business":"跨境收单","ccy":"PHP","volume":218869.77},{"business":"跨境收单","ccy":"QAR","volume":13705576.91},{"business":"跨境收单","ccy":"SEK","volume":1883650.64},{"business":"跨境收单","ccy":"SGD","volume":9694049.11},{"business":"跨境收单","ccy":"THB","volume":364089528.7},{"business":"跨境收单","ccy":"TRY","volume":487169.28},{"business":"跨境收单","ccy":"USD","volume":4596877939},{"business":"融合二期","ccy":"HKD","volume":857941282}]},"vol_cache":{"USD":{"realized_vol_pct":1.5122,"avg_move_bps":0.12,"max_move_bps":3.49,"data_points":1528,"data_source":"BBG-1min-MID","last_price":6.8685},"HKD":{"realized_vol_pct":1.5385,"avg_move_bps":0.12,"max_move_bps":4.64,"data_points":2671,"data_source":"BBG-1min-MID","last_price":0.87834},"EUR":{"realized_vol_pct":7.2135,"avg_move_bps":0.64,"max_move_bps":30.66,"data_points":3129,"data_source":"BBG-1min-MID","last_price":8.09805},"GBP":{"realized_vol_pct":4.2222,"avg_move_bps":0.53,"max_move_bps":6.51,"data_points":1533,"data_source":"BBG-1min-MID","last_price":9.282},"SGD":{"realized_vol_pct":5.317,"avg_move_bps":0.45,"max_move_bps":29.89,"data_points":2662,"data_source":"BBG-1min-MID","last_price":5.4281},"JPY":{"realized_vol_pct":8.129,"avg_move_bps":0.94,"max_move_bps":16.99,"data_points":1439,"data_source":"BBG-1min-MID","last_price":0.04389},"CAD":{"realized_vol_pct":5.889,"avg_move_bps":0.51,"max_move_bps":29.06,"data_points":2672,"data_source":"BBG-1min-MID","last_price":5.0169},"THB":{"realized_vol_pct":8.7418,"avg_move_bps":0.8,"max_move_bps":40.69,"data_points":2720,"data_source":"BBG-1min-MID","last_price":0.221064},"AUD":{"realized_vol_pct":8.9429,"avg_move_bps":0.89,"max_move_bps":37.52,"data_points":2672,"data_source":"BBG-1min-MID","last_price":4.87135},"SEK":{"realized_vol_pct":9.5697,"avg_move_bps":0.94,"max_move_bps":31.44,"data_points":2951,"data_source":"BBG-1min-MID","last_price":0.7598},"NZD":{"realized_vol_pct":8.9058,"avg_move_bps":0.89,"max_move_bps":48.12,"data_points":2825,"data_source":"BBG-1min-MID","last_price":4.105},"CHF":{"realized_vol_pct":8.5108,"avg_move_bps":0.74,"max_move_bps":57.35,"data_points":2824,"data_source":"BBG-1min-MID","last_price":8.877},"MOP":{"realized_vol_pct":1.5385,"avg_move_bps":0.12,"max_move_bps":4.64,"data_points":2671,"data_source":"pegged->HKD","last_price":0.87834}}};

// ═══ Engine ═══
class MarkupEngine {
  constructor(n){this.name=n;this.cells={};this.businesses=[];this.ccys=[];this.month_total=0}
  loadFromRecords(recs){
    this.cells={};const bs=new Set,cs=new Set,bt={},ct={};
    for(const r of recs){const k=r.business+'|'+r.ccy;this.cells[k]={business:r.business,ccy:r.ccy,volume:r.volume,markup_bps:0};bs.add(r.business);cs.add(r.ccy);bt[r.business]=(bt[r.business]||0)+r.volume;ct[r.ccy]=(ct[r.ccy]||0)+r.volume}
    this.businesses=[...bs].sort((a,b)=>(bt[b]||0)-(bt[a]||0));this.ccys=[...cs].sort((a,b)=>(ct[b]||0)-(ct[a]||0));this.month_total=Object.values(this.cells).reduce((s,c)=>s+c.volume,0)
  }
  calcAll(){
    let tv=0,tr=0;const bs={},cs={},co=[];
    for(const c of Object.values(this.cells)){if(c.volume<=0)continue;const r=c.volume*c.markup_bps*1e-4;co.push({business:c.business,ccy:c.ccy,volume:Math.round(c.volume),markup_bps:+c.markup_bps.toFixed(2),revenue:+r.toFixed(2)});tv+=c.volume;tr+=r;
      if(!bs[c.business])bs[c.business]={volume:0,revenue:0};bs[c.business].volume+=c.volume;bs[c.business].revenue+=r;
      if(!cs[c.ccy])cs[c.ccy]={volume:0,revenue:0};cs[c.ccy].volume+=c.volume;cs[c.ccy].revenue+=r}
    for(const s of Object.values(bs)){s.avg_markup_bps=s.volume>0?+(s.revenue/(s.volume*1e-4)).toFixed(2):0;s.volume=Math.round(s.volume);s.revenue=+s.revenue.toFixed(2);s.annual_revenue=+(s.revenue*12).toFixed(2)}
    for(const s of Object.values(cs)){s.avg_markup_bps=s.volume>0?+(s.revenue/(s.volume*1e-4)).toFixed(2):0;s.volume=Math.round(s.volume);s.revenue=+s.revenue.toFixed(2);s.annual_revenue=+(s.revenue*12).toFixed(2)}
    return{cells:co,biz_summary:bs,ccy_summary:cs,totals:{volume:Math.round(tv),revenue:+tr.toFixed(2),annual_revenue:+(tr*12).toFixed(2),avg_markup_bps:tv>0?+(tr/(tv*1e-4)).toFixed(2):0}}
  }
  getCcyVolumes(){
    const d={};for(const c of Object.values(this.cells)){if(c.volume<=0)continue;if(!d[c.ccy])d[c.ccy]={ccy:c.ccy,volume:0,markups:[]};d[c.ccy].volume+=c.volume;d[c.ccy].markups.push(c.markup_bps)}
    return this.ccys.filter(c=>d[c]).map(c=>{const x=d[c];return{ccy:c,volume:Math.round(x.volume),current_markup_bps:+(x.markups.reduce((a,b)=>a+b,0)/x.markups.length).toFixed(2)}})
  }
  getVolumeMatrix(){return{businesses:this.businesses,ccys:this.ccys,matrix:this.businesses.map(b=>this.ccys.map(c=>{const x=this.cells[b+'|'+c];return x?x.volume:0}))}}
  getMarkupMatrix(){return{businesses:this.businesses,ccys:this.ccys,matrix:this.businesses.map(b=>this.ccys.map(c=>{const x=this.cells[b+'|'+c];return x&&x.volume>0?x.markup_bps:null}))}}
  setCcyMarkup(cy,bp){for(const c of Object.values(this.cells))if(c.ccy===cy)c.markup_bps=bp}
  setBizMarkup(bz,bp){for(const c of Object.values(this.cells))if(c.business===bz)c.markup_bps=bp}
  setUniformMarkup(bp){for(const c of Object.values(this.cells))c.markup_bps=bp}
  updateCell(bz,cy,bp){const k=bz+'|'+cy;if(this.cells[k])this.cells[k].markup_bps=bp}
  scanUniform(mn,mx,st){const r=[];for(let m=mn;m<=mx+st/2;m+=st){let rv=0;for(const c of Object.values(this.cells))if(c.volume>0)rv+=c.volume*m*1e-4;r.push({markup_bps:+m.toFixed(2),revenue:+rv.toFixed(2),annual_revenue:+(rv*12).toFixed(2)})}return r}
  reset(){for(const c of Object.values(this.cells))c.markup_bps=0}
}

// ═══ Globals ═══
const engines={};let currentEntity='summary',currentData=null;
const volCache=EMBEDDED_DATA.vol_cache;
const DARK={paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{color:'#94a3b8',size:11},xaxis:{gridcolor:'#334155',zerolinecolor:'#475569'},yaxis:{gridcolor:'#334155',zerolinecolor:'#475569'},margin:{t:45,b:55,l:90,r:30}};
const COLORS=['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#06b6d4','#84cc16','#f97316','#14b8a6','#a78bfa','#fb7185','#38bdf8'];
function fmt$(v){if(Math.abs(v)>=1e8)return'¥'+(v/1e8).toFixed(2)+'亿';if(Math.abs(v)>=1e4)return'¥'+(v/1e4).toFixed(2)+'万';if(Math.abs(v)>=1e3)return'¥'+(v/1e3).toFixed(1)+'千';return'¥'+v.toFixed(0)}
function fmtV(v){if(v>=1e8)return(v/1e8).toFixed(2)+'亿';if(v>=1e4)return(v/1e4).toFixed(1)+'万';return v.toFixed(0)}
function fmtAccounting(el){const p=el.selectionStart,ol=el.value.length;let r=el.value.replace(/[^\d.]/g,'');if(!r){el.value='';return}const pts=r.split('.');pts[0]=pts[0].replace(/^0+(?=\d)/,'');pts[0]=pts[0].replace(/\B(?=(\d{3})+(?!\d))/g,',');el.value=pts.length>1?pts[0]+'.'+pts[1]:pts[0];const nl=el.value.length;el.setSelectionRange(Math.max(0,p+(nl-ol)),Math.max(0,p+(nl-ol)))}
function parseAccounting(s){return parseFloat((s||'0').replace(/,/g,''))||0}
const yAxisYi={...DARK.yaxis,ticksuffix:'亿',tickformat:',.1f'};const yAxisWan={...DARK.yaxis,ticksuffix:'万',tickformat:',.1f'};
function getEngine(){return engines[currentEntity]}

// ═══ Init ═══
function initEngines(){for(const n of['summary','mso','svf']){engines[n]=new MarkupEngine(n);engines[n].loadFromRecords(EMBEDDED_DATA[n].records)}}

function switchTab(name,el){document.querySelectorAll('[id^=tab-]').forEach(e=>e.classList.add('hidden'));document.getElementById('tab-'+name).classList.remove('hidden');document.querySelectorAll('.tab-btn').forEach(e=>e.classList.remove('active'));el.classList.add('active')}
function switchEntity(entity,el){currentEntity=entity;document.querySelectorAll('.entity-btn').forEach(e=>e.classList.remove('active'));el.classList.add('active');loadEntityData()}

function loadEntityData(){
  const eng=getEngine(),lbl={summary:'全量',mso:'MSO',svf:'SVF'}[currentEntity]||currentEntity;
  const cc=Object.values(eng.cells).filter(c=>c.volume>0).length;
  document.getElementById('month-label').textContent=EMBEDDED_DATA.month_label+' | '+lbl+' | ¥'+fmtV(eng.month_total)+' | '+cc+'组合';
  const bs=document.getElementById('biz-select');bs.innerHTML='';eng.businesses.forEach(b=>{const o=document.createElement('option');o.value=b;o.textContent=b;bs.appendChild(o)});
  const cs=document.getElementById('ccy-select');cs.innerHTML='';eng.ccys.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;cs.appendChild(o)});
  calcAll();loadCcyMarkupTab();renderMarkupMatrix()
}

function renderKPI(t){document.getElementById('kpi-volume').textContent='¥'+fmtV(t.volume);document.getElementById('kpi-avg-markup').textContent=t.avg_markup_bps+' BPS';document.getElementById('kpi-revenue').textContent=fmt$(t.revenue);document.getElementById('kpi-annual').textContent=fmt$(t.annual_revenue)}

function calcAll(){const r=getEngine().calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);renderCcyMarkupCharts(r)}

function resetAll(){getEngine().reset();calcAll();loadCcyMarkupTab();renderMarkupMatrix()}

// ═══ CCY Markup Tab ═══
function loadCcyMarkupTab(){
  const ccys=getEngine().getCcyVolumes(),mx=Math.max(...ccys.map(c=>c.volume));
  let h='<div style="display:grid;grid-template-columns:100px 1fr 200px 80px 100px;gap:0;font-size:12px;padding:4px 12px;color:#64748b;font-weight:600;margin-bottom:4px"><div>币种</div><div>占比</div><div style="text-align:right">月交易量</div><div style="text-align:center">Markup</div><div style="text-align:center">月收入</div></div>';
  ccys.forEach((c,i)=>{const p=(c.volume/mx*100).toFixed(0),r=c.volume*c.current_markup_bps*1e-4;h+=`<div class="ccy-markup-row" style="display:grid;grid-template-columns:100px 1fr 200px 80px 100px;align-items:center"><div style="font-weight:700;color:${COLORS[i%COLORS.length]}">${c.ccy}</div><div><div class="vol-bar" style="width:${Math.max(p,1)}%;background:${COLORS[i%COLORS.length]}40"></div></div><div style="text-align:right;color:#94a3b8">¥${fmtV(c.volume)}</div><div style="text-align:center"><input type="number" class="ccy-markup-input" data-ccy="${c.ccy}" value="${c.current_markup_bps}" step="0.5" min="0" style="width:60px;text-align:center"></div><div style="text-align:center;color:#10b981;font-weight:600" id="ccy-rev-${c.ccy}">${fmt$(r)}</div></div>`});
  document.getElementById('ccy-markup-list').innerHTML=h;
  document.querySelectorAll('.ccy-markup-input').forEach(inp=>{inp.addEventListener('input',()=>{const cy=inp.dataset.ccy,bp=parseFloat(inp.value)||0,obj=ccys.find(c=>c.ccy===cy);if(obj)document.getElementById('ccy-rev-'+cy).textContent=fmt$(obj.volume*bp*1e-4);let tr=0;document.querySelectorAll('.ccy-markup-input').forEach(i=>{const o=ccys.find(c=>c.ccy===i.dataset.ccy);if(o)tr+=o.volume*(parseFloat(i.value)||0)*1e-4});document.getElementById('kpi-revenue').textContent=fmt$(tr);document.getElementById('kpi-annual').textContent=fmt$(tr*12);const tv=ccys.reduce((s,c)=>s+c.volume,0);document.getElementById('kpi-avg-markup').textContent=(tv>0?tr/(tv*1e-4):0).toFixed(2)+' BPS'})})
}
function quickFillAll(){const bp=parseFloat(document.getElementById('quick-uniform-bps').value)||0;document.querySelectorAll('.ccy-markup-input').forEach(i=>{i.value=bp;i.dispatchEvent(new Event('input'))})}
function applyCcyMarkups(){const e=getEngine();document.querySelectorAll('.ccy-markup-input').forEach(i=>e.setCcyMarkup(i.dataset.ccy,parseFloat(i.value)||0));const r=e.calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);renderCcyMarkupCharts(r)}
function renderCcyMarkupCharts(d){
  const cs=d.ccy_summary,cn=Object.keys(cs).sort((a,b)=>cs[b].revenue-cs[a].revenue);
  Plotly.newPlot('chart-ccy-markup-rev',[{x:cn,y:cn.map(c=>cs[c].revenue/1e4),type:'bar',marker:{color:cn.map((_,i)=>COLORS[i%COLORS.length])},text:cn.map(c=>fmt$(cs[c].revenue)),textposition:'outside',textfont:{size:10,color:'#94a3b8'}}],{...DARK,title:{text:'月度加价收入 by 币种',font:{size:13,color:'#e2e8f0'}},yaxis:{...DARK.yaxis,ticksuffix:'万'}},{responsive:true});
  const cv=Object.keys(cs).sort((a,b)=>cs[a].volume-cs[b].volume);
  Plotly.newPlot('chart-ccy-markup-vol',[{x:cv,y:cv.map(c=>cs[c].volume/1e8),type:'bar',marker:{color:cv.map((_,i)=>COLORS[i%COLORS.length])},text:cv.map(c=>'¥'+fmtV(cs[c].volume)+'<br>'+cs[c].avg_markup_bps+'BPS'),textposition:'outside',textfont:{size:9,color:'#94a3b8'}}],{...DARK,title:{text:'月交易量 & Markup by 币种',font:{size:13,color:'#e2e8f0'}},yaxis:{...DARK.yaxis,ticksuffix:'亿'}},{responsive:true})
}

// ═══ Overview ═══
function renderOverview(d){
  const bs=d.biz_summary,cs=d.ccy_summary;
  const bv=Object.keys(bs).sort((a,b)=>bs[a].volume-bs[b].volume);Plotly.newPlot('chart-biz-volume',[{x:bv,y:bv.map(b=>bs[b].volume/1e8),type:'bar',marker:{color:bv.map((_,i)=>COLORS[i%COLORS.length])},text:bv.map(b=>'¥'+fmtV(bs[b].volume)),textposition:'outside',textfont:{size:10,color:'#94a3b8'}}],{...DARK,title:{text:'交易量 by 业务线',font:{size:13,color:'#e2e8f0'}},yaxis:yAxisYi,xaxis:{...DARK.xaxis,tickangle:-30}},{responsive:true});
  const cv=Object.keys(cs).sort((a,b)=>cs[a].volume-cs[b].volume);Plotly.newPlot('chart-ccy-volume',[{x:cv,y:cv.map(c=>cs[c].volume/1e8),type:'bar',marker:{color:cv.map((_,i)=>COLORS[i%COLORS.length])},text:cv.map(c=>'¥'+fmtV(cs[c].volume)),textposition:'outside',textfont:{size:10,color:'#94a3b8'}}],{...DARK,title:{text:'交易量 by 币种',font:{size:13,color:'#e2e8f0'}},yaxis:yAxisYi},{responsive:true});
  const br=Object.keys(bs).sort((a,b)=>bs[b].revenue-bs[a].revenue);Plotly.newPlot('chart-biz-rev',[{x:br,y:br.map(b=>bs[b].revenue/1e4),type:'bar',marker:{color:br.map((_,i)=>COLORS[i%COLORS.length])},text:br.map(b=>fmt$(bs[b].revenue)),textposition:'outside',textfont:{size:10,color:'#94a3b8'}}],{...DARK,title:{text:'收入 by 业务线',font:{size:13,color:'#e2e8f0'}},yaxis:yAxisWan,xaxis:{...DARK.xaxis,tickangle:-30}},{responsive:true});
  const cr=Object.keys(cs).sort((a,b)=>cs[b].revenue-cs[a].revenue);Plotly.newPlot('chart-ccy-rev',[{x:cr,y:cr.map(c=>cs[c].revenue/1e4),type:'bar',marker:{color:cr.map((_,i)=>COLORS[i%COLORS.length])},text:cr.map(c=>fmt$(cs[c].revenue)),textposition:'outside',textfont:{size:10,color:'#94a3b8'}}],{...DARK,title:{text:'收入 by 币种',font:{size:13,color:'#e2e8f0'}},yaxis:yAxisWan},{responsive:true});
  const vol=getEngine().getVolumeMatrix(),zR=vol.matrix.map(r=>r.map(v=>v||0)),zL=zR.map(r=>r.map(v=>v>0?Math.log10(v):0)),tx=zR.map(r=>r.map(v=>v>0?'¥'+fmtV(v):''));
  Plotly.newPlot('chart-rev-heatmap',[{z:zL,x:vol.ccys,y:vol.businesses,type:'heatmap',colorscale:[[0,'#1e293b'],[0.25,'#1e3a5f'],[0.5,'#065f46'],[0.75,'#10b981'],[1,'#34d399']],text:tx,texttemplate:'%{text}',showscale:false}],{...DARK,title:{text:'交易量 Heatmap',font:{size:13,color:'#e2e8f0'}},margin:{...DARK.margin,l:140,r:40}},{responsive:true})
}

// ═══ Matrix ═══
function renderMarkupMatrix(){
  const e=getEngine(),mk=e.getMarkupMatrix(),vol=e.getVolumeMatrix();
  let h='<table><thead><tr><th style="text-align:left">业务\\币种</th>';mk.ccys.forEach(c=>h+=`<th>${c}</th>`);h+='<th>业务量</th></tr></thead><tbody>';
  mk.businesses.forEach((biz,bi)=>{h+=`<tr><td style="font-weight:600;font-size:12px">${biz}</td>`;let bv=0;mk.ccys.forEach((ccy,ci)=>{const m=mk.matrix[bi][ci],v=vol.matrix[bi][ci];bv+=v;if(m!==null&&v>0)h+=`<td><input type="number" class="markup-input" data-biz="${biz}" data-ccy="${ccy}" value="${m.toFixed(1)}" step="0.5" min="0" style="background:#0d3320;border-color:#065f46"></td>`;else h+='<td class="text-slate-600">—</td>'});h+=`<td class="text-slate-500">¥${fmtV(bv)}</td></tr>`});
  h+='</tbody></table>';document.getElementById('markup-matrix-container').innerHTML=h
}
function applyMatrixMarkups(){const e=getEngine();document.querySelectorAll('.markup-input').forEach(i=>{const v=parseFloat(i.value);if(!isNaN(v))e.updateCell(i.dataset.biz,i.dataset.ccy,v)});const r=e.calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);loadCcyMarkupTab()}

// ═══ Detail Tables ═══
function renderBizDetail(d){const bs=d.biz_summary,bk=Object.keys(bs).sort((a,b)=>bs[b].revenue-bs[a].revenue),tr=d.totals.revenue;let h='<table><thead><tr><th style="text-align:left">业务线</th><th>月交易量</th><th>加权Markup</th><th>月度收入</th><th>年化收入</th><th>占比</th></tr></thead><tbody>';bk.forEach(b=>{const s=bs[b];h+=`<tr><td style="font-weight:600">${b}</td><td>¥${fmtV(s.volume)}</td><td class="text-blue-400">${s.avg_markup_bps} BPS</td><td class="text-emerald-400" style="font-weight:700">${fmt$(s.revenue)}</td><td class="text-amber-400">${fmt$(s.annual_revenue)}</td><td>${tr>0?(s.revenue/tr*100).toFixed(1):'—'}%</td></tr>`});const t=d.totals;h+=`<tr style="background:#334155;font-weight:700"><td>TOTAL</td><td>¥${fmtV(t.volume)}</td><td class="text-blue-400">${t.avg_markup_bps} BPS</td><td class="text-emerald-400">${fmt$(t.revenue)}</td><td class="text-amber-400">${fmt$(t.annual_revenue)}</td><td>100%</td></tr></tbody></table>`;document.getElementById('biz-detail-table').innerHTML=h}
function renderCcyDetail(d){const cs=d.ccy_summary,ck=Object.keys(cs).sort((a,b)=>cs[b].revenue-cs[a].revenue),tr=d.totals.revenue;let h='<table><thead><tr><th style="text-align:left">币种</th><th>月交易量</th><th>加权Markup</th><th>月度收入</th><th>年化收入</th><th>占比</th></tr></thead><tbody>';ck.forEach(c=>{const s=cs[c];h+=`<tr><td style="font-weight:600">${c}</td><td>¥${fmtV(s.volume)}</td><td class="text-blue-400">${s.avg_markup_bps} BPS</td><td class="text-emerald-400" style="font-weight:700">${fmt$(s.revenue)}</td><td class="text-amber-400">${fmt$(s.annual_revenue)}</td><td>${tr>0?(s.revenue/tr*100).toFixed(1):'—'}%</td></tr>`});const t=d.totals;h+=`<tr style="background:#334155;font-weight:700"><td>TOTAL</td><td>¥${fmtV(t.volume)}</td><td class="text-blue-400">${t.avg_markup_bps} BPS</td><td class="text-emerald-400">${fmt$(t.revenue)}</td><td class="text-amber-400">${fmt$(t.annual_revenue)}</td><td>100%</td></tr></tbody></table>`;document.getElementById('ccy-detail-table').innerHTML=h}

// ═══ Scenario ═══
function applyUniform(){const e=getEngine(),bp=parseFloat(document.getElementById('uniform-bps').value)||0;e.setUniformMarkup(bp);const r=e.calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);renderMarkupMatrix();loadCcyMarkupTab()}
function applyBiz(){const e=getEngine(),bz=document.getElementById('biz-select').value,bp=parseFloat(document.getElementById('biz-bps').value)||0;if(!bz)return;e.setBizMarkup(bz,bp);const r=e.calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);renderMarkupMatrix();loadCcyMarkupTab()}
function applyCcy(){const e=getEngine(),cy=document.getElementById('ccy-select').value,bp=parseFloat(document.getElementById('ccy-bps').value)||0;if(!cy)return;e.setCcyMarkup(cy,bp);const r=e.calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);renderMarkupMatrix();loadCcyMarkupTab()}
function runScan(){const sc=getEngine().scanUniform(parseFloat(document.getElementById('scan-min').value)||0,parseFloat(document.getElementById('scan-max').value)||20,0.5),x=sc.map(s=>s.markup_bps);Plotly.newPlot('chart-scan',[{x,y:sc.map(s=>s.revenue),type:'scatter',mode:'lines+markers',name:'月度',line:{color:'#3b82f6',width:2.5},marker:{size:4},fill:'tozeroy',fillcolor:'rgba(59,130,246,0.05)'},{x,y:sc.map(s=>s.annual_revenue),type:'scatter',mode:'lines',name:'年化',line:{color:'#10b981',width:2,dash:'dot'},yaxis:'y2'}],{...DARK,title:{text:'统一加价扫描',font:{size:13,color:'#e2e8f0'}},xaxis:{...DARK.xaxis,title:'BPS'},yaxis:{...DARK.yaxis,title:'月度Revenue',tickprefix:'¥',tickformat:',.0f'},yaxis2:{overlaying:'y',side:'right',title:'年化Revenue',tickprefix:'¥',tickformat:',.0f',gridcolor:'transparent'},legend:{orientation:'h',y:1.12}},{responsive:true})}

// ═══ Reverse Calc ═══
let reverseCalcData=null,selectedPlanIdx=0;
const stealthPinnedCcys=new Map();
function toggleStealthOpts(){const chk=document.querySelector('.plan-checkbox[value=stealth]');document.getElementById('stealth-options').style.display=chk.checked?'block':'none'}
function addStealthPin(){const all=['USD','HKD','EUR','GBP','MOP','SGD','JPY','CAD','THB','AUD','SEK','NZD','CHF'],av=all.filter(c=>!stealthPinnedCcys.has(c));if(!av.length){alert('所有已锁定');return}stealthPinnedCcys.set(av[0],5);renderStealthPins()}
function removeStealthPin(c){stealthPinnedCcys.delete(c);renderStealthPins()}
function updateStealthPinCcy(o,n){const b=stealthPinnedCcys.get(o)||5;stealthPinnedCcys.delete(o);stealthPinnedCcys.set(n,b);renderStealthPins()}
function updateStealthPinBps(c,b){stealthPinnedCcys.set(c,parseFloat(b)||0)}
function renderStealthPins(){const all=['USD','HKD','EUR','GBP','MOP','SGD','JPY','CAD','THB','AUD','SEK','NZD','CHF'],el=document.getElementById('stealth-pinned-list');let h='';stealthPinnedCcys.forEach((bp,cy)=>{const opts=all.filter(c=>c===cy||!stealthPinnedCcys.has(c)).map(c=>`<option value="${c}" ${c===cy?'selected':''}>${c}</option>`).join('');h+=`<div class="flex items-center gap-1" style="background:#0f172a;padding:4px 8px;border-radius:6px;border:1px solid #334155"><select onchange="updateStealthPinCcy('${cy}',this.value)" style="width:70px;font-size:11px">${opts}</select><input type="number" value="${bp}" step="0.5" min="0" max="100" style="width:55px;text-align:center;font-size:11px" onchange="updateStealthPinBps('${cy}',this.value)"><span class="text-xs text-slate-500">BPS</span><span style="cursor:pointer;color:#ef4444;font-size:14px;margin-left:2px" onclick="removeStealthPin('${cy}')">×</span></div>`});el.innerHTML=h}

function stealthOptimize(ccyList,volumes,totalVol,targetRev,maxBps,randomness,pinned){
  const big=new Set(['USD','HKD','MOP']),n=ccyList.length;
  let pinnedRev=0;const pMask=new Array(n).fill(false),pBps=new Array(n).fill(0);
  for(let i=0;i<n;i++){if(pinned[ccyList[i].ccy]!==undefined){pMask[i]=true;pBps[i]=pinned[ccyList[i].ccy];pinnedRev+=ccyList[i].volume*pBps[i]*1e-4}}
  const remTarget=targetRev-pinnedRev,freeIdx=[];for(let i=0;i<n;i++)if(!pMask[i])freeIdx.push(i);
  if(freeIdx.length===0||remTarget<=0){const res={};for(let i=0;i<n;i++)res[ccyList[i].ccy]=+pBps[i].toFixed(4);return res}
  const tbv=remTarget/1e-4,fVols=freeIdx.map(i=>ccyList[i].volume),fBig=freeIdx.map(i=>big.has(ccyList[i].ccy)?1:0);
  // Analytical: small ccys fill to max first, big ccys get remainder
  let bps=new Array(freeIdx.length).fill(0),rem=tbv;
  const smIdx=freeIdx.map((_,j)=>j).filter(j=>fBig[j]===0).sort((a,b)=>fVols[a]-fVols[b]);
  for(const j of smIdx){const f=fVols[j]>0?Math.min(maxBps,rem/fVols[j]):0;bps[j]=Math.max(0,f);rem-=fVols[j]*bps[j]}
  const bgIdx=freeIdx.map((_,j)=>j).filter(j=>fBig[j]===1);
  const bgVol=bgIdx.reduce((s,j)=>s+fVols[j],0);
  if(bgVol>0&&rem>0){const bb=Math.min(maxBps,rem/bgVol);for(const j of bgIdx)bps[j]=Math.max(0,bb)}
  // Randomness
  if(randomness>0&&freeIdx.length>1){const ns=randomness*maxBps*0.15;for(let j=0;j<bps.length;j++)bps[j]+=Math.random()*2*ns-ns;bps=bps.map(b=>Math.max(0,Math.min(maxBps,b)));const act=fVols.reduce((s,v,j)=>s+v*bps[j],0);if(act>0){const corr=tbv/act;bps=bps.map(b=>Math.max(0,Math.min(maxBps,b*corr)));const sf=tbv-fVols.reduce((s,v,j)=>s+v*bps[j],0);if(Math.abs(sf)>1){const adj=bps.map((b,j)=>b<maxBps*0.99?j:-1).filter(j=>j>=0),av=adj.reduce((s,j)=>s+fVols[j],0);if(av>0){for(const j of adj)bps[j]=Math.max(0,Math.min(maxBps,bps[j]+sf/av))}}}}
  const res={};for(let i=0;i<n;i++)res[ccyList[i].ccy]=pMask[i]?+pBps[i].toFixed(4):0;
  for(let j=0;j<freeIdx.length;j++)res[ccyList[freeIdx[j]].ccy]=+bps[j].toFixed(4);
  return res
}

function computeVolWeightedMarkups(volumes,volData,targetBps){
  const ccys=Object.keys(volumes).filter(c=>volumes[c]>0&&volData[c]);
  let tvol=0,wvol=0;const info={};
  for(const c of ccys){const v=volumes[c],vp=volData[c].realized_vol_pct;tvol+=v;wvol+=v*vp;info[c]={volume:v,vol_pct:vp}}
  const avgVol=tvol>0?wvol/tvol:1;let totalRev=0;const result={};
  for(const c of ccys){const mk=targetBps*(info[c].vol_pct/avgVol),rev=info[c].volume*mk*1e-4;totalRev+=rev;result[c]={ccy:c,volume:info[c].volume,volume_pct:+(info[c].volume/tvol*100).toFixed(2),realized_vol_pct:info[c].vol_pct,avg_move_bps:volData[c].avg_move_bps||0,suggested_markup_bps:+mk.toFixed(4),monthly_revenue:+rev.toFixed(2),data_source:volData[c].data_source||''}}
  const actAvg=tvol>0?totalRev/(tvol*1e-4):0;
  return{ccys:result,summary:{total_volume:tvol,vol_weighted_avg_pct:+(wvol/tvol).toFixed(4),actual_weighted_avg_bps:+actAvg.toFixed(4),total_monthly_revenue:+totalRev.toFixed(2),total_annual_revenue:+(totalRev*12).toFixed(2)}}
}

function runReverseCalc(){
  const sel=[];document.querySelectorAll('.plan-checkbox:checked').forEach(c=>sel.push(c.value));if(!sel.length){alert('请选方案');return}
  const target=parseAccounting(document.getElementById('rev-target-input').value);
  document.getElementById('rev-kpi-target').textContent=fmt$(target);document.getElementById('rev-kpi-annual').textContent=fmt$(target*12);
  const eng=getEngine(),ccyList=eng.getCcyVolumes(),volumes={},totalVol=ccyList.reduce((s,c)=>{volumes[c.ccy]=c.volume;return s+c.volume},0);
  document.getElementById('rev-kpi-volume').textContent='¥'+fmtV(totalVol);
  const uBps=target/(totalVol*1e-4),plans=[];
  const colorMap={uniform:'#3b82f6',vol_weight:'#10b981',big_only:'#f59e0b',small_only:'#8b5cf6',tiered:'#ec4899',stealth:'#06b6d4'};
  const iconMap={uniform:'📊',vol_weight:'📈',big_only:'🏦',small_only:'💱',tiered:'📶',stealth:'🥷'};

  if(sel.includes('uniform')){const p={id:'uniform',name:'统一加价',desc:'所有币种统一 BPS',avg_bps:+uBps.toFixed(2),monthly_rev:Math.round(target),annual_rev:Math.round(target*12),ccys:{}};ccyList.forEach(c=>{const r=c.volume*uBps*1e-4;p.ccys[c.ccy]={ccy:c.ccy,volume:c.volume,volume_pct:+(c.volume/totalVol*100).toFixed(2),markup_bps:+uBps.toFixed(2),monthly_revenue:Math.round(r)}});plans.push(p)}

  if(sel.includes('vol_weight')){const vr=computeVolWeightedMarkups(volumes,volCache,uBps);const p={id:'vol_weight',name:'波动率加权',desc:'高波动多加、低波动少加',avg_bps:+vr.summary.actual_weighted_avg_bps.toFixed(2),monthly_rev:Math.round(vr.summary.total_monthly_revenue),annual_rev:Math.round(vr.summary.total_annual_revenue),ccys:{}};for(const[c,i] of Object.entries(vr.ccys))p.ccys[c]={ccy:c,volume:i.volume,volume_pct:i.volume_pct,markup_bps:i.suggested_markup_bps,monthly_revenue:Math.round(i.monthly_revenue)};plans.push(p)}

  if(sel.includes('big_only')){const bc=['USD','HKD','EUR','MOP'],bv=bc.reduce((s,c)=>s+(volumes[c]||0),0),bb=bv>0?target/(bv*1e-4):0;const p={id:'big_only',name:'只加大币种',desc:`仅 ${bc.join(',')}`,avg_bps:+uBps.toFixed(2),big_bps:+bb.toFixed(2),monthly_rev:Math.round(target),annual_rev:Math.round(target*12),ccys:{}};ccyList.forEach(c=>{const ib=bc.includes(c.ccy),bp=ib?bb:0,r=c.volume*bp*1e-4;p.ccys[c.ccy]={ccy:c.ccy,volume:c.volume,volume_pct:+(c.volume/totalVol*100).toFixed(2),markup_bps:+bp.toFixed(2),monthly_revenue:Math.round(r)}});plans.push(p)}

  if(sel.includes('small_only')){const sc=ccyList.filter(c=>!['USD','HKD','MOP'].includes(c.ccy)).map(c=>c.ccy),sv=sc.reduce((s,c)=>s+(volumes[c]||0),0),sb=sv>0?target/(sv*1e-4):0;const p={id:'small_only',name:'只加小币种',desc:'USD/HKD/MOP 不加',avg_bps:+uBps.toFixed(2),small_bps:+sb.toFixed(2),monthly_rev:Math.round(target),annual_rev:Math.round(target*12),ccys:{}};ccyList.forEach(c=>{const is=sc.includes(c.ccy),bp=is?sb:0,r=c.volume*bp*1e-4;p.ccys[c.ccy]={ccy:c.ccy,volume:c.volume,volume_pct:+(c.volume/totalVol*100).toFixed(2),markup_bps:+bp.toFixed(2),monthly_revenue:Math.round(r)}});plans.push(p)}

  if(sel.includes('tiered')){const st=['USD','HKD','MOP'],sv=st.reduce((s,c)=>s+(volumes[c]||0),0),vv=totalVol-sv,mul=3,bb=target/((sv+mul*vv)*1e-4);const p={id:'tiered',name:'阶梯式加价',desc:`稳定 ${(+bb.toFixed(2))} BPS / 其余 ${(+(bb*mul).toFixed(2))} BPS`,avg_bps:+uBps.toFixed(2),monthly_rev:0,annual_rev:0,ccys:{}};let tr=0;ccyList.forEach(c=>{const is=st.includes(c.ccy),bp=is?bb:bb*mul,r=c.volume*bp*1e-4;tr+=r;p.ccys[c.ccy]={ccy:c.ccy,volume:c.volume,volume_pct:+(c.volume/totalVol*100).toFixed(2),markup_bps:+bp.toFixed(2),monthly_revenue:Math.round(r)}});p.monthly_rev=Math.round(tr);p.annual_rev=Math.round(tr*12);plans.push(p)}

  if(sel.includes('stealth')){const mxBps=parseFloat(document.getElementById('stealth-max-bps').value)||20,rnd=parseFloat(document.getElementById('stealth-randomness').value)||0;const pin={};stealthPinnedCcys.forEach((b,c)=>pin[c]=b);
    const bpsMap=stealthOptimize(ccyList,volumes,totalVol,target,mxBps,rnd,pin);const bigS=new Set(['USD','HKD','MOP']);let tr=0,bgA=0,smA=0,bgV=0,smV=0;
    const p={id:'stealth',name:'隐蔽式加价',desc:`上限${mxBps}BPS${Object.keys(pin).length?'，锁定'+Object.keys(pin).join(','):''}${rnd>0?'，随机'+Math.round(rnd*100)+'%':''}`,avg_bps:+uBps.toFixed(2),monthly_rev:0,annual_rev:0,ccys:{}};
    ccyList.forEach(c=>{const bp=bpsMap[c.ccy]||0,r=c.volume*bp*1e-4;tr+=r;const ib=bigS.has(c.ccy);if(ib){bgA+=c.volume*bp;bgV+=c.volume}else{smA+=c.volume*bp;smV+=c.volume}p.ccys[c.ccy]={ccy:c.ccy,volume:c.volume,volume_pct:+(c.volume/totalVol*100).toFixed(2),markup_bps:+bp.toFixed(2),monthly_revenue:Math.round(r),group:ib?'big':'small',pinned:pin[c.ccy]!==undefined}});
    p.monthly_rev=Math.round(tr);p.annual_rev=Math.round(tr*12);p.big_avg_bps=bgV>0?+(bgA/bgV).toFixed(2):0;p.small_avg_bps=smV>0?+(smA/smV).toFixed(2):0;plans.push(p)}

  reverseCalcData={plans,target_monthly_rev:target,total_volume:totalVol};selectedPlanIdx=0;renderReversePlans(reverseCalcData)
}

function renderReversePlans(data){
  const plans=data.plans,colorMap={uniform:'#3b82f6',vol_weight:'#10b981',big_only:'#f59e0b',small_only:'#8b5cf6',tiered:'#ec4899',stealth:'#06b6d4'},iconMap={uniform:'📊',vol_weight:'📈',big_only:'🏦',small_only:'💱',tiered:'📶',stealth:'🥷'};
  const cols=Math.min(plans.length,6);let h=`<div class="grid gap-3" style="grid-template-columns:repeat(${cols},1fr)">`;
  plans.forEach((p,i)=>{const color=colorMap[p.id]||'#3b82f6',icon=iconMap[p.id]||'📊',ia=i===selectedPlanIdx,brd=ia?`border:2px solid ${color}`:'border:1px solid #334155',glow=ia?`box-shadow:0 0 15px ${color}33`:'';
    const bl=Object.values(p.ccys).map(c=>c.markup_bps).filter(b=>b>0),mx=bl.length?Math.max(...bl):0,mn=bl.length?Math.min(...bl):0;
    h+=`<div class="card p-3 cursor-pointer" style="${brd};${glow}" onclick="selectPlan(${i})"><div class="flex items-center gap-2 mb-2"><span style="font-size:18px">${icon}</span><span class="text-xs font-bold" style="color:${color}">${p.name}</span></div><div class="text-xs text-slate-500 mb-2" style="min-height:32px">${p.desc}</div><div class="text-xs text-slate-400">加权平均</div><div class="text-lg font-bold" style="color:${color}">${p.avg_bps} BPS</div><div class="text-xs text-slate-500 mt-1">范围: ${mn.toFixed(1)} ~ ${mx.toFixed(1)} BPS</div>`;
    if(p.id==='stealth'&&p.big_avg_bps!==undefined)h+=`<div class="text-xs mt-1" style="color:#94a3b8">大币种: <span style="color:#10b981;font-weight:700">${p.big_avg_bps} BPS</span> | 小币种: <span style="color:#f59e0b;font-weight:700">${p.small_avg_bps} BPS</span></div>`;
    h+=`<div class="text-xs text-emerald-400 mt-1 font-bold">${fmt$(p.monthly_rev)}/月</div><button class="btn btn-sm mt-2 w-full" style="background:${color}22;color:${color};border:1px solid ${color}44" onclick="event.stopPropagation();applyPlan(${i})">应用此方案</button></div>`});
  h+='</div>';document.getElementById('rev-plans-container').innerHTML=h;
  if(plans.length>0)renderPlanDetail(plans[selectedPlanIdx]);renderReverseCharts(data)
}
function selectPlan(i){selectedPlanIdx=i;if(reverseCalcData)renderReversePlans(reverseCalcData)}
function applyPlan(i){if(!reverseCalcData)return;const p=reverseCalcData.plans[i],e=getEngine();for(const[c,info] of Object.entries(p.ccys))e.setCcyMarkup(c,info.markup_bps);const r=e.calcAll();currentData=r;renderKPI(r.totals);renderOverview(r);renderBizDetail(r);renderCcyDetail(r);renderMarkupMatrix();loadCcyMarkupTab();renderCcyMarkupCharts(r)}
function renderPlanDetail(plan){
  const sorted=Object.values(plan.ccys).sort((a,b)=>b.volume-a.volume);let h=`<div class="text-xs font-bold text-slate-400 mb-2">${plan.name} — 明细</div><table><thead><tr><th style="text-align:left">币种</th><th>月交易量</th><th>占比</th><th style="color:#3b82f6">加价(BPS)</th><th>月收入</th><th>年收入</th></tr></thead><tbody>`;let tr=0;
  sorted.forEach(c=>{tr+=c.monthly_revenue;const bc=c.markup_bps>0?(c.markup_bps>5?'text-red-400':c.markup_bps>2?'text-amber-400':'text-blue-400'):'text-slate-600';const pi=c.pinned?'<span title="锁定" style="font-size:10px">🔒</span> ':'';h+=`<tr><td style="font-weight:700">${c.ccy}</td><td>¥${fmtV(c.volume)}</td><td>${c.volume_pct}%</td><td class="${bc}" style="font-weight:700;font-size:14px">${pi}${c.markup_bps.toFixed(2)} BPS</td><td class="text-emerald-400">${fmt$(c.monthly_revenue)}</td><td class="text-amber-400">${fmt$(c.monthly_revenue*12)}</td></tr>`});
  h+=`<tr style="background:#334155;font-weight:700"><td>TOTAL</td><td>¥${fmtV(sorted.reduce((s,c)=>s+c.volume,0))}</td><td>100%</td><td class="text-blue-400">${plan.avg_bps} BPS</td><td class="text-emerald-400">${fmt$(tr)}</td><td class="text-amber-400">${fmt$(tr*12)}</td></tr></tbody></table>`;
  document.getElementById('rev-plan-detail').innerHTML=h
}
function renderReverseCharts(data){
  const plans=data.plans,colorMap={uniform:'#3b82f6',vol_weight:'#10b981',big_only:'#f59e0b',small_only:'#8b5cf6',tiered:'#ec4899',stealth:'#06b6d4'};
  const pn=plans.map(p=>p.name),pc=plans.map(p=>colorMap[p.id]||'#3b82f6');
  Plotly.newPlot('chart-rev-compare',[{x:pn,y:plans.map(p=>p.avg_bps),type:'bar',marker:{color:pc},text:plans.map(p=>p.avg_bps+' BPS'),textposition:'outside',textfont:{size:11,color:'#e2e8f0'}}],{...DARK,title:{text:'各方案加权平均 Markup',font:{size:13,color:'#e2e8f0'}},yaxis:{...DARK.yaxis,title:'BPS'}},{responsive:true});
  const ac=[...new Set(plans.flatMap(p=>Object.keys(p.ccys)))].sort((a,b)=>{const va=plans[0].ccys[a]?.volume||0,vb=plans[0].ccys[b]?.volume||0;return vb-va});
  const traces=plans.map((p,i)=>({x:ac,y:ac.map(c=>p.ccys[c]?.markup_bps||0),type:'bar',name:p.name,marker:{color:pc[i]+'99'}}));
  Plotly.newPlot('chart-rev-ccy-compare',traces,{...DARK,title:{text:'各方案×各币种 Markup',font:{size:13,color:'#e2e8f0'}},yaxis:{...DARK.yaxis,title:'BPS'},barmode:'group',legend:{orientation:'h',y:1.15,font:{size:10,color:'#94a3b8'}}},{responsive:true})
}

// ═══ Vol Weight Tab ═══
function renderVolRawTable(){
  const data=volCache,ccyKeys=Object.keys(data).sort((a,b)=>(data[b].realized_vol_pct||0)-(data[a].realized_vol_pct||0));
  let h='<div class="text-xs font-bold text-slate-400 mb-2">各币种波动率数据 (按波动率降序)</div><table><thead><tr><th style="text-align:left">币种</th><th>年化波动率</th><th>10min均幅(BPS)</th><th>10min最大幅</th><th>数据点</th><th>来源</th><th>最新价</th></tr></thead><tbody>';
  ccyKeys.forEach(c=>{const v=data[c],vp=v.realized_vol_pct||0,vc=vp>5?'text-red-400':vp>2?'text-amber-400':'text-emerald-400';h+=`<tr><td style="font-weight:700">${c}</td><td class="${vc}" style="font-weight:700;font-size:14px">${vp.toFixed(2)}%</td><td>${(v.avg_move_bps||0).toFixed(2)}</td><td>${(v.max_move_bps||0).toFixed(1)}</td><td>${(v.data_points||0).toLocaleString()}</td><td class="text-slate-500" style="font-size:10px">${v.data_source||'—'}</td><td>${v.last_price||'—'}</td></tr>`});
  h+='</tbody></table>';document.getElementById('vol-raw-data-table').innerHTML=h
}
function loadVolSuggestion(){
  const target=parseFloat(document.getElementById('vol-target-bps').value)||0.5;
  document.getElementById('vol-kpi-target').textContent=target.toFixed(2)+' BPS';
  const vols={};getEngine().getCcyVolumes().forEach(c=>vols[c.ccy]=c.volume);
  const r=computeVolWeightedMarkups(vols,volCache,target);
  document.getElementById('vol-kpi-actual').textContent=r.summary.actual_weighted_avg_bps.toFixed(4)+' BPS';
  document.getElementById('vol-kpi-monthly').textContent=fmt$(r.summary.total_monthly_revenue);
  document.getElementById('vol-kpi-annual2').textContent=fmt$(r.summary.total_annual_revenue);
  const sorted=Object.values(r.ccys).sort((a,b)=>b.volume-a.volume);
  let h='<table><thead><tr><th style="text-align:left">币种</th><th>月交易量</th><th>占比</th><th>波动率</th><th>均幅(BPS)</th><th style="color:#3b82f6">建议Markup</th><th>月收入</th><th>来源</th></tr></thead><tbody>';
  sorted.forEach(c=>{const vc=c.realized_vol_pct>3?'text-red-400':c.realized_vol_pct>1.5?'text-amber-400':'text-emerald-400';h+=`<tr><td style="font-weight:700">${c.ccy}</td><td>¥${fmtV(c.volume)}</td><td>${c.volume_pct}%</td><td class="${vc}" style="font-weight:700">${c.realized_vol_pct.toFixed(2)}%</td><td>${c.avg_move_bps.toFixed(1)}</td><td class="text-blue-400" style="font-weight:700;font-size:14px">${c.suggested_markup_bps.toFixed(2)} BPS</td><td class="text-emerald-400">${fmt$(c.monthly_revenue)}</td><td class="text-slate-500" style="font-size:10px">${c.data_source||'—'}</td></tr>`});
  h+=`<tr style="background:#334155;font-weight:700"><td>TOTAL</td><td>¥${fmtV(r.summary.total_volume)}</td><td>100%</td><td>${r.summary.vol_weighted_avg_pct.toFixed(2)}%</td><td>—</td><td class="text-blue-400">${r.summary.actual_weighted_avg_bps.toFixed(2)} BPS</td><td class="text-emerald-400">${fmt$(r.summary.total_monthly_revenue)}</td><td>—</td></tr></tbody></table>`;
  document.getElementById('vol-suggest-table').innerHTML=h;
  const mx=Math.max(...sorted.map(c=>c.volume));
  Plotly.newPlot('chart-vol-scatter',[{x:sorted.map(c=>c.realized_vol_pct),y:sorted.map(c=>c.suggested_markup_bps),mode:'markers+text',type:'scatter',text:sorted.map(c=>c.ccy),textposition:'top center',textfont:{size:11,color:'#e2e8f0'},marker:{size:sorted.map(c=>Math.max(10,Math.sqrt(c.volume/mx)*60)),color:sorted.map(c=>c.realized_vol_pct),colorscale:[[0,'#3b82f6'],[0.5,'#f59e0b'],[1,'#ef4444']],showscale:true,colorbar:{title:{text:'Vol%',font:{size:10,color:'#94a3b8'}}},line:{width:1,color:'#1e293b'}}}],{...DARK,title:{text:'波动率 vs 建议Markup',font:{size:13,color:'#e2e8f0'}},xaxis:{...DARK.xaxis,title:'年化波动率(%)'},yaxis:{...DARK.yaxis,title:'建议Markup(BPS)'}},{responsive:true});
  const bv=Object.values(r.ccys).sort((a,b)=>a.realized_vol_pct-b.realized_vol_pct);
  Plotly.newPlot('chart-vol-markup-bar',[{x:bv.map(c=>c.ccy),y:bv.map(c=>c.realized_vol_pct),type:'bar',name:'波动率(%)',marker:{color:'rgba(59,130,246,0.4)'},yaxis:'y'},{x:bv.map(c=>c.ccy),y:bv.map(c=>c.suggested_markup_bps),type:'scatter',mode:'lines+markers',name:'Markup(BPS)',line:{color:'#10b981',width:3},marker:{size:8,color:'#10b981'},yaxis:'y2'}],{...DARK,title:{text:'波动率排序 & 建议Markup',font:{size:13,color:'#e2e8f0'}},yaxis:{...DARK.yaxis,title:'波动率(%)',side:'left'},yaxis2:{overlaying:'y',side:'right',title:'Markup(BPS)',gridcolor:'transparent',tickfont:{color:'#10b981'}},legend:{orientation:'h',y:1.12,font:{color:'#94a3b8'}}},{responsive:true})
}
function applyVolSuggestion(){
  const target=parseFloat(document.getElementById('vol-target-bps').value)||0.5,vols={},eng=getEngine();
  eng.getCcyVolumes().forEach(c=>vols[c.ccy]=c.volume);
  const r=computeVolWeightedMarkups(vols,volCache,target);
  for(const[c,i] of Object.entries(r.ccys))eng.setCcyMarkup(c,i.suggested_markup_bps);
  const res=eng.calcAll();currentData=res;renderKPI(res.totals);renderOverview(res);renderBizDetail(res);renderCcyDetail(res);renderMarkupMatrix();loadCcyMarkupTab();loadVolSuggestion()
}

// ═══ Boot ═══
initEngines();renderVolRawTable();loadEntityData();
