/* 一覧内ライブプレビュー。YouTubeのポリシーに合わせ自動再生は同時に1本のみ。 */
(()=>{'use strict';
const grid=document.getElementById('camGrid');
const toolbar=document.querySelector('.toolbar');
if(!grid||!toolbar||!('IntersectionObserver' in window))return;
const modal=document.getElementById('modal');
const KEY='machinomado.inline-preview';
let enabled=true;
try{const saved=localStorage.getItem(KEY);if(saved!==null)enabled=saved==='on'}catch(_e){}
let current=null,chosenManually=null,visible=new Set();
const toggle=document.createElement('button');
toggle.type='button';toggle.id='previewToggle';toggle.className='secondary preview-toggle';
toggle.title='画面に入った取得時ライブの1件だけをミュートで再生します';
const info=document.createElement('span');info.className='preview-hint';
info.textContent='一覧内は1映像ずつ・ミュート再生（ライブ状態は取得時点）';
const favFilter=document.getElementById('favoritesOnly');
if(favFilter)favFilter.before(toggle);else toolbar.append(toggle);
toolbar.append(info);
function save(){try{localStorage.setItem(KEY,enabled?'on':'off')}catch(_e){}}
function toggleLabel(){toggle.textContent=enabled?'◉ ライブ映像プレビュー ON':'▷ ライブ映像プレビュー OFF';toggle.classList.toggle('preview-on',enabled);toggle.setAttribute('aria-pressed',String(enabled));}
function stop(){
 if(!current)return;
 const host=current.closest('.cam');
 current.replaceChildren();current.hidden=true;
 if(host)host.classList.remove('inline-playing');
 current=null;
}
function updateSelection(){
 for(const btn of grid.querySelectorAll('button[data-inline-preview]')){
  const selected=Boolean(current&&current.dataset.videoId===btn.dataset.inlinePreview);
  btn.textContent=selected?'◉ 一覧で再生中':'▷ この映像を表示';
  btn.setAttribute('aria-pressed',String(selected));
 }
}
function choose(){
 if(!enabled||document.hidden||grid.hidden||(modal&&!modal.hidden)){stop();updateSelection();return;}
 const available=[...grid.querySelectorAll('div.thumb[data-preview-video]')].filter(node=>visible.has(node));
 const target=available.find(node=>node.dataset.previewVideo===chosenManually)||available[0];
 if(!target){stop();updateSelection();return;}
 const slot=target.querySelector('.inline-player');
 if(!slot){stop();updateSelection();return;}
 if(current===slot){updateSelection();return;}
 stop();
 const id=target.dataset.previewVideo;
 if(!/^[a-zA-Z0-9_-]{11}$/.test(id))return;
 const frame=document.createElement('iframe');
 frame.title='ライブ映像プレビュー（ミュート）：'+(target.closest('.cam')?.querySelector('h3')?.textContent||'YouTube');
 frame.src='https://www.youtube.com/embed/'+id+'?autoplay=1&mute=1&playsinline=1&rel=0';
 frame.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';
 frame.referrerPolicy='strict-origin-when-cross-origin';
 frame.allowFullscreen=true;
 frame.loading='eager';
 slot.replaceChildren(frame);slot.hidden=false;
 target.closest('.cam')?.classList.add('inline-playing');
 current=slot;
 updateSelection();
}
const observer=new IntersectionObserver(entries=>{
 for(const entry of entries){
  // YouTube埋め込み仕様: 50%以上が見えてから自動再生開始。
  if(entry.isIntersecting&&entry.intersectionRatio>=0.6)visible.add(entry.target);
  else visible.delete(entry.target);
 }
 choose();
},{threshold:[0,0.5,0.6,0.75,1]});
function decorate(){
 stop();visible.clear();observer.disconnect();chosenManually=null;
 for(const card of grid.querySelectorAll('article.cam')){
  const button=card.querySelector('button.thumb[data-play]');
  const thumb=button?.parentElement;
  const id=button?.dataset.play;
  if(!thumb||!button.querySelector('.badge.live')||!/^[a-zA-Z0-9_-]{11}$/.test(id||''))continue;
  thumb.dataset.previewVideo=id;
  const favorite=thumb.querySelector('button.fav');
  const tags=card.querySelector('.tags');
  if(favorite&&tags){favorite.classList.add('preview-fav');tags.appendChild(favorite);}
  const slot=document.createElement('div');slot.className='inline-player';slot.dataset.videoId=id;slot.hidden=true;thumb.appendChild(slot);
  const action=card.querySelector('.card-actions');
  if(action){const b=document.createElement('button');b.type='button';b.className='preview-select';b.dataset.inlinePreview=id;b.textContent='▷ この映像を表示';b.setAttribute('aria-pressed','false');action.prepend(b);}
  observer.observe(thumb);
 }
 toggleLabel();
}
const changes=new MutationObserver(records=>{
 if(records.some(x=>x.type==='childList'))decorate();
});
changes.observe(grid,{childList:true});
grid.addEventListener('click',e=>{
 const b=e.target.closest('button[data-inline-preview]');if(!b)return;
 const id=b.dataset.inlinePreview;
 if(current?.dataset.videoId===id){enabled=false;chosenManually=null;stop();}
 else{enabled=true;chosenManually=id;}
 save();toggleLabel();choose();
});
toggle.addEventListener('click',()=>{enabled=!enabled;chosenManually=null;save();toggleLabel();choose();});
document.addEventListener('visibilitychange',choose);
if(modal)new MutationObserver(choose).observe(modal,{attributes:true,attributeFilter:['hidden']});
document.getElementById('tabCams')?.addEventListener('click',()=>setTimeout(choose,0));
document.getElementById('tabChannels')?.addEventListener('click',()=>setTimeout(choose,0));
decorate();
})();
