# -*- coding: utf-8 -*-
# CDP接続済みChromeのJLCページを操作するヘルパ。
# 使い方:
#   python jlc_act.py shot
#   python jlc_act.py upload <zip path>
#   python jlc_act.py click "<text>"
#   python jlc_act.py eval "<js>"
import sys, time, os
from playwright.sync_api import sync_playwright

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
	cmd = sys.argv[1] if len(sys.argv) > 1 else "shot"
	os.makedirs("screenshots", exist_ok=True)

	if cmd == "upload":
		fp = sys.argv[2]
		inputs = page.query_selector_all("input[type=file]")
		print("file inputs found:", len(inputs))
		page.set_input_files("input[type=file]", fp)
		print("set_input_files done:", fp)
		page.wait_for_timeout(10000)  # 解析待ち
	elif cmd == "click":
		page.get_by_text(sys.argv[2], exact=False).first.click()
		print("clicked:", sys.argv[2])
		page.wait_for_timeout(3000)
	elif cmd == "eval":
		print(page.evaluate(sys.argv[2]))
	elif cmd == "pwclick":
		sel = sys.argv[2]
		idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
		loc = page.locator(sel).nth(idx)
		loc.scroll_into_view_if_needed()
		loc.click()
		print("pwclicked", sel, idx)
		page.wait_for_timeout(3500)
	elif cmd == "txtclick":
		# 完全一致テキストのボタンをPlaywrightネイティブクリック
		txt = sys.argv[2]
		idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
		loc = page.get_by_text(txt, exact=True).nth(idx)
		loc.scroll_into_view_if_needed()
		loc.click()
		print("txtclicked:", txt, "idx", idx)
		page.wait_for_timeout(3000)

	print("URL:", page.url)
	page.screenshot(path="screenshots/jlc.png", full_page=True)
	print("shot -> screenshots/jlc.png (full)")
	br.close()
