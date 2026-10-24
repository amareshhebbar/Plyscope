import sys
from pathlib import Path

import pymupdf

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("sample_structural.pdf")
W, H = 1191, 842
GRID_X = [140, 300, 460, 620, 780]
GRID_Y = [160, 300, 440, 580]
BLACK = (0, 0, 0)
GREY = (0.45, 0.45, 0.45)
RED = (0.8, 0.1, 0.1)
BLUE = (0.1, 0.25, 0.75)


def layers(doc):
    names = ["S GRID", "S OUTLINE", "S REBAR", "S LINKS", "S DIM", "S TEXT", "S HATCH", "TITLEBLOCK", "SHEET BORDER", "DEFPOINTS", "0"]
    return {n: doc.add_ocg(n, on=True) for n in names}


def border(page, oc):
    page.draw_rect(pymupdf.Rect(20, 20, W - 20, H - 20), color=BLACK, width=1.2, oc=oc["SHEET BORDER"])


def titleblock(page, oc, title, sheet):
    r = pymupdf.Rect(W - 300, H - 140, W - 30, H - 30)
    page.draw_rect(r, color=BLACK, width=0.8, oc=oc["TITLEBLOCK"])
    page.draw_line((r.x0, r.y0 + 40), (r.x1, r.y0 + 40), color=BLACK, width=0.5, oc=oc["TITLEBLOCK"])
    page.insert_text((r.x0 + 10, r.y0 + 18), "PLYSCOPE SAMPLE PROJECT", fontsize=10, oc=oc["TITLEBLOCK"])
    page.insert_text((r.x0 + 10, r.y0 + 32), "Synthetic drawing for demonstration", fontsize=7, oc=oc["TITLEBLOCK"])
    page.insert_text((r.x0 + 10, r.y0 + 62), title, fontsize=11, oc=oc["TITLEBLOCK"])
    page.insert_text((r.x0 + 10, r.y0 + 90), f"SHEET {sheet}    SCALE 1:100    REV 0", fontsize=8, oc=oc["TITLEBLOCK"])


def grid(page, oc):
    for i, x in enumerate(GRID_X):
        page.draw_line((x, 110), (x, 630), color=GREY, width=0.4, dashes="[8 3 2 3] 0", oc=oc["S GRID"])
        page.draw_circle((x, 98), 10, color=GREY, width=0.5, oc=oc["S GRID"])
        page.insert_text((x - 3, 102), str(i + 1), fontsize=9, oc=oc["S GRID"])
    for j, y in enumerate(GRID_Y):
        page.draw_line((90, y), (830, y), color=GREY, width=0.4, dashes="[8 3 2 3] 0", oc=oc["S GRID"])
        page.draw_circle((845, y), 10, color=GREY, width=0.5, oc=oc["S GRID"])
        page.insert_text((842, y + 4), "ABCD"[j], fontsize=9, oc=oc["S GRID"])


def plan(page, oc):
    for x in GRID_X:
        for y in GRID_Y:
            page.draw_rect(pymupdf.Rect(x - 9, y - 9, x + 9, y + 9), color=BLACK, fill=BLACK, oc=oc["S OUTLINE"])
    for y in GRID_Y:
        page.draw_rect(pymupdf.Rect(GRID_X[0], y - 6, GRID_X[-1], y + 6), color=BLACK, width=0.7, oc=oc["S OUTLINE"])
    for x in GRID_X:
        page.draw_rect(pymupdf.Rect(x - 6, GRID_Y[0], x + 6, GRID_Y[-1]), color=BLACK, width=0.7, oc=oc["S OUTLINE"])
    page.draw_rect(pymupdf.Rect(GRID_X[1] + 10, GRID_Y[1] + 10, GRID_X[2] - 10, GRID_Y[2] - 10), color=GREY, width=0.3, oc=oc["S HATCH"])
    for k in range(0, 260, 12):
        x0 = GRID_X[1] + 10 + k
        page.draw_line((x0, GRID_Y[1] + 10), (max(GRID_X[1] + 10, x0 - 120), GRID_Y[1] + 130), color=GREY, width=0.3, oc=oc["S HATCH"])
    for i in range(len(GRID_X) - 1):
        a, b = GRID_X[i], GRID_X[i + 1]
        page.draw_line((a + 10, 140), (b - 10, 140), color=BLACK, width=0.4, oc=oc["S DIM"])
        page.draw_line((a, 134), (a, 146), color=BLACK, width=0.4, oc=oc["S DIM"])
        page.insert_text(((a + b) / 2 - 12, 136), f"{(b - a) * 25}", fontsize=8, oc=oc["S DIM"])
    for i, y in enumerate(GRID_Y):
        page.insert_text((GRID_X[0] + 20, y - 10), f"B{i + 1} 300x600", fontsize=7, oc=oc["S TEXT"])
    page.insert_text((140, 700), "GROUND FLOOR GENERAL ARRANGEMENT", fontsize=14, oc=oc["S TEXT"])
    page.insert_text((140, 716), "All dimensions in millimetres unless noted otherwise", fontsize=8, oc=oc["S TEXT"])
    page.draw_line((470, 470), (520, 430), color=BLACK, width=0.5, oc=oc["0"])


def beam_detail(page, oc, x, y, label, bars_top, bars_bot):
    w, h = 120, 220
    r = pymupdf.Rect(x, y, x + w, y + h)
    page.draw_rect(r, color=BLACK, width=1.0, oc=oc["S OUTLINE"])
    page.draw_rect(pymupdf.Rect(x + 12, y + 12, x + w - 12, y + h - 12), color=BLUE, width=0.6, oc=oc["S LINKS"])
    for i in range(bars_top):
        cx = x + 20 + i * (w - 40) / max(1, bars_top - 1)
        page.draw_circle((cx, y + 22), 5, color=RED, fill=RED, oc=oc["S REBAR"])
    for i in range(bars_bot):
        cx = x + 20 + i * (w - 40) / max(1, bars_bot - 1)
        page.draw_circle((cx, y + h - 22), 6, color=RED, fill=RED, oc=oc["S REBAR"])
    page.draw_line((x, y + h + 18), (x + w, y + h + 18), color=BLACK, width=0.4, oc=oc["S DIM"])
    page.insert_text((x + w / 2 - 10, y + h + 14), str(w * 2 + 60), fontsize=8, oc=oc["S DIM"])
    page.insert_text((x, y + h + 40), label, fontsize=11, oc=oc["S TEXT"])
    page.insert_text((x, y + h + 54), f"{bars_top}T16 top  {bars_bot}T20 bottom  R8 links at 150", fontsize=7, oc=oc["S TEXT"])


def column_schedule(page, oc):
    page.insert_text((80, 90), "COLUMN SCHEDULE", fontsize=14, oc=oc["S TEXT"])
    for i in range(5):
        x = 80 + i * 170
        page.draw_rect(pymupdf.Rect(x, 120, x + 150, 520), color=GREY, width=0.4, oc=oc["0"])
        cx, cy = x + 75, 260
        page.draw_rect(pymupdf.Rect(cx - 45, cy - 45, cx + 45, cy + 45), color=BLACK, width=1.0, oc=oc["S OUTLINE"])
        page.draw_rect(pymupdf.Rect(cx - 36, cy - 36, cx + 36, cy + 36), color=BLUE, width=0.6, oc=oc["S LINKS"])
        for dx in (-28, 28):
            for dy in (-28, 0, 28) if i % 2 else (-28, 28):
                page.draw_circle((cx + dx, cy + dy), 5, color=RED, fill=RED, oc=oc["S REBAR"])
        page.insert_text((x + 55, 480), f"C{i + 1}", fontsize=12, oc=oc["S TEXT"])
        page.insert_text((x + 30, 500), "300x300", fontsize=8, oc=oc["S DIM"])


def main():
    doc = pymupdf.open()
    oc = layers(doc)
    sheets = [("GROUND FLOOR GA", "S 01", "plan"), ("BEAM DETAILS", "S 02", "beams"), ("COLUMN SCHEDULE", "S 03", "columns"), ("FIRST FLOOR GA", "S 04", "plan")]
    for title, sheet, kind in sheets:
        page = doc.new_page(width=W, height=H)
        border(page, oc)
        titleblock(page, oc, title, sheet)
        if kind == "plan":
            grid(page, oc)
            plan(page, oc)
        elif kind == "beams":
            page.insert_text((80, 90), "BEAM SECTIONS", fontsize=14, oc=oc["S TEXT"])
            for i, (top, bot) in enumerate([(2, 3), (3, 4), (2, 2), (3, 5)]):
                beam_detail(page, oc, 90 + i * 200, 140, f"B{i + 1} SECTION", top, bot)
        else:
            column_schedule(page, oc)
    doc.set_metadata({"title": "Plyscope sample structural set", "creator": "Plyscope examples/make_sample.py"})
    doc.save(OUT, garbage=3, deflate=True)
    print(OUT)


if __name__ == "__main__":
    main()
