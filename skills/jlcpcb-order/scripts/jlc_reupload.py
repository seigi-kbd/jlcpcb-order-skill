# -*- coding: utf-8 -*-
# 「Re-Upload」ボタン経由でガーバーzipを差し替える。
# ファイルchooserをハンドルして set_files する。
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

zip_path = sys.argv[1]

with sync_playwright() as p:
	br = connect(p)
	ctx = br.contexts[0] if br.contexts else br.new_context()
	page = None
	for pg in ctx.pages:
		if "jlcpcb" in (pg.url or ""):
			page = pg
			break
	page = page or (ctx.pages[0] if ctx.pages else ctx.new_page())

	# まず既存の hidden file input を探す
	inp = page.query_selector("input[type=file]")
	if inp:
		page.set_input_files("input[type=file]", zip_path)
		print("set via existing input")
	else:
		# Re-Upload ボタンを押して file chooser を捕捉
		btn = page.get_by_text("Re-Upload", exact=False).first
		with page.expect_file_chooser() as fc_info:
			btn.click()
		fc = fc_info.value
		fc.set_files(zip_path)
		print("set via file chooser")

	page.wait_for_timeout(12000)  # 再解析待ち
	txt = page.inner_text("body")
	import re
	m = re.search(r"Detected[^\n]{0,80}", txt)
	print("DETECTED:", m.group(0) if m else "(none)")
	print("URL:", page.url)
	br.close()
