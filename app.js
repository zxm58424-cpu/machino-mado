(()=>{'use strict';
const db=window.CATALOG||{cameras:[],channels:[],meta:{}};
const cameras=db.cameras||[], channels=db.channels||[];
const $=id=>document.getElementById(id);
const h=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const norm=s=>String(s??'').normalize('NFKC').toLowerCase();
const num=x=>Number(x).toLocaleString('ja-JP');
const time=s=>{if(!s)return '未確認';let x=new Date(s);return Number.isNaN(x.getTime())?'未確認':new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}).format(x)};
const statusText={'ライブ':'取得時 LIVE','配信終了':'配信終了','配信予定':'配信予定','未確認':'未確認'};
const prefs='北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split(' ');
const state={tab:'cams',page:1,perPage:24,onlyFav:false,filtered:[]};
let fav=new Set();try{fav=new Set(JSON.parse(localStorage.getItem('machinomado.favorites')||'[]'))}catch(e){}
function saveFav(){try{localStorage.setItem('machinomado.favorites',JSON.stringify([...fav]))}catch(e){}$('favCount').textContent=fav.size}
const youtube=id=>'https://www.youtube.com/watch?v='+id;
const channelUrl=id=>'https://www.youtube.com/channel/'+id;
const thumb=id=>'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg';
function addOpt(sel,value){let o=document.createElement('option');o.value=value;o.textContent=value;sel.appendChild(o)}
for(const p of prefs)addOpt($('pref'),p);addOpt($('pref'),'未判定');
for(const g of [...new Set(cameras.map(x=>x.g))].sort((a,b)=>a.localeCompare(b,'ja')))addOpt($('genre'),g);
$('statVideos').textContent=num(cameras.length);$('statChannels').textContent=num(channels.length);
$('statPrefs').textContent=new Set(cameras.map(c=>c.p).filter(p=>prefs.includes(p))).size;
$('statLive').textContent=num(cameras.filter(c=>c.s==='ライブ').length);
$('checkedTime').textContent=time(db.meta?.latest_check);
saveFav();
const photoOrder=['富士山','渋谷','海岸'];const used=new Set();
photoOrder.forEach((q,i)=>{let c=cameras.find(x=>!used.has(x.id)&&x.t.includes(q)&&x.q==='有力'&&x.s==='ライブ');if(!c)c=cameras.find(x=>!used.has(x.id)&&x.q==='有力'&&x.s==='ライブ');if(!c)return;used.add(c.id);if(window.FALLBACK_IMAGES?.[i])$('heroPhoto'+(i+1)).parentElement.style.backgroundImage='url('+window.FALLBACK_IMAGES[i]+')';$('heroPhoto'+(i+1)).src=thumb(c.id);$('heroPhoto'+(i+1)).onerror=()=>{$('heroPhoto'+(i+1)).onerror=null;$('heroPhoto'+(i+1)).src=window.FALLBACK_IMAGES?.[i]||'assets/'+['landscape.svg','city.svg','coast.svg'][i]};$('heroPhotoLabel'+(i+1)).textContent=c.t});
function selected(){
 const q=norm($('q').value.trim()),p=$('pref').value,r=$('region').value,g=$('genre').value,s=$('status').value;
 let arr=state.tab==='cams'?cameras:channels;
 return arr.filter(x=>{
  if(p&&x.p!==p)return false;
  if(r&&x.r!==r&&!(state.tab==='channels'&&cameras.some(y=>y.cid===x.id&&y.r===r)))return false;
  if(q&&!norm(state.tab==='cams'?x.t+' '+x.c+' '+x.p+' '+x.g:x.t+' '+x.p).includes(q))return false;
  if(state.tab==='cams'){
   if(g&&x.g!==g)return false;if(s&&x.s!==s)return false;
   if(x.q==='対象外疑い'&&!$('showExcluded').checked)return false;
   if(x.q==='要確認'&&!$('showReview').checked)return false;
   if(x.d!=='国内候補'&&!$('showUnknown').checked)return false;
   if(state.onlyFav&&!fav.has(x.id))return false;
  }
  return true;
 });
}
function sorted(arr){let a=arr.slice(),by=$('sort').value;
 if(state.tab==='channels')return a.sort((x,y)=>by==='name'?x.t.localeCompare(y.t,'ja'):(y.n-x.n)||x.t.localeCompare(y.t,'ja'));
 if(by==='new')a.sort((x,y)=>(y.checked||'').localeCompare(x.checked||''));
 if(by==='name')a.sort((x,y)=>x.t.localeCompare(y.t,'ja'));
 if(by==='pref')a.sort((x,y)=>prefs.indexOf(x.p)-prefs.indexOf(y.p)||x.t.localeCompare(y.t,'ja'));
 if(by==='live'){
   // Surface regional variety instead of showing dozens of the same prefecture first.
   const ranks=['ライブ','未確認','配信予定','配信終了'],out=[];
   for(const rank of ranks){const group=a.filter(x=>x.s===rank),buckets=new Map();
     for(const x of group){if(!buckets.has(x.p))buckets.set(x.p,[]);buckets.get(x.p).push(x)}
     for(const val of buckets.values())val.sort((x,y)=>Number(y.g!=='その他・未判定')-Number(x.g!=='その他・未判定')||(y.checked||'').localeCompare(x.checked||''));
     const order=[...prefs.filter(p=>buckets.has(p)),...Array.from(buckets.keys()).filter(p=>!prefs.includes(p))];
     let remains=true;while(remains){remains=false;for(const p of order){let arr=buckets.get(p);if(arr.length){out.push(arr.shift());remains=true}}}
   }
   return out;
 }
 return a;
}
function card(x){return `<article class="cam"><div class="thumb" role="group" aria-label="動画のサムネイル"><button class="thumb" type="button" data-play="${h(x.id)}" aria-label="${h(x.t)} を再生"><img src="${thumb(x.id)}" loading="lazy" alt="${h(x.t)} のYouTubeサムネイル" onerror="this.style.display='none'"><span class="badge ${x.s==='ライブ'?'live':x.s==='配信終了'?'end':x.s==='配信予定'?'scheduled':''}">${statusText[x.s]||'未確認'}</span></button><button class="fav ${fav.has(x.id)?'on':''}" type="button" aria-label="お気に入り切り替え" aria-pressed="${fav.has(x.id)}" data-fav="${h(x.id)}">${fav.has(x.id)?'★':'☆'}</button></div><div class="cam-body"><div class="tags"><span class="tag area">${h(x.p)}</span><span class="tag">${h(x.g)}</span>${x.q!=='有力'?'<span class="tag warn">要確認</span>':''}</div><h3 title="${h(x.t)}">${h(x.t)}</h3><p class="byline" title="${h(x.c)}">◉ ${h(x.c||'チャンネル名未登録')}</p><p class="updated">状態確認：${time(x.checked)}</p><div class="card-actions"><button class="watch" type="button" data-play="${h(x.id)}">映像を見る ▶</button><a class="youtube" target="_blank" rel="noopener noreferrer" href="${youtube(x.id)}">YouTube ↗</a></div></div></article>`}
function chCard(x){return `<article class="channel"><div class="avatar">◉</div><div style="min-width:0"><div class="chname">${h(x.t)}</div><div class="chmeta">${h(x.p)} · 収録動画 ${x.n}件</div><a href="${channelUrl(x.id)}" target="_blank" rel="noopener noreferrer">チャンネルを開く ↗</a></div></article>`}
function render(){
 state.filtered=sorted(selected());let total=state.filtered.length,pages=Math.max(1,Math.ceil(total/state.perPage));state.page=Math.min(Math.max(1,state.page),pages);
 let pageRows=state.filtered.slice((state.page-1)*state.perPage,state.page*state.perPage);
 $('resultCount').textContent=num(total);$('resultLabel').textContent=state.tab==='cams'?'件のカメラ候補':'件のチャンネル候補';
 const empty='<div class="empty"><strong>該当する結果はありません</strong><p>検索語や絞り込み条件を変更してください。</p></div>';
 if(state.tab==='cams')$('camGrid').innerHTML=total?pageRows.map(card).join(''):empty;
 else $('channelGrid').innerHTML=total?pageRows.map(chCard).join(''):empty;
 $('pagination').innerHTML=total>state.perPage?`<button data-page="prev" ${state.page===1?'disabled':''}>← 前へ</button><span>${state.page} / ${pages} ページ</span><button data-page="next" ${state.page===pages?'disabled':''}>次へ →</button>`:'';
 $('favoritesOnly').classList.toggle('selected',state.onlyFav);
}
function change(){state.page=1;render()}
function tab(mode){state.tab=mode;state.page=1;state.onlyFav=false;let cam=mode==='cams';$('tabCams').classList.toggle('active',cam);$('tabChannels').classList.toggle('active',!cam);$('tabCams').setAttribute('aria-selected',String(cam));$('tabChannels').setAttribute('aria-selected',String(!cam));$('camGrid').hidden=!cam;$('channelGrid').hidden=cam;document.querySelectorAll('.cam-only').forEach(x=>x.hidden=!cam);$('favoritesOnly').hidden=!cam;$('sort').value=cam?'live':'new';render()}
function openPlayer(id){let x=cameras.find(c=>c.id===id);if(!x||!/^[\w-]{11}$/.test(id))return;
 $('modalTitle').textContent=x.t;$('modalYT').href=youtube(id);
 const iframe=document.createElement('iframe');iframe.title=x.t;iframe.src='https://www.youtube-nocookie.com/embed/'+id+'?rel=0';iframe.allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';iframe.referrerPolicy='strict-origin-when-cross-origin';iframe.allowFullscreen=true;
 $('player').replaceChildren(iframe);$('modal').hidden=false;document.body.style.overflow='hidden';$('closeModal').focus();}
function closePlayer(){$('modal').hidden=true;$('player').replaceChildren();document.body.style.overflow=''}
function csvExport(){let fields=state.tab==='cams'?['都道府県','ジャンル','取得時の配信状態','カメラ判定','国内映像判定','動画タイトル','チャンネル','YouTube URL','確認日時']:['チャンネル名','動画候補数','主な都道府県','チャンネルURL'];
 let clean=s=>{let t=String(s??'');if(/^[=+@\-\t\r]/.test(t))t="'"+t;return '"'+t.replaceAll('"','""')+'"'};
 let lines=[fields.map(clean).join(',')];for(let x of state.filtered){let cells=state.tab==='cams'?[x.p,x.g,x.s,x.q,x.d,x.t,x.c,youtube(x.id),x.checked]:[x.t,x.n,x.p,channelUrl(x.id)];lines.push(cells.map(clean).join(','))}
 let blob=new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=state.tab==='cams'?'日本ライブカメラ_検索結果.csv':'日本ライブカメラ_チャンネル検索結果.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000)}
['q','pref','region','genre','status','showReview','showUnknown','showExcluded','sort'].forEach(id=>$(id).addEventListener(['q','pref','region','genre','status','sort'].includes(id)?'change':'change',change));
$('q').addEventListener('input',()=>{clearTimeout(window._searchTimer);window._searchTimer=setTimeout(change,140)});
$('heroSearch').addEventListener('submit',e=>{e.preventDefault();$('q').value=$('heroInput').value;tab('cams');document.getElementById('directory').scrollIntoView({behavior:'smooth'});$('q').focus()});
$('tabCams').addEventListener('click',()=>tab('cams'));$('tabChannels').addEventListener('click',()=>tab('channels'));
$('navChannels').addEventListener('click',()=>tab('channels'));
$('topFav').addEventListener('click',()=>{tab('cams');state.onlyFav=true;render();document.getElementById('directory').scrollIntoView({behavior:'smooth'})});
$('favoritesOnly').addEventListener('click',()=>{state.onlyFav=!state.onlyFav;change()});
$('resetFilters').addEventListener('click',()=>{for(let id of ['q','pref','region','genre','status'])$(id).value='';for(let id of ['showReview','showUnknown','showExcluded'])$(id).checked=false;state.onlyFav=false;change()});
$('downloadCsv').addEventListener('click',csvExport);
$('camGrid').addEventListener('click',e=>{let play=e.target.closest('[data-play]'),f=e.target.closest('[data-fav]');if(play)openPlayer(play.dataset.play);if(f){let id=f.dataset.fav;if(fav.has(id))fav.delete(id);else fav.add(id);saveFav();render()}});
$('pagination').addEventListener('click',e=>{let b=e.target.closest('[data-page]');if(!b||b.disabled)return;state.page+=b.dataset.page==='next'?1:-1;render();document.getElementById('directory').scrollIntoView({behavior:'smooth'})});
$('closeModal').addEventListener('click',closePlayer);$('modal').addEventListener('click',e=>{if(e.target===$('modal'))closePlayer()});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('modal').hidden)closePlayer()});
render();
})();
