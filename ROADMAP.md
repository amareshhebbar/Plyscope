# CAD Layer Explorer: Product Upgrade and Publishing Plan

Status: v0.1 working prototype (live task build). Target: v1.0 public, independent, open source product.

---

## 1. Project Definition

### What it is

A local first tool that opens CAD exported PDF drawings, extracts their layers (PDF Optional Content Groups), measures what each layer actually draws on every page, classifies and explains each layer, and lets users view, isolate, compare and export layers.

### Who it is for

| User | Problem it solves |
|---|---|
| Quantity surveyors and estimators | Isolate rebar, outlines or dimensions for takeoff without the CAD source |
| Structural and civil engineers | Review consultant drawing sets quickly, check what is on which sheet |
| BIM and CAD managers | Audit layer naming standards across a received drawing set |
| Contractors and site teams | Read busy sheets by hiding noise (title blocks, hatching, annotations) |
| Developers and AI teams | Clean, layer separated inputs for drawing analysis pipelines |

### Scope for v1.0

1. PDF input only (CAD exported, vector based).
2. Layer extraction, measurement, classification, isolation, overlay, export.
3. Runs fully on the user's machine: web UI, CLI and Python library.
4. Deterministic output for the same file.

### Out of scope for v1.0

1. DWG or DXF input (planned as an extension later).
2. Raster drawings or scanned sheets (they have no layers).
3. Editing or writing back to the PDF.
4. Multi user accounts or cloud storage.

---

## 2. Current State (v0.1)

| Area | Done |
|---|---|
| Upload and file info | Name, size, pages, sheet size, version, creator, has layers, hash |
| Layer extraction | OCGs grouped by name, duplicate definitions merged, original ids kept |
| Measurement | Baseline vs single layer render diff, ink pixels, coverage, empty flag |
| Classification | Name rules plus repetition based title block detection |
| Viewer | Page browsing, toggles, solo isolation, DPI, fit width |
| Output | Table, JSON, CSV, same single source |
| Robustness | No layer PDFs, invalid files, page and size caps, hash cache |

---

## 3. Critical Decision Before Publishing: Licensing

PyMuPDF (the PDF engine used now) is licensed under **AGPL v3**. Publishing with it means one of:

| Option | Effect | Recommended when |
|---|---|---|
| A. Release the whole project under AGPL v3 | Free to publish; anyone hosting it as a service must share their source | Pure open source community project |
| B. Buy an Artifex commercial license | Any license you like, including proprietary | You plan to sell it |
| C. Replace the engine | Use pdf.js (Apache 2.0) in the browser for rendering and layer toggling, and pypdf or pikepdf (permissive) on the backend for structure reading | You want MIT or Apache licensing |

Recommendation: **Option C for the long term**, Option A if you want to publish this week. pdf.js supports optional content natively, which also removes server rendering cost and gives instant layer toggling in the browser.

Decide this first. Everything in Phase 4 depends on it.

---

## 4. Upgrade Catalog

### 4.1 Extraction accuracy

| Upgrade | Value |
|---|---|
| Vector statistics per layer: path count, line length, text span count, image count | A second, exact measure of content alongside pixels |
| Content stream parser for marked content (BDC / EMC with OC) | Exact per layer object counts, works at any resolution |
| OCMD support (layers controlled by visibility expressions) | Correct results on complex exports |
| Radio button groups and locked layers from the PDF config | Respect the author's intended layer behavior |
| Layers missing from the layer panel order | Currently cannot be toggled; fix by direct OCG state control |
| Bounding box per layer per page | Zoom to layer, heatmaps, spatial queries |
| Untagged content report | Show exactly what sits outside every layer |

### 4.2 Classification and explanation

| Upgrade | Value |
|---|---|
| Rule packs for naming standards: AIA / NCS, ISO 13567, BS 1192, Uniclass | Correct labels for real world firm conventions |
| User editable rule file (YAML) | Firms add their own layer names without code changes |
| Feature based classifier: line density, text ratio, hatch fill ratio, repetition, position on sheet | Classifies layers with meaningless names like `D` or `SE` |
| Confidence score per classification | Users know when to double check |
| Optional local LLM explanation (Ollama, small model, temperature 0, cached) | Richer descriptions while staying local; off by default to keep determinism |
| Sheet title and number reading via OCR on the title block region | Page dropdown shows "S 05a First Floor GA" instead of "Page 22" |

### 4.3 Viewer and UX

| Upgrade | Value |
|---|---|
| Color coded overlay: each layer tinted its own color | See which line belongs to which layer when many are on |
| Pan and zoom with tiled rendering | Read A0 sheets at full detail |
| Hover a line to show its layer name | Instant identification |
| Thumbnails strip for pages | Fast browsing of large sets |
| Layer heatmap per page | See where each layer concentrates |
| Compare mode: two pages or two revisions side by side | Revision checking |
| Layer presets: "Structure only", "Annotations only", "Clean print" | One click views |
| Search across layers and page text | Find a beam mark or a note quickly |
| Keyboard shortcuts panel, dark and light theme, mobile layout | Polish |
| Progress bar with page count during analysis | No silent waiting on large files |

### 4.4 Output and integration

| Upgrade | Value |
|---|---|
| Export selected layers as a new PDF | Clean drawings for clients or printing |
| Export layer as SVG or PNG | Use in reports or ML datasets |
| Export full report as PDF or HTML | Shareable audit document |
| JSON Schema published and versioned | Stable contract for integrators |
| Excel export with one sheet per page | What estimators actually use |
| Layer naming audit report | Flags duplicates, nonstandard names, empty layers |

### 4.5 Performance and scale

| Upgrade | Value |
|---|---|
| Background job queue for analysis with status polling | UI never blocks |
| Parallel page analysis across CPU cores | 4 to 8 times faster on large sets |
| Server side render cache keyed by hash, page, layers, DPI | Instant toggles |
| Streaming results: layers appear as pages finish | Usable before analysis completes |
| Memory guard for very large sheets | No crashes on A0 at high DPI |

### 4.6 Robustness and security

| Upgrade | Value |
|---|---|
| Strict upload validation and timeouts per page | Survives malformed PDFs |
| Bind to localhost by default, explicit opt in for network | Safe default for a local tool |
| Cache cleanup command and size limit | Disk does not fill up |
| Fuzz testing with broken PDFs | Real crash resistance |
| No telemetry, stated clearly | Trust for engineering firms |

### 4.7 Developer surface

| Upgrade | Value |
|---|---|
| Python library: `analyze(path)` returns typed result | Use inside other tools |
| CLI: `cadlayers analyze drawing.pdf`, `cadlayers serve`, `cadlayers export` | Batch use and automation |
| REST API with OpenAPI docs (FastAPI gives this) | Integration with other systems |
| Plugin hook for custom classifiers | Community extensions |

---

## 5. Phased Architecture

### Phase 1: Hardening and Restructure (v0.2)

Goal: turn the prototype into a clean, testable codebase.

| Task | Requirement | Dependency | Done when |
|---|---|---|---|
| Restructure into a package: `cadlayers/core`, `cadlayers/api`, `cadlayers/cli`, `web/` | Clear module boundaries | None | App runs from the package |
| Typed result models with Pydantic | Every JSON field has a type | Restructure | Schema exported to `schema/layers.schema.json` |
| Test suite with pytest | Fixtures: this drawing, a no layer PDF, an empty layer PDF, an encrypted PDF, a broken PDF | Models | Tests pass locally |
| Determinism test | Analyze the same file twice, compare byte for byte | Tests | Passes in CI |
| Background analysis job with progress | Upload returns a job id, UI polls | Restructure | Large file shows live progress |
| Render cache on disk | Keyed by hash, page, layer set, DPI | Restructure | Repeat toggles return in under 50 ms |
| Licensing decision recorded | Option A, B or C chosen | None | LICENSE file in repo |

### Phase 2: Accuracy (v0.3)

Goal: results an engineer can trust.

| Task | Requirement | Dependency | Done when |
|---|---|---|---|
| Content stream parser for OC marked content | Path, text and image counts per layer per page | Phase 1 | Counts match manual checks on 5 sample pages |
| OCMD, radio groups, hidden from panel layers | Full optional content model | Parser | Test fixtures for each case pass |
| Bounding boxes per layer per page | Stored in JSON | Parser | Zoom to layer works |
| Rule packs and YAML rule file | AIA / NCS, ISO 13567, BS 1192 included | Phase 1 | Rules selectable in settings |
| Feature based classifier with confidence | Uses measured features, deterministic | Parser | Unknown layers drop below 10 percent on test set |
| Collect a test corpus | 10 to 20 public CAD PDFs from different firms and countries | None | Corpus stored with licenses noted |

### Phase 3: Product UX (v0.4)

Goal: a viewer people enjoy using.

| Task | Requirement | Dependency | Done when |
|---|---|---|---|
| Move rendering to pdf.js in the browser (if Option C) | Layer toggles happen client side | Licensing decision | Toggle is instant with no server call |
| Color coded overlay and hover to identify | Per layer tint | pdf.js or server tint | Each layer has a stable color |
| Pan, zoom, thumbnails | Smooth on A0 sheets | pdf.js | Works on a 100 page set |
| Presets, search, heatmap | As in section 4.3 | Phase 2 data | Usability test with 3 users |
| Exports: layer PDF, SVG, PNG, Excel, HTML report | As in section 4.4 | Phase 2 | Each export opens correctly in its target app |
| Rebuild frontend in React plus Vite plus TypeScript | Maintainable UI | None | Feature parity with v0.1 UI |

### Phase 4: Packaging and Distribution (v0.9 release candidate)

Goal: anyone can install it in one step.

| Task | Requirement | Dependency | Done when |
|---|---|---|---|
| PyPI package `cadlayers` with CLI entry point | `pip install cadlayers` then `cadlayers serve` | Phase 1 | Installs clean on Windows, macOS, Linux |
| Docker image on GitHub Container Registry | One command run | Phase 1 | `docker run` opens the app on port 8000 |
| Desktop app (optional): Tauri or PyInstaller bundle | No Python needed | Phase 3 | Signed installers for Windows and macOS |
| GitHub Actions CI: lint, type check, tests, build, publish on tag | Automated releases | Phase 1 tests | Tag push publishes PyPI and Docker |
| Documentation site with MkDocs Material on GitHub Pages | Install, usage, API, rule packs, JSON schema | Phases 1 to 3 | Docs live at a public URL |
| Security policy, contributing guide, code of conduct, issue templates | Standard open source hygiene | None | Files present in repo |

### Phase 5: Public Launch (v1.0)

Goal: real users and visibility.

| Task | Requirement | Dependency | Done when |
|---|---|---|---|
| Public demo on Hugging Face Spaces with the sample drawing preloaded | Visitors try it without installing; banner states uploads go to the demo server | Phase 4 Docker | Space is live |
| README with GIF demo, badges, quick start, comparison table | First impression | Phase 3 UI | Under 60 seconds from landing to understanding |
| Launch posts: Show HN, Reddit (r/civilengineering, r/AutoCAD, r/Python), LinkedIn, Product Hunt | Reach both engineers and developers | Demo live | Posts published within one week |
| Blog post: "How CAD layers survive inside a PDF and how to read them" | Technical credibility and search traffic | None | Published and linked from README |
| Feedback loop: GitHub Discussions, issue labels, public roadmap board | Users steer the product | Launch | First 10 issues triaged |

### Phase 6: Growth Extensions (after v1.0)

| Extension | Notes |
|---|---|
| DWG and DXF input via ezdxf or ODA converter | Same UI, true CAD source |
| Revision diff: compare two versions of a drawing set layer by layer | High value for contractors |
| Takeoff helpers: measure lengths and areas per layer with scale detection | Bridges into quantity surveying |
| Local AI assistant over the drawing (Ollama), opt in | "Show all beams on grid C" style queries |
| Team server edition with SSO | Possible paid tier if licensing allows |

---

## 6. Target Repository Structure

```
cadlayers/
  cadlayers/
    core/          extraction, parser, measurement, classification
    rules/         YAML rule packs
    api/           FastAPI app and job queue
    cli/           command line entry points
  web/             React frontend
  schema/          JSON Schema for outputs
  tests/
    fixtures/      sample PDFs with license notes
  docs/            MkDocs site
  docker/
  .github/workflows/
  LICENSE
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
```

---

## 7. Quality Gates for v1.0

| Gate | Target |
|---|---|
| Determinism | Same file gives identical JSON across runs and platforms |
| Test coverage | Core package above 85 percent |
| Corpus results | No crashes on any corpus file; unknown layers under 10 percent |
| Performance | 38 page A3 set analyzed under 5 seconds on a laptop; 300 page set under 60 seconds |
| Toggle speed | Under 100 ms per toggle |
| Install | One command on all three operating systems |
| Privacy | No outbound network calls, verified by a test |

---

## 8. Path to Completion

1. **Start:** make the licensing decision and create the public GitHub repo with the current code under that license. Tag it v0.1.0.
2. **Build:** work phase by phase. Each phase ends with a tagged release, an updated CHANGELOG and green CI.
3. **Test:** every new feature adds a fixture and a test. The determinism and corpus tests run on every pull request.
4. **Bridge milestones:** Phase 2 data (vector counts, boxes) feeds Phase 3 UI (overlay, heatmap, zoom to layer). Phase 1 restructuring is what makes Phase 4 packaging possible.
5. **Release:** Phase 4 automation publishes PyPI, Docker and docs from a single tag.
6. **Launch:** Phase 5 posts go out only once the demo, README GIF and docs are live.
7. **Conclude v1.0:** all quality gates in section 7 pass, then grow from user feedback through Phase 6.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| AGPL obligations from PyMuPDF | Decide in Phase 1; migrate to pdf.js and permissive libraries if needed |
| CAD exporters differ wildly (AutoCAD, Revit, MicroStation, Nitro resaves) | Build a diverse test corpus early in Phase 2 |
| Some exports flatten layers | Detect and explain clearly in the UI instead of failing |
| Name based rules fail on unconventional names | Feature based classifier plus user rule files |
| Hosted demo conflicts with the privacy promise | Demo uses the sample file by default and states clearly that uploads go to the demo server |
| Product name collision | Check PyPI, GitHub and trademark search before publishing |
