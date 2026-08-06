"""Xuat cac khoi mermaid trong smart_garden_diagrams_v2.md thanh PNG.

Hai luot:
  1. render tat ca, doc kich thuoc CSS cua tung SVG
  2. chup tung so do voi window-size dung bang kich thuoc do, scale 3x
"""
import json
import pathlib
import re
import subprocess
import sys

MD = pathlib.Path(sys.argv[1])          # smart_garden_diagrams_v2.md
WORK = pathlib.Path(sys.argv[2])        # thu muc lam viec
OUT = pathlib.Path(sys.argv[3])         # thu muc dat PNG
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8895
SCALE = 3

NAMES = [
    '01-kien-truc-tong-quan',
    '02-cay-quyet-dinh-5-muc',
    '03-luong-xu-ly-du-lieu',
    '04a-sequence-tuoi-khan-cap',
    '04b-sequence-watchdog',
    '05-so-do-trien-khai',
    '06-gantt-wbs',
    '07-so-do-chan-cam',
]

blocks = re.findall(r'```mermaid\n(.*?)```', MD.read_text(encoding='utf-8'), re.S)
assert len(blocks) == len(NAMES), f'co {len(blocks)} khoi nhung {len(NAMES)} ten'
WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

PAGE = """<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:#fff;}
  #d{display:inline-block;padding:12px;background:#fff;}
  #d svg{display:block;height:auto!important;}
</style>
<body><div id="d"></div><pre id="sz" style="display:none"></pre>
<script type="module">
import m from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
m.initialize({startOnLoad:false, theme:'default',
              flowchart:{useMaxWidth:false}, sequence:{useMaxWidth:false},
              gantt:{useMaxWidth:false}});
const SRC = __SRC__;
const i = Number(new URLSearchParams(location.search).get('i') || 0);
const {svg} = await m.render('g'+i, SRC[i]);
document.getElementById('d').innerHTML = svg;
const s = document.querySelector('#d svg');
s.removeAttribute('style');
const vb = s.viewBox.baseVal;
if (vb && vb.width) { s.setAttribute('width', vb.width); s.setAttribute('height', vb.height); }
const box = document.getElementById('d').getBoundingClientRect();
document.getElementById('sz').textContent =
  'SIZE ' + i + ' ' + Math.ceil(box.width) + ' ' + Math.ceil(box.height);
document.getElementById('sz').style.display = 'block';
</script>"""

(WORK / 'render.html').write_text(
    PAGE.replace('__SRC__', json.dumps(blocks)), encoding='utf-8')

srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                        '--bind', '127.0.0.1', '-d', str(WORK)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
import time
time.sleep(2)

def chrome(args):
    return subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
                           '--hide-scrollbars'] + args,
                          capture_output=True, text=True, timeout=180,
                          encoding='utf-8', errors='replace')

try:
    sizes = {}
    for i in range(len(blocks)):
        r = chrome(['--virtual-time-budget=12000', '--dump-dom',
                    f'http://127.0.0.1:{PORT}/render.html?i={i}'])
        m2 = re.search(r'SIZE (\d+) (\d+) (\d+)', r.stdout)
        if not m2:
            print(f'{NAMES[i]}: KHONG DOC DUOC KICH THUOC')
            continue
        sizes[i] = (int(m2.group(2)), int(m2.group(3)))

    for i, (w, h) in sizes.items():
        png = OUT / f'{NAMES[i]}.png'
        chrome([f'--window-size={w},{h}',
                f'--force-device-scale-factor={SCALE}',
                '--virtual-time-budget=12000',
                f'--screenshot={png}',
                f'http://127.0.0.1:{PORT}/render.html?i={i}'])
        ok = png.exists()
        print(f'{NAMES[i]}.png  {w}x{h} css -> {w*SCALE}x{h*SCALE} px  '
              f'{png.stat().st_size//1024 if ok else 0} KB  {"OK" if ok else "THAT BAI"}')
finally:
    srv.terminate()
