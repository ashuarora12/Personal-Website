// build_docx.js - builds the Word version of the paper from paper/blocks.json
// Run from the welfare-anchor folder:  node paper/build_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, AlignmentType,
  WidthType, BorderStyle, Footer, PageNumber, LevelFormat, HeadingLevel, ShadingType, TableLayoutType,
  VerticalAlign,
} = require("docx");

const IN = process.argv[2] || "blocks.json", OUT = process.argv[3] || "paper.docx";
const blocks = JSON.parse(fs.readFileSync(path.join(__dirname, IN), "utf8"));
const PAGE_W = 12240, PAGE_H = 15840, MARGIN = 1440, CONTENT = PAGE_W - 2 * MARGIN; // US Letter, 1-inch margins
const BODY = "Times New Roman", SANS = "Arial";
const LINE = 480; // double spacing for the manuscript body
const INK = "111111", SOFT = "444444", TEAL = "444444", NAVY = "111111";

function textRuns(runs, base = {}) {
  const out = [];
  for (const r of runs || []) {
    if (r.br) { out.push(new TextRun({ break: 1 })); continue; }
    out.push(new TextRun({
      text: r.text, bold: r.b || base.bold, italics: r.i || base.italics,
      subScript: r.sub, superScript: r.sup,
      font: r.mono ? "Consolas" : (base.font || BODY),
      size: r.small ? (base.size || 22) - 4 : (r.mono ? (base.size || 22) - 2 : base.size),
      color: base.color,
    }));
  }
  return out;
}

const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const rule = (sz) => ({ style: BorderStyle.SINGLE, size: sz, color: INK });

function colWidths(tb, ncol) {
  if (tb.kind === "reg") {
    const first = Math.round(CONTENT * (ncol > 4 ? 0.30 : 0.42));
    const rest = Math.floor((CONTENT - first) / (ncol - 1));
    const w = [first, ...Array(ncol - 1).fill(rest)];
    w[ncol - 1] += CONTENT - w.reduce((a, b) => a + b, 0);
    return w;
  }
  // simple tables: weight by the longest text in each column (bounded)
  const len = Array(ncol).fill(4);
  const txt = (cell) => (cell || []).map((r) => r.text || "").join("");
  const all = [tb.head, ...tb.rows.map((r) => r.cells)];
  for (const row of all) row.forEach((c, j) => { if (j < ncol) len[j] = Math.max(len[j], Math.min(txt(c).length, j === 0 ? 70 : 34)); });
  // never narrower than the longest single word in the column (plus padding)
  for (const row of all) row.forEach((c, j) => {
    if (j < ncol) for (const wd of txt(c).split(/\s+/)) len[j] = Math.max(len[j], Math.min(wd.length + 3, 30));
  });
  for (let j = 1; j < ncol; j++) len[j] = Math.max(len[j], 10);
  const tot = len.reduce((a, b) => a + b, 0);
  const w = len.map((l) => Math.floor((CONTENT * l) / tot));
  w[0] += CONTENT - w.reduce((a, b) => a + b, 0);
  return w;
}

function cell(runs, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    columnSpan: opts.span,
    borders: { top: opts.top || none, bottom: opts.bottom || none, left: none, right: none },
    margins: { top: 30, bottom: 30, left: 70, right: 70 },
    verticalAlign: VerticalAlign.BOTTOM,
    shading: opts.shade ? { type: ShadingType.CLEAR, color: "auto", fill: opts.shade } : undefined,
    children: [new Paragraph({
      keepNext: !!opts.keepNext,
      alignment: opts.align || AlignmentType.LEFT, spacing: { before: 0, after: 0, line: 240 },
      children: textRuns(runs, { font: SANS, size: opts.size || 17, bold: opts.bold, italics: opts.italics, color: opts.color }),
    })],
  });
}

function caption(label, runs) {
  return new Paragraph({
    keepNext: true, spacing: { before: 200, after: 80 },
    children: [new TextRun({ text: (label ? label + ". " : ""), bold: true, font: SANS, size: 19, color: INK }),
      ...textRuns(runs, { font: SANS, size: 19 })],
  });
}

function note(runs) {
  return new Paragraph({ spacing: { before: 60, after: 200 }, children: textRuns(runs, { font: SANS, size: 15, color: SOFT }) });
}

function buildTable(tb) {
  const ncol = Math.max(tb.head.length, ...tb.rows.map((r) => r.cells.length + (r.span > 1 ? r.span - 1 : 0)));
  const w = colWidths(tb, ncol);
  const rows = [];
  if (tb.head.length) {
    rows.push(new TableRow({
      tableHeader: true, cantSplit: true,
      children: tb.head.map((h, j) => cell(h, w[j], { top: rule(12), bottom: rule(6), bold: true, keepNext: true,
        align: j === 0 ? AlignmentType.LEFT : AlignmentType.CENTER })),
    }));
  }
  let statSeen = false;
  tb.rows.forEach((r, i) => {
    const last = i === tb.rows.length - 1;
    const keepNext = !last && tb.rows.length <= 16;
    const bottom = last ? rule(12) : (tb.kind === "simple" ? { style: BorderStyle.SINGLE, size: 2, color: "DFE3E8" } : none);
    let top = none;
    if (r.cls === "stat" && !statSeen) { top = rule(6); statSeen = true; }
    if (r.cls === "grp") {
      rows.push(new TableRow({ cantSplit: true, children: [cell(r.cells[0], CONTENT, { span: ncol, italics: true, color: TEAL, bottom, keepNext })] }));
      return;
    }
    const size = r.cls === "se" ? 15 : 17;
    const color = r.cls === "se" ? SOFT : undefined;
    rows.push(new TableRow({
      cantSplit: true,
      children: r.cells.map((c, j) => cell(c, w[j], { top, bottom, size, color, keepNext,
        align: j === 0 || tb.kind === "simple" && j === 0 ? AlignmentType.LEFT : (tb.kind === "simple" && ncol === 3 && j === 2 && (tb.label === null) ? AlignmentType.LEFT : AlignmentType.CENTER) })),
    }));
  });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w, layout: TableLayoutType.FIXED, rows });
}

const children = [];
for (const b of blocks) {
  switch (b.type) {
    case "kicker":
      children.push(new Paragraph({ spacing: { after: 240 }, children: textRuns(b.runs, { font: SANS, size: 16, color: TEAL }) }));
      break;
    case "title":
      children.push(new Paragraph({ heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: textRuns(b.runs, { font: BODY, size: 32, bold: true, color: INK }) }));
      break;
    case "author":
      children.push(new Paragraph({ spacing: { after: 40 }, children: textRuns(b.runs, { font: SANS, size: 22 }) }));
      break;
    case "aff":
      children.push(new Paragraph({ spacing: { after: 280 }, children: textRuns(b.runs, { font: SANS, size: 18, color: SOFT }) }));
      break;
    case "abstract":
      children.push(new Paragraph({
        spacing: { before: 120, after: 240, line: 360 }, children: textRuns(b.runs, { size: 24 }),
      }));
      break;
    case "kw":
      children.push(new Paragraph({ spacing: { after: 240 }, children: textRuns(b.runs, { font: SANS, size: 17, color: SOFT }) }));
      break;
    case "h2":
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: !!b.pagebreak, keepNext: true,
        spacing: { before: 240, after: 0, line: LINE }, children: textRuns(b.runs, { font: BODY, size: 24, bold: true, color: INK }) }));
      break;
    case "h3":
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, pageBreakBefore: !!b.pagebreak,
        spacing: { before: 0, after: 0, line: LINE }, children: textRuns(b.runs, { font: BODY, size: 24, italics: true, color: INK }) }));
      break;
    case "p":
      children.push(new Paragraph({ indent: { firstLine: 576 }, spacing: { after: 0, line: LINE }, children: textRuns(b.runs, { size: 24 }) }));
      break;
    case "center":
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: textRuns(b.runs, { size: 24 }) }));
      break;
    case "small":
      children.push(new Paragraph({ spacing: { after: 160, line: 300 }, children: textRuns(b.runs, { size: 22 }) }));
      break;
    case "eq":
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 160 }, children: textRuns(b.runs, { size: 22, italics: true }) }));
      break;
    case "li":
      children.push(new Paragraph({ numbering: { reference: "recs", level: 0 }, alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 0, line: LINE }, children: textRuns(b.runs, { size: 24 }) }));
      break;
    case "ref":
      children.push(new Paragraph({ indent: { left: 576, hanging: 576 }, spacing: { after: 120, line: 360 }, children: textRuns(b.runs, { size: 24 }) }));
      break;
    case "authornote":
      children.push(new Paragraph({ shading: { type: ShadingType.CLEAR, color: "auto", fill: "F8F1DE" }, spacing: { after: 160 },
        children: textRuns(b.runs, { size: 19 }) }));
      break;
    case "note":
      children.push(note(b.runs));
      break;
    case "table":
      if (b.caption) children.push(caption(b.label, b.caption));
      children.push(buildTable(b));
      if (b.note) children.push(note(b.note)); else children.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
      break;
    case "figure": {
      children.push(caption(b.label, b.caption));
      const wpx = 600, hpx = Math.round((wpx * b.h) / b.w);
      children.push(new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, children: [new ImageRun({
        type: "png", data: fs.readFileSync(b.src), transformation: { width: wpx, height: hpx },
        altText: { title: b.label, description: (b.caption || []).map((r) => r.text || "").join(""), name: b.label } })] }));
      if (b.note) children.push(note(b.note));
      break;
    }
    default:
      break;
  }
}

const doc = new Document({
  creator: "Ashu Arora",
  title: "What Is Behind 'People Receiving Quality Health Services'? Measurement in the World Bank Group's Health Results",
  styles: {
    default: { document: { run: { font: BODY, size: 24, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: BODY, size: 24, bold: true, color: INK }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: BODY, size: 24, italics: true, color: INK }, paragraph: { outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "recs", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 400 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: 1440, bottom: 1440, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: SANS, size: 16, color: SOFT })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, OUT);
  fs.writeFileSync(out, buf);
  console.log("wrote", out);
});
