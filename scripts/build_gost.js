#!/usr/bin/env node
// Build a structured DOCX report without inventing user content.
// Usage: node build_gost.js assignment.json output.docx

const fs = require("fs");
const { loadSpec, PROFILES } = require("./task_spec");
const {
  Document, Packer, Paragraph, TextRun, Footer, AlignmentType, PageNumber,
  HeadingLevel, LineRuleType, TableOfContents,
} = loadDocx();

function loadDocx() {
  try {
    return require("docx");
  } catch (error) {
    if (error.code !== "MODULE_NOT_FOUND") throw error;
    console.error(`Install the Node.js dependencies: npm ci --prefix "${__dirname}"`);
    process.exit(1);
  }
}

const FONT = "Times New Roman";
const SIZE = 28; // 14 pt in half-points
const A4 = { width: 11906, height: 16838 };
const MARGINS = { top: 1134, bottom: 1134, left: 1701, right: 851, header: 709, footer: 709 };
const LINE_15 = 360;
const FIRST_INDENT = 709; // 1.25 cm

function textRun(text, options = {}) {
  return new TextRun({ text: String(text ?? ""), font: FONT, size: SIZE, ...options });
}

function body(text) {
  return new Paragraph({
    children: [textRun(text)], alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: FIRST_INDENT },
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function structural(text, { pageBreakBefore = true } = {}) {
  return new Paragraph({
    children: [textRun(String(text).toUpperCase(), { bold: true })],
    alignment: AlignmentType.CENTER, heading: HeadingLevel.HEADING_1,
    pageBreakBefore,
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function titlePlaceholder() {
  return new Paragraph({
    children: [textRun("ТИТУЛЬНЫЙ ЛИСТ", { bold: true })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function sectionHeading(text, { pageBreakBefore = false } = {}) {
  return new Paragraph({
    children: [textRun(text, { bold: true })], alignment: AlignmentType.LEFT,
    indent: { firstLine: FIRST_INDENT }, heading: HeadingLevel.HEADING_1,
    keepNext: true, pageBreakBefore,
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function addParagraphs(children, values) {
  (Array.isArray(values) ? values : []).forEach((value) => children.push(body(value)));
}

function addAbstract(children, spec) {
  children.push(structural("Реферат"));
  const abstract = spec.abstract || {};
  addParagraphs(children, abstract.metadata);
  if (Array.isArray(abstract.keywords) && abstract.keywords.length > 0) {
    children.push(new Paragraph({
      children: [textRun(abstract.keywords.join(", ").toUpperCase())],
      alignment: AlignmentType.LEFT, indent: { firstLine: 0 },
      spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
    }));
  }
  addParagraphs(children, abstract.text);
}

function addSources(children, sources) {
  (Array.isArray(sources) ? sources : []).forEach((source, index) => {
    const value = typeof source === "string" ? source : source.text;
    if (value) children.push(body(`${index + 1}. ${value}`));
  });
}

function build(spec) {
  const profile = spec.profile ?? "report";

  const children = [titlePlaceholder()];
  addAbstract(children, spec);
  children.push(structural("Содержание"));
  children.push(new TableOfContents("Содержание", {
    hyperlink: true, headingStyleRange: "1-3", beginDirty: true,
  }));
  children.push(structural("Введение"));
  addParagraphs(children, spec.introduction);

  (Array.isArray(spec.chapters) ? spec.chapters : []).forEach((chapter) => {
    if (!chapter || !chapter.heading) return;
    children.push(sectionHeading(chapter.heading, { pageBreakBefore: true }));
    addParagraphs(children, chapter.paragraphs);
    (Array.isArray(chapter.subsections) ? chapter.subsections : []).forEach((subsection) => {
      if (!subsection || !subsection.heading) return;
      children.push(sectionHeading(subsection.heading));
      addParagraphs(children, subsection.paragraphs);
    });
  });

  children.push(structural("Заключение"));
  addParagraphs(children, spec.conclusion);
  children.push(structural("Список использованных источников"));
  addSources(children, spec.sources);

  if (Array.isArray(spec.appendices)) {
    spec.appendices.forEach((appendix, index) => {
      const letter = appendix.letter || String.fromCharCode("А".charCodeAt(0) + index);
      children.push(structural(`Приложение ${letter}`));
      if (appendix.heading) children.push(new Paragraph({
        children: [textRun(appendix.heading, { bold: true })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
      }));
      addParagraphs(children, appendix.paragraphs);
    });
  }

  return new Document({
    creator: "gost-docx", description: `GOST document profile: ${PROFILES[profile]}`,
    styles: { default: { document: { run: { font: FONT, size: SIZE } } } },
    sections: [{
      properties: { page: { size: A4, margin: MARGINS }, titlePage: true },
      footers: {
        first: new Footer({ children: [] }),
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER, indent: { firstLine: 0 },
          children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: SIZE })],
        })] }),
      },
      children,
    }],
  });
}

async function main() {
  const [, , specPath, outPath] = process.argv;
  if (!specPath || !outPath) {
    console.error("Usage: node build_gost.js assignment.json output.docx");
    process.exit(2);
  }
  const spec = loadSpec(specPath);
  const buf = await Packer.toBuffer(build(spec));
  fs.writeFileSync(outPath, buf);
  console.log(`Created: ${outPath}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
