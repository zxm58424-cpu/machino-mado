# GitHub専用セット（まずGITHUB_最初に読む.txtを参照）

# まちの窓 — YouTubeライブカメラの自動収集・サイト公開フルセット

> 2026年10月11日作成。動作確認: Python 3.12/3.13、SQLite初期DB、API呼び出しをしない更新フロー。
>
> **重要:** 1,093動画・1,008チャンネルは提供いただいた既存データの候補数で、日本に存在する全ライブカメラの確定数ではありません。分類・所在地・「ライブ」状態は自動推定や過去時点のものです。

## 一番簡単な始め方

ZIPを**フォルダーごと**展開します。`index.html` をダブルクリックすると、現在のサイトを表示できます。

収集済みデータの更新・サイト生成・公開まで自動化するには **A または B のどちらか1つ**を選んでください。同じAPIキーを使ったAとBの同時運転は、枠の競合やSQLiteの世代違いを招くため推奨しません。

### A. GitHub Actions — 推奨（PCの電源が不要・毎日自動公開）

1. [GitHub](https://github.com/) に公開リポジトリを作成します（例: `machino-mado`）。ZIPを解凍したフォルダー内の**隠しフォルダー `.github` も含むすべてのファイルとフォルダー**を、リポジトリのルート（`main`）へコミットします。APIキーは同梱していません。
2. リポジトリの `Settings` → `Secrets and variables` → `Actions` → `New repository secret` に移動。Nameを **`YOUTUBE_API_KEY`**、ValueにGoogle CloudのYouTube Data APIキーを入力して保存します。**Issue・README・CSV・Gitコミットにはキーを貼らないでください。**
3. `Settings` → `Pages` → `Build and deployment` → `Source` を **GitHub Actions** に設定します。`Deploy from a branch` ではなく `GitHub Actions` を選択してください。
4. `Actions` タブ → **Daily live camera update and deploy** → `Run workflow` で動作確認します。成功すると Pages サイトが公開されます。
5. 以降は毎日 **日本時間10:17ごろ** に検索・拡張・状態更新・Web生成・公開が自動実行されます（GitHubの都合で遅延・不実行になる場合もあります）。

公開先は通常 `https://ユーザー名.github.io/リポジトリ名/` になります。

**既に収集を続けている場合:** 最初のGitHubアップロード前に、あなたのPCの最新版 `livecam.sqlite` をこのセット内の `日本ライブカメラ収集DB/livecam.sqlite` に差し替えてください。両方のプロセスが止まっている状態でコピーすること（SQLiteのWAL動作中に単体ファイルだけをコピーしない）。最新DBがある場合はそれを最優先します。サイト表示の元データはDBで、サイト公開用CSV・HTMLは毎回DBから再生成されます。

**GitHubに上げるもの:** 動画タイトル等の公開元情報、SQLiteの取得履歴・検索計画、生成HTML。**APIキーはGitHub Secretsにのみ設定**します。公開リポジトリのSQLite/CSVは第三者にも閲覧可能です。

**GitHubでの自動公開は2段階とも1つのワークフローに入れています。** `GITHUB_TOKEN`によるコミットでは別のpushワークフローは通常起動しないため、同じワークフローでPagesアーティファクトを作成し`deploy-pages`を実行しています。

### B. Windows タスクスケジューラ（PCで毎日収集）

こちらは、**Windowsにログインしている間**に毎日実行する設定です。PCの電源が切れているときは動作しません。収集とローカルサイト生成は自動で行われます。

VS Codeのターミナル（PowerShell）でサイトフォルダーに移動してから：

```powershell
# 画面に表示せずAPIキーをWindowsユーザー環境変数に登録（初回だけ）
powershell -ExecutionPolicy Bypass -File .\set_api_key_windows.ps1

# この操作後にVS Codeのターミナルを開き直す
py -3 auto_update.py --dry-run
py -3 auto_update.py

# 毎日10:17に実行するタスクを登録
powershell -ExecutionPolicy Bypass -File .\install_windows_task.ps1
```

`logs/daily.log` に実行ログが残ります。時刻を変更したいときは `-At '21:30'` を付けます。

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows_task.ps1 -At '21:30'
```

タスクを解除するには：

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_windows_task.ps1
```

Windows用タスクは `run_daily.cmd` で `py -3 auto_update.py --publish` を呼びます。**Gitを導入してGitHubリポジトリの `origin` を設定し、pushできる認証が完了している場合のみサイトをネット公開**します。Git未設定のままでもローカル生成は完了します。ネット公開までPC側で自動化したいときは下の「Windowsから公開」を参照してください。

キーをWindowsのユーザー環境変数に保存する方法は、**同じWindowsユーザーで読み取り可能な保存方式であり、暗号化された秘密保管庫ではありません**。共有PCではGitHub Actions方式の利用を推奨します。

### WindowsからGitHubへ自動公開する場合

事前に[Git for Windows](https://git-scm.com/download/win)を導入し、GitHubにログインできる状態にします。初回だけリポジトリを用意して `origin` を設定します（GitHub上の既存リポジトリを `git clone` して、そこにこのセットのファイルを配置する方法がおすすめ）。

```powershell
# git管理されたサイトのフォルダーで確認
 git remote -v
 git push -u origin main

# 一度手動で「収集 → サイト生成 → GitHub push」を試す
py -3 auto_update.py --publish
```

**GitHub Actions と Windows の両方から同時にpushしないでください。** PCでのpush後、GitHub Pagesの更新は公開設定に従います。Windows運用ではGitHub Pagesの公開元を `Deploy from a branch → main / (root)` にするか、独立したデプロイ用ワークフローを準備してください。**ただし本セットにはGitHub Actions側で毎日更新して直接デプロイする方式Aを推奨しています。**

## API上限と現在の初期設定

| 操作 | API | 初期設定 | 概要 |
|---|---|---:|---|
| 新規検索 | `search.list` | **25回/日** | 標準1日100回枠の一部を使う |
| 既知チャンネルの拡張 | `channels.list` / `playlistItems.list` / `videos.list` | **最大180回/日** | 通常読み取りの標準1日10,000ユニットの一部を使う |
| 動画状態再確認 | `videos.list` | **最大30回/日** | 1回に最大50動画をまとめて確認 |
| CSV生成/サイト更新 | ローカル処理 | API消費なし | HTML単体で表示可能 |

検索100回/日とその他の通常読み取り10,000ユニット/日の**別枠**（2026年10月公式記載）。上限とコストは変更される可能性があります。[公式割り当て計算](https://developers.google.com/youtube/v3/determine_quota_cost)。同じGoogle Cloudプロジェクトを別プログラムでも使っている場合、**本ツールのSQLiteに記録されていない外部消費までは自動検知できません**。Google Cloud ConsoleのAPI割り当ても確認してください。

`config.json` を編集すると、回数や再確認頻度を変更できます。設定を100回いっぱいにしないのは、手動検証と再試行用の余裕を残すためです。

初期収集データで既に上限到達している場合、次の実行の検索処理はGoogle側から制限される可能性があります。通常読み取りAPIが残っていれば拡張・refreshは継続可能です。

**見つかった動画はすべて「日本のライブカメラ」と確定したものではありません。** 過去のLIVE判定が残る場合や、リアルタイムの表示とずれる場合があります。視聴時の実際の再生状態はYouTubeで確認してください。

## よく使うコマンド

```powershell
# 動作と割り当て（API消費なし）
py -3 auto_update.py --dry-run

# 一度だけ収集してサイト更新（APIを消費）
py -3 auto_update.py

# APIを使わず、既存DBからサイトだけ作り直す
py -3 auto_update.py --site-only

# 検索枠を使い切った日（検索せず通常APIで更新）
py -3 auto_update.py --skip-search

# API未設定の場合にも、サイト生成だけ可能
py -3 auto_update.py --site-only
```

途中で止めるにはターミナルで `Ctrl+C`。完了済みの動画・チャンネル情報はSQLiteに保存されます。中断直後はCSV/HTMLが以前のままのことがあるので、`
py -3 auto_update.py --site-only` で再生成してください。処理が異常終了して `.automation.lock` が残った場合、**プロセスが停止したことを確認してから**そのファイルを削除します。

## `data` フォルダーについて

`data/全動画候補.csv` と `data/全チャンネル候補.csv` は**サイト生成用の出力コピー**です。これらを手動で編集しても、次の自動収集時にSQLiteの内容で上書きされます。継続運用での正本は `日本ライブカメラ収集DB/livecam.sqlite` です。サイトの分類を人手で確定・訂正する専用UIはまだ付いていません。

データ元CSVを手動指定して一回限りのHTMLを作る場合：

```powershell
py -3 update_site.py --videos "C:\収集フォルダー\全動画候補.csv" --channels "C:\収集フォルダー\全チャンネル候補.csv"
```

## 内容物

```
index.html                           完成版サイト（このファイルだけでも表示できる）
template.html / app.js / style.css   HTMLサイトの編集用ソース
assets/                              装飾用SVG
catalog.json                         サイト検索用の生成データ
data/                                サイトに読み込ませる候補CSV
日本ライブカメラ収集DB/livecam.sqlite    継続収集の正本（1,093動画で開始）
日本ライブカメラ収集DB/*.csv             DBから書き出した確認用CSV
collect_livecams.py                 YouTube Data APIの収集・重複排除プログラム
update_site.py                      CSV -> サイト生成
auto_update.py                       収集 -> CSV -> サイト -> 任意push の統合実行
config.json                          API回数・調査条件
.github/workflows/daily.yml         GitHub上で毎日自動実行・公開
run_daily.cmd                        Windowsタスク用エントリーポイント
set_api_key_windows.ps1             APIキーをWindowsユーザー環境変数に設定
install_windows_task.ps1            Windowsタスクを登録
uninstall_windows_task.ps1          Windowsタスクを解除
seeds/                               元の候補CSV（調査の再構築時の参考）
.gitignore                           キー・ローカルログ等のGit除外設定
README.md                            この説明書
```

## 停止/不具合の調べ方

- GitHub Actionsが失敗: GitHubの `Actions → Daily live camera update and deploy → 該当実行` でログを確認。Secretsの設定、PagesのSource、Workflow permissions、API quotaを確認。
- `quotaExceeded` / `rateLimitExceeded`: Google Cloudの残り枠を確認。APIの太平洋時間の午前0時をまたいで再試行。必要なら `--skip-search`。
- サイトは古いまま: `index.html` 更新日時 / Actionsでdeploy成功を確認。GitHub Pagesは反映まで時間がかかる場合があります。
- APIキーのエラー: YouTube Data API v3の有効化とAPIキーのAPI制限を確認。
- 動画再生できない: YouTube側の削除、公開範囲や埋め込み禁止が原因のことがあります。
- データが減った: 最新DBを入れずに初期DBから更新した可能性があります。以前の `livecam.sqlite` をバックアップから戻してやり直してください。
- 同時実行は避けること。同一SQLiteへのアクセスと日次枠を競合させます。

## 外部仕様・注意

- [YouTube Data API の割り当て](https://developers.google.com/youtube/v3/determine_quota_cost)
- [YouTube検索API](https://developers.google.com/youtube/v3/docs/search/list)
- [GitHub Actions schedule](https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule)
- [GitHub Pagesのカスタムワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

公開リポジトリにAPIキー・メールアドレス等の個人情報・権限のない映像素材を含めないでください。YouTube API利用規約と動画の埋め込み制限を守ってください。GitHub Actionsでのスケジュール実行は稀に遅延・スキップされるため「毎日必ず成功」とは保証できません。
