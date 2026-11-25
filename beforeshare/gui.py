"""BeforeShare window: a small local web page.

`beforeshare-gui` starts a server on 127.0.0.1 only, opens your browser, and serves one page.
Drop a file on it, review the findings, tick what to remove, and download the verified safe copy.
Files are handled in a temporary folder on your machine and deleted when you close the program.
Nothing is sent over the internet. Every request needs a random token printed in the URL.
"""
import json
import os
import secrets
import shutil
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

from .core import scan, scan_and_verify, SUPPORTED

MAX_BYTES = 200 * 1024 * 1024

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BeforeShare</title><style>
:root{--bg:#07110d;--fg:#d7f5e3;--mut:#7fa592;--card:#0d1c15;--line:#1d3a2c;--acc:#2ee59d;--hi:#ff6b5e;--me:#f0b23a;--lo:#5db7ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 ui-monospace,Menlo,Consolas,monospace}
.wrap{max-width:820px;margin:0 auto;padding:28px 20px}h1{margin:0 0 4px}h1:before{content:"> ";color:var(--acc)}
.mut{color:var(--mut)}#drop{border:2px dashed var(--line);border-radius:6px;padding:46px 20px;text-align:center;margin:20px 0;cursor:pointer;background:var(--card)}
#drop.over{border-color:var(--acc)}.f{display:flex;gap:10px;align-items:flex-start;padding:10px 14px;border:1px solid var(--line);border-radius:4px;margin:8px 0;background:var(--card)}
.sev{font-weight:700;min-width:70px}.HIGH{color:var(--hi)}.MEDIUM{color:var(--me)}.LOW{color:var(--lo)}
button{background:var(--acc);color:#04150d;border:0;border-radius:4px;padding:11px 20px;font:inherit;font-weight:700;cursor:pointer;margin:10px 8px 10px 0}
button:disabled{opacity:.4;cursor:default}a.dl{display:inline-block;background:var(--acc);color:#04150d;padding:11px 20px;border-radius:4px;font-weight:700;text-decoration:none}
.ok{color:var(--acc)}.bad{color:var(--hi)}.note{font-size:.85rem;color:var(--mut)}
</style></head><body><div class="wrap">
<h1>BeforeShare</h1><div class="mut">Your files may reveal more than you think. Everything stays on this computer.</div>
<div id="drop"><input id="file" type="file" hidden><b>Drop a file here</b> or click to choose<div class="mut" id="types"></div></div>
<div id="result"></div>
<script>
const TOKEN=new URLSearchParams(location.search).get('t');
const $=id=>document.getElementById(id);let current=null;
$('types').textContent='Supported: '+__TYPES__;
const drop=$('drop'),inp=$('file');
drop.onclick=()=>inp.click();
drop.ondragover=e=>{e.preventDefault();drop.classList.add('over')};drop.ondragleave=()=>drop.classList.remove('over');
drop.ondrop=e=>{e.preventDefault();drop.classList.remove('over');if(e.dataTransfer.files[0])up(e.dataTransfer.files[0])};
inp.onchange=()=>{if(inp.files[0])up(inp.files[0])};
const esc=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function up(file){
  $('result').innerHTML='<p class="mut">Scanning '+esc(file.name)+'...</p>';
  const r=await fetch('/scan?t='+TOKEN+'&name='+encodeURIComponent(file.name),{method:'POST',body:file});
  const d=await r.json();
  if(d.error){$('result').innerHTML='<p class="bad">'+esc(d.error)+'</p>';return}
  current=d;render(d);
}
function render(d){
  let h='<h3>'+esc(d.name)+'</h3>';
  if(!d.findings.length)h+='<p class="ok">No hidden data found by the checks BeforeShare has for this file type.</p><p class="note">This is not a guarantee that the file is safe to share.</p>';
  d.findings.forEach((f,i)=>{
    h+='<label class="f">'+(f.removable?'<input type="checkbox" checked data-code="'+f.code+'">':'<span style="width:13px"></span>')+
       '<span class="sev '+f.severity+'">'+f.severity+'</span><span>'+esc(f.message)+(f.removable?'':'<div class="note">Review by hand. Cannot be removed automatically.</div>')+'</span></label>';
  });
  if(d.findings.some(f=>f.removable))h+='<button id="mk">Create safe copy</button>';
  $('result').innerHTML=h+'<div id="done"></div>';
  if($('mk'))$('mk').onclick=make;
}
async function make(){
  const codes=[...document.querySelectorAll('input[data-code]:checked')].map(x=>x.dataset.code);
  $('mk').disabled=true;
  const r=await fetch('/clean?t='+TOKEN+'&id='+current.id,{method:'POST',body:JSON.stringify({codes})});
  const d=await r.json();
  if(d.error){$('done').innerHTML='<p class="bad">'+esc(d.error)+'</p>';return}
  let h=d.verified?'<p class="ok">Verified: the items you selected are gone from the copy. Your original file was not changed.</p>':'<p class="bad">Verification failed. Still present: '+d.remaining.map(esc).join('; ')+'</p>';
  if(d.left.length)h+='<p class="note">Still in the copy (not selected or not removable): '+d.left.map(esc).join('; ')+'</p>';
  h+='<a class="dl" href="/download?t='+TOKEN+'&id='+current.id+'">Download '+esc(d.copy_name)+'</a>';
  $('done').innerHTML=h;
}
</script></div></body></html>"""


def _fmt(f):
    return {"code": f.code, "severity": f.severity.label(), "message": f.message, "removable": f.removable}


class App:
    def __init__(self):
        self.token = secrets.token_urlsafe(16)
        self.tmp = tempfile.mkdtemp(prefix="beforeshare-")
        self.files = {}  # id -> {"path", "name", "copy"}

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def make_server(host="127.0.0.1", port=0):
    app = App()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _ok(self):
            q = parse_qs(urlparse(self.path).query)
            if q.get("t", [""])[0] != app.token or self.client_address[0] != "127.0.0.1":
                self.send_error(403)
                return None
            return q

        def _json(self, obj, code=200):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urlparse(self.path)
            q = self._ok()
            if q is None:
                return
            if u.path == "/":
                data = PAGE.replace("__TYPES__", json.dumps(" ".join(SUPPORTED))).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif u.path == "/download":
                rec = app.files.get(q.get("id", [""])[0])
                if not rec or not rec.get("copy"):
                    return self.send_error(404)
                data = Path(rec["copy"]).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(Path(rec["copy"]).name))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404)

        def do_POST(self):
            u = urlparse(self.path)
            q = self._ok()
            if q is None:
                return
            n = int(self.headers.get("Content-Length", 0))
            if n > MAX_BYTES:
                return self._json({"error": "File is too large (limit 200 MB)."}, 413)
            body = self.rfile.read(n)
            try:
                if u.path == "/scan":
                    name = os.path.basename(q.get("name", ["file"])[0]) or "file"
                    fid = secrets.token_hex(6)
                    d = Path(app.tmp) / fid
                    d.mkdir()
                    path = d / name
                    path.write_bytes(body)
                    findings = scan(str(path))
                    app.files[fid] = {"path": str(path), "name": name, "copy": None}
                    return self._json({"id": fid, "name": name, "findings": [_fmt(f) for f in findings]})
                if u.path == "/clean":
                    rec = app.files.get(q.get("id", [""])[0])
                    if not rec:
                        return self._json({"error": "Unknown file. Drop it again."}, 404)
                    codes = json.loads(body or b"{}").get("codes", [])
                    out, remaining, ok = scan_and_verify(rec["path"], None, codes)
                    rec["copy"] = out
                    left = [str(f) for f in scan(out)]
                    return self._json({"verified": ok, "remaining": [str(f) for f in remaining], "left": left, "copy_name": Path(out).name})
                self.send_error(404)
            except Exception as e:  # unreadable or corrupt files
                self._json({"error": f"Could not process this file ({type(e).__name__}). It may be corrupt or an unsupported type."}, 200)

    srv = ThreadingHTTPServer((host, port), H)
    srv.app = app
    return srv


def main(argv=None):
    srv = make_server()
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={srv.app.token}"
    print(f"BeforeShare is running at {url}\nPress Ctrl+C to stop. Files are kept in a temporary folder that is deleted on exit.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.app.close()


if __name__ == "__main__":
    main()
