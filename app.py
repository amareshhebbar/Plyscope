import csv
import io
import json
import os
import re
import threading
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from analyzer import ANALYSIS_VERSION, analyze, render_png, sha256_bytes

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
STATIC = BASE / "static"

ANALYSIS_DPI = int(os.getenv("ANALYSIS_DPI", "30"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "1000"))
MAX_MB = int(os.getenv("MAX_MB", "300"))
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

app = FastAPI(title="Plyscope")
_locks = {}
_locks_guard = threading.Lock()


def lock_for(h):
    with _locks_guard:
        return _locks.setdefault(h, threading.Lock())


def paths(h):
    if not HASH_RE.match(h):
        raise HTTPException(400, "Invalid file id")
    d = DATA / h
    return d, d / "drawing.pdf", d / f"analysis_v{ANALYSIS_VERSION}_dpi{ANALYSIS_DPI}.json"


def load_analysis(h):
    _, pdf, js = paths(h)
    if not js.exists():
        raise HTTPException(404, "Unknown file; upload it first")
    return json.loads(js.read_text(encoding="utf-8"))


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=False, ensure_ascii=False), encoding="utf-8")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    data = file.file.read(MAX_MB * 1024 * 1024 + 1)
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"File larger than {MAX_MB} MB")
    if not data.startswith(b"%PDF") and b"%PDF" not in data[:1024]:
        raise HTTPException(400, "Not a PDF file")
    h = sha256_bytes(data)
    d, pdf, js = paths(h)
    with lock_for(h):
        if js.exists():
            return JSONResponse(json.loads(js.read_text(encoding="utf-8")))
        d.mkdir(parents=True, exist_ok=True)
        if not pdf.exists():
            pdf.write_bytes(data)
        try:
            result = analyze(str(pdf), Path(file.filename or "drawing.pdf").name, h, len(data), ANALYSIS_DPI, MAX_PAGES)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(422, f"Could not read PDF: {e}")
        write_json(js, result)
        return JSONResponse(result)


@app.get("/api/files")
def files():
    out = []
    for d in sorted(DATA.iterdir()):
        js = d / f"analysis_v{ANALYSIS_VERSION}_dpi{ANALYSIS_DPI}.json"
        if js.exists():
            f = json.loads(js.read_text(encoding="utf-8"))["file"]
            out.append({"sha256": f["sha256"], "name": f["name"], "page_count": f["page_count"], "layer_count": f["layer_count"]})
    return out


@app.get("/api/analysis/{h}")
def analysis(h: str):
    return load_analysis(h)


@app.get("/api/analysis/{h}/layers.json")
def layers_json(h: str):
    a = load_analysis(h)
    body = json.dumps({"file": a["file"]["name"], "sha256": h, "layers": a["layers"]}, indent=2, ensure_ascii=False)
    return Response(body, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="layers.json"'})


@app.get("/api/analysis/{h}/layers.csv")
def layers_csv(h: str):
    a = load_analysis(h)
    buf = io.StringIO()
    cols = ["name", "role", "category", "pages", "page_count", "ink_pixels", "avg_coverage_pct", "max_coverage_pct", "content_level", "empty", "default_visible", "ocg_ids", "explanation"]
    w = csv.writer(buf)
    w.writerow(cols)
    for l in a["layers"]:
        w.writerow([" ".join(map(str, l[c])) if isinstance(l[c], list) else l[c] for c in cols])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="layers.csv"'})


@app.get("/api/render/{h}")
def render(h: str, page: int = 1, mode: str = "custom", layer: List[str] = Query(default=[]), dpi: int = 100):
    _, pdf, _ = paths(h)
    if not pdf.exists():
        raise HTTPException(404, "Unknown file; upload it first")
    if mode not in ("custom", "all", "default"):
        raise HTTPException(400, "Invalid mode")
    dpi = max(20, min(dpi, 300))
    try:
        png = render_png(str(pdf), page, layer, mode, dpi)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
