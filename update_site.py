#!/usr/bin/env python3
"""CSV -> stand-alone static live camera directory. Needs Python stdlib only."""
import argparse, csv, datetime as dt, html, json, re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
REGIONS = {'北海道':'北海道・東北','青森県':'北海道・東北','岩手県':'北海道・東北','宮城県':'北海道・東北','秋田県':'北海道・東北','山形県':'北海道・東北','福島県':'北海道・東北', '茨城県':'関東','栃木県':'関東','群馬県':'関東','埼玉県':'関東','千葉県':'関東','東京都':'関東','神奈川県':'関東', '新潟県':'中部','富山県':'中部','石川県':'中部','福井県':'中部','山梨県':'中部','長野県':'中部','岐阜県':'中部','静岡県':'中部','愛知県':'中部', '三重県':'近畿','滋賀県':'近畿','京都府':'近畿','大阪府':'近畿','兵庫県':'近畿','奈良県':'近畿','和歌山県':'近畿','鳥取県':'中国・四国','島根県':'中国・四国','岡山県':'中国・四国','広島県':'中国・四国','山口県':'中国・四国','徳島県':'中国・四国','香川県':'中国・四国','愛媛県':'中国・四国','高知県':'中国・四国', '福岡県':'九州・沖縄','佐賀県':'九州・沖縄','長崎県':'九州・沖縄','熊本県':'九州・沖縄','大分県':'九州・沖縄','宮崎県':'九州・沖縄','鹿児島県':'九州・沖縄','沖縄県':'九州・沖縄'}
PATTERNS = [
 ('空港・飛行機',r'空港|滑走路|飛行機|航空機|機体|羽田|成田'),
 ('鉄道',r'新幹線|鉄道|電車|列車|駅前|駅構内|駅ライブ|駅カメラ|駅(?!弁)|線路|本線|車庫|貨物列車|踏切|JR\b|阪急|東急|京急|小田急|特急|鉄橋|鉄オタ'),
 ('道路・交通',r'交差点|高速道路|首都高|道路|国道\d|県道\d|交通状況|渋滞|バイパス|インターチェンジ|\bIC\b|ジャンクション|トンネル|駐車場|道の駅'),
 ('雪・スキー',r'スキー|積雪|雪景色|ゲレンデ|雪山|スノーボード|スノボ'),
 ('動物・水族館',r'水族館|動物園|ラッコ|パンダ|イルカ|カピバラ|ペンギン|野鳥|猫カメラ|猫神社|水槽|活蟹|カニ水槽|ねこ|犬猫|ビーバー'),
 ('河川・湖・ダム',r'河川|水位|ダム|湖畔|\w湖(?!南)|川河口|多摩川|荒川|信濃川|利根川|淀川|鴨川|琵琶湖|河口|水門|堤防'),
 ('海・港・波',r'海岸|海水浴|海の家|ビーチ|海辺|漁港|港湾|港(?!区)|波浪|サーフ|海洋|海上|海峡|海浜|太平洋|マリーナ|東京湾|湾岸|海辺|灯台'),
 ('山・火山',r'富士山|桜島|阿蘇山|山頂|山岳|噴火|噴煙|登山|高原|森林限界|アルプス|御嶽山|立山|上高地'),
 ('寺社・歴史',r'神社|大社|寺院|仏閣|参道|鳥居|\w寺(?!町)|お城|城跡|城址|天守閣|姫路城|熊本城|清水寺|境内'),
 ('街・観光・天気',r'スクランブル|街並|市街|繁華街|商店街|夜景|展望|公園|広場|温泉|湯畑|花火|通り|風景|天気|街角|市内|繁華|歩行者|タワー|観光|広場'),
]
def read_rows(filename):
    with open(filename, newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def genre(title, other):
    # Only apply word checks from titles, not location hints that may contaminate categories.
    for label, pattern in PATTERNS:
        if re.search(pattern,title,re.IGNORECASE):return label
    return 'その他・未判定' # never imply that raw heuristic label was verified

def main():
    p=argparse.ArgumentParser(description='収集CSVからライブカメラサイトを再生成')
    p.add_argument('--videos',default=str(BASE/'data/全動画候補.csv'))
    p.add_argument('--channels',default=str(BASE/'data/全チャンネル候補.csv'))
    args=p.parse_args()
    raw=read_rows(args.videos)
    unique={}
    for r in raw:
        vid=(r.get('video_id') or '').strip()
        if not re.fullmatch(r'[\w-]{11}',vid):continue
        if vid in unique:continue
        title=(r.get('title') or '名称未登録').strip()
        pref=(r.get('prefecture') or '').strip()
        if pref not in REGIONS:pref='未判定'
        status=(r.get('status') or '').strip()
        if status not in ('ライブ','配信終了','配信予定'):status='未確認'
        judgement=(r.get('camera_judgement') or '').strip()
        quality=('有力' if judgement=='定点カメラ有力' else '対象外疑い' if judgement=='対象外疑い' else '要確認')
        domestic=(r.get('domestic_judgement') or '')
        unique[vid]={'id':vid,'t':title[:220], 'c':(r.get('channel_title') or 'チャンネル不明')[:120], 'cid':(r.get('channel_id') or '').strip(), 'p':pref,'r':REGIONS.get(pref,'未判定'), 'g':genre(title,r.get('genre') or ''),'s':status,'q':quality,'d':'国内候補' if domestic.startswith('国内候補') else '未判定','checked':(r.get('status_checked_utc') or '')[:20], 'seen':(r.get('last_seen_utc') or '')[:20], 'via':(r.get('discovery_source') or '')[:50], 'location_basis':(r.get('location_basis') or '')[:40]}
    cams=list(unique.values())
    chans=[]; channel_idx={}
    for r in read_rows(args.channels):
        cid=(r.get('channel_id') or '').strip()
        if not re.fullmatch(r'UC[\w-]{22}',cid) or cid in channel_idx:continue
        item={'id':cid,'t':(r.get('channel_title') or 'チャンネル名未確認')[:140],'n':0,'p':'未判定','camera':r.get('camera_named') or ''}
        chans.append(item);channel_idx[cid]=item
    prefs={}
    for c in cams:
        if c['cid']:
            if c['cid'] not in channel_idx and re.fullmatch(r'UC[\w-]{22}',c['cid']):
                item={'id':c['cid'],'t':c['c'] or 'チャンネル名未確認','n':0,'p':'未判定','camera':''}
                chans.append(item);channel_idx[c['cid']]=item
            if c['cid'] in channel_idx:
                item=channel_idx[c['cid']];item['n']+=1
                pref_counts=prefs.setdefault(c['cid'],Counter())
                if c['p']!='未判定':pref_counts[c['p']]+=1
    for item in chans:
        if prefs.get(item['id']):item['p']=prefs[item['id']].most_common(1)[0][0]
    cams.sort(key=lambda x: (0 if x['s']=='ライブ' else 1 if x['s']=='未確認' else 2,x['p'],x['t']))
    chans.sort(key=lambda x:(-x['n'],x['t']))
    print('動画:',len(cams),'チャンネル:',len(chans),'ジャンル:',Counter(c['g'] for c in cams))
    manifest={'meta':{'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'latest_check':max((c['checked'] for c in cams),default=''),'source':'CSV提供データ / YouTube Data API・掲載サイト','version':'1.0'}, 'cameras':cams,'channels':chans}
    (BASE/'catalog.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    encoded=json.dumps(manifest,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=(BASE/'template.html').read_text(encoding='utf-8')
    css=(BASE/'style.css').read_text(encoding='utf-8')+'\n'+(BASE/'live-preview.css').read_text(encoding='utf-8')
    javascript=(BASE/'app.js').read_text(encoding='utf-8')+'\n'+(BASE/'live-preview.js').read_text(encoding='utf-8')
    import base64
    fallback=['data:image/svg+xml;base64,'+base64.b64encode((BASE/'assets'/name).read_bytes()).decode('ascii') for name in ['landscape.svg','city.svg','coast.svg']]
    output=template.replace('/*__CATALOG_DATA__*/',f'window.CATALOG={encoded};')
    output=output.replace('<link rel="stylesheet" href="style.css">','<style>'+css+'</style>')
    output=output.replace('<script src="app.js"></script>','<script>window.FALLBACK_IMAGES='+json.dumps(fallback)+';'+javascript+'</script>')
    if output==template:raise ValueError('HTML template insertion point not found')
    (BASE/'index.html').write_text(output,encoding='utf-8')
    print('生成完了:',BASE/'index.html')
if __name__=='__main__':main()
