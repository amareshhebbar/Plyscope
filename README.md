# Plyscope

**See every layer inside your CAD drawings.**

Plyscope opens CAD exported PDF drawings, extracts the hidden CAD layers inside them, measures exactly what each layer draws on every sheet, explains what each layer contains, and lets you view any layer alone or in any combination. It runs entirely on your machine. Your drawings never leave it.

![Plyscope main view](docs/screenshot.png)

---

## Why Plyscope

When AutoCAD, Revit or MicroStation export a drawing to PDF, the CAD layers usually survive inside the file as PDF Optional Content Groups. Most people never see them. Plyscope turns them into something you can read, measure and use:

1. **Isolate** reinforcement, outlines or dimensions for takeoff without the CAD source.
2. **Audit** a received drawing set: which layers exist, where they appear, which are empty or junk.
3. **Declutter** busy sheets by hiding title blocks, hatching and annotations.
4. **Feed** clean, layer separated data into estimation or AI pipelines.

---

## Features

| Feature | Description |
|---|---|
| File overview | Pages, sheet size, PDF version, creator, whether layers exist, SHA256 |
| Layer extraction | Every layer found, duplicate definitions merged by name, original ids kept |
| Real measurement | Each layer is rendered alone against a blank baseline; changed pixels give exact content per page |
| Empty detection | Layers defined in the file but drawing nothing are flagged |
| Explanation | Each layer gets a role (core, support, noise, unknown, empty), a category and a plain description |
| Title block detection | Layers that repeat almost identically across sheets are flagged as sheet template noise |
| Isolation | Solo any layer to see only its content |
| Overlay | Toggle any combination of layers over the full drawing |
| Table and JSON | Same data, one source; download as JSON or CSV |
| Deterministic | Same file always gives the same output, cached by file hash |
| Private | No cloud calls, no AI services, no telemetry |

![Isolating the rebar layer](docs/isolate.png)

---

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/amareshhebbar/plyscope.git
cd plyscope
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8000**.

One step scripts are included as well:

| OS | Command |
|---|---|
| Linux or macOS | `./run.sh` |
| Windows | `run.bat` |

---

## What to upload

| Upload | Result |
|---|---|
| A PDF exported directly from AutoCAD, Revit, MicroStation, ArchiCAD or similar | Full layer analysis |
| The included `examples/sample_structural.pdf` | Instant demo with 11 layers including an empty one |
| A scanned drawing, photo or screenshot saved as PDF | Opens and renders, but reports no layers, because pixels carry no CAD layers |
| A PDF flattened by a print driver or "Microsoft Print to PDF" | Usually no layers; export again with layers enabled in your CAD tool |

Tip: in AutoCAD, use **Export to PDF** or **Plot** with **Include layer information** enabled.

To regenerate the sample:

```bash
python examples/make_sample.py
```

---

## How to use

1. Click **Upload PDF** or drop a file on the page.
2. Read the file card and summary on the left.
3. Pick a page from the dropdown, or use the arrow keys.
4. Tick or untick layers to change what shows. Use **All on**, **All off** or **Only this page**.
5. Press **Solo** on a layer, or click a row in the table, to see that layer alone. Press **Esc** to exit.
6. Switch between **Table** and **JSON**, and download either.

---

## Output

Each layer in the JSON looks like this:

```json
{
  "name": "S REBAR",
  "ocg_ids": [5],
  "duplicate_definitions": 1,
  "default_visible": true,
  "pages": [2, 3],
  "page_count": 2,
  "listed_on_pages": [2, 3],
  "ink_pixels": 1177,
  "avg_coverage_pct": 0.3389,
  "max_coverage_pct": 0.3738,
  "content_level": "medium",
  "empty": false,
  "role": "core",
  "category": "Reinforcement",
  "explanation": "Reinforcement bars drawn in beams, columns and slabs",
  "classified_by": "name",
  "per_page": {
    "2": { "ink_pixels": 649, "coverage_pct": 0.3738 },
    "3": { "ink_pixels": 528, "coverage_pct": 0.3041 }
  }
}
```

| Field | Meaning |
|---|---|
| `pages` | Pages where the layer draws visible content |
| `listed_on_pages` | Pages that reference the layer, even if it draws nothing there |
| `ink_pixels` | Pixels this layer changes, summed over all pages, at analysis resolution |
| `content_level` | none, low, medium or high, from average coverage |
| `role` | core (main structure), support (annotation, grid, hatch), noise (title block, border, default layer), unknown, empty |
| `classified_by` | `name` for naming rules, `repetition` for measured title block behavior |

---

## How it works

1. **Read:** the PDF's optional content groups are listed and grouped by name.
2. **Locate:** each page's resource tree is scanned to find which layers it references.
3. **Measure:** the page is rendered with all layers off (baseline), then once per layer with only that layer on. The pixel difference is the layer's real content on that page.
4. **Classify:** naming conventions (S structural, A architectural, dim, txt, grid, hatch, rebar, links and more) give the role and description. Layers drawing near identical content on most sheets are marked as sheet template.
5. **Cache:** results are stored by SHA256, so the same file always returns the same answer instantly.

---

## API

The server exposes a REST API with interactive docs at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/upload` | Upload and analyze a PDF |
| GET | `/api/files` | Previously analyzed files |
| GET | `/api/analysis/{hash}` | Full analysis |
| GET | `/api/analysis/{hash}/layers.json` | Layer data as JSON |
| GET | `/api/analysis/{hash}/layers.csv` | Layer data as CSV |
| GET | `/api/render/{hash}?page=2&layer=S%20REBAR&dpi=110` | PNG of a page with chosen layers |

Use `mode=all` to render every layer, or `mode=default` for the file's own visibility settings.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | 8000 | Server port |
| `ANALYSIS_DPI` | 30 | Resolution used for measurement |
| `MAX_PAGES` | 1000 | Page cap for very large files |
| `MAX_MB` | 300 | Upload size limit |

---

## Project structure

```
plyscope/
  app.py                    FastAPI server and endpoints
  analyzer.py               extraction, measurement, classification, rendering
  static/index.html         web viewer
  examples/make_sample.py   generates the sample drawing
  examples/sample_structural.pdf
  docs/                     screenshots
  data/                     local cache (not committed)
  requirements.txt
  run.sh / run.bat
  ROADMAP.md
```

---

## Privacy

Plyscope binds to `127.0.0.1` and makes no outbound requests. Uploaded files and results stay in the local `data/` folder. Delete that folder to clear everything.

---

## Roadmap

Color coded overlays, exact vector counts per layer, naming standard rule packs (AIA NCS, ISO 13567, BS 1192), layer export to PDF and SVG, a CLI and a PyPI package. See [ROADMAP.md](ROADMAP.md).

---

## License

AGPL v3. Plyscope uses PyMuPDF, which is licensed under AGPL v3.

---

Built by [Amaresh Hebbar](https://github.com/amareshhebbar).
