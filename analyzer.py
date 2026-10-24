import hashlib
import re
from collections import defaultdict

import numpy as np
import pymupdf

ANALYSIS_VERSION = "1.0"
REF_RE = re.compile(r"(\d+)\s+0\s+R")
STRIP_RE = re.compile(r"/(Parent|Annots|B|Thumb)\s*(\d+\s+0\s+R|\[[^\]]*\])")
SHEET_RE = re.compile(r"\bS\s?[-–]\s?\d{1,2}[A-Za-z]?\b")
DIFF_THRESHOLD = 16

RULES = [
    (r"rebar|rebaer|\brf\b|reinf", "core", "Reinforcement", "Reinforcement bars drawn in beams, columns and slabs"),
    (r"link|stirrup|tie", "core", "Reinforcement", "Shear links and stirrups around main bars"),
    (r"\bout\b|outline|edge|conc", "core", "Structure", "Outlines of structural members such as beams, columns, slabs and pile caps"),
    (r"h iron|l angle|iron|angle|steel|\bub\b|nut|bolt", "core", "Steelwork", "Structural steel sections, angles, plates and bolts"),
    (r"grid", "support", "Grid", "Structural grid lines and grid bubbles used for setting out"),
    (r"dim", "support", "Annotation", "Dimension lines and measured distances"),
    (r"txt|text", "support", "Annotation", "Text labels, member marks and notes"),
    (r"arrow|leader", "support", "Annotation", "Leader arrows and section markers"),
    (r"hatch|patch|fill", "support", "Hatching", "Hatch patterns showing cut sections, fills or concrete"),
    (r"\belv\b|elev|section", "support", "Views", "Elevation or section view geometry"),
    (r"wall|cage|handrail|door|window|stair", "support", "Architectural", "Architectural reference geometry from the background drawing"),
    (r"frame|border|title|sheet|defpoints|viewport|vport", "noise", "Sheet", "Sheet frame, border or title block content"),
    (r"^0$", "noise", "Default", "AutoCAD default layer; usually miscellaneous or unassigned objects"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify(name: str):
    key = re.sub(r"[_\-]+", " ", name.strip().lower())
    key = re.sub(r"\s+", " ", key)
    for pattern, role, category, text in RULES:
        if re.search(pattern, key):
            return role, category, text, "name"
    return "unknown", "Unknown", "Name does not match a known CAD convention", "none"


def ocg_refs_for_page(doc, page, ocg_xrefs, limit=20000):
    found, seen, stack = set(), set(), [page.xref]
    while stack and len(seen) < limit:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        try:
            obj = doc.xref_object(x, compressed=True)
        except Exception:
            continue
        obj = STRIP_RE.sub("", obj)
        for m in REF_RE.finditer(obj):
            r = int(m.group(1))
            if r in ocg_xrefs:
                found.add(r)
            elif r not in seen and r < doc.xref_length():
                stack.append(r)
    return found


def gray(page, dpi):
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False, annots=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.stride)[:, : pix.w]
    return arr.astype(np.int16)


def ui_name(cfg):
    return (cfg.get("text") or "").strip()


def set_visible_names(doc, names):
    wanted = set(names)
    for cfg in doc.layer_ui_configs():
        if cfg.get("type") == "label":
            continue
        doc.set_layer_ui_config(cfg["number"], 0 if ui_name(cfg) in wanted else 2)


def restore_defaults(doc, ocgs):
    on_names = {v["name"].strip() for v in ocgs.values() if v["on"]}
    set_visible_names(doc, on_names)


def sheet_label(page):
    try:
        matches = SHEET_RE.findall(page.get_text("text"))
    except Exception:
        matches = []
    if not matches:
        return None
    return re.sub(r"\s", "", matches[-1]).replace("–", "-")


def content_level(avg_cov):
    if avg_cov <= 0:
        return "none"
    if avg_cov < 0.1:
        return "low"
    if avg_cov < 1.0:
        return "medium"
    return "high"


def analyze(path: str, filename: str, file_hash: str, size_bytes: int, dpi: int = 30, max_pages: int = 1000):
    doc = pymupdf.open(path)
    if doc.needs_pass:
        raise ValueError("PDF is password protected")
    if not doc.is_pdf:
        raise ValueError("File is not a PDF")

    ocgs = doc.get_ocgs() or {}
    all_xrefs = sorted(ocgs)
    groups = defaultdict(list)
    for x in all_xrefs:
        groups[ocgs[x]["name"].strip() or f"(unnamed {x})"].append(x)
    xref_to_name = {x: n for n, xs in groups.items() for x in xs}

    page_total = doc.page_count
    page_limit = min(page_total, max_pages)

    per_layer_pages = defaultdict(dict)
    listed_pages = defaultdict(set)
    pages_out = []
    untagged_pages = []
    if all_xrefs:
        set_visible_names(doc, list(groups))
    labels = [sheet_label(doc[i]) for i in range(page_limit)]

    for pno in range(page_limit):
        page = doc[pno]
        rect = page.rect
        px_area = max(1, int(rect.width * dpi / 72) * int(rect.height * dpi / 72))
        entry = {
            "page": pno + 1,
            "sheet": labels[pno],
            "width_pt": round(rect.width, 2),
            "height_pt": round(rect.height, 2),
            "rotation": page.rotation,
            "listed_layers": [],
            "layers_with_content": [],
            "untagged_content_pixels": 0,
        }
        if all_xrefs:
            refs = ocg_refs_for_page(doc, page, set(all_xrefs))
            names_here = sorted({xref_to_name[r] for r in refs})
            entry["listed_layers"] = names_here
            set_visible_names(doc, [])
            base = gray(doc[pno], dpi)
            untagged = int(np.count_nonzero(base < 255 - DIFF_THRESHOLD))
            entry["untagged_content_pixels"] = untagged
            if untagged:
                untagged_pages.append(pno + 1)
            for name in names_here:
                listed_pages[name].add(pno + 1)
                set_visible_names(doc, [name])
                img = gray(doc[pno], dpi)
                ink = int(np.count_nonzero(np.abs(img - base) > DIFF_THRESHOLD))
                if ink:
                    per_layer_pages[name][pno + 1] = {"ink_pixels": ink, "coverage_pct": round(100.0 * ink / px_area, 4)}
                    entry["layers_with_content"].append(name)
        pages_out.append(entry)

    if all_xrefs:
        restore_defaults(doc, ocgs)

    layers_out = []
    for name in sorted(groups, key=lambda s: (s.lower(), s)):
        xs = sorted(groups[name])
        pp = per_layer_pages.get(name, {})
        pages = sorted(pp)
        ink_total = sum(v["ink_pixels"] for v in pp.values())
        covs = [v["coverage_pct"] for v in pp.values()]
        avg_cov = round(sum(covs) / len(covs), 4) if covs else 0.0
        empty = ink_total == 0
        role, category, text, basis = classify(name)
        inks = [v["ink_pixels"] for v in pp.values()]
        repeats = False
        if len(inks) >= 5 and len(inks) >= 0.5 * page_limit:
            mean = sum(inks) / len(inks)
            sd = (sum((i - mean) ** 2 for i in inks) / len(inks)) ** 0.5
            repeats = mean > 0 and sd / mean < 0.1
        if repeats and role in ("unknown", "support", "noise"):
            role, category, basis = "noise", "Sheet template", "repetition"
            text = "Draws nearly the same content on most sheets; likely title block, border or sheet template"
        if empty:
            role = "empty"
            text = "Defined in the file but draws nothing visible on any page" if not listed_pages.get(name) else "Referenced by pages but draws nothing visible"
        layers_out.append({
            "name": name,
            "ocg_ids": xs,
            "duplicate_definitions": len(xs),
            "default_visible": any(ocgs[x]["on"] for x in xs),
            "pages": pages,
            "page_count": len(pages),
            "listed_on_pages": sorted(listed_pages.get(name, set())),
            "ink_pixels": ink_total,
            "avg_coverage_pct": avg_cov,
            "max_coverage_pct": max(covs) if covs else 0.0,
            "content_level": content_level(avg_cov),
            "empty": empty,
            "role": role,
            "category": category,
            "explanation": text,
            "classified_by": basis,
            "per_page": {str(k): pp[k] for k in pages},
        })

    first = doc[0].rect if page_total else pymupdf.Rect()
    meta = doc.metadata or {}
    summary = defaultdict(int)
    for l in layers_out:
        summary[l["role"]] += 1
    result = {
        "analysis_version": ANALYSIS_VERSION,
        "analysis_dpi": dpi,
        "file": {
            "name": filename,
            "sha256": file_hash,
            "size_bytes": size_bytes,
            "pdf_version": meta.get("format", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "title": meta.get("title", ""),
            "creation_date": meta.get("creationDate", ""),
            "page_count": page_total,
            "pages_analyzed": page_limit,
            "truncated": page_limit < page_total,
            "first_page_size_mm": [round(first.width * 25.4 / 72, 1), round(first.height * 25.4 / 72, 1)],
            "has_layers": bool(all_xrefs),
            "layer_count": len(groups),
            "ocg_count": len(all_xrefs),
            "pages_with_untagged_content": untagged_pages,
        },
        "summary": {
            "total": len(layers_out),
            "core": summary["core"],
            "support": summary["support"],
            "noise": summary["noise"],
            "unknown": summary["unknown"],
            "empty": summary["empty"],
        },
        "pages": pages_out,
        "layers": layers_out,
    }
    doc.close()
    return result


def render_png(path: str, page_no: int, layer_names, mode: str, dpi: int):
    doc = pymupdf.open(path)
    try:
        if page_no < 1 or page_no > doc.page_count:
            raise ValueError("Page out of range")
        ocgs = doc.get_ocgs() or {}
        if ocgs:
            if mode == "all":
                set_visible_names(doc, [v["name"].strip() for v in ocgs.values()])
            elif mode == "default":
                restore_defaults(doc, ocgs)
            else:
                set_visible_names(doc, [n.strip() for n in layer_names])
        pix = doc[page_no - 1].get_pixmap(dpi=dpi, alpha=False, annots=False)
        return pix.tobytes("png")
    finally:
        doc.close()
