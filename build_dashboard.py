#!/usr/bin/env python3
"""
Dashboard builder for the Innimmo Activist Screener (T-AI-10).

Reads the rich JSON (innimmo_watchlist_data.json) produced by
activist_screener.py and writes a single self-contained dashboard — no server,
no external files, no internet. Each name gets its metric set, five sub-scores,
and a REAL price chart (1-year line with 50/200-day moving averages plus
support & resistance levels) drawn client-side from the price series.

Usage:
    python build_dashboard.py                       # from default JSON
    python build_dashboard.py data.json out.html
    python build_dashboard.py --fragment            # body-only (for Artifact)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

DEFAULT_JSON = "innimmo_watchlist_data.json"
DEFAULT_HTML = "dashboard.html"

# --------------------------------------------------------------------------- #
CSS = r"""
:root{
  --paper:#f4f6f8;--card:#fff;--ink:#191d23;--muted:#5f6a76;--line:#e3e7eb;
  --line2:#d3d9df;--accent:#7d2b3a;--accent2:#7d2b3a;
  --s-lo:#9a6a15;--s-mid:#2f7d55;--s-hi:#17663f;--pos:#2f7d55;--neg:#9c3a48;
  --track:#eceef1;--ma50:#2f6f8f;--ma200:#b4531f;
  --shadow:0 1px 2px rgba(20,30,45,.05),0 4px 14px rgba(20,30,45,.05);
  --serif:Calibri,Carlito,"Segoe UI",-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;
  --sans:Calibri,Carlito,"Segoe UI",-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"Cascadia Code","SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --paper:#13171c;--card:#1b2027;--ink:#e7eaee;--muted:#98a2ae;--line:#2a313a;
  --line2:#39424d;--accent:#cf6478;--accent2:#e08596;--s-lo:#b8842a;
  --s-mid:#3f9d6c;--s-hi:#2f8a58;--pos:#3f9d6c;--neg:#d46f81;--track:#252c34;
  --ma50:#5aa6c9;--ma200:#d9793f;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.28);}}
:root[data-theme="light"]{--paper:#f4f6f8;--card:#fff;--ink:#191d23;--muted:#5f6a76;
  --line:#e3e7eb;--line2:#d3d9df;--accent:#7d2b3a;--accent2:#7d2b3a;--s-lo:#9a6a15;
  --s-mid:#2f7d55;--s-hi:#17663f;--pos:#2f7d55;--neg:#9c3a48;--track:#eceef1;
  --ma50:#2f6f8f;--ma200:#b4531f;--shadow:0 1px 2px rgba(20,30,45,.05),0 4px 14px rgba(20,30,45,.05);}
:root[data-theme="dark"]{--paper:#13171c;--card:#1b2027;--ink:#e7eaee;--muted:#98a2ae;
  --line:#2a313a;--line2:#39424d;--accent:#cf6478;--accent2:#e08596;--s-lo:#b8842a;
  --s-mid:#3f9d6c;--s-hi:#2f8a58;--pos:#3f9d6c;--neg:#d46f81;--track:#252c34;
  --ma50:#5aa6c9;--ma200:#d9793f;--shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.28);}

*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:36px 22px 72px}
.mast{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;
  flex-wrap:wrap;padding-bottom:14px;border-bottom:2px solid var(--accent)}
.word{font-family:var(--serif);font-size:30px;line-height:1.05;margin:0;
  letter-spacing:-.01em;font-weight:700}
.word em{font-style:italic;color:var(--accent2);font-weight:700}
.kicker{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 0 6px}
.themebtn{font-family:var(--sans);font-size:12px;color:var(--muted);background:transparent;
  border:1px solid var(--line2);border-radius:7px;padding:7px 12px;cursor:pointer}
.themebtn:hover{color:var(--ink);border-color:var(--muted)}
.themebtn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.sub{color:var(--muted);font-size:12.5px;margin:12px 0 4px}
.sub b{color:var(--ink);font-weight:600}
.live{display:inline-flex;align-items:center;gap:6px;color:var(--s-mid);font-weight:600}
.live .dot{width:7px;height:7px;border-radius:50%;background:var(--s-mid)}
.note{color:var(--muted);font-size:12px;margin:2px 0 24px;font-style:italic}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:24px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 17px;box-shadow:var(--shadow)}
.kpi .l{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.kpi .v{font-family:var(--mono);font-size:25px;font-weight:600;margin-top:7px;letter-spacing:-.02em}
.kpi .v small{font-family:var(--sans);font-size:13px;color:var(--muted);font-weight:500;margin-left:4px}

.divers{background:var(--card);border:1px solid var(--line);border-radius:12px;
  box-shadow:var(--shadow);padding:16px 18px;margin-bottom:24px}
.divers h3{font-family:var(--serif);font-size:15px;margin:0 0 4px}
.divers .verdict{font-size:13px;margin:0 0 12px}
.divers .verdict b{font-weight:700}
.divers .cols{display:grid;grid-template-columns:1fr 1fr;gap:18px 26px}
@media (max-width:720px){.divers .cols{grid-template-columns:1fr}}
.divers .lab{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.drow{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:12.5px}
.drow .nm{width:130px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.drow .bar{flex:1;height:9px;background:var(--track);border-radius:4px;overflow:hidden}
.drow .bar b{display:block;height:100%;border-radius:4px;background:var(--accent)}
.drow .pc{width:64px;text-align:right;font-family:var(--mono);color:var(--muted)}
.conc-hi{color:var(--neg);font-weight:700}.conc-mid{color:var(--s-lo);font-weight:700}.conc-lo{color:var(--s-mid);font-weight:700}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.toolbar .count{font-size:12.5px;color:var(--muted)}
#search{font-family:var(--sans);font-size:14px;color:var(--ink);background:var(--card);
  border:1px solid var(--line2);border-radius:9px;padding:9px 13px;width:300px;max-width:100%}
#search:focus-visible{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}

.card{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);overflow-x:auto}
table{width:100%;border-collapse:collapse;min-width:1000px}
thead th{position:sticky;top:0;background:var(--card);z-index:1;font-size:11px;letter-spacing:.04em;
  text-transform:uppercase;color:var(--muted);font-weight:600;text-align:left;padding:13px 14px;
  cursor:pointer;white-space:nowrap;border-bottom:1px solid var(--line2);user-select:none}
thead th:hover{color:var(--ink)}
th.r,td.r{text-align:right}
th .arw{opacity:0;margin-left:3px}th.asc .arw,th.desc .arw{opacity:.7;display:inline-block}
th.desc .arw{transform:rotate(180deg)}
tbody td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr.main:hover{background:color-mix(in srgb,var(--accent) 4%,transparent)}
tbody tr.main{cursor:pointer}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.co{font-weight:600}.tkr{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:2px}
.meta{font-size:11px;color:var(--muted);margin-top:2px}

.chip{display:inline-block;min-width:40px;text-align:center;padding:3px 9px;border-radius:6px;
  color:#fff;font-weight:700;font-size:13px;font-family:var(--mono)}
.expand{color:var(--muted);font-family:var(--mono);font-size:12px}

.mini{display:flex;gap:3px;align-items:flex-end;height:26px}
.mini i{width:8px;background:var(--track);border-radius:2px 2px 0 0;position:relative}
.mini i b{position:absolute;bottom:0;left:0;right:0;border-radius:2px 2px 0 0;display:block}

.trend-up{color:var(--s-hi);font-weight:600}.trend-dn{color:var(--neg);font-weight:600}
.trend-rg{color:var(--muted)}
.tag{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.03em;padding:2px 7px;
  border-radius:5px;text-transform:uppercase}
.tag.bo{background:color-mix(in srgb,var(--pos) 18%,transparent);color:var(--pos)}
.tag.bd{background:color-mix(in srgb,var(--neg) 18%,transparent);color:var(--neg)}
.ctrl{display:inline-block;font-size:10.5px;font-weight:600;padding:2px 7px;border-radius:5px;
  border:1px solid var(--line2);color:var(--muted);white-space:nowrap}
.ctrl.blocked{border-color:var(--neg);color:var(--neg);
  background:color-mix(in srgb,var(--neg) 8%,transparent)}
.ctrl.open{border-color:var(--s-mid);color:var(--s-mid);
  background:color-mix(in srgb,var(--s-mid) 8%,transparent)}
.delta{font-family:var(--mono);font-size:11px;margin-left:6px}
.delta.up{color:var(--pos)}.delta.dn{color:var(--neg)}
.conf{display:inline-block;font-size:10.5px;font-weight:600;padding:2px 7px;border-radius:5px}
.conf.high{background:color-mix(in srgb,var(--s-mid) 15%,transparent);color:var(--s-mid)}
.conf.medium{background:color-mix(in srgb,var(--s-lo) 15%,transparent);color:var(--s-lo)}
.conf.low{background:color-mix(in srgb,var(--neg) 15%,transparent);color:var(--neg)}
.flags{margin-top:12px;font-size:12px}
.flag{display:block;color:var(--neg);margin:2px 0}
.flag.info{color:var(--muted)}

.detail{background:color-mix(in srgb,var(--accent) 2.5%,transparent)}
/* Pin the expanded panel to the left edge and cap it to the visible width so it
   never runs off the right with the wide, horizontally-scrolling table. */
.detail td{padding:0;position:sticky;left:0}
.panel{display:grid;grid-template-columns:1.15fr .85fr;gap:22px;padding:20px 22px;
  width:calc(min(100vw,1240px) - 46px);box-sizing:border-box}
@media (max-width:840px){.panel{grid-template-columns:1fr}}
.panel h3{font-family:var(--serif);font-size:16px;margin:0 0 10px}
.chartwrap{border:1px solid var(--line);border-radius:10px;padding:12px 12px 6px;background:var(--card)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);margin-top:8px}
.legend span{display:inline-flex;align-items:center;gap:5px}
.legend i{width:14px;height:0;border-top-width:2px;border-top-style:solid;display:inline-block}
.legend i.dash{border-top-style:dashed}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:6px 22px;font-size:13px}
.grid2 .k{color:var(--muted)}.grid2 .val{font-family:var(--mono);text-align:right}
.subrow{display:flex;align-items:center;gap:10px;margin:5px 0}
.subrow .lab{width:78px;font-size:12px;color:var(--muted)}
.subrow .bar{flex:1;height:8px;background:var(--track);border-radius:4px;overflow:hidden}
.subrow .bar b{display:block;height:100%;border-radius:4px}
.subrow .sc{width:26px;text-align:right;font-family:var(--mono);font-size:12.5px}
.thesis{margin-top:14px;font-size:13.5px;line-height:1.6}
.thesis .lab{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.macro{margin-top:12px;font-size:12px;color:var(--muted);line-height:1.55;font-style:italic}
footer{color:var(--muted);font-size:12px;margin-top:22px;line-height:1.6}
@media (prefers-reduced-motion:no-preference){.kpi,tbody tr.main{transition:background .15s ease}}
"""

# --------------------------------------------------------------------------- #
# Streamlit embeds this page in an iframe. Left at a fixed height it gets its own
# inner scrollbar, so the user has to scroll twice — once for the page, once
# inside the frame. Streamlit's component protocol accepts a
# "streamlit:setFrameHeight" postMessage (the same mechanism
# Streamlit.setFrameHeight() uses), so the page reports its true height and the
# frame grows to fit — leaving a single page scrollbar. Re-measured on load, on
# resize, and after clicks, because table rows expand on click. Harmless when the
# page is opened directly as a file: window.parent is itself and the message is
# simply ignored.
AUTOHEIGHT_JS = r"""
(function(){
  function send(){
    var h = Math.max(document.documentElement.scrollHeight,
                     document.body ? document.body.scrollHeight : 0);
    try{
      window.parent.postMessage({isStreamlitMessage:true,
        type:"streamlit:setFrameHeight", height:h + 8}, "*");
    }catch(e){}
  }
  send();
  window.addEventListener("load", send);
  window.addEventListener("resize", send);
  if (window.ResizeObserver){
    var ro = new ResizeObserver(send);
    ro.observe(document.documentElement);
    if (document.body) ro.observe(document.body);
  }
  document.addEventListener("click", function(){ setTimeout(send, 60); });
})();
"""

JS = r"""
const DATA = __DATA__;
window.__REVIEWS__ = __REVIEWS_JSON__;
const $ = (s,el=document)=>el.querySelector(s);
const fmt=(v,d=2)=>v==null||v!==v?'n/a':Number(v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});
const pctf=(v)=>v==null||v!==v?'n/a':(v*100).toFixed(1)+'%';
const money=(v)=>{if(v==null)return 'n/a';const a=Math.abs(v);const s=v<0?'-':'';
  if(a>=1e9)return s+(a/1e9).toFixed(2)+'B';if(a>=1e6)return s+(a/1e6).toFixed(0)+'M';return s+a.toFixed(0);};
const scoreColor=(s)=>s>=4.5?'var(--s-hi)':s>=3.5?'var(--s-mid)':'var(--s-lo)';
const tgtpc=(t,p)=>{if(t==null||p==null||!p)return 'n/a';const v=(t/p-1)*100;
  const col=v>=0?'var(--pos)':'var(--neg)';return `<span style="color:${col}">${v>=0?'+':''}${v.toFixed(0)}%</span>`;};

function trendClass(t){return t==='Uptrend'?'trend-up':t==='Downtrend'?'trend-dn':'trend-rg';}

/* ---- price chart: line + 50/200 MA + support/resistance + volume ---- */
function chart(c){
  const W=560,H=260,padL=48,padR=14,padT=12,padB=34,volH=40;
  const close=c.chart_close||[];
  if(close.length<2)return '<div style="color:var(--muted);font-size:13px">No price history.</div>';
  const s50=c.chart_sma50||[],s200=c.chart_sma200||[],vols=c.chart_volume||[];
  const levels=[c.support,c.resistance,c.high52,c.low52].filter(v=>v!=null);
  let lo=Math.min(...close,...levels),hi=Math.max(...close,...levels);
  const pad=(hi-lo)*0.06||1;lo-=pad;hi+=pad;
  const n=close.length;
  const priceBottom=H-padB-volH;
  const X=i=>padL+(W-padL-padR)*i/(n-1);
  const Y=v=>padT+(priceBottom-padT)*(1-(v-lo)/(hi-lo));
  const vmax=Math.max(1,...vols.filter(v=>v!=null));
  const VY=v=>(v==null?0:(volH*v/vmax));
  const barW=Math.max(1,(W-padL-padR)/n*0.7);
  const volBars=vols.map((v,i)=>v==null?'':`<rect x="${(X(i)-barW/2).toFixed(1)}" y="${(H-padB-VY(v)).toFixed(1)}" width="${barW.toFixed(1)}" height="${VY(v).toFixed(1)}" fill="var(--muted)" opacity="0.28"/>`).join('');
  const path=(arr)=>{let d='',started=false;arr.forEach((v,i)=>{if(v==null||v!==v){return;}
    d+=(started?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';started=true;});return d;};
  const area=()=>{let d='M'+X(0).toFixed(1)+' '+Y(close[0]).toFixed(1)+' ';
    close.forEach((v,i)=>d+='L'+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ');
    d+='L'+X(n-1).toFixed(1)+' '+priceBottom+' L'+X(0).toFixed(1)+' '+priceBottom+' Z';return d;};
  const gy=[lo,(lo+hi)/2,hi];
  const grid=gy.map(v=>`<line x1="${padL}" y1="${Y(v).toFixed(1)}" x2="${W-padR}" y2="${Y(v).toFixed(1)}" stroke="var(--line)" stroke-width="1"/><text x="${padL-6}" y="${(Y(v)+3).toFixed(1)}" text-anchor="end" font-size="10" fill="var(--muted)" font-family="var(--mono)">${fmt(v,1)}</text>`).join('');
  const level=(v,label,color,dash)=>v==null?'':`<line x1="${padL}" y1="${Y(v).toFixed(1)}" x2="${W-padR}" y2="${Y(v).toFixed(1)}" stroke="${color}" stroke-width="1.2" stroke-dasharray="${dash}"/><text x="${W-padR}" y="${(Y(v)-4).toFixed(1)}" text-anchor="end" font-size="9.5" fill="${color}" font-family="var(--mono)">${label} ${fmt(v,1)}</text>`;
  const dates=c.chart_dates||[];
  const xlab=(i)=>dates[i]?`<text x="${X(i).toFixed(1)}" y="${H-6}" text-anchor="middle" font-size="10" fill="var(--muted)" font-family="var(--mono)">${dates[i].slice(0,7)}</text>`:'';
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Price chart for ${c.ticker}">
    ${grid}
    ${volBars}
    <text x="${padL-6}" y="${(H-padB-2).toFixed(1)}" text-anchor="end" font-size="9" fill="var(--muted)" font-family="var(--mono)">vol</text>
    <path d="${area()}" fill="var(--accent)" opacity="0.06"/>
    ${level(c.resistance,'Resistance','var(--neg)','4 3')}
    ${level(c.support,'Support','var(--s-mid)','4 3')}
    <path d="${path(s200)}" fill="none" stroke="var(--ma200)" stroke-width="1.4" opacity="0.9"/>
    <path d="${path(s50)}" fill="none" stroke="var(--ma50)" stroke-width="1.4" opacity="0.9"/>
    <path d="${path(close)}" fill="none" stroke="var(--accent2)" stroke-width="2"/>
    <circle cx="${X(n-1).toFixed(1)}" cy="${Y(close[n-1]).toFixed(1)}" r="3.2" fill="var(--accent2)"/>
    ${xlab(0)}${xlab(Math.floor(n/2))}${xlab(n-1)}
  </svg>`;
}

const SUBS=[['value','Value'],['quality','Quality'],['balance','Balance'],['growth','Growth'],['technical','Technical'],['actionability','Actionability']];
function subBars(c){
  return SUBS.map(([k,lab])=>{const v=c.sub_scores?c.sub_scores[k]:null;
    const w=v==null?0:(v/5*100);const col=v==null?'var(--track)':scoreColor(v);
    return `<div class="subrow"><span class="lab">${lab}</span><span class="bar"><b style="width:${w}%;background:${col}"></b></span><span class="sc">${v==null?'—':v}</span></div>`;}).join('');
}

const capEUR=(v)=>{if(v==null)return 'n/a';const a=v;return a>=1e9?'€'+(a/1e9).toFixed(1)+'B':'€'+(a/1e6).toFixed(0)+'M';};
const COLS=[
  ['co','Company',false],['score','Score',true],['conf','Conf.',false],['mcap','Mkt cap (€)',true],
  ['control','Control',false],['value','Val',true],['quality','Qual',true],['balance','Bal',true],
  ['growth','Grw',true],['technical','Tech',true],['actionability','Act',true],
  ['fv_upside','Upside',true],['pb','P/B',true],['roe','ROE',true],
  ['trend','Chart',false],['ret_12m','12m',true]
];

function cell(c,key){
  const s=c.sub_scores||{};
  switch(key){
    case 'co':{let d='';if(c.score_delta!=null&&c.score_delta!==0)d=`<span class="delta ${c.score_delta>0?'up':'dn'}">${c.score_delta>0?'▲':'▼'}${Math.abs(c.score_delta).toFixed(1)}</span>`;
      return `<div class="co">${c.name}${d}</div><div class="tkr">${c.ticker} · ${c.currency||''}</div><div class="meta">${c.sector||''}${c.country?' · '+c.country:''}${c.style?' · '+c.style:''}</div>`;}
    case 'score':return `<span class="chip" style="background:${scoreColor(c.score)}">${fmt(c.score,1)}</span>`;
    case 'conf':{const cl=(c.confidence_label||'').toLowerCase();
      return `<span class="conf ${cl}">${c.confidence_label||'—'}</span>`;}
    case 'mcap':return `<span class="num">${capEUR(c.market_cap_eur)}</span>`;
    case 'control':{const a=(c.sub_scores||{}).actionability;
      const cls=a==null?'':a<2.5?'blocked':a>=4?'open':'';
      return `<span class="ctrl ${cls}">${c.control_label||'—'}</span>`;}
    case 'value':case 'quality':case 'balance':case 'growth':case 'technical':case 'actionability':
      {const v=s[key];return `<span class="num">${v==null?'—':v}</span>`;}
    case 'fv_upside':return `<span class="num" style="color:${c.fv_upside==null?'inherit':c.fv_upside>=0?'var(--pos)':'var(--neg)'}">${c.fv_upside==null?'—':(c.fv_upside*100).toFixed(0)+'%'}</span>`;
    case 'pb':return `<span class="num">${fmt(c.pb)}</span>`;
    case 'pe':return `<span class="num">${fmt(c.pe)}</span>`;
    case 'roe':return `<span class="num">${pctf(c.roe)}</span>`;
    case 'trend':{const cl=trendClass(c.trend);const bo=c.breakout==='up'?`<span class="tag bo">breakout${c.vol_confirm?' ✓vol':''}</span>`:c.breakout==='down'?'<span class="tag bd">breakdown</span>':'';
      return `<span class="${cl}">${c.trend||'—'}</span> ${bo}`;}
    case 'ret_12m':return `<span class="num" style="color:${c.ret_12m>=0?'var(--pos)':'var(--neg)'}">${pctf(c.ret_12m)}</span>`;
  }
}
function sortVal(c,key){
  if(key==='co')return (c.name||'').toLowerCase();
  if(key==='conf')return ({'High':2,'Medium':1,'Low':0})[c.confidence_label]??-1;
  if(key==='mcap')return c.market_cap_eur==null?-Infinity:c.market_cap_eur;
  if(key==='fv_upside')return c.fv_upside==null?-Infinity:c.fv_upside;
  if(key==='control')return (c.control_label||'').toLowerCase();
  if(key==='trend')return ({'Uptrend':2,'Range / mixed':1,'Downtrend':0})[c.trend]??-1;
  if(['value','quality','balance','growth','technical','actionability'].includes(key))return c.sub_scores?(c.sub_scores[key]??-1):-1;
  return c[key]==null?-Infinity:c[key];
}

function detail(c){
  return `<div class="panel">
    <div>
      <h3>Price chart — 1 year</h3>
      <div class="chartwrap">${chart(c)}
        <div class="legend">
          <span><i style="border-color:var(--accent2)"></i>Price</span>
          <span><i style="border-color:var(--ma50)"></i>50-day MA</span>
          <span><i style="border-color:var(--ma200)"></i>200-day MA</span>
          <span><i class="dash" style="border-color:var(--neg)"></i>Resistance</span>
          <span><i class="dash" style="border-color:var(--s-mid)"></i>Support</span>
        </div>
      </div>
      <div class="thesis"><div class="lab">Technical read</div>${c.tech_read||'n/a'}</div>
      <div class="thesis"><div class="lab">Ownership / actionability</div><b>${c.control_label||'—'}.</b> ${c.control_note||''} <span style="color:var(--muted)">(verified ${c.control_verified||'n/a'})</span></div>
      <div class="thesis"><div class="lab">Activist thesis</div>${c.thesis||'—'}</div>
      <div class="macro"><b>Macro overlay (editorial):</b> ${c.macro||'—'}</div>
      ${(c.flags&&c.flags.length)?`<div class="flags"><div class="lab" style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)">Data flags</div>${c.flags.map(f=>`<span class="flag ${/caution|unknown/i.test(f)?'info':''}">⚠ ${f}</span>`).join('')}</div>`:''}
    </div>
    <div>
      <h3>Scorecard</h3>${subBars(c)}
      <h3 style="margin-top:16px">Valuation, liquidity &amp; catalyst</h3>
      <div class="grid2">
        <span class="k">Peer-implied upside</span><span class="val" style="color:${c.fv_upside==null?'inherit':c.fv_upside>=0?'var(--pos)':'var(--neg)'}">${c.fv_upside==null?'—':(c.fv_upside*100).toFixed(0)+'%'}</span>
        <span class="k">Fair value (crude)</span><span class="val">${fmt(c.fair_value)}</span>
        <span class="k">Avg daily value</span><span class="val">${capEUR(c.adv_eur)}</span>
        <span class="k">Days to 5% stake</span><span class="val">${c.days_to_5pct==null?'—':Math.round(c.days_to_5pct)}</span>
        <span class="k">Data confidence</span><span class="val">${c.confidence_label||'—'} (${c.confidence==null?'—':Math.round(c.confidence*100)+'%'})</span>
      </div>
      <h3 style="margin-top:16px">Catalysts</h3>
      <div class="grid2">
        <span class="k">Next earnings</span><span class="val">${c.next_earnings||'n/a'}</span>
        <span class="k">Ex-dividend</span><span class="val">${c.ex_div_date||'n/a'}</span>
        <span class="k">Dividend paid</span><span class="val">${c.div_pay_date||'n/a'}</span>
        <span class="k">Index reviews</span><span class="val" style="text-align:right">${(window.__REVIEWS__||[]).map(r=>r.when).join(' · ')||'n/a'}</span>
      </div>
      <div class="macro" style="margin-top:6px"><b>AGM (editorial, verify):</b> ${c.agm_season||'—'}. Earnings/ex-div from Yahoo; index-review windows are scheduled dates.</div>
      <h3 style="margin-top:16px">Analyst view <span style="font-weight:400;color:var(--muted);font-size:11px">(Yahoo consensus — others' forecasts, not ours)</span></h3>
      ${c.analyst_n ? `<div class="grid2">
        <span class="k">Rating</span><span class="val">${c.rec_key||'n/a'} · ${c.analyst_n} analysts</span>
        <span class="k">Target low</span><span class="val">${fmt(c.target_low)} (${tgtpc(c.target_low,c.price)})</span>
        <span class="k">Target mean</span><span class="val">${fmt(c.target_mean)} (${tgtpc(c.target_mean,c.price)})</span>
        <span class="k">Target high</span><span class="val">${fmt(c.target_high)} (${tgtpc(c.target_high,c.price)})</span>
        <span class="k">Our peer fair value</span><span class="val">${fmt(c.fair_value)} (${c.fv_upside==null?'—':(c.fv_upside*100).toFixed(0)+'%'})</span>
      </div>` : `<div class="macro" style="font-style:normal">No / thin analyst coverage for this name.</div>`}
      <h3 style="margin-top:16px">Fundamentals</h3>
      <div class="grid2">
        <span class="k">Style</span><span class="val">${c.style||'—'}</span>
        <span class="k">P/B</span><span class="val">${fmt(c.pb)}</span>
        <span class="k">P/E (fwd)</span><span class="val">${fmt(c.pe)} (${fmt(c.fwd_pe)})</span>
        <span class="k">PEG</span><span class="val">${fmt(c.peg)}</span>
        <span class="k">Beta (risk)</span><span class="val">${fmt(c.beta)}</span>
        <span class="k">EV/EBITDA</span><span class="val">${fmt(c.ev_ebitda)}</span>
        <span class="k">P/S</span><span class="val">${fmt(c.ps)}</span>
        <span class="k">Div yield</span><span class="val">${pctf(c.div_yield)}</span>
        <span class="k">ROE</span><span class="val">${pctf(c.roe)}</span>
        <span class="k">Oper margin</span><span class="val">${pctf(c.oper_margin)}</span>
        <span class="k">Net margin</span><span class="val">${pctf(c.profit_margin)}</span>
        <span class="k">Debt/Equity</span><span class="val">${fmt(c.debt_to_equity)}</span>
        <span class="k">Current ratio</span><span class="val">${fmt(c.current_ratio)}</span>
        <span class="k">Rev growth</span><span class="val">${pctf(c.rev_growth)}</span>
        <span class="k">Earn growth</span><span class="val">${pctf(c.earn_growth)}</span>
        <span class="k">FCF yield</span><span class="val">${pctf(c.fcf_yield)}</span>
        <span class="k">Net cash</span><span class="val">${money(c.net_cash)}</span>
      </div>
      <h3 style="margin-top:16px">Chart levels</h3>
      <div class="grid2">
        <span class="k">Price</span><span class="val">${fmt(c.price)}</span>
        <span class="k">50d / 200d MA</span><span class="val">${fmt(c.sma50)} / ${fmt(c.sma200)}</span>
        <span class="k">Support / Resist.</span><span class="val">${fmt(c.support)} / ${fmt(c.resistance)}</span>
        <span class="k">52w low / high</span><span class="val">${fmt(c.low52)} / ${fmt(c.high52)}</span>
        <span class="k">vs 52w high</span><span class="val">${pctf(c.pct_from_high)}</span>
        <span class="k">RSI(14)</span><span class="val">${fmt(c.rsi14,0)}</span>
        <span class="k">3m / 12m return</span><span class="val">${pctf(c.ret_3m)} / ${pctf(c.ret_12m)}</span>
      </div>
    </div>
  </div>`;
}

function render(rows){
  const tb=$('#tbl tbody');tb.innerHTML='';
  rows.forEach((c,i)=>{
    const tr=document.createElement('tr');tr.className='main';tr.dataset.i=i;
    tr.innerHTML=COLS.map(([k])=>`<td class="${k==='co'?'':'r'}">${cell(c,k)}</td>`).join('')
      .replace('</td>','</td>');
    // append expand affordance to first cell
    tr.firstChild.insertAdjacentHTML('beforeend','<div class="expand">▸ details</div>');
    const dr=document.createElement('tr');dr.className='detail';dr.style.display='none';
    dr.innerHTML=`<td colspan="${COLS.length}">${detail(c)}</td>`;
    tr.addEventListener('click',()=>{const open=dr.style.display!=='none';
      dr.style.display=open?'none':'';tr.querySelector('.expand').textContent=open?'▸ details':'▾ details';});
    tb.appendChild(tr);tb.appendChild(dr);
  });
  $('#count').textContent=rows.length+' names';
}

/* ---- concentration / diversification across the whole watchlist ---- */
function diversification(){
  const n=DATA.length; if(!n)return;
  function groupCounts(keyfn){
    const m={};DATA.forEach(c=>{const k=keyfn(c)||'—';m[k]=(m[k]||0)+1;});
    return Object.entries(m).sort((a,b)=>b[1]-a[1]);
  }
  const bySector=groupCounts(c=>c.sector);
  const byCountry=groupCounts(c=>c.country);
  // Herfindahl index on sector shares -> concentration verdict.
  const hhi=bySector.reduce((s,[,v])=>s+Math.pow(v/n,2),0);
  const lvl=hhi>0.25?['High','conc-hi']:hhi>0.15?['Moderate','conc-mid']:['Low','conc-lo'];
  const topSec=bySector[0], topCty=byCountry[0];
  // "one bet" heuristic: financials share
  const fin=DATA.filter(c=>/financ|insurance/i.test(c.sector||'')).length;
  const finPc=Math.round(fin/n*100);
  let verdict=`<span class="${lvl[1]}">${lvl[0]} concentration</span> — largest sector is `+
    `<b>${topSec[0]}</b> at ${Math.round(topSec[1]/n*100)}% (${topSec[1]}/${n}), largest country `+
    `<b>${topCty[0]}</b> at ${Math.round(topCty[1]/n*100)}%.`;
  if(finPc>=40)verdict+=` <b>${finPc}% are financials</b> — several names may be one rates/CEE-bank bet, not independent ideas.`;
  const rows=(arr)=>arr.map(([k,v])=>`<div class="drow"><span class="nm">${k}</span><span class="bar"><b style="width:${v/n*100}%"></b></span><span class="pc">${v} · ${Math.round(v/n*100)}%</span></div>`).join('');
  const rev=(window.__REVIEWS__||[]).map(r=>`${r.name}: ${r.when}`).join(' · ');
  $('#divers').innerHTML=`<h3>Diversification &amp; concentration</h3>`+
    `<p class="verdict">${verdict}</p>`+
    `<div class="cols"><div><div class="lab">By sector</div>${rows(bySector)}</div>`+
    `<div><div class="lab">By country</div>${rows(byCountry)}</div></div>`+
    (rev?`<p class="verdict" style="margin-top:12px;color:var(--muted)"><b>Upcoming index reviews:</b> ${rev} (scheduled dates — potential passive-flow catalysts).</p>`:'');
}

let view=DATA.slice();
function init(){
  diversification();
  const thead=$('#tbl thead tr');
  thead.innerHTML=COLS.map(([k,lab,r])=>`<th class="${r?'r':''}" data-k="${k}">${lab}<span class="arw">▲</span></th>`).join('');
  thead.querySelectorAll('th').forEach((th,idx)=>{
    th.addEventListener('click',()=>{
      const k=th.dataset.k;const asc=!th.classList.contains('asc');
      thead.querySelectorAll('th').forEach(h=>h.classList.remove('asc','desc'));
      th.classList.add(asc?'asc':'desc');
      view.sort((a,b)=>{const x=sortVal(a,k),y=sortVal(b,k);
        if(x<y)return asc?-1:1;if(x>y)return asc?1:-1;return 0;});
      render(view);
    });
  });
  $('#search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();
    view=DATA.filter(c=>(c.name+' '+c.ticker+' '+(c.sector||'')+' '+(c.thesis||'')+' '+(c.tech_read||'')).toLowerCase().includes(q));
    render(view);});
  $('#theme').addEventListener('click',()=>{const r=document.documentElement;
    const cur=r.getAttribute('data-theme');
    const dark=cur?cur==='dark':matchMedia('(prefers-color-scheme:dark)').matches;
    r.setAttribute('data-theme',dark?'light':'dark');});
  render(view);
}
init();
"""


# --------------------------------------------------------------------------- #
def _kpis(data):
    n = len(data)
    avg = sum(c.get("score") or 0 for c in data) / n if n else 0
    top = max(data, key=lambda c: c.get("score") or 0) if data else None
    pbs = [c for c in data if c.get("pb") is not None]
    cheap = min(pbs, key=lambda c: c["pb"]) if pbs else None
    ups = sum(1 for c in data if c.get("trend") == "Uptrend")
    act = sum(1 for c in data if (c.get("sub_scores") or {}).get("actionability") not in (None,)
              and (c["sub_scores"]["actionability"] or 0) >= 3.5)
    tiles = [
        ("Names on watchlist", str(n)),
        ("Average score", f"{avg:.1f}<small>/ 5</small>"),
        ("Top pick", top["ticker"] if top else "—"),
        ("Actionable ownership", f"{act}<small>/ {n}</small>"),
        ("In an uptrend", f"{ups}<small>/ {n}</small>"),
    ]
    return "".join(f'<div class="kpi"><div class="l">{l}</div><div class="v">{v}</div></div>'
                   for l, v in tiles)


def build_dashboard(src=DEFAULT_JSON, html_path=DEFAULT_HTML, fragment=False):
    if not os.path.exists(src):
        raise FileNotFoundError(f"{src} not found — run activist_screener.py first.")
    with open(src, encoding="utf-8") as fh:
        data = json.load(fh)

    generated = datetime.now().strftime("%d %b %Y %H:%M")
    try:
        from catalysts import next_index_reviews
        reviews = next_index_reviews(datetime.now().date())
    except Exception:
        reviews = []
    js = (JS.replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__REVIEWS_JSON__", json.dumps(reviews, ensure_ascii=False)))

    body = f"""<title>Innimmo Activist Watchlist</title>
<style>{CSS}</style>
<div class="wrap">
  <header class="mast">
    <div><p class="kicker">Innimmo Investment Capital Group · T-AI-10</p>
      <h1 class="word">Innimmo <em>Activist</em> Watchlist</h1></div>
    <button class="themebtn" id="theme" type="button">Toggle theme</button>
  </header>
  <p class="sub"><span class="live"><span class="dot"></span>Live data</span>
    · scored on Value · Quality · Balance sheet · Growth · Technical · Actionability
    · market caps in EUR · generated {generated} · research draft, <b>not investment advice</b>.</p>
  <p class="note">Click any row for its price chart (with volume), six-factor scorecard,
    full ratio set, ownership read, and activist thesis. <b>Control</b> shows whether an
    activist could realistically act. Ownership &amp; macro are editorial overlays, not live feeds.</p>
  <section class="kpis">{_kpis(data)}</section>
  <section class="divers" id="divers"></section>
  <div class="toolbar">
    <input id="search" type="search" placeholder="Filter names, sectors, theses…" aria-label="Filter">
    <span class="count" id="count"></span>
  </div>
  <div class="card"><table id="tbl"><thead><tr></tr></thead><tbody></tbody></table></div>
  <footer>Live metrics via Yahoo Finance (<code>yfinance</code>); figures as-reported and
    unaudited. Technicals (trend, support/resistance, breakouts, RSI) are computed from daily
    price history. Theses are AI-generated drafts. This is an internal research-support tool —
    <b>not investment advice</b>.</footer>
</div>
<script>{js}</script>
<script>{AUTOHEIGHT_JS}</script>"""

    if fragment:
        page = body
    else:
        page = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                f"</head><body style=\"margin:0\">{body}</body></html>")

    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return html_path


def main(argv):
    fragment = "--fragment" in argv
    args = [a for a in argv if not a.startswith("--")]
    src = args[0] if len(args) > 0 else DEFAULT_JSON
    out = args[1] if len(args) > 1 else DEFAULT_HTML
    print("Dashboard written to", build_dashboard(src, out, fragment=fragment))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
