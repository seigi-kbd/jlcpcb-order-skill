# -*- coding: utf-8 -*-
# BOM/CPL モーダルの file input にそれぞれ設定する。
import sys, time, re
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

bom_path = sys.argv[1]
cpl_path = sys.argv[2]

with sync_playwright() as p:
	br = connect(p)
	ctx = br.contexts[0] if br.contexts else br.new_context()
	page = None
	for pg in ctx.pages:
		if "jlcpcb" in (pg.url or ""):
			page = pg
			break
	page = page or (ctx.pages[0] if ctx.pages else ctx.new_page())

	inputs = page.locator("input[type=file]")
	n = inputs.count()
	print("file inputs:", n)

	# input[0]=BOM, input[1]=CPL
	inputs.nth(0).set_input_files(bom_path)
	print("BOM set:", bom_path)
	page.wait_for_timeout(4000)
	inputs.nth(1).set_input_files(cpl_path)
	print("CPL set:", cpl_path)
	page.wait_for_timeout(6000)

	txt = page.inner_text("body")
	# アップロード後のファイル名表示やエラーを拾う
	for kw in ["bom.csv", "cpl.csv", "rows", "parts", "error", "fail", "invalid"]:
		m = re.search(r".{0,30}" + kw + r".{0,40}", txt, re.I)
		if m:
			print("HINT[%s]:" % kw, m.group(0).replace("\n", " "))
	page.screenshot(path="screenshots/jlc.png", full_page=True)
	print("shot saved")
	br.close()
