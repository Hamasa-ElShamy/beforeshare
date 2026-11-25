"""Real-browser test of the window: drops a file, creates a safe copy, saves screenshots.
Run: pip install playwright; python tests/e2e_gui.py /path/to/chrome   (uses an installed Chrome/Chromium)
"""
import sys, threading
from playwright.sync_api import sync_playwright
from beforeshare.gui import make_server

chrome = sys.argv[1] if len(sys.argv) > 1 else "/usr/bin/google-chrome"
sample = sys.argv[2] if len(sys.argv) > 2 else "demo/Company_Report.xlsx"
srv = make_server()
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/?t={srv.app.token}"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 900, "height": 900})
    pg.goto(url)
    pg.set_input_files("#file", sample)
    pg.wait_for_selector(".f")
    pg.screenshot(path="demo/gui-scan.png")
    pg.click("#mk")
    pg.wait_for_selector("a.dl")
    assert "Verified" in pg.inner_text("#done")
    pg.screenshot(path="demo/gui-clean.png")
    b.close()
srv.shutdown(); srv.app.close()
print("e2e ok")
