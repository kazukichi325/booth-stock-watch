"""BOOTH の商品在庫を確認し、在庫が復活したバリエーションを Discord に通知する。"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ITEM_IDS = [6376654]  # 監視したい BOOTH 商品 ID（複数可）
STATE_FILE = Path(__file__).parent / "state.json"
INTERVAL_SECONDS = 60  # 確認間隔
RUN_MINUTES = float(os.environ.get("RUN_MINUTES", 0))  # 0 なら1回だけ確認して終了
USER_AGENT = "Mozilla/5.0 (booth-stock-watch)"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def fetch_stock(item_id):
    """{variation_id: {"name", "price", "in_stock"}} と商品情報を返す。"""
    item = fetch_json(f"https://booth.pm/ja/items/{item_id}.json")
    variations = {
        str(v["id"]): {
            "name": v["name"],
            "price": v["price"],
            "in_stock": not v.get("is_empty_stock", True),
        }
        for v in item["variations"]
    }
    return item, variations


def notify_discord(webhook_url, item, restocked):
    lines = [f"- **{v['name']}**（¥{v['price']:,}）" for v in restocked]
    payload = {
        "content": "🔔 BOOTH で在庫が復活しました！",
        "embeds": [
            {
                "title": item["name"],
                "url": item["url"],
                "description": "\n".join(lines),
                "color": 0xFC4D50,
                "thumbnail": {"url": item["images"][0]["original"]} if item.get("images") else None,
            }
        ],
    }
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)


def check_once(webhook_url, state):
    new_state = {}
    for item_id in ITEM_IDS:
        item, variations = fetch_stock(item_id)
        prev = state.get(str(item_id), {})
        restocked = [
            v for vid, v in variations.items()
            if v["in_stock"] and not prev.get(vid, {}).get("in_stock", False)
        ]
        new_state[str(item_id)] = variations

        summary = " / ".join(f"{v['name']}:{'○' if v['in_stock'] else '×'}" for v in variations.values())
        print(f"{time.strftime('%H:%M:%S')} [{item_id}] {summary}", flush=True)

        if restocked:
            print(f"[{item_id}] 在庫復活: {[v['name'] for v in restocked]}", flush=True)
            if webhook_url:
                notify_discord(webhook_url, item, restocked)
            else:
                print("DISCORD_WEBHOOK_URL が未設定のため通知をスキップしました", file=sys.stderr)

    if new_state != state:
        STATE_FILE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n")
    return new_state


def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    deadline = time.time() + RUN_MINUTES * 60

    while True:
        try:
            state = check_once(webhook_url, state)
        except Exception as e:  # 一時的な通信エラーでは止めずに次の確認へ
            print(f"確認に失敗しました: {e}", file=sys.stderr, flush=True)
        if time.time() + INTERVAL_SECONDS > deadline:
            break
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
