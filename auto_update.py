#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""まちの窓: 毎日収集 -> DB/CSV -> index.html 更新 -> (任意) GitHub push。標準ライブラリのみ。"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
DB_DIR = BASE / '日本ライブカメラ収集DB'
DB = DB_DIR / 'livecam.sqlite'
DATA = BASE / 'data'
LOCK = BASE / '.automation.lock'
CONFIG = BASE / 'config.json'


def message(text):
    print(f'[{datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")}] {text}', flush=True)


def execute(args, allow_fail=False):
    message('実行: ' + ' '.join(map(str, args)))
    code = subprocess.call([str(v) for v in args], cwd=BASE)
    if code and not allow_fail:
        raise RuntimeError(f'処理が失敗しました (exit={code}): {args[0]}')
    return code


def sync_data():
    DATA.mkdir(parents=True, exist_ok=True)
    for file in ('全動画候補.csv', '全チャンネル候補.csv'):
        src = DB_DIR / file
        if not src.is_file():
            raise FileNotFoundError(f'必要なデータがありません: {src}')
        shutil.copy2(src, DATA / file)
        message('CSV更新: ' + file)
    execute([sys.executable, BASE / 'update_site.py'])
    if not (BASE / 'index.html').is_file():
        raise FileNotFoundError('index.html が生成できませんでした')


def publish_git():
    # GitHub Actions はワークフロー内でコミット・Pagesデプロイを行う。
    if not (BASE / '.git').exists():
        message('Git管理が未設定なので公開はスキップしました。ローカルのサイト更新は完了しています。')
        return
    try:
        remote = subprocess.run(['git','remote','get-url','origin'],cwd=BASE,capture_output=True,text=True)
    except FileNotFoundError:
        message('Gitがインストールされていないため公開をスキップしました。')
        return
    if remote.returncode != 0:
        message('Gitの origin がありません。GitHub公開をスキップします。')
        return
    names = [
        'index.html','catalog.json','data/全動画候補.csv','data/全チャンネル候補.csv',
        '日本ライブカメラ収集DB/livecam.sqlite','日本ライブカメラ収集DB/収集状況.json',
    ]
    execute(['git','add','--',*names])
    changed = subprocess.run(['git','diff','--cached','--quiet','--',*names],cwd=BASE)
    if changed.returncode == 0:
        message('公開対象の変更がないためGitHubへのpushは不要です。')
        return
    if changed.returncode != 1:
        raise RuntimeError('git diff に失敗しました')
    execute(['git','-c','user.name=machino-mado-bot','-c','user.email=bot@users.noreply.github.com',
             'commit','-m','chore: update livecam catalog'])
    execute(['git','push','origin','HEAD'])
    message('GitHubへpushしました。公開反映はGitHub Pagesの設定・ビルド状態に依存します。')


def main():
    parser = argparse.ArgumentParser(description='日本全国ライブカメラ: 自動収集・CSV・サイト更新')
    parser.add_argument('--site-only', action='store_true', help='APIを使わずDBからCSVとWebサイトを再生成')
    parser.add_argument('--dry-run', action='store_true', help='APIを呼ばず実行予定の処理を表示')
    parser.add_argument('--publish', action='store_true', help='設定済みGitリポジトリへ生成結果をコミットしてpush')
    parser.add_argument('--skip-search', action='store_true', help='検索枠不足時に動画検索を省略')
    parser.add_argument('--skip-expand', action='store_true', help='既知チャンネルからの探索を省略')
    parser.add_argument('--skip-refresh', action='store_true', help='ライブ状態の更新を省略')
    args = parser.parse_args()
    conf = json.loads(CONFIG.read_text(encoding='utf-8'))
    if not DB.is_file():
        raise FileNotFoundError(f'DBが見つかりません: {DB}。READMEの移行手順を確認してください。')
    if not args.site_only and not args.dry_run and not os.getenv('YOUTUBE_API_KEY'):
        raise RuntimeError('YOUTUBE_API_KEY がありません。GitHub Actions Secretか、Windowsのユーザー環境変数に設定してください。')

    options = [
        ('search', min(90,max(0,int(conf['search_calls']))), ['--skip-details','--pages',str(conf['search_pages'])],args.skip_search),
        ('expand', max(0,int(conf['expand_calls'])), ['--max-channels',str(conf['max_channels']), '--channel-pages',str(conf['channel_pages'])],args.skip_expand),
        ('refresh',max(0,int(conf['refresh_calls'])),['--max-videos',str(conf['refresh_max_videos']),'--refresh-hours',str(conf['refresh_hours'])],args.skip_refresh),
    ]
    if args.dry_run:
        message('DRY RUN: APIリクエストは一切行いません。')
        for phase, count, flags, skipped in options:
            message(f'{phase}: ' + ('スキップ' if skipped or not count else f'最大{count}回 / {" ".join(flags)}'))
        message('CSV -> index.html -> ' + ('GitHub push' if args.publish else 'ローカル保存'))
        return
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(f'pid={os.getpid()}\n')
    except FileExistsError:
        raise RuntimeError('別の更新処理が実行中か、前回のロックが残っています。.automation.lock を確認してください。')
    try:
        message('開始。YouTube検索は標準1日100回、通常読み取りは別枠で合計10,000ユニットが目安です。')
        if args.site_only:
            # APIにアクセスせず、DBから既存CSVを書き出し直す。
            execute([sys.executable,BASE/'collect_livecams.py','--phase','import','--seed-dir',BASE/'seed-empty','--out',DB_DIR])
        else:
            for phase, count, flags, skipped in options:
                if skipped or count==0:
                    message(phase + ' はスキップ')
                    continue
                execute([sys.executable,BASE/'collect_livecams.py','--phase',phase,'--calls',str(count),
                         '--seed-dir',BASE/'seed-empty','--out',DB_DIR,*flags])
        sync_data()
        if args.publish:
            publish_git()
        message('終了: サイトと収集データの更新が完了しました。')
    finally:
        LOCK.unlink(missing_ok=True)

if __name__ == '__main__':
    try:main()
    except KeyboardInterrupt:
        message('Ctrl+C で中断しました。これまでのSQLiteデータは保持されています。');sys.exit(130)
    except Exception as error:
        message(f'エラー: {error}');sys.exit(1)
