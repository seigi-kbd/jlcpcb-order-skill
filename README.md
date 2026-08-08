# jlcpcb-order — JLCPCB の発注を Claude Code にやらせるスキル

KiCad の製造ファイルを **JLCPCB** に入稿し、**注文確定の手前**まで自動で進める
[Claude Code](https://claude.com/claude-code) 用スキルです。

ガーバー生成 → アップロード → PCBA 設定 → BOM/CPL 入稿 → Product Description 選択 → Submit
までを Claude が実機 Chrome を操作して行い、**住所入力・支払いの手前で必ず止まります**。

> **どのくらい動くか、正直なところ**
> 個人の PCBA 発注で実際に使って通っているものです。**うまくいけば発注直前まで自動で行けます**が、
> 100% 動く保証はしません。JLCPCB の UI 更新でセレクタが変わることがあります。
> ただしこのスキルの中身は**手順書というより教訓集**で、消費者が LLM である前提で書いてあるため、
> セレクタが多少変わっても Claude が読み替えて進めてくれる可能性は高いです。
> 「そこそこの精度で動く」くらいに思って使ってください。

## 何が入っているか

**価値の本体は SKILL.md 冒頭の「高くついた教訓」7項目です。** スクリプトはその参考実装です。

特に効くのはこれ:

> **「The PCB size exceeds the maximum size Xmm for standard PCB assembly」の真因は、
> ガーバーzipに入っている余計なレイヤー。**
> KiCad デフォルト出力の Margin / Courtyard / Fab / User_Drawings 等を JLC のサイズ判定が
> 基板外形の外まで拾って巨大寸法と誤認する。エラー文の数値が `Xmm` と未挿入なのが目印。
> **寸法は合っているのに弾かれる**という、一人でハマると原因に辿り着けないやつです。

他にも「CDP は `localhost` だと繋がらない（IPv6で ECONNREFUSED）」「element-ui は JS の `.click()` では
ハンドラが発火しない」「エラートーストは数秒で消えるので 50ms ポーリングで捕まえる」
「Economic PCBA は片面のみ」など、全部実際に踏んだものです。

## インストール

```bash
git clone https://github.com/seigi-kbd/jlcpcb-order-skill.git
cp -r jlcpcb-order-skill/skills/jlcpcb-order ~/.claude/skills/
```

依存:
```bash
pip install playwright
playwright install chromium
```

KiCad CLI（`kicad-cli`）にもパスが通っている必要があります。

## 使い方

Claude Code で普通に頼むだけです。

```
JLCPCBに発注して
```

初回だけ、CDP 起動した Chrome で JLCPCB に手動ログインしてください
（プロファイルに Cookie が残るので次回以降は不要）。詳細は
[SKILL.md](skills/jlcpcb-order/SKILL.md) を読んでください。

## 安全設計

- **決済・住所入力・注文確定は絶対に自動化しません。** 支払い選択の手前で必ず停止し、
  設定内容を報告してユーザーの判断を仰ぎます
- pre-order 部品を含む場合、Submit 後に出る価格は PCB＋送料のみの仮計算です
  （PCBA 組立費・部品代は後日 JLC からメールで届く）。スキルはこれを明示して報告します

## 免責

- **自己責任で使ってください。** 発注は実際にお金が動く操作です。停止位置から先に進める前に、
  必ず内容をご自身で確認してください
- JLCPCB の利用規約（2026-08 時点）にブラウザ自動操作を明示的に禁じる条項は見当たりませんが、
  同社は「規約違反と判断した場合、予告なく利用を制限・停止できる」としています。
  **アカウント停止のリスクはゼロではありません**
- このスキルは JLCPCB とは無関係の非公式なものです

## ライセンス

MIT
