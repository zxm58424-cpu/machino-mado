#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""まちの窓の現在のGitHubフォルダーに「一覧内ライブプレビュー」を追加。

既存の SQLite / CSV / テンプレート / 動画情報を変更しません。
最新版の app.js や update_site.py に対し、必要な読み込み行だけを追加します。
"""
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
WORKFLOW = BASE / '.github' / 'workflows' / 'daily.yml'
UPDATER = BASE / 'update_site.py'


def once_replace(text, old, new, label):
    if new in text:
        print(f'[そのまま] {label} は適用済み')
        return text
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: 期待する箇所が{n}件です。安全のため変更せず終了します。')
    print(f'[追加] {label}')
    return text.replace(old, new, 1)


def main():
    for required in [UPDATER, WORKFLOW, BASE/'app.js', BASE/'style.css', BASE/'live-preview.js', BASE/'live-preview.css']:
        if not required.is_file():
            raise RuntimeError(f'ファイルが見つかりません: {required}\nGitHub Desktopの machino-mado フォルダー直下に、この3ファイルを置いてください。')
    update_src = UPDATER.read_text(encoding='utf-8')
    css_old = "css=(BASE/'style.css').read_text(encoding='utf-8')"
    js_old = "javascript=(BASE/'app.js').read_text(encoding='utf-8')"
    update_src = once_replace(update_src, css_old, css_old + "+'\\n'+(BASE/'live-preview.css').read_text(encoding='utf-8')", 'CSS埋め込み')
    update_src = once_replace(update_src, js_old, js_old + "+'\\n'+(BASE/'live-preview.js').read_text(encoding='utf-8')", 'JavaScript埋め込み')

    workflow_src = WORKFLOW.read_text(encoding='utf-8')
    push_triggers = """on:
  push:
    branches: [main]
    paths:
      - 'live-preview.js'
      - 'live-preview.css'
      - 'update_site.py'
      - 'app.js'
      - 'style.css'
      - 'template.html'
      - '.github/workflows/daily.yml'
  schedule:"""
    workflow_src=once_replace(workflow_src, 'on:\n  schedule:', push_triggers, 'サイト編集時の自動ビルド')
    workflow_src=once_replace(workflow_src,
        'if [ -z "$YOUTUBE_API_KEY" ]; then',
        'if [ "${{ github.event_name }}" != "push" ] && [ -z "$YOUTUBE_API_KEY" ]; then',
        'サイト編集時のAPIキー不要化')
    workflow_src=once_replace(workflow_src,
        '          python auto_update.py\n',
        '          if [ "${{ github.event_name }}" = "push" ]; then\n            python auto_update.py --site-only\n          else\n            python auto_update.py\n          fi\n',
        'サイト編集時のAPI不要再生成')

    # 両ファイルの変換に成功してから書き戻す
    UPDATER.write_text(update_src, encoding='utf-8')
    WORKFLOW.write_text(workflow_src, encoding='utf-8')
    print('\n成功: 動画データベースには触れていません。')
    print('次: GitHub Desktopで変更をCommit to main → Push origin。')
    print('Pushすると収集APIを使わずサイト再生成・公開が起動します。')


if __name__ == '__main__':
    try:main()
    except Exception as e:
        print('エラー:',e, file=sys.stderr)
        sys.exit(1)
