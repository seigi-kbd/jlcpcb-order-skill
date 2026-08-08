---
name: jlcpcb-order
description: JLCPCBへPCB/PCBA(基板＋実装)をブラウザ自動操作で入稿し、注文確定の手前まで進めるスキル。「JLCPCBで発注して」「JLCに入稿して」「ガーバーを入稿して」「PCBを発注して」「PCBA発注の続き」等で発火。CDP接続のChromeを操作し、ガーバー生成→アップロード→PCBA設定→BOM/CPL入稿→Product Description選択→Submitまでを自動化する。決済・注文確定は必ずユーザーに委ね、住所入力/支払いの手前で停止する。回路設計そのもの(KiCad配線)には使わない。
---

# jlcpcb-order

KiCad の製造ファイルを **JLCPCB** にブラウザ自動操作で入稿し、**注文確定の手前**まで進める。
実機 Chrome（住宅IP＋ログイン保持）を CDP 経由で操作する。

> ⚠️ **絶対原則**: 決済・住所入力・注文確定（"Place Order" / "Pay"）は **絶対に自動でやらない**。
> 配送先住所入力画面 or 支払い選択の **手前で必ず停止し、ユーザーに確認**する。外部にお金が動く操作のため。

## このスキルを発火するとき

- 「JLCPCBで発注」「JLCに入稿」「ガーバー入稿」「PCB/PCBAを発注」「発注の続き」
- KiCad で製造ファイルが揃い、JLC に出す段階

逆に**発火しない**: KiCad上の回路図/配線設計そのもの、ガーバー生成だけが目的のとき（それは kicad-cli を直接）。

## 高くついた教訓（最初に必ず読む）

**このスキルの本体はここ**。以下は実際に発注して詰まった箇所で、検索してもまず出てこない。
下の手順でセレクタが変わっていても、この教訓が分かっていれば対処できる。

1. **「The PCB size exceeds the maximum size Xmm for standard PCB assembly」エラーの真因＝ガーバーzipの余計なレイヤー**。
   KiCad のデフォルト出力に含まれる **Margin / Courtyard / Fab / Adhesive / User_Drawings / Comments / Eco** 等を、
   JLC のアセンブリ・サイズ判定が基板外形(Edge_Cuts)の外まで拾い、巨大寸法と誤認して弾く。
   数値が "Xmm" と**未挿入**なのが特徴（壊れた値を比較している）。
   → **対策＝標準fabレイヤーだけで再エクスポート**（下記コマンド）。
   PCB外形パーサ自体は余計なレイヤー入りでも正しい寸法を表示するので「寸法は合ってるのに弾かれる」罠になる。
2. **CDP接続は `localhost` 不可**（IPv6 `::1` で `ECONNREFUSED`）→ 必ず **`http://127.0.0.1:9222`**。
3. **element-ui / Vue の要素は JS の `.click()` ではハンドラが発火しない** → Playwright の**ネイティブclick**を使う。
   トグル / ボタン / カスケーダ全て。
4. **エラートーストは数秒で消える** → ボタン押下**直後に高頻度ポーリング**(50ms間隔)で `.el-message` を捕捉する
   （`jlc_catch_toast.py`）。捕捉に失敗すると「無反応に見えるが実は弾かれている」状態になる。
5. **Economic PCBA は片面のみ**。両面実装（部品が表裏両方）なら **Standard PCBA** が必須
   （Standard にすると "Both Sides" が選べる）。両面は追加セットアップ費あり。
6. **pre-order部品（`C9900xxxxx` 等）を含むと `systemType=smt_assistance_order` `calType=PRE_CAL` に分岐**。
   Submit 後に表示される価格は **PCB＋送料のみの仮計算**で、**PCBA組立費・部品代は含まれない**。
   **部品選定結果と最終見積は JLC から1〜2営業日後にメール**で届く（＝ブラウザ内に即時の部品割当テーブルは出ない）。
7. **Product Description は2段カスケーダ**（カテゴリ→HSコード付きの具体種別）。
   第1階層を選ぶと第2階層が右に出る。**末端（リーフ）まで選ばないと値が確定しない**。

## 前提環境

- **OS**: Windows で検証。macOS / Linux でもパスと Chrome 起動方法を読み替えれば動く見込み（未検証）
- **Python**: playwright 入りの環境。`pip install playwright && playwright install chromium`
  - Windows で日本語を扱うなら実行時に `PYTHONUTF8=1` を付ける
- **Chrome**: CDP 用に `--remote-debugging-port=9222` で起動する
- **ログイン保持プロファイル**: 任意のディレクトリを `--user-data-dir` に指定する。
  ここに JLC のログイン Cookie が残るので再ログイン不要になる（初回だけ手でログインする）
- **KiCad CLI**: `kicad-cli`（Windows 既定は `C:\Program Files\KiCad\9.0\bin\kicad-cli.exe`）
- Chrome は**最小化起動**にしておくとフォーカスを奪われない

> 以下の手順では `$PY`（python 実行ファイル）、`$PROFILE`（Chromeプロファイルのパス）、
> `$SKILL`（このスキルの scripts/ のパス）を各自の環境に読み替える。

## 手順

### 0. 製造ファイルを用意（クリーンガーバー＋BOM/CPL）

**クリーンガーバー**（教訓1。`<SRC>.kicad_pcb` から標準9レイヤー＋ドリルのみ）:

```bash
CLI="kicad-cli"                    # Windows はフルパス推奨
SRC="output/routed-v2.kicad_pcb"   # 真実源のPCB
OUT="output/gerbers-jlc"
rm -rf "$OUT"; mkdir -p "$OUT"
"$CLI" pcb export gerbers --output "$OUT/" \
  --layers "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" \
  --no-x2 --subtract-soldermask "$SRC"
"$CLI" pcb export drill --output "$OUT/" \
  --format excellon --drill-origin absolute --excellon-units mm "$SRC"
# zip化
"$PY" -c "import zipfile,glob,os; z=zipfile.ZipFile('output/gerbers-clean.zip','w',zipfile.ZIP_DEFLATED); [z.write(f,os.path.basename(f)) for f in glob.glob('$OUT/*')]; z.close()"
```

> ドリルの boolean フラグに `=false` を付けない（`--generate-map=false` 等はパースエラーで help 表示になる。
> 不要なら**フラグ自体を省く**）。

**BOM/CPL**: JLCPCB 形式。
- BOM列: `Comment,Designator,Footprint,JLCPCB Part #`（各部品に LCSC `C` 番号）
- CPL列: `Designator,Mid X,Mid Y,Layer,Rotation`（`Layer` は `Top`/`Bottom`。**両面実装はここで表裏を必ず指定**）

### 1. CDP Chrome を起動（ログイン保持プロファイル）

既に 9222 が生きてるか確認 → 死んでたら起動:
```bash
curl -s --max-time 5 http://127.0.0.1:9222/json/version   # 生きてれば JSON が返る
```

Windows（PowerShell、最小化起動）:
```powershell
$chrome="C:\Program Files\Google\Chrome\Application\chrome.exe"
$prof="<任意のプロファイル保存先>"
Start-Process -FilePath $chrome -ArgumentList @(
  "--remote-debugging-port=9222","--user-data-dir=$prof",
  "--no-first-run","--no-default-browser-check",
  "https://cart.jlcpcb.com/quote") -WindowStyle Minimized
```

macOS / Linux:
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check https://cart.jlcpcb.com/quote &
```

4〜8秒待って `curl .../json/version` が返るまで確認。タブが `cart.jlcpcb.com/quote` であることを確認。
**初回はここで手動ログインする**（以降はプロファイルに Cookie が残る）。

### 2. ガーバーをアップロード → 寸法確認

```bash
cd "$SKILL/scripts"
"$PY" jlc_act.py upload "<クリーンzipの絶対パス>"
"$PY" jlc_act.py eval "(()=>(document.body.innerText.match(/Detected[^\n]{0,70}/)||['(none)'])[0])()"
```
`Detected N layer board of WxHmm` が想定寸法か確認。

### 3. PCB Assembly(PCBA) を有効化＋設定

```bash
"$PY" jlc_act.py pwclick ".switch-box" 0        # PCB Assemblyトグル
"$PY" jlc_act.py txtclick "Standard" 0
"$PY" jlc_act.py txtclick "Both Sides" 0        # 片面なら "Top Side"/"Bottom Side"
"$PY" jlc_act.py txtclick "By JLCPCB" 0         # 部品持込なら "By Customer"
```
- **Economic では "Both Sides" は無効**。必ず先に Standard（教訓5）
- 状態確認は `jlc_act.py eval` で各ボタンの `className` に `cur`(active) が付くか見る

### 4. NEXT → エラートーストを必ず捕捉

```bash
"$PY" jlc_catch_toast.py
```
- トーストが**0件**＝成功。出たら内容に従う
  （例：サイズ超過＝教訓1のクリーンガーバーで上げ直し → **リロードすると PCBA 設定がリセットされる**ので手順3から再設定）
- 成功すると "Upload BOM & CPL files" モーダルが開く（部品を JLC 調達の場合）

### 5. BOM/CPL モーダル入稿

```bash
"$PY" jlc_upload_bomcpl.py "<bom.csvの絶対パス>" "<cpl.csvの絶対パス>"
"$PY" jlc_pick_desc.py    # Product Description（2段カスケーダ・必須）
```
- `jlc_pick_desc.py` は第1階層を開いて選ぶ→第2階層リーフを `get_by_text(..., exact)` で選ぶ実装。
  **製品が違うときは中の `OPTION` 文字列と第2階層リーフ名を編集する**
- 同意チェックボックスは既定でON。`bom.csv`/`cpl.csv` がモーダルに表示されているか・
  Product Description に値が入ったかを `jlc_act.py eval` で確認してから Submit

### 6. 停止して報告（ここで終わり）

Submit 成功でモーダルが閉じ、**チェックアウト（配送先住所入力）画面**に進む。

- **ここで完全停止**。住所入力・配送/支払い選択・注文確定は**やらない**
- ユーザーに報告する内容:
  - 今の到達点（住所入力画面／注文確定の手前）
  - 設定内容（層数・寸法・PCBA Type・Assembly Side・Parts Selection・Product Description）
  - 価格が仮計算で、最終見積はメール後日である旨（pre-order部品を含む場合。教訓6）
  - 残操作（住所→配送/支払→確定）はユーザー判断

## scripts/ の中身

いずれも CDP 先頭で `http://127.0.0.1:9222` に接続し、`jlcpcb` を含むタブを操作する。

| スクリプト | 役割 |
|---|---|
| `jlc_connect.py` | CDP接続して現ページのURL/タイトル/スクショ |
| `jlc_act.py` | 汎用操作。`upload <zip>` / `eval "<js>"` / `click "<text>"` / `txtclick "<exact>" [idx]`(ネイティブ完全一致) / `pwclick "<css>" [idx]`(ネイティブCSS) / `shot` |
| `jlc_catch_toast.py` | `button.saveCart` を押して直後トーストを高頻度捕捉（教訓4） |
| `jlc_upload_bomcpl.py` | `<bom> <cpl>` を input[0]/input[1] に設定 |
| `jlc_pick_desc.py` | Product Description カスケーダを選択（`OPTION` 定数を製品に合わせ編集） |
| `jlc_reupload.py` | 既存 input または file chooser 経由でガーバー差し替え |

## 注意・ハマりどころ早見

- ページを**リロードすると PCBA 設定（Standard/Both Sides等）が全部リセット**される。
  エラーでガーバーを上げ直すときは手順3からやり直す
- `input[placeholder='Select']` は**ページ内に複数ある**（PCBオプション側にも）。
  モーダル内のは `.el-dialog` 配下で絞るか、可視判定で選ぶ
- 画面の小さな赤枠＝必須未入力（Product Description等）。Submit が無反応のときはまず赤枠を疑う
- CDP接続が `ECONNREFUSED` なら Chrome が落ちている → 手順1で再起動（プロファイル指定を忘れずに＝ログイン保持）
- **セレクタは JLC の UI 更新で変わりうる**。変わっていたら `jlc_act.py eval` で DOM を調べて読み替える。
  教訓3（ネイティブclick必須）と教訓4（トースト捕捉）はセレクタが変わっても効き続ける
