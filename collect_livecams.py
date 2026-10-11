#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTubeの日本国内ライブカメラを、重複を避けて継続収集する標準ライブラリ専用ツール。

初回: py 日本ライブカメラ拡張収集.py --phase import --seed-dir .
     py 日本ライブカメラ拡張収集.py --phase expand --calls 900
     py 日本ライブカメラ拡張収集.py --phase search --calls 90 --skip-details
翌日: 同じコマンドをもう一度実行（DBから再開）。
必要: 環境変数 YOUTUBE_API_KEY（API実行時のみ）。検索一覧作成は不要。
注意: 本ツールは候補の発見・暫定分類を行う。日本国内/定点カメラと断定しない。
"""
import argparse
import hashlib
import csv
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen

PREF = '北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split()
GENRES = [
 'ライブカメラ','定点カメラ','お天気カメラ','24時間 LIVE','ライブ配信 定点','ライブ中継 景色','風景配信','交通情報 カメラ',
 '駅前 ライブカメラ','電車 鉄道 ライブカメラ','新幹線 LIVE','空港 ライブカメラ','航空機 24時間 live','港湾 船舶 ライブ',
 '漁港 ライブカメラ','海岸 波 ライブカメラ','サーフィン 波情報 ライブ','河川 水位 ライブカメラ','ダム ライブカメラ',
 '国道 ライブカメラ','高速道路 ライブ映像','都市 街並み ライブカメラ','繁華街 定点カメラ','交差点 LIVE',
 '火山 噴煙 ライブカメラ','山岳 登山 ライブカメラ','富士山 ライブ映像','積雪 スキー場 ライブカメラ',
 '神社 参道 ライブカメラ','城 観光地 ライブ配信','寺 寺院 ライブカメラ','温泉 街並み LIVE',
 '水族館 生中継','動物園 ライブカメラ','鳥 巣箱 ライブカメラ','牧場 ライブカメラ','桜 紅葉 ライブカメラ',
 'Japan webcam 24/7','Japan live street cam','Japan train live camera','Japan airport live','Japan beach surf cam',
 'Japan live weather','Tokyo live cam 4K','Japan city live stream','日本 今の空','日本 ライブ定点','#ライブカメラ',
]
CITY_MAP = {
 '北海道':['札幌','函館','旭川','小樽','帯広','釧路','稚内','知床','富良野'],
 '青森県':['青森','八戸','弘前','十和田'], '岩手県':['盛岡','花巻','宮古','大船渡'],
 '宮城県':['仙台','松島','石巻','気仙沼'], '秋田県':['秋田','男鹿','横手'],
 '山形県':['山形','酒田','鶴岡','蔵王'], '福島県':['福島','郡山','いわき','会津若松'],
 '茨城県':['水戸','つくば','大洗','日立'], '栃木県':['宇都宮','日光','那須','鬼怒川'],
 '群馬県':['前橋','高崎','草津温泉','伊香保'], '埼玉県':['さいたま','大宮','川越','秩父'],
 '千葉県':['千葉','成田','銚子','館山','木更津'],
 '東京都':['東京駅','新宿','渋谷','池袋','上野','浅草','羽田空港','お台場','秋葉原','八王子','六本木','町田'],
 '神奈川県':['横浜','川崎','鎌倉','江ノ島','小田原','箱根','三浦'],
 '新潟県':['新潟','長岡','佐渡','湯沢','妙高'], '富山県':['富山','立山','高岡','雨晴'],
 '石川県':['金沢','輪島','能登','加賀','白山'], '福井県':['福井','敦賀','東尋坊','大野'],
 '山梨県':['甲府','河口湖','山中湖','富士吉田','本栖湖'],
 '長野県':['長野','松本','上高地','軽井沢','白馬','諏訪湖','志賀高原'],
 '岐阜県':['岐阜','高山','白川郷','郡上','下呂温泉'],
 '静岡県':['静岡','浜松','沼津','伊豆','富士宮','熱海','三島'],
 '愛知県':['名古屋','豊橋','岡崎','中部国際空港','豊田'],
 '三重県':['津','四日市','鳥羽','伊勢','熊野'], '滋賀県':['大津','琵琶湖','彦根','長浜'],
 '京都府':['京都駅','祇園','嵐山','宇治','天橋立','舞鶴'],
 '大阪府':['大阪駅','梅田','なんば','道頓堀','天王寺','新大阪','関西空港'],
 '兵庫県':['神戸','姫路','明石','淡路島','城崎','西宮'],
 '奈良県':['奈良公園','東大寺','吉野','橿原'], '和歌山県':['和歌山','白浜','串本','那智の滝'],
 '鳥取県':['鳥取砂丘','米子','境港','大山'], '島根県':['松江','出雲','隠岐','石見銀山'],
 '岡山県':['岡山','倉敷','津山','瀬戸内'], '広島県':['広島','宮島','尾道','呉','福山'],
 '山口県':['下関','岩国','萩','関門橋'], '徳島県':['徳島','鳴門','阿波池田'],
 '香川県':['高松','丸亀','小豆島','瀬戸大橋'], '愛媛県':['松山','今治','宇和島','道後温泉'],
 '高知県':['高知','室戸','四万十','足摺'],
 '福岡県':['博多','天神','小倉','門司港','福岡空港','久留米'],
 '佐賀県':['佐賀','唐津','鳥栖','嬉野'], '長崎県':['長崎','佐世保','軍艦島','島原','対馬'],
 '熊本県':['熊本','阿蘇','天草','人吉'], '大分県':['大分','別府','由布院','中津'],
 '宮崎県':['宮崎','日南','延岡','高千穂'], '鹿児島県':['鹿児島','桜島','霧島','屋久島','奄美'],
 '沖縄県':['那覇','国際通り','名護','恩納村','宮古島','石垣島','久米島'],
}
# 誤判定を避け、キーワードは暫定判定にしか使用しない。
CAMERA = re.compile(r'ライブカメラ|定点(?:観測|カメラ|配信|映像)|防災カメラ|監視カメラ|webcam|live\s*cam(?:era)?|livecam|streaming\s*camera|24/7\s*cam',re.I)
NOT_CAMERA = re.compile(r'ゲーム実況|ゲーム配信|歌枠|生演奏|ライブペイント|描いてみた|開封ライブ|株価(?:予想|配信)|スポーツ実況|観戦ライブ|同時視聴|雑談配信|占いライブ|ASMR|勉強配信|VTuber|ポケモン',re.I)
GENRE = [
 ('鉄道',r'新幹線|鉄道|電車|列車|踏切|駅前|停車場|railway|train'),
 ('空港・飛行機',r'空港|飛行機|滑走路|航空|airport|aviation'),
 ('道路・交通',r'高速道路|国道|交差点|道路|道路状況|traffic|road'),
 ('河川・湖・ダム',r'河川|水位|川|湖|ダム|river|lake'),
 ('海・港・波',r'海岸|海辺|海|港|船舶|漁港|波|湾|beach|surf|port|harbor'),
 ('山・火山',r'山岳|富士山|桜島|阿蘇山|火山|噴火|登山|mountain|volcano'),
 ('動物・水族館',r'動物園|水族館|ラッコ|ペンギン|鳥|動物|aquarium|zoo'),
 ('雪・スキー',r'スキー|ゲレンデ|積雪|降雪|snow'),
 ('寺社・歴史',r'神社|お寺|寺院|寺|仏閣|城|鳥居|shrine|temple'),
 ('街・観光・天気',r'街|市街|交差点|タワー|公園|通り|駅前|温泉|観光|夜景|天気|空模様|city|street|sky|town'),
]
SOURCE_LINK = 'https://japan-livecam.com/'
COLUMNS_V = ['video_id','title','channel_id','channel_title','youtube_url','status','status_checked_utc','started_utc','ended_utc','scheduled_utc','prefecture','location_basis','camera_judgement','domestic_judgement','genre','source_count','source_examples','discovery_source','last_seen_utc','description_excerpt']
COLUMNS_C = ['channel_id','channel_title','channel_url','uploads_playlist_id','last_scan_utc','last_metadata_check_utc','video_count','camera_named','source_count','discovery_source']

def utc_now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def csv_rows(path):
    with Path(path).open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def csv_save(path,headers,items):
    dest=Path(path);tmp=dest.with_suffix(dest.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');writer.writeheader();writer.writerows(items)
    tmp.replace(dest)
def chunk(seq,n):
    for i in range(0,len(seq),n):yield seq[i:i+n]
def init_db(conn):
    conn.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS videos(
       id TEXT PRIMARY KEY,title TEXT DEFAULT '',channel_id TEXT DEFAULT '',channel_title TEXT DEFAULT '',status TEXT DEFAULT '未確認',
       status_checked TEXT DEFAULT '',started TEXT DEFAULT '',ended TEXT DEFAULT '',scheduled TEXT DEFAULT '',description TEXT DEFAULT '',
       first_seen TEXT DEFAULT '',last_seen TEXT DEFAULT '',discovery_source TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS channels(
       id TEXT PRIMARY KEY,title TEXT DEFAULT '',uploads TEXT DEFAULT '',last_meta TEXT DEFAULT '',last_scan TEXT DEFAULT '',first_seen TEXT DEFAULT '',discovery_source TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS sources(
       kind TEXT NOT NULL,item_id TEXT NOT NULL,origin TEXT NOT NULL,reference TEXT NOT NULL, PRIMARY KEY(kind,item_id,origin,reference));
    CREATE TABLE IF NOT EXISTS api_usage(
       date_pt TEXT NOT NULL, api_key_hash TEXT NOT NULL, bucket TEXT NOT NULL, calls INTEGER DEFAULT 0,
       PRIMARY KEY(date_pt,api_key_hash,bucket));
    CREATE TABLE IF NOT EXISTS handles(
       handle TEXT PRIMARY KEY,title TEXT DEFAULT '',original_url TEXT DEFAULT '',source_url TEXT DEFAULT '',checked TEXT DEFAULT '',resolved_channel TEXT DEFAULT '',error TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS site_index(
       seq INTEGER PRIMARY KEY,pref TEXT,spot TEXT,genre TEXT,video_id TEXT DEFAULT '',source_url TEXT,search_url TEXT);
    CREATE TABLE IF NOT EXISTS jobs(
       key TEXT PRIMARY KEY,kind TEXT,q TEXT,pref_hint TEXT,source TEXT,priority INTEGER DEFAULT 50,
       next_token TEXT DEFAULT '',pages_done INTEGER DEFAULT 0,finished INTEGER DEFAULT 0,total_found INTEGER DEFAULT 0,new_found INTEGER DEFAULT 0,
       last_run TEXT DEFAULT '',error TEXT DEFAULT '');
    ''')
    conn.commit()

def video_add(db,vid,title='',cid='',channel_title='',origin='source',ref='',seen=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid or ''):return False
    seen=seen or utc_now()
    prev=db.execute('SELECT id FROM videos WHERE id=?',(vid,)).fetchone()
    db.execute('''INSERT INTO videos(id,title,channel_id,channel_title,first_seen,last_seen,discovery_source) VALUES(?,?,?,?,?,?,?)
         ON CONFLICT(id) DO UPDATE SET title=CASE WHEN excluded.title!='' AND (videos.title='' OR videos.title LIKE '%%ライブカメラ候補%%') THEN excluded.title ELSE videos.title END,
           channel_id=CASE WHEN excluded.channel_id!='' THEN excluded.channel_id ELSE videos.channel_id END,
           channel_title=CASE WHEN excluded.channel_title!='' THEN excluded.channel_title ELSE videos.channel_title END,last_seen=excluded.last_seen''',
           (vid,title,cid,channel_title,seen,seen,origin))
    if cid:channel_add(db,cid,channel_title,origin,ref,seen)
    if ref:db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?)',('video',vid,origin,str(ref)[:1500]))
    return prev is None

def channel_add(db,cid,title='',origin='source',ref='',seen=None):
    if not re.fullmatch(r'UC[\w-]{22}',cid or ''):return False
    seen=seen or utc_now()
    prev=db.execute('SELECT id FROM channels WHERE id=?',(cid,)).fetchone()
    db.execute('''INSERT INTO channels(id,title,first_seen,discovery_source) VALUES(?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET title=CASE WHEN excluded.title!='' AND (channels.title='' OR channels.title LIKE '%%Unknown%%') THEN excluded.title ELSE channels.title END''',(cid,title,seen,origin))
    if ref:db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?)',('channel',cid,origin,str(ref)[:1500]))
    return prev is None

def video_id_from_url(url):
    if not url:return ''
    u=urlparse(url)
    if u.hostname and 'youtu.be' in u.hostname:
        key=u.path.strip('/').split('/')[0]
    elif u.hostname and ('youtube.com' in u.hostname or 'youtube-nocookie.com' in u.hostname):
        key=parse_qs(u.query).get('v',[''])[0] or (u.path.split('/shorts/')[-1].split('/')[0] if '/shorts/' in u.path else '')
    else:key=''
    return key if re.fullmatch(r'[\w-]{11}',key) else ''

def import_seeds(db,seed_dir):
    root=Path(seed_dir)
    n={'videos':0,'channels':0,'index':0,'index_link':0,'index_unlinked':0}
    file=root/'チャンネル候補.csv'
    if file.exists():
        for r in csv_rows(file):
            if channel_add(db,r.get('channel_id',''),r.get('channel_title',''),'旧CSV',r.get('first_query','')):n['channels']+=1
    file=root/'ライブ配信候補.csv'
    if file.exists():
        for r in csv_rows(file):
            vid=r.get('video_id','') or video_id_from_url(r.get('youtube_url',''))
            if video_add(db,vid,r.get('title',''),r.get('channel_id',''),r.get('channel_title',''),'旧CSV',r.get('source_query','')):n['videos']+=1
            if vid:
                checked=r.get('checked_at_utc','');st=r.get('status','未確認')
                db.execute('''UPDATE videos SET status=?,status_checked=?,started=? WHERE id=? AND (status_checked='' OR status_checked<?)''',
                           (st,checked,r.get('actual_start',''),vid,checked))
    file=root/'youtube_japan_livecam_324_2026-10-11.csv'
    if file.exists():
        for idx,r in enumerate(csv_rows(file),1):
            pref=r.get('都道府県',''); name=r.get('掲載地点・名称','')
            url=r.get('直接YouTube URL（47件）','');vid=video_id_from_url(url)
            db.execute('''INSERT OR REPLACE INTO site_index(seq,pref,spot,genre,video_id,source_url,search_url)
                VALUES(?,?,?,?,?,?,?)''',(idx,pref,name,r.get('ジャンル（名称から推定）',''),vid,r.get('配信元の掲載一覧URL',''),r.get('YouTube検索URL','')))
            n['index']+=1
            if vid:
                if video_add(db,vid,f'{pref} {name}（掲載サイト由来・要再確認）','','','掲載サイト直接リンク',url):n['index_link']+=1
            else:n['index_unlinked']+=1
    # 外部掲載の42チャンネル（YouTubeの@ハンドルはAPIでIDに解決する）
    file=root/'外部掲載チャンネル42件.csv'
    n['source_channels']=0
    n['handles_to_resolve']=0
    if file.exists():
        for r in csv_rows(file):
            url=r.get('YouTubeチャンネルURL','')
            name=r.get('チャンネル・運営主体','')
            ref=r.get('リンク元','')
            match=re.search(r'/channel/(UC[\w-]{22})',url)
            if match:
                if channel_add(db,match.group(1),name,'外部掲載チャンネル',ref):n['source_channels']+=1
            else:
                handle_match=re.search(r'youtube\.com/(@[^/?#]+)',url)
                if handle_match:
                    handle=handle_match.group(1)
                    db.execute('INSERT OR IGNORE INTO handles(handle,title,original_url,source_url) VALUES(?,?,?,?)',(handle,name,url,ref))
                    n['handles_to_resolve']+=1
    db.commit();return n

def classify(title, desc=''):
    text=(title or '')+' '+(desc or '')[:300]
    loc_hits=[p for p in PREF if p in (title or '')]
    if len(loc_hits)==1:
        pref,basis=loc_hits[0],'タイトルに都道府県名'
    else:
        city_matches=[(p,city) for p,cities in CITY_MAP.items() for city in cities if city in (title or '')]
        uniques=list(dict.fromkeys(p for p,c in city_matches))
        if len(uniques)==1:pref,basis=uniques[0],'タイトルの地名から推定'
        else:pref,basis='未判定','地名なし・複数候補'
    if NOT_CAMERA.search(title or '') and not CAMERA.search(title or ''):camera='対象外疑い'
    elif CAMERA.search(title or ''):camera='定点カメラ有力'
    elif re.search(r'24時間|LIVE|生中継|ライブ配信|眺望|中継',title or '',re.I):camera='映像要確認'
    else:camera='映像要確認'
    if pref!='未判定' and camera!='対象外疑い':dom='国内候補（場所未検証）'
    else:dom='未判定'
    if re.search(r'iceland|icelandic|インドネシア|ハワイ島|海外|new york|london|paris|イタリア|スイス',title or '',re.I) and pref=='未判定':dom='海外疑い'
    genre=next((g for g,pattern in GENRE if re.search(pattern,title or '',re.I)),'その他・未判定')
    return pref,basis,camera,dom,genre

def add_jobs(db):
    plan=[]
    def add(kind,q,region='',source='',priority=50,order='relevance'):
        k=f'{kind}|{q}|{order}'
        plan.append((k,kind,q,region,source,priority))
    for p in PREF:
        for s,pr in [('ライブカメラ',12),('定点カメラ',25),('お天気カメラ',35),('生中継 24時間',45),('交通 ライブカメラ',44),('海 港 ライブカメラ',47),('駅 鉄道 ライブカメラ',47),('空港 ライブカメラ',48)]:add('video',p+' '+s,p,'都道府県',pr)
        add('channel',p+' ライブカメラ',p,'県別チャンネル',23)
    for q in GENRES:
        add('video',q,'','ジャンル',21)
        if 'カメラ' in q or 'webcam' in q or 'live cam' in q:add('channel',q,'','ジャンル別チャンネル',31)
    for p,cities in CITY_MAP.items():
        for city in cities:
            add('video',city+' ライブカメラ',p,'市・地名',29)
            add('video',city+' 定点映像',p,'市・地名／別名',47)
    for q in ['ライブカメラ','定点カメラ','#ライブカメラ','live camera japan','24時間配信 カメラ 日本','防災カメラ','現地中継 日本','live webcam Tokyo','ライブカメラ 公式']:
        add('channel',q,'','全国チャンネル',11)
    for row in db.execute('SELECT pref,spot,video_id FROM site_index WHERE video_id=""'):
        q=f'{row["pref"]} {row["spot"]} ライブカメラ'
        add('video',q,row['pref'],'掲載サイト未照合地点',18)
    # 恒久的な一意キー。入力データを後日増やしても完了済みタスクは再実行しない。
    db.executemany('''INSERT OR IGNORE INTO jobs(key,kind,q,pref_hint,source,priority) VALUES(?,?,?,?,?,?)''',plan)
    db.commit();return len(plan)

class API:
    def __init__(self,key,db):
        self.key=key;self.db=db;self.key_hash=hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]
    def mark_call(self,method):
        try:
            from zoneinfo import ZoneInfo
            date_pt=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
        except Exception:
            # tzdataがないWindows: 安全側の太平洋標準時を使用
            date_pt=(datetime.now(timezone.utc)-timedelta(hours=8)).date().isoformat()
        bucket='search' if method=='search' else 'general'
        cap=90 if bucket=='search' else 9500
        row=self.db.execute('SELECT calls FROM api_usage WHERE date_pt=? AND api_key_hash=? AND bucket=?',(date_pt,self.key_hash,bucket)).fetchone()
        used=row['calls'] if row else 0
        if used>=cap:raise RuntimeError(f'{date_pt} PTの{bucket} API安全上限 {cap} 回に到達。翌日以降に再開してください。')
        self.db.execute('INSERT INTO api_usage(date_pt,api_key_hash,bucket,calls) VALUES(?,?,?,1) ON CONFLICT(date_pt,api_key_hash,bucket) DO UPDATE SET calls=calls+1',(date_pt,self.key_hash,bucket))
        self.db.commit()  # APIが失敗しても割り当て消費に含まれるので、リクエスト前に記録
    def get(self,method,params):
        qs=urlencode({**params,'key':self.key})
        # URLにAPIキーが含まれるのでエラーにはURLを表示しない
        req=Request(f'https://www.googleapis.com/youtube/v3/{method}?'+qs,headers={'User-Agent':'LiveCamCatalogResearch/2.0'})
        for attempt in range(3):
            self.mark_call(method)
            try:
                with urlopen(req,timeout=45) as resp:return json.load(resp)
            except HTTPError as e:
                try:payload=json.loads(e.read().decode('utf-8'));reason=payload.get('error',{}).get('errors',[{}])[0].get('reason','');message=payload.get('error',{}).get('message','')
                except Exception:reason='';message='HTTP error'
                if e.code in (429,500,502,503,504) and attempt<2:
                    time.sleep((attempt+1)*2);continue
                raise RuntimeError(f'HTTP {e.code}: {reason}: {message}') from None
            except (URLError,TimeoutError) as e:
                if attempt<2:time.sleep(attempt+1);continue
                raise RuntimeError('通信エラー（接続設定を確認）') from None

def update_video_details(db,api,ids):
    ids=[x for x in dict.fromkeys(ids) if re.fullmatch(r'[\w-]{11}',x)]
    if not ids:return 0
    resp=api.get('videos',{'part':'snippet,liveStreamingDetails','id':','.join(ids)})
    now=utc_now()
    for item in resp.get('items',[]):
        vid=item['id'];sn=item.get('snippet',{});live=item.get('liveStreamingDetails',{})
        status=('配信終了' if live.get('actualEndTime') else 'ライブ' if sn.get('liveBroadcastContent')=='live' else '配信予定' if sn.get('liveBroadcastContent')=='upcoming' else '配信状態不明')
        video_add(db,vid,sn.get('title',''),sn.get('channelId',''),sn.get('channelTitle',''),'API動画詳細','詳細取得',now)
        db.execute('''UPDATE videos SET title=?,channel_id=?,channel_title=?,status=?,status_checked=?,started=?,ended=?,scheduled=?,description=?,last_seen=? WHERE id=?''',
            (sn.get('title',''),sn.get('channelId',''),sn.get('channelTitle',''),status,now,live.get('actualStartTime',''),live.get('actualEndTime',''),live.get('scheduledStartTime',''),sn.get('description','')[:1800],now,vid))
    return len(resp.get('items',[]))

def do_search(db,api,budget,pages,term_limit=0,fetch_details=True):
    # タスクごとに動画テーブル全件を走査する相関SQLを廃止（大幅なローカル処理短縮）。
    # 都道府県別件数は一括計算し、新規動画を発見した分だけ更新する。
    pref_counts={r['pref_hint']:0 for r in db.execute("SELECT DISTINCT pref_hint FROM jobs WHERE pref_hint!=''")}
    for r in db.execute('SELECT title FROM videos'):
        title=r['title'] or ''
        for pref in pref_counts:
            if pref in title:pref_counts[pref]+=1
    used=0;new_count=0
    while used<budget:
        jobs=db.execute('SELECT * FROM jobs WHERE finished=0').fetchall()
        if not jobs:
            cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
            # 全タスクを一巡した後、古い検索を再開可能にして新規動画の差分を発見する。
            n=db.execute('UPDATE jobs SET finished=0,pages_done=0,next_token="" WHERE finished=1 AND last_run<?',(cutoff,)).rowcount
            db.commit()
            if n:print(f'前回検索から7日以上経過したタスクを{n}件再開しました。');continue
            print('検索計画の現在のタスクは完了です（7日後から定期的に再検索します）。');break
        job=min(jobs,key=lambda j:(j['priority']+min(pref_counts.get(j['pref_hint'],0),20)*2,j['pages_done'],j['key']))
        if term_limit and used>=term_limit:break
        args={'part':'snippet','q':job['q'],'type':job['kind'],'maxResults':50,'regionCode':'JP','relevanceLanguage':'ja','safeSearch':'none'}
        if job['kind']=='video':args['eventType']='live'
        if job['next_token']:args['pageToken']=job['next_token']
        try:resp=api.get('search',args)
        except RuntimeError as e:print(f'検索停止: {e}',file=sys.stderr);break
        used+=1;found=0;fresh=[];num=0
        for item in resp.get('items',[]):
            sn=item.get('snippet',{});v=item.get('id',{}).get('videoId','')
            c=item.get('id',{}).get('channelId') or sn.get('channelId','')
            ref=job['q']+' | '+job['kind']
            if job['kind']=='channel':
                if channel_add(db,c,sn.get('title',''),'API検索（チャンネル）',ref):found+=1
            else:
                title=sn.get('title','')
                if video_add(db,v,title,c,sn.get('channelTitle',''),'API検索（動画）',ref):
                    found+=1
                    for pref in pref_counts:
                        if pref in title:pref_counts[pref]+=1
                    if not fetch_details:
                        db.execute("UPDATE videos SET status='検索時LIVE候補' WHERE id=? AND status='未確認'",(v,))
                if v:fresh.append(v)
            num+=1
        # --skip-details 時は search.list のみで収集し、詳細は後から --phase refresh で取得する。
        if fresh and fetch_details:
            try:
                for group in chunk(fresh,50):update_video_details(db,api,group)
            except RuntimeError as e:print('動画詳細は次回更新対象:',e,file=sys.stderr)
        done=job['pages_done']+1
        token=resp.get('nextPageToken','')
        finished=not token or done>=max(1,pages) or (done>=1 and found<=2)
        db.execute('''UPDATE jobs SET pages_done=?,next_token=?,finished=?,total_found=total_found+?,new_found=new_found+?,last_run=?,error='' WHERE key=?''',
                  (done,'' if finished else token,int(finished),num,found,utc_now(),job['key']))
        db.commit();new_count+=found
        print(f'検索 {used}/{budget}: {job["kind"]} {job["q"][:32]} / {num}ヒット、新規{found}')
    return {'検索API回数':used,'新規ID数':new_count}

def resolve_handles(db,api,budget):
    used=0;resolved=0
    for row in db.execute('SELECT * FROM handles WHERE checked="" ORDER BY handle').fetchall():
        if used>=budget:break
        try:res=api.get('channels',{'part':'snippet,contentDetails','forHandle':row['handle']})
        except RuntimeError as e:
            print('チャンネル@ID解決を停止:',e,file=sys.stderr);break
        used+=1
        items=res.get('items',[])
        if items:
            ch=items[0];cid=ch['id'];meta=ch.get('snippet',{});u=ch.get('contentDetails',{}).get('relatedPlaylists',{}).get('uploads','')
            channel_add(db,cid,meta.get('title') or row['title'],'外部掲載チャンネル',row['source_url'])
            db.execute('UPDATE channels SET uploads=?,last_meta=? WHERE id=?',(u,utc_now(),cid))
            db.execute('UPDATE handles SET checked=?,resolved_channel=?,error="" WHERE handle=?',(utc_now(),cid,row['handle']))
            resolved+=1
        else:db.execute('UPDATE handles SET checked=?,error=? WHERE handle=?',(utc_now(),'未検出',row['handle']))
        db.commit()
    return used,resolved

def do_expand(db,api,budget,max_channels=500,scan_hours=24,channel_pages=1):
    now=datetime.now(timezone.utc)
    target=[]
    for r in db.execute('''SELECT c.*, (SELECT COUNT(*) FROM videos v WHERE v.channel_id=c.id AND (v.title LIKE '%カメラ%' OR v.title LIKE '%定点%' OR LOWER(v.title) LIKE '%webcam%')) known
                           FROM channels c'''):
        has_title=bool(CAMERA.search(r['title'] or ''))
        if not has_title and not r['known'] and r['discovery_source']!='外部掲載チャンネル':continue
        try:last=datetime.fromisoformat(r['last_scan'].replace('Z','+00:00')) if r['last_scan'] else None
        except ValueError:last=None
        if last and now-last<timedelta(hours=scan_hours):continue
        target.append((0 if r['discovery_source']=='外部掲載チャンネル' else 1 if has_title else 2,-r['known'],r['last_scan'],r['id']))
    target.sort();targets=[cid for *_,cid in target[:max_channels]]
    print(f'既知チャンネルから再検査候補 {len(target)}件、今回対象 {len(targets)}件')
    used=0;scanned=0;added=0;api_missing=0
    for group in chunk(targets,50):
        if used>=budget:break
        missing=[cid for cid in group if not db.execute('SELECT uploads FROM channels WHERE id=?',(cid,)).fetchone()['uploads']]
        if missing:
            try:res=api.get('channels',{'part':'snippet,contentDetails','id':','.join(missing)})
            except RuntimeError as e:print('チャンネル詳細取得を停止:',e,file=sys.stderr);break
            used+=1
            for obj in res.get('items',[]):
                ch_id=obj['id'];up=obj.get('contentDetails',{}).get('relatedPlaylists',{}).get('uploads','')
                title=obj.get('snippet',{}).get('title','')
                db.execute('UPDATE channels SET uploads=?,title=?,last_meta=? WHERE id=?',(up,title,utc_now(),ch_id))
            db.commit()
        for cid in group:
            if used>=budget:break
            row=db.execute('SELECT uploads FROM channels WHERE id=?',(cid,)).fetchone();pl=row['uploads'] if row else ''
            if not pl:api_missing+=1;db.execute('UPDATE channels SET last_scan=? WHERE id=?',(utc_now(),cid));continue
            token='';all_ids=[];failed=False
            for pn in range(channel_pages):
                if used>=budget:break
                params={'part':'snippet,contentDetails','playlistId':pl,'maxResults':50}
                if token:params['pageToken']=token
                try:resp=api.get('playlistItems',params)
                except RuntimeError as e:print('アップロード一覧取得の一時停止:',e,file=sys.stderr);failed=True;break
                used+=1
                for it in resp.get('items',[]):
                    sn=it.get('snippet',{});vid=it.get('contentDetails',{}).get('videoId') or sn.get('resourceId',{}).get('videoId','')
                    name=sn.get('title','')
                    if name in ('Private video','Deleted video'):continue
                    # 誤収集の大量増加を避け、チャンネルの全動画ではなくライブ関連の可能性をもつ候補のみ入れる。
                    if not (CAMERA.search(name) or re.search(r'ライブ|生中継|LIVE|映像|天気|波|交通|定点|24時間|4K|stream|weather',name,re.I)):continue
                    if video_add(db,vid,name,cid,sn.get('channelTitle',''),'既知チャンネルのアップロード一覧',pl):added+=1
                    if vid:all_ids.append(vid)
                token=resp.get('nextPageToken','')
                if not token:break
            # バッチ取得で現在の配信状態を確認。検索クォータは消費しない。
            for parts in chunk(all_ids,50):
                if used>=budget:break
                try:update_video_details(db,api,parts);used+=1
                except RuntimeError as e:print('動画詳細取得の一時停止:',e,file=sys.stderr);failed=True;break
            if not failed:
                db.execute('UPDATE channels SET last_scan=? WHERE id=?',(utc_now(),cid));scanned+=1
            db.commit()
        if used>=budget:break
    return {'通常API回数':used,'調査チャンネル':scanned,'新規動画':added,'uploads未取得':api_missing}

def do_refresh(db,api,budget,max_videos=1200,age_hours=12):
    before=(datetime.now(timezone.utc)-timedelta(hours=age_hours)).isoformat()
    # 非定点の候補も履歴に残すが、最近LIVEだったもの／未確認のものを優先。
    records=db.execute('''SELECT id FROM videos WHERE status_checked='' OR status_checked<?
          ORDER BY CASE WHEN status IN ('ライブ','未確認','検索時LIVE候補') THEN 0 ELSE 1 END,
          CASE WHEN status_checked='' THEN 0 ELSE 1 END,status_checked ASC LIMIT ?''',(before,max_videos)).fetchall()
    total=0;calls=0
    for batch in chunk([r['id'] for r in records],50):
        if calls>=budget:break
        try:n=update_video_details(db,api,batch)
        except RuntimeError as e:print('再確認を停止:',e,file=sys.stderr);break
        total+=n;calls+=1;db.commit()
    return {'通常API回数':calls,'再確認動画':total}

def export_all(db,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    ids=db.execute('''SELECT v.*, (SELECT COUNT(*) FROM sources s WHERE s.kind='video' AND s.item_id=v.id) src_count,
             (SELECT GROUP_CONCAT(x.reference,' || ') FROM (SELECT reference FROM sources s WHERE s.kind='video' AND s.item_id=v.id LIMIT 3) x) source_examples FROM videos v ORDER BY v.status_checked DESC,v.id''').fetchall()
    videos=[]
    for row in ids:
        row=dict(row);pref,basis,camera,dom,genre=classify(row['title'],row['description'])
        videos.append(dict(video_id=row['id'],title=row['title'],channel_id=row['channel_id'],channel_title=row['channel_title'],youtube_url='https://www.youtube.com/watch?v='+row['id'],
               status=row['status'],status_checked_utc=row['status_checked'],started_utc=row['started'],ended_utc=row['ended'],scheduled_utc=row['scheduled'],
               prefecture=pref,location_basis=basis,camera_judgement=camera,domestic_judgement=dom,genre=genre,
               source_count=row['src_count'],source_examples=(row['source_examples'] or '')[:1000],discovery_source=row['discovery_source'],last_seen_utc=row['last_seen'],description_excerpt=row['description'][:200]))
    csv_save(out/'全動画候補.csv',COLUMNS_V,videos)
    counts={r['channel_id']:r['n'] for r in db.execute('SELECT channel_id,COUNT(*) n FROM videos WHERE channel_id!="" GROUP BY channel_id')}
    src_counts={r['item_id']:r['n'] for r in db.execute('SELECT item_id,COUNT(*) n FROM sources WHERE kind="channel" GROUP BY item_id')}
    channels=[]
    for row in db.execute('SELECT * FROM channels ORDER BY last_scan,id'):
        row=dict(row)
        channels.append(dict(channel_id=row['id'],channel_title=row['title'],channel_url='https://www.youtube.com/channel/'+row['id'],
            uploads_playlist_id=row['uploads'],last_scan_utc=row['last_scan'],last_metadata_check_utc=row['last_meta'],video_count=counts.get(row['id'],0),camera_named='有' if CAMERA.search(row['title'] or '') else '未判定',source_count=src_counts.get(row['id'],0),discovery_source=row['discovery_source']))
    csv_save(out/'全チャンネル候補.csv',COLUMNS_C,channels)
    site=[]
    for r in db.execute('SELECT * FROM site_index ORDER BY seq'):
        r=dict(r);site.append({**r,'照合状況':('直接動画URLあり（状態は別途確認）' if r['video_id'] else '動画URL未取得'), '地点名検索URL':r['search_url']})
    csv_save(out/'掲載サイト324地点照合.csv',['seq','pref','spot','genre','video_id','source_url','search_url','照合状況','地点名検索URL'],site)
    jobs=[dict(r) for r in db.execute('SELECT * FROM jobs ORDER BY priority,key')]
    csv_save(out/'検索タスク進捗.csv',['key','kind','q','pref_hint','source','priority','next_token','pages_done','finished','total_found','new_found','last_run','error'],jobs)
    handles=[dict(r) for r in db.execute('SELECT * FROM handles ORDER BY handle')]
    csv_save(out/'外部掲載ハンドル進捗.csv',['handle','title','original_url','source_url','checked','resolved_channel','error'],handles)
    needs=[r for r in videos if r['camera_judgement']!='定点カメラ有力' or r['domestic_judgement']!='国内候補（場所未検証）']
    csv_save(out/'目視確認が必要.csv',COLUMNS_V,needs)
    stat={'更新日時UTC':utc_now(),'動画候補数':len(videos),'チャンネル候補数':len(channels),
          'サイト掲載地点数':len(site),'サイト直接動画URL数':sum(bool(r['video_id']) for r in site),
          'ライブ判定（最終確認時点）':sum(r['status']=='ライブ' for r in videos),
          'カメラ有力（機械判定）':sum(r['camera_judgement']=='定点カメラ有力' for r in videos),
          '未調査検索タスク数':sum(not r['finished'] for r in jobs),
          '検索タスク総数':len(jobs),'既知チャンネルうちアップロード検査済':sum(bool(c['last_scan_utc']) for c in channels),
          '外部掲載ハンドル解決済':db.execute('SELECT COUNT(*) FROM handles WHERE resolved_channel!=""').fetchone()[0],
          '外部掲載ハンドル未解決':db.execute('SELECT COUNT(*) FROM handles WHERE checked=""').fetchone()[0],
          '日本の全ライブカメラ取得':'保証不可（タイトル分類と検索APIの対象制限あり）'}
    (out/'収集状況.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\n--- 収集状況 ---');print(json.dumps(stat,ensure_ascii=False,indent=2));return stat

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--seed-dir',default='.',help='既存CSVの置き場所。初回はライブ配信候補.csvとチャンネル候補.csvを配置')
    p.add_argument('--out',default='日本ライブカメラ収集DB',help='データベースとCSVの出力場所')
    p.add_argument('--phase',choices=['import','search','expand','refresh','all'],default='all')
    p.add_argument('--calls',type=int,default=90,help='対象phaseのAPI呼び出し上限。allでは検索上限に使う')
    p.add_argument('--read-calls',type=int,default=900,help='allの通常読み取りAPI呼び出し上限（目安）')
    p.add_argument('--pages',type=int,default=2,help='検索語ごとの最大ページ数')
    p.add_argument('--skip-details',action='store_true',help='高速検索: 動画詳細APIをその場では取得せず、後からrefreshで確認する')
    p.add_argument('--channel-pages',type=int,default=1,help='既知チャンネルの最新アップロード取得ページ数')
    p.add_argument('--max-channels',type=int,default=450)
    p.add_argument('--max-videos',type=int,default=1200)
    p.add_argument('--refresh-hours',type=int,default=24)
    p.add_argument('--api-key',default=os.environ.get('YOUTUBE_API_KEY',''))
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(out/'livecam.sqlite');db.row_factory=sqlite3.Row
    init_db(db)
    imported=import_seeds(db,args.seed_dir)
    nplan=add_jobs(db)
    print('既存CSVの新規追加',imported,'検索タスク登録（重複込）',nplan)
    if args.phase!='import' and not args.api_key:
        print('APIキーがありません。既存データの統合CSVだけ出力します。API検索は未実施です。',file=sys.stderr)
    else:
        if args.phase!='import':
            api=API(args.api_key,db)
            try:
                if args.phase in ('search','all'):
                    print('検索結果:',do_search(db,api,max(0,min(args.calls,100)),max(1,args.pages),fetch_details=not args.skip_details))
                if args.phase in ('expand','all'):
                    allot=args.read_calls if args.phase=='all' else args.calls
                    consumed, resolved = resolve_handles(db,api,min(max(0,allot),60))
                    print(f'掲載サイトチャンネル名からID解決: {resolved}件、通常API {consumed}回')
                    print('既知チャンネル拡張:',do_expand(db,api,max(0,allot-consumed),args.max_channels,max(1,args.refresh_hours),max(1,args.channel_pages)))
                if args.phase=='refresh':
                    print('ライブ状態の再確認:',do_refresh(db,api,max(0,args.calls),args.max_videos,max(1,args.refresh_hours)))
            except KeyboardInterrupt:print('中断されました。ここまでの成果を保存します。',file=sys.stderr)
    db.commit();export_all(db,out);db.close()

if __name__=='__main__':main()
