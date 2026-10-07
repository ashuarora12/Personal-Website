"""
html_to_blocks.py - converts paper/paper.html into a list of structured blocks (paper/blocks.json)
that paper/build_docx.js turns into a Word document. Keeps one source of text for PDF and Word.
"""
import json
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image

PAPER = Path(__file__).resolve().parent


def runs(node, fmt=None):
    """Flatten inline HTML into runs: {text, b, i, sub, sup, mono, br}."""
    fmt = dict(fmt or {})
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            t = str(ch).replace("\n", " ")
            if t:
                out.append({"text": t, **fmt})
        elif isinstance(ch, Tag):
            f = dict(fmt)
            if ch.name in ("b", "strong"):
                f["b"] = True
            if ch.name in ("i", "em"):
                f["i"] = True
            if ch.name == "sub":
                f["sub"] = True
            if ch.name == "sup":
                f["sup"] = True
            if ch.name == "span" and "mono" in (ch.get("class") or []):
                f["mono"] = True
            if ch.name == "span" and "sub" in (ch.get("class") or []):
                f["small"] = True
            if ch.name == "br":
                out.append({"br": True})
                continue
            out.extend(runs(ch, f))
    # collapse double spaces at run boundaries
    clean = []
    for r in out:
        if "text" in r:
            r["text"] = " ".join(r["text"].split(" ")) if r["text"].strip() else " "
            while "  " in r["text"]:
                r["text"] = r["text"].replace("  ", " ")
        clean.append(r)
    if clean and "text" in clean[0]:
        clean[0]["text"] = clean[0]["text"].lstrip()
    if clean and "text" in clean[-1]:
        clean[-1]["text"] = clean[-1]["text"].rstrip()
    return clean


def table_block(tbl, caption=None, note=None, label=None):
    head = [runs(th) for th in tbl.find("thead").find_all("th")] if tbl.find("thead") else []
    rows = []
    for tr in tbl.find("tbody").find_all("tr"):
        cls = (tr.get("class") or [""])[0]
        tds = tr.find_all("td")
        cells = [runs(td) for td in tds]
        span = int(tds[0].get("colspan", 1)) if tds else 1
        rows.append({"cls": cls, "cells": cells, "span": span})
    kind = "reg" if "reg" in (tbl.get("class") or []) else "simple"
    return {"type": "table", "kind": kind, "label": label, "caption": caption, "note": note, "head": head, "rows": rows}


def caption_parts(figcap):
    b = figcap.find("b")
    label = b.get_text().strip().rstrip(".") if b else None
    if b:
        b.extract()
    return label, runs(figcap)


def convert():
    soup = BeautifulSoup((PAPER / "paper.html").read_text(encoding="utf-8"), "html.parser")
    blocks = []
    page_break_next = False
    for el in soup.body.children:
        if not isinstance(el, Tag):
            continue
        cls = el.get("class") or []
        if el.name == "div" and "wp" in cls:
            blocks.append({"type": "kicker", "runs": runs(el)})
        elif el.name == "h1":
            blocks.append({"type": "title", "runs": runs(el)})
        elif el.name == "div" and "author" in cls:
            blocks.append({"type": "author", "runs": runs(el)})
        elif el.name == "div" and "aff" in cls:
            blocks.append({"type": "aff", "runs": runs(el)})
        elif el.name == "div" and "abstract" in cls:
            blocks.append({"type": "abstract", "runs": runs(el.find("p"))})
        elif el.name == "div" and "refs" in cls:
            for p in el.find_all("p"):
                blocks.append({"type": "ref", "runs": runs(p)})
        elif el.name in ("h2", "h3"):
            blocks.append({"type": el.name, "runs": runs(el), "pagebreak": "pb" in cls})
        else:
            walk(el, blocks)
    return blocks


def walk(el, blocks):
    cls = el.get("class") or []
    if el.name == "p":
        kind = "eq" if "eq" in cls else "kw" if "kw" in cls else "note" if "note" in cls else \
            "authornote" if "author-note" in cls else "p"
        blocks.append({"type": kind, "runs": runs(el)})
    elif el.name in ("h2", "h3"):
        blocks.append({"type": el.name, "runs": runs(el), "pagebreak": "pb" in cls})
    elif el.name == "ol":
        for i, li in enumerate(el.find_all("li", recursive=False), 1):
            blocks.append({"type": "li", "n": i, "runs": runs(li)})
    elif el.name == "figure":
        label, cap = caption_parts(el.find("figcaption"))
        note_el = el.find("p", class_="note")
        note = runs(note_el) if note_el else None
        if el.find("table"):
            blocks.append(table_block(el.find("table"), cap, note, label))
        else:
            src = el.find("img")["src"]
            path = (PAPER / src).resolve()
            w, h = Image.open(path).size
            blocks.append({"type": "figure", "label": label, "caption": cap, "note": note, "src": str(path), "w": w, "h": h})
    elif el.name == "table":
        blocks.append(table_block(el))
    else:
        for ch in el.children:
            if isinstance(ch, Tag):
                walk(ch, blocks)


if __name__ == "__main__":
    b = convert()
    (PAPER / "blocks.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(b), "blocks;", sum(x["type"] == "table" for x in b), "tables;", sum(x["type"] == "figure" for x in b), "figures")
