# -*- coding: utf-8 -*-
# CDP(remote-debugging-port=9222)で起動済みChromeに接続して操作するヘルパ。
# 使い方: python jlc_connect.py shot        … 現在ページをスクショ
#          python jlc_connect.py url            … URL/タイトルだけ表示
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

action = sys.argv[1] if len(sys.argv) > 1 else "shot"
with sync_playwright() as p:
	br = connect(p)
	ctx = br.contexts[0] if br.contexts else br.new_context()
	pages = ctx.pages
	page = pages[0] if pages else ctx.new_page()
	# 一番手前(URLがjlcpcbのもの)を優先
	for pg in pages:
		if "jlcpcb" in (pg.url or ""):
			page = pg
			break
	print("URL:", page.url)
	try:
		print("TITLE:", page.title())
	except Exception as e:
		print("title err:", e)
	os.makedirs("screenshots", exist_ok=True)
	if action == "shot":
		page.screenshot(path="screenshots/jlc.png")
		print("shot -> screenshots/jlc.png")
	br.close()  # CDPはdetachのみ(ブラウザは閉じない)
