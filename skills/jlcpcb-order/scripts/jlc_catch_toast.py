# -*- coding: utf-8 -*-
# 指定ボタンを押し、直後に出る el-message トーストを高頻度で即キャプチャする。
# 使い方:
#   python jlc_catch_toast.py                  … button.saveCart (NEXT) を押す
#   python jlc_catch_toast.py text "Submit"    … 完全一致テキストのボタンを押す
#   python jlc_catch_toast.py css "button.foo" … CSSセレクタのボタンを押す
import sys, time
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

mode = sys.argv[1] if len(sys.argv) > 1 else "saveCart"
arg = sys.argv[2] if len(sys.argv) > 2 else None

with sync_playwright() as p:
	br = connect(p)
	ctx = br.contexts[0] if br.contexts else br.new_context()
	page = None
	for pg in ctx.pages:
		if "jlcpcb" in (pg.url or ""):
			page = pg
			break
	page = page or (ctx.pages[0] if ctx.pages else ctx.new_page())

	# クリック対象を決定
	if mode == "text":
		btn = page.get_by_role("button", name=arg, exact=True).first
	elif mode == "css":
		btn = page.locator(arg).first
	else:  # saveCart (NEXT)
		btn = page.locator("button.saveCart").first
	btn.scroll_into_view_if_needed()
	btn.click()

	# 直後にトーストを高頻度ポーリング(最大6秒)
	seen = set()
	for _ in range(120):
		try:
			msgs = page.eval_on_selector_all(
				".el-message, .el-notification, .el-message-box__message",
				"els => els.map(e => e.innerText)")
		except Exception:
			msgs = []
		for m in msgs:
			m = (m or "").strip()
			if m and m not in seen:
				seen.add(m)
				print("TOAST:", m.replace("\n", " "))
		time.sleep(0.05)

	print("URL:", page.url)
	print("captured:", len(seen))
	br.close()
