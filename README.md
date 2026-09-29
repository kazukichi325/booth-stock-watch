# booth-stock-watch

BOOTH の商品在庫を GitHub Actions で約1分おきに確認し、在庫が復活したら Discord に通知します。

- 監視対象: `check_stock.py` の `ITEM_IDS`（BOOTH の商品URL末尾の数字）
- 通知先: リポジトリの Secrets `DISCORD_WEBHOOK_URL`
- 前回の在庫状態は `state.json` に保存され、「在庫なし → 在庫あり」に変わったときだけ通知します
