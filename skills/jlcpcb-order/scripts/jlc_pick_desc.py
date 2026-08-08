# -*- coding: utf-8 -*-
# Product Description(2段カスケーダ)を選択する。
#   第1階層(カテゴリ) → 第2階層(HSコード付きリーフ) の順にクリックしないと値が確定しない。
# 使い方:
#   python jlc_pick_desc.py                          … 既定(センサーモジュール)を選ぶ
#   python jlc_pick_desc.py "<第1階層先頭語>" "<第2階層リーフ部分一致>"
# 例: python jlc_pick_desc.py "Sensor" "Distance Measurement Sensor Module"
import sys, time
from playwright.sync_api import sync_playwright

# 既定: 光学/汎用センサーモジュール向け
CATEGORY_PREFIX = sys.argv[1] if len(sys.argv) > 1 else "Sensor"
LEAF_CONTAINS   = sys.argv[2] if len(sys.argv) > 2 else "Distance Measurement Sensor Module"

def connect(p, tries=20):
	last = None
	for _ in range(tries):
		try:
			return p.chromium.connect_over_cdp("http://127.0.0.1:9222")
		except Exception as e:
			last = e
			time.sleep(1)
	raise last

with sync_playwright() as p:
	br = connect(p)
	ctx = br.contexts[0] if br.contexts else br.new_context()
	page = None
	for pg in ctx.pages:
		if "jlcpcb" in (pg.url or ""):
			page = pg
			break
	page = page or (ctx.pages[0] if ctx.pages else ctx.new_page())

	# モーダル内の Select を開く
	sel = page.locator(".el-dialog input[placeholder='Select']").first
	sel.scroll_into_view_if_needed()
	sel.click()
	page.wait_for_timeout(1000)

	# 第1階層: 先頭語が一致する可視オプションをクリック
	items = page.locator(".el-select-dropdown__item")
	n = items.count()
	clicked_cat = False
	for i in range(n):
		it = items.nth(i)
		try:
			if not it.is_visible():
				continue
			t = (it.inner_text() or "").strip()
		except Exception:
			continue
		if t.startswith(CATEGORY_PREFIX):
			it.click()
			clicked_cat = True
			print("category:", t)
			break
	if not clicked_cat:
		print("category not found:", CATEGORY_PREFIX)
	page.wait_for_timeout(900)

	# 第2階層: リーフ(部分一致)をクリック。Playwrightの自動待機で可視化を待つ
	leaf = page.get_by_text(LEAF_CONTAINS, exact=False)
	try:
		leaf.first.click(timeout=6000)
		print("leaf clicked:", LEAF_CONTAINS)
	except Exception as e:
		print("leaf click failed:", str(e)[:80])

	page.wait_for_timeout(800)
	print("value:", sel.input_value())   # 確定すると "カテゴリ / リーフ - HS Code ..." が入る
	br.close()
