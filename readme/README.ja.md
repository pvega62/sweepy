                                  ████  █   █  ████  ████  ████  █   █
                                  █     █   █  █     █     █  █  █   █
                                  ████  █ █ █  ███   ███   ████   █ █ 
                                    █  ██ ██  █     █     █       █  
                                  ████  █   █  ████  ████  █       █  
<h1 align="center">Sweepy: 複数エンジンによる求人検索とスコアリング</h1>

<p align="center">
  <strong>より賢く、より良く、より速く、より強く検索します。</strong><br>
  主要プラットフォームを横断する並列の求人スクレイピング、履歴書の自動スコアリング、ランキング付きのレポート。
</p>

<p align="center">
  <a href="https://github.com/pvega62/sweepy/actions"><img src="https://github.com/pvega62/sweepy/actions/workflows/ci.yml/badge.svg" alt="CI（継続的インテグレーション）"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10 以降"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT ライセンス"></a>
  <a href="https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme"><img src="https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271" alt="M8ven スコア"></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>クイックスタート</strong></a> ·
  <a href="#features">機能</a> ·
  <a href="#job-engines">求人エンジン</a> ·
  <a href="#portfolio-support">ポートフォリオ対応</a> ·
  <a href="#documentation">ドキュメント</a> ·
  <a href="https://github.com/pvega62/sweepy/issues/new">問題を報告する</a>
</p>

<p align="center">
  <a href="../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.hi.md">हिन्दी</a> · <strong>日本語</strong> · <a href="README.ar.md">العربية</a> · <a href="README.zh.md">简体中文</a>
</p>

---

Sweepy は無料のツールで、求人ボードを検索し、各求人をあなたの履歴書と照合してスコアを付けます。企業の採用サイトと求人ボードを読み取り、重複した求人と期限切れの求人を除外してから、ランキング付きのレポートを書き出します。プロファイルを変更せずに、1 回のスイープだけで重複チェックをオフにできます。セットアップウィザードは、検索、プロファイル設定、検索の調整、エンジンやアグリゲーターの管理といった Sweepy のツールボックスのタスクのためのランチパッドを開きます。

> 現在のバージョンとリリース履歴は **[CHANGELOG.md](../CHANGELOG.md)** を参照してください。

## <a name="features"></a>機能

- **多くの場所を一度に検索します。** Greenhouse、Ashby、Lever、Workable、Built In NYC、LinkedIn、Indeed、Glassdoor、ZipRecruiter から求人を収集します。これらのソースはすべて API キーなしで動作します。
- **すべてのエンジンを並列で実行します。** 有効なエンジンは同時に起動します。そのため、スイープにかかる時間は各エンジンの合計ではなく、最も遅いエンジンとほぼ同じになります。
- **ボードが失敗しても処理を続けます。** 各エンジンにはタイムアウトとサーキットブレーカーがあります。1 つのエンドポイントが失敗しても、実行が止まったり、同じリクエストが 5 回繰り返されたりすることはありません。
- **必要に応じてエンジンを追加します。** ターミナルを離れずに、ウィザードから HireHunt、openroles、jobdrop、Apify をインストールできます。
- **各求人を履歴書と照合してスコアを付けます。** PDF または Word の履歴書のテキストを読み取り、求人とどれだけ一致するかを測定します。
- **期限切れのリンクを除外します。** 各 URL を確認し、存在しなくなった求人を削除します。
- **ボード間の重複求人をチェックします。** ボードごとに URL が異なっても、正規化した職種名、企業名、勤務地で照合します。1 回の実行で各ボードの掲載をすべて残すには、`--no-dedupe` を渡します。
- **すでに見た求人をスキップします。** 毎日のスイープでは、昨日のリストではなく新しい求人を報告します。Sweepy は報告済みの求人を 4 日間の範囲で抑止します。1 回の実行でそれらを再び表示するには、`--include-seen` を渡します。
- **適切な履歴書に振り分けます。** 各求人を、その職種向けに作成した履歴書トラックに送り、カードに色付きバッジでラベルを付けます。
- **ポートフォリオをすべての判断に組み込みます。** Sweepy にオンラインのポートフォリオ、またはローカルの PDF、Word、Markdown、テキスト、HTML ファイルを指定します。各カードにはそのポートフォリオの作品が表示されます。複数の種類の職種に応募する場合は、履歴書トラックごとに 1 つのポートフォリオを用意してください。
- **そのまま使えるレポートを作成します。** クリック可能なリンク付きの 1 ページ 1 カードの PDF に加えて、自分の管理用の CSV と JSON ファイルを出力します。
- **CSV を応募トラッカーに変えます。** CSV の末尾には `date_applied`、`status`、`interview_stage`、`offer_amount`、`offer_date`、`follow_up_date`、`contact`、`notes` が並びます。Excel、Google Sheets、Notion でこれらを入力します。Sweepy は同じプロファイルの以降のスイープにあなたの入力を引き継ぎます。PDF は各カードに応募リンクを持つ 1 つのランキング付きリストになります。スプレッドシートは PDF のカード上限を超える職種を保持し、それぞれに何をしたかを記録します。列をオフにするには `export.tracking: false` を使います。

## <a name="quick-start"></a>クイックスタート

**Python 3.10 以降**が必要です。Python 3.13 では一部のパッケージがソースからビルドされます。先に Microsoft C++ Build Tools が必要になる場合があります。詳しくは [Sweepy のインストール](https://pvega62.github.io/software/docs/sweepy/installation) を参照してください。

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` はコアの依存関係をすべてインストールし、Python の Scripts フォルダーに `sweepy` コマンドを登録します。シェルが PATH からそのフォルダーを読み込むように、ターミナルを一度開き直します。ウィザードを開始するには `sweepy` を実行するか、`sweepy --run` のようなコマンドオプションを追加します。`python swee.py` でスクリプトを直接実行することもできます。

この 1 つのコマンドで、2 つの組み込みエンジンが使えます。ウィザードは必要に応じて 4 つのオプションエンジンを提示するので、別の requirements ファイルを手動でインストールする必要はありません。

代わりに互換性のあるすべてのエンジンを最初から取得するには、同じコマンドにフラグを 1 つ追加します。

```bash
pip install -e ".[all-engines]"
```

これにより、HireHunt、openroles、Apify が 1 回の解決で追加されます。`jobdrop` は JobSpy と共存できないメタデータを持つため除外されます。33 のボードが必要な場合は、`sweepy --install-engines jobdrop --allow-engine-conflicts` でインストールします。[求人エンジン](#job-engines) のセクションで両方の方法を説明します。

`sweepy` を実行すると、ウィザードのタイル形式のランチパッドが開きます。矢印キーで **スイープ開始**、**プロファイル作成**、**プロファイル読み込み**、**スイープ設定**、**Sweepy のツールボックス**、**Sweepy を終了** の間を移動し、Enter を押します。タイルのサブタイトルは **今すぐ求人検索を実行** や **保存した検索を開く** のように、動作を平易な言葉で示します。**プロファイル読み込み** では、次のスイープで使う保存済みプロファイルを選択できます。ツールボックスには、プロファイルの編集、エンジン管理、デバッグログ、ヘルプ、最近のログ、ドキュメント変換、更新が含まれます。**プロファイル作成** は名前、希望の職種名、勤務地、履歴書のパスを収集します。ウィザードは完了時にプロファイルを保存します。プロファイルを直接編集するには `sweepy --setup --profile profiles/your_profile.yaml` を実行します。

サブメニューは **← 戻る** で閉じると、開いた元のメニューに戻ります。Esc も同じ動作です。質問の途中では、Esc で前の回答を開き直します。サブメニュー内では、Esc で 1 つ上の階層に移動します。ランチパッドでは、Esc で終了します。Ctrl+C はどこからでも終了します。

新しいバージョンがリリースされたときに新しいコードを取得するには、次を実行します。

```bash
sweepy --update
```

Sweepy は Git のリモートを確認し、チェックアウトを fast-forward します。`requirements.txt` と、すでにインストールしたオプションエンジンを再インストールします。未コミットの変更があるチェックアウトは変更しません。何も変更せずに新しいバージョンを確認するには、`sweepy --check-update` を使います。

次に、最初のスイープを実行します。

```bash
sweepy --run
```

`--run` は最後に保存したプロファイルでスイープします。別のプロファイルを指定するには、`sweepy --profile profiles/your_profile.yaml` を使います。

プロファイルの設定を編集せずに、1 回の実行だけ重複チェックをオフにします。

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

デフォルトでは、異なるボードが同じ正規化済みの職種名、企業名、勤務地を掲載している場合に、Sweepy は 1 件の求人を残します。Model Context Protocol（MCP）の `run_sweep` ツールは、同じ 1 回限りの上書きとして `deduplicate=false` を受け付けます。

Sweepy は以前のスイープで報告した求人も非表示にします。それらを見直すか、最初からやり直します。

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

Sweepy をスクリプトから使うときに、プロンプトなしでプロファイルを作成または更新します。

```bash
sweepy --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer,UX Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,openroles \
  --openroles-companies figma,stripe,notion \
  --timeout 120 --no-cache
```

Sweepy はファイルを書き込む前に、有効なエンジンを検証します。必須フィールドが不足している場合は、その理由を示してすぐに失敗します。対話式ウィザードでは、OpenRoles の企業スラッグを空のままにするとそのエンジンをスキップします。OpenRoles は名前を指定した企業ボードのみを検索します。OpenRoles を有効にする非対話式プロファイルには、引き続き `--openroles-companies` が必要です。非対話式のフラグは `--sources`、`--jobspy-sites`、`--hirehunt-sources`、`--jobdrop-sites`、`--openroles-companies`、`--apify-actor`、`--timeout`、`--cache-ttl`、`--no-cache`、`--history-days`、`--no-history`、`--job-tracking` / `--no-job-tracking` をカバーします。

プロンプトやツール呼び出しよりエディターを使いたい場合は、プロファイルファイルに記入します。

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

テンプレートはすべての設定をデフォルト値とともに説明しています。Sweepy は検出を開始する前に、名前、職種名、勤務地を出力します。入力ミスは最初の出力行に表示されます。

ウィザードを開かずに、履歴書またはメモのファイルを PDF に変換します。

```bash
sweepy --convert path/to/resume.docx
```

`--convert` は `.docx`、`.doc`、`.txt`、`.md`、`.pdf` の各ファイルを受け付けます。元のファイルの隣に PDF を書き出し、最終的なパスを出力します。

スイープには 30 秒から 90 秒かかります。Sweepy は処理の進行状況を出力します。

1. **プロファイルを読み込みます。**
2. **有効にしたプラットフォーム全体で求人を検出します。**
3. **リンクを検証**して期限切れのものを削除します。
4. **各職種を履歴書と照合してスコアを付けます。**
5. **レポートを書き出します。**

## <a name="what-you-get"></a>得られる結果

各実行は日付入りのファイルを `results/` フォルダーに書き出します。以前のレポートはそのまま残ります。MCP 経由で実行されるスイープは、ファイル名に `mcp` を追加します（例: `paralegal_nyc_mcp_2026-10-27-223115.pdf`）。日時はお使いのマシンの時計に従います。別のタイムゾーンでファイル名を付けるには、`export.timezone` を設定します。

- **PDF レポート。** 1 職種につき 1 枚のカードで、マッチスコア順に並び、給与、福利厚生、応募へのリンクが付きます。
- **CSV ファイル。** すべてのカードフィールド、求人本文の全体、Sweepy が以降のスイープに引き継ぐ 8 つの応募トラッキング列を含みます。Excel、Google Sheets、Notion で開けます。ファイルを小さくしたい場合は、`export.description_chars` に正の数を設定します。切り詰めた本文は、省略した文字数を示す注記で終わります。
- **JSON ファイル。** 他のツールが読める形式の同じデータです。

[サンプル PDF](../docs/sample_report.pdf) を開くか、[1 ページ目の画像](../docs/sample_report.png) を表示してください。

## <a name="job-engines"></a>求人エンジン

Sweepy には 2 つのエンジンが含まれ、さらに 4 つをダウンロードできます。`ats` エンジンは応募者追跡システム（ATS）を直接読み取ります。すべてのエンジンは同じアダプターの背後で動作します。どのエンジンが求人を見つけたかに関係なく、プロファイルは同じように扱えます。

| エンジン | 利用方法 | 取得する内容 | プロキシ | User-Agent | 説明文 |
|---|---|---|---|---|---|
| `jobspy` | 組み込み | LinkedIn、Indeed、Glassdoor、ZipRecruiter、Google Jobs、Bayt、Naukri、BDJobs | あり | あり | 切り替え |
| `ats` | 組み込み | Greenhouse、Ashby、Lever、Workable、BuiltinNYC | なし | なし | 常に |
| `hirehunt` | ダウンロード | LinkedIn、Indeed、Naukri、Shine、Internshala、Unstop、および 6 つの企業ボード（Google Careers、Amazon、Meta、Apple、Netflix、Microsoft） | なし | なし | 常に |
| `openroles` | ダウンロード | 名前を指定した Greenhouse、Lever、Ashby、Workday のボード | なし | なし | 常に |
| `jobdrop` | ダウンロード | Google、Wellfound、Workday、iCIMS、Dice、USAJobs を含む 33 のボード | あり | あり | 切り替え |
| `apify` | ダウンロード | マネージドアクター、デフォルトでは LinkedIn | アクターが処理 | アクターが処理 | アクターによる |

`jobdrop` は JobSpy とのメタデータの競合を報告します。`curl-cffi<0.8` を固定していますが、JobSpy は `curl_cffi>=0.16.2` を要求します。この固定は古くなっています。`jobdrop` は新しいライブラリでも問題なく動作し、そのライブラリには使用するすべての偽装プロファイル（`safari17_2_ios`、`chrome120`、`chrome124`）が含まれています。

両方を通常の `pip install` でインストールしても、やはり失敗します。`--install-engines all` では `jobdrop` が除外されます。サポートされている方法でインストールするには `--allow-engine-conflicts` を追加します。Sweepy は `jobdrop` を `--no-deps` でインストールしてから、その他の要件を解決するため、`curl_cffi` は JobSpy のバージョンのまま、両方のエンジンが動作します。

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

そのインストール後も、`pip check` は `jobdrop` の古い上限を報告します。この警告は実行中のコードではなく、メタデータを説明しています。

または、ウィザードを開き、**Sweepy のツールボックス** を選んでから **求人エンジンをダウンロード** を選びます。この画面には各エンジンのボードとインストール状態が表示されます。`pip` を実行する前に確認を求めます。プロファイルの作成中に未インストールのエンジンを選ぶと、ウィザードが同じダウンロードを提示します。Sweepy はあなたの確認なしにインストールを実行しません。

### <a name="disk-footprint"></a>ディスク使用量

Windows の Python 3.13 で計測した値は次のとおりです。

| インストール | ディスク上のパッケージ | 備考 |
|---|---|---|
| コア（`requirements.txt`） | 283 MB | pandas、pymupdf、MCP SDK を含む 53 パッケージ |
| `hirehunt` | +13 MB | rich と markdown-it-py を追加 |
| `openroles` | +0.3 MB | Python 標準ライブラリのみ |
| `apify-client` | +14 MB | impit と more-itertools を追加 |
| `jobdrop` | +406 MB | scipy（134 MB）、playwright（113 MB）、tls-client（93 MB）、selenium（34 MB）が中心 |

互換エンジンをすべてインストールすると約 **310 MB** になります。`jobdrop` を追加すると、ブラウザーをダウンロードする前の時点で合計約 **716 MB** になります。

ブラウザーのバイナリは Python 環境の外に置かれ、初回使用時に取得されます。

- Playwright の Chromium ビルドは約 **710 MB** です（Chromium とそのヘッドレスシェル）。
- Firefox と WebKit を含む完全な Playwright セットは約 **1.2 GB** です。
- `jobdrop` がステルス経路で使用する Camoufox は、初回起動時にパッチ済みの Firefox をダウンロードします。

Sweepy はすべての組み込みエンジンをブラウザーなしで実行します。コアのインストールではその容量は不要です。

エンジンとそのインストール状態はいつでも一覧表示できます。

```bash
sweepy --list-engines
```

`openroles` は指定したボードを読み取り、企業スラッグが必要です。`apify` は `APIFY_TOKEN` 環境変数を読み取り、Apify アカウントに課金されます。

エンジンをインストールしても有効にはなりません。次の 3 つのいずれかの方法でプロファイルに追加します。

1. **ウィザード。** `sweepy` を実行し、**Sweepy のツールボックス**、**求人エンジンの管理**、**エンジンと設定を選択** の順に選びます。インストール済みのエンジンには `[installed]` タグが表示されます。1 つにチェックを入れると、ウィザードがその設定を求めます。
2. **プロファイル編集。** プロファイルを読み込み、確認画面で **求人エンジンの管理** を選びます。
3. **コマンドライン。** `--sources` にエンジンを指定し、その設定を渡します。

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

どの方法でも、ファイルを書き込む前にエンジンの設定を検証します。`openroles` の企業スラッグなど値が不足している場合は、壊れたプロファイルを保存せずに理由を示して失敗します。

### <a name="choosing-boards"></a>ボードの選択

プロファイルウィザードのプラットフォーム手順には、Sweepy が検索できるすべてのボードが、それを読み取るエンジンごとにまとめて表示されます。63 のボードがすべて 1 か所に表示され、組み込みの 13 ボードだけではありません。

| グループ | ボード | タグ |
|---|---|---|
| `jobspy`（8） | LinkedIn、Indeed、Glassdoor、ZipRecruiter、Google Jobs、Bayt、Naukri、BDJobs | `built in` |
| `ats`（5） | Greenhouse、Ashby、Lever、Workable、BuiltinNYC | `built in` |
| `hirehunt`（12） | LinkedIn、Indeed、Naukri、Shine、Internshala、Unstop、Google Careers、Amazon、Meta、Apple、Netflix、Microsoft | インストールまで `needs download` |
| `openroles`（4） | Greenhouse、Lever、Ashby、Workday | `needs download`、および企業スラッグが必要 |
| `jobdrop`（33） | Google、Wellfound、Workday、iCIMS、Dice、USAJobs、Handshake など | `needs download`、および JobSpy と競合 |
| `apify`（1） | Apify アクター経由の LinkedIn | `needs download`、および `APIFY_TOKEN` が必要 |

各行にはエンジンとインストール状態が表示されます（例: `Indeed  [jobspy · built in]` や `Wellfound  [jobdrop · needs download]`）。選択を確定する前にタグを確認できます。ローカルにインストールされていないエンジンのボードにチェックを入れると、ウィザードがそれをインストールするコマンドを出力します。インストール済みのエンジンでは代わりに `installed` と表示されます。保存したプロファイルを開き直すと、現在のボードがすでにチェックされた状態で表示されます。Sweepy は未インストールのエンジンのボードをプロファイルに残し、インストールが完了するまでスイープは警告を出してそのエンジンをスキップします。

### <a name="engine-settings"></a>エンジン設定

```yaml
sources:
  enabled: [jobspy, ats, openroles]
  greenhouse:
    discovery: broad
    concurrency: 20
  openroles:
    ats: [greenhouse, lever, ashby, workday]
    companies: [figma, stripe, notion]
  jobdrop:
    sites: [linkedin, indeed, google, glassdoor]
    headless: true
    fetch_descriptions: true
    proxies: ["user:pass@host:port"]
cache:
  enabled: true
  ttl_seconds: 3600
history:
  enabled: true
  retention_days: 4
  match: url+role
  path: null
orchestrator:
  timeout_per_source_seconds: 180
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

古いプロファイルも引き続き動作します。`sources.jobspy` の下のボードのブール値は、個々の JobSpy ボードのオンとオフを切り替えます。`sources.enabled` リストがないプロファイルは、JobSpy と組み込みの ATS リーダーがデフォルトになります。

- **説明文はデフォルトで有効です。** スコアリングは求人のテキストを履歴書と照合します。より速いスイープと引き換えに弱いマッチを許容する場合にのみ、`fetch_descriptions` をオフにします。
- **Greenhouse は要求に応じてより広いボードリストを読み取ります。** `sources.greenhouse.boards` に希望するボードを指定します。`sources.greenhouse.discovery: broad` を設定すると、`data/sources/greenhouse_slugs_broad.txt` にある同梱の 619 スラッグのリストもスイープし、プロファイルですでに指定したボードは Sweepy が追加します。`sources.greenhouse.concurrency` は Sweepy が同時に読み取るボードの数を設定します。broad モードでは 20、それ以外では 1 です。broad プローブは設計上、多数の HTTP 404 応答を返します。Sweepy は失敗数と最初の 10 個のスラッグを、ボードごとに 1 行ではなく 1 つの警告で報告します。
- **プロキシはエンジンごとにオプトインです。** ウィザードはファイルから読み取るか、1 つをインラインで受け付け、入力中はパスワードを隠し、内容を出力しません。`hirehunt` はプロキシのオプションを提供しないため、プロファイルで設定すると Sweepy は警告をログに記録します。
- **キャッシュは最初から有効です。** 同じエンジンと設定での繰り返しのクエリは、1 時間の間は前回の結果を返します。`cache.enabled: false` でクリアするか、`ttl_seconds` を短くします。
- **タイムアウトは境界で止まります。** Python はライブラリ呼び出しの内部ですでにブロックしているスレッドを停止できません。Sweepy は待機をやめて先に進み、各ライブラリが内部で独自の HTTP タイムアウトを適用します。
- **サーキットブレーカーは失敗するエンジンをスキップします。** 5 回連続で失敗すると、Sweepy はそのエンジンの呼び出しを 30 秒間停止し、`skipped_sources` で報告します。

### <a name="reported-postings"></a>報告済みの求人

Sweepy は報告したすべての求人を記録し、次のスイープで同じ求人をスキップします。Sweepy は記録を `~/.sweepy/history.db` にプロファイルごとに分けて保存します。別の場所に保存するには `SWEEPY_HISTORY_PATH` を設定します。ウィザードの **スイープ設定** 画面にオン/オフの切り替えと保持期間が表示されます。

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **保持期間は再報告の間隔です。** Sweepy は `retention_days` が経過するまで求人を抑止し、その後で再び報告します。継続的に掲載されている求人は、最大で 4 日ごとに戻ってきます。
- **照合はデフォルトで寛容です。** Sweepy はトラッキングパラメーターとフラグメントを削除した後に正規 URL を比較します。その後、正規化した職種名、企業名、勤務地にフォールバックするため、別のボードでの再掲載は同じ職種として扱われます。正規 URL の一致を必須にするには `match: url` を設定します。
- **有効な求人だけを数えます。** 求人は URL の検証に合格した後に履歴に入ります。期限切れのリンクが非表示になることはありません。
- **MCP の呼び出し元も同じデフォルトを使えます。** `run_sweep` は `previously_seen_count` と `new_count` を報告します。以前の求人を見直すには `include_seen=true` を渡すか、`clear_history` を呼び出して忘れさせます。`create_profile` は `history_config` を受け付けます。

### <a name="adding-another-engine"></a>別のエンジンの追加

1. `engine/adapters/<name>_adapter.py` を作成し、`ScraperAdapter` をサブクラス化します。
2. `name`、3 つの `supports_*` フラグ、`default_concurrency`、`library` を設定します。
3. 設定を確認する `preflight()` と、DataFrame を返す `scrape()` を書きます。
4. `engine/adapters/__init__.py` に登録します。
5. ウィザードが表示とインストールを行えるように、`engine/engines.py` で説明します。
6. `engine/sweep_config.py` に設定ブロックを、`_ENGINE_PROMPTS` にプロンプトを追加します（`engine/config.py` 内）。
7. `requirements-engines.txt` と pyproject の extras にパッケージを追加します。
8. アダプターを単独でテストしてから、スイープ中にそれだけを有効にします。

残りはオーケストレーターが処理します。名前でディスパッチし、タイムアウトを適用します。返ってきたフレームは正規化されます。

## <a name="agent-judgment"></a>エージェントの判断

Sweepy は共通の語彙で求人をスコアリングし、そのスコアリングはモデルを呼び出さず、ネットワークも使いません。同じ入力からは同じスコアが出て、そのスコアは適性ではなく言葉遣いを測ります。MCP サーバーは、エージェントによる評価を想定された経路として扱います。

`run_sweep` はモデルを呼び出しません。`assessment_mode: "agent"`、`assessment_required: true`、`assessed_count: 0` を返します。ワークフローは `get_jobs`、各職種を履歴書と照合する独立した評価、`submit_judgments`、`render_report` と続きます。24 職種の評価を 1 回の呼び出しに収めるには、すべての判断を 1 つの `judgments` リストで渡します。評価済みのカードは `NN% MATCH` と表示されます。未評価のカードは `NN% KEYWORD OVERLAP` のままです。

`get_jobs` は `resume_documents` を返し、そこには各履歴書トラックの解析済みテキストが含まれます。判断するのはそのテキストであり、プロファイルの `must_have_skills` や `synonyms` ではありません。これらは決定論的なキーワード照合にのみ使われます。採用担当者と同じ観点でドキュメントを読みます。移転可能なスキル、各箇条書きの背景にある範囲とシニアリティ、ドメイン、ツール、そしてそれが実証する成果です。次に、求人の応募者追跡システムが解析する方法でスコアを付けます。パーサーが標準の Experience セクションまたは Skills セクションで見つけた用語は、証拠として数えます。同じ用語が表、ヘッダー、フッター、画像、2 列のサイドバーの中にあると、人には届かない可能性があるため、重みを下げます。Sweepy は応募 URL から ATS の系列がわかる場合にその名前を示し、判断はパーサーが失う内容を記録します。

`match_pct` は資質を測るため、雇用条件は含まれません。パートタイムの勤務時間、契約形態、勤務地は `concerns` に入れます。応募者が実行できる職種は、スキルや経験が求人の明示された要件と一致しない場合にのみ減点されます。これにより、ランキングは可用性ではなく適性を測ります。

ケースの両面を評価します。`alignment` はハイライト、つまり応募者が適合する最も強い証拠を示します。`concerns` は応募者にとって不利に働く点を示します。たとえば、不足する資質、在職期間の空白、パートタイムの勤務時間、契約期間、引っ越しが必要な勤務地、下限を下回る給与などです。レポートは要件の行の下にこの 2 つを 1 行で出力し、CSV には `concerns` 列が追加されます。キーワードのみの実行では、履歴書に欠けている求人キーワードから `concerns` を埋めます。

`submit_judgments` は `portfolio_highlight` も受け付けます。その求人に対するポートフォリオの作品を渡すと、カードに **ハイライト** として表示されます。ハイライトが送信されていないカードは、Sweepy が見つけた作品を一覧表示します。

## <a name="portfolio-support"></a>ポートフォリオ対応

Sweepy はスイープごとに 1 回ポートフォリオを読み取り、その作品をすべてのカードに一覧表示します。プロファイルを作成する前にポートフォリオを収集します。オンライン URL、またはローカルの `.pdf`、`.docx`、`.md`、`.txt`、`.html` ファイルを指定します。複数の職種ファミリーを対象とする場合は、履歴書トラックごとに 1 つのエントリを渡します。

```yaml
portfolio:
  # One entry per resume track. An entry without `track` serves every track.
  sources:
    - track: "UX Writer Resume"
      url: "https://example.com/work"
    - track: "Technical Writer Resume"
      path: "C:/portfolios/technical-writing.pdf"
  pieces_per_card: 3
```

Sweepy は見出しとリンクを読むためにオンラインのポートフォリオを取得します。ページがリクエストをブロックした場合、カードはリンクを保持し、作品リストをスキップします。PDF のカードにはポートフォリオとその作品が表示されます。CSV と JSON のエクスポートには `portfolio_url`、`portfolio_pieces`、`portfolio_highlight` が追加されます。

保存したプロファイルにポートフォリオを添付するには、MCP から `set_portfolio` を呼び出すか、ウィザードのポートフォリオ手順に答えます。ヘッドレスセットアップでは `--portfolio` と `--portfolio-track` を受け付けます。

`render_report` は最後の戦略ボックス用に `playbook` 引数を受け取ります。平文で書きます。Sweepy はアンパサンドをエスケープし、改行を改行タグに変換します。`**bold**` は太字で表示され、山かっこはプレーンテキストになります。Sweepy はプレイブックをセッションとともに保存し、後のレンダリングでは生成されたものではなくそれを再利用します。新しいスイープを開始するとクリアされます。

`agent` モードでは、`render_report` は混在したレポートの作成を拒否します。未評価のジョブ ID を列挙したエラーを返します。アシスタントはそのリストを読み、欠けている ID の判断を送信します。キーワードのみのレポートを望むプロファイルは `report.assessment: "keyword"` を設定します。コマンドラインからの実行も、エージェントが判断を提供しないためキーワードの重複を報告します。`SWEEPY_REQUIRE_JUDGMENTS=1` は、ゲートをすべてのプロファイルと `export_report` にも適用する必要がある場合に設定します。

実際のスイープはボードを 1 分以上スクレイピングします。MCP サーバーはそれをバックグラウンドで実行します。`run_sweep` は最大 45 秒待ち、その後 `sweep_status: "running"` を `job_id` とともに返します。`get_sweep_status` を、`completed` を報告するまでポーリングします。クライアントが切断してもスイープは実行を続けます。ツールのタイムアウトが厳しいホストでは、`SWEEPY_MCP_WAIT_SECONDS` を設定して待機時間を短くします。

- MCP で作成したプロファイルは、組み込みエンジンに加えて、デフォルトの設定チェックに合格したインストール済みのオプションエンジンを使用します。
- エンジンを明示的に選ぶには `sources_config` を指定します。
- OpenRoles は企業ごとにスラッグが必要です。
- Apify は課金が発生する可能性があるため、明示的なオプトインが必要です。

アシスタントは検索ツールで結果を検証し、不足を補えます。スキップされたソースと求人を企業の採用ページと照合します。検証済みの抜けを追加し、アクセスできない掲載は未検証として示します。完全な網羅を確認できない場合は、その旨を明らかにします。

セットアップ手順は [MCP 連携](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) を参照してください。

すべての MCP ツールは、読み取り専用、破壊的、冪等、オープンワールドのヒントを公開します。互換性のあるホストは、ツールを呼び出す前にこれらのヒントを読み取ります。

## <a name="before-you-upload-your-resume"></a>履歴書をアップロードする前に

レイアウトによって、Sweepy が読み取れるテキストの量が決まります。2 列のデザイン、表、スキャンしたページは、エンジンが読み取るテキストを乱し、スコアを下げます。実際のテキストによる 1 列のきれいなレイアウトが最も確実に抽出でき、応募者追跡システムも同じように読み取ります。

最初のスイープの前に [履歴書の書式のヒント](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips) を読んでください。

## <a name="documentation"></a>ドキュメント

### <a name="getting-started"></a>はじめに

- [概要](https://pvega62.github.io/software/docs/sweepy/intro)
- [インストール](https://pvega62.github.io/software/docs/sweepy/installation)
- [設定](https://pvega62.github.io/software/docs/sweepy/setup)
- [最初のスイープの実行](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [結果の理解](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### <a name="resumes-and-match-scores"></a>履歴書とマッチスコア

- [履歴書の書式のヒント](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [スコアリングと制限](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### <a name="command-and-configuration-reference"></a>コマンドと設定のリファレンス

- [コマンドとフラグ](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [設定リファレンス](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [求人ソースとプラットフォーム](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [MCP 連携](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [MCP ツールリファレンス](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [開発者リファレンス](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## <a name="legal-and-responsible-use"></a>法的および責任ある使用

Sweepy は公開されている求人ボードと求人ボードの API をスクレイピングします。スクレイピングは一部のプラットフォームの利用規約に違反する場合があります。ツールに依存する前に、それらの規約を確認してください。

- **個人的な求職**に使用します。一括収集や再配布には使用しないでください。
- レート制限を尊重してください。Sweepy は礼儀正しい User-Agent とリクエスト間の短い遅延を送信します。`SWEEPY_SOURCE_DELAY` 環境変数で遅延を増やせます。
- Sweepy は法的助言を提供しません。

スクレイピングは [`python-jobspy`](https://github.com/Bunsly/JobSpy) を通じて実行され、インストールした場合は [`hirehunt`](https://pypi.org/project/hirehunt/)、[`openroles`](https://pypi.org/project/openroles/)、[`jobdrop`](https://pypi.org/project/jobdrop/)、[Apify](https://apify.com/) も使われます。各プロジェクトは独自の使用上の注意を公開しています。Google Jobs、LinkedIn、Indeed、Glassdoor のスクレイピングは、それらのプラットフォームの利用規約に違反する場合があります。Apify はリクエストをマネージドサービスに移します。それによって法的リスクは変わりません。

## <a name="license"></a>ライセンス

Sweepy は [MIT License](../LICENSE) の下でリリースされています。
