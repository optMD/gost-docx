#!/usr/bin/env node
// Создаёт .docx с нуля по ГОСТ 7.32 и методичке РТУ МИРЭА.
// Использование: node build_gost.js задание.json файл.docx
// Формат задания (JSON): { "title": {...}, "chapters": [{ "heading": "...", "paragraphs": ["..."] }] }
// Текст глав пишет пользователь. Скрипт только оформляет.

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Footer, AlignmentType, PageNumber,
  HeadingLevel, LineRuleType,
} = require("docx");

const FONT = "Times New Roman";
const SIZE = 28; // 14 пт в half-points
const A4 = { width: 11906, height: 16838 };
const MARGINS = { top: 1134, bottom: 1134, left: 1701, right: 851, header: 709, footer: 709 };
const LINE_15 = 360;
const FIRST_INDENT = 709; // 1,25 см

function body(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: FONT, size: SIZE })],
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: FIRST_INDENT },
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function structural(text) {
  return new Paragraph({
    children: [new TextRun({ text: text.toUpperCase(), font: FONT, size: SIZE, bold: true })],
    alignment: AlignmentType.CENTER,
    pageBreakBefore: true,
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function sectionHeading(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: FONT, size: SIZE, bold: true })],
    alignment: AlignmentType.LEFT,
    indent: { firstLine: FIRST_INDENT },
    heading: HeadingLevel.HEADING_1,
    keepNext: true,
    spacing: { before: 0, after: 0, line: LINE_15, lineRule: LineRuleType.AUTO },
  });
}

function build(spec) {
  const children = [];
  children.push(structural("Введение"));
  (spec.introduction || []).forEach((t) => children.push(body(t)));
  (spec.chapters || []).forEach((ch) => {
    children.push(sectionHeading(ch.heading));
    ch.paragraphs.forEach((t) => children.push(body(t)));
  });
  children.push(structural("Заключение"));
  (spec.conclusion || []).forEach((t) => children.push(body(t)));
  children.push(structural("Список использованных источников"));
  (spec.sources || []).forEach((t, i) => children.push(body(`${i + 1}. ${t}`)));

  return new Document({
    styles: {
      default: {
        document: { run: { font: FONT, size: SIZE } },
      },
    },
    sections: [
      {
        properties: {
          page: { size: A4, margin: MARGINS },
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                indent: { firstLine: 0 },
                children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: SIZE })],
              }),
            ],
          }),
        },
        children,
      },
    ],
  });
}

async function main() {
  const [, , specPath, outPath] = process.argv;
  if (!specPath || !outPath) {
    console.error("Использование: node build_gost.js задание.json файл.docx");
    process.exit(2);
  }
  const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  const buf = await Packer.toBuffer(build(spec));
  fs.writeFileSync(outPath, buf);
  console.log(`Готово: ${outPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
