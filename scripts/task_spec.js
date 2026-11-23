// Shared task loader for validate and build.
const fs = require("fs");

const PROFILES = {
  report: "Отчёт",
  coursework: "Курсовая работа",
  thesis: "Выпускная квалификационная работа",
  laboratory: "Лабораторная работа",
  practical: "Практическая работа",
  research: "Отчёт о научно-исследовательской работе",
  technical: "Техническая документация",
};

function requireObject(value, path) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${path}: expected an object`);
  }
}

function requireText(value, path) {
  if (typeof value !== "string") {
    throw new Error(`${path}: expected a string`);
  }
}

function validateList(value, path, validateItem = requireText) {
  if (value === undefined) return;
  if (!Array.isArray(value)) {
    throw new Error(`${path}: expected an array`);
  }
  value.forEach((item, index) => validateItem(item, `${path}[${index}]`));
}

function validateSection(section, path) {
  requireObject(section, path);
  if (typeof section.heading !== "string" || !section.heading.trim()) {
    throw new Error(`${path}.heading: expected a non-empty string`);
  }
  validateList(section.paragraphs, `${path}.paragraphs`);
}

function validateSpec(spec) {
  requireObject(spec, "$");
  if (Object.hasOwn(spec, "keywords")) {
    throw new Error("keywords: move this field to abstract.keywords (array of strings)");
  }
  if (spec.profile !== undefined) {
    requireText(spec.profile, "profile");
    if (!Object.hasOwn(PROFILES, spec.profile)) {
      throw new Error(`profile: expected one of ${Object.keys(PROFILES).join(", ")}`);
    }
  }

  if (spec.abstract !== undefined) {
    requireObject(spec.abstract, "abstract");
    for (const field of ["metadata", "keywords", "text"]) {
      validateList(spec.abstract[field], `abstract.${field}`);
    }
  }
  validateList(spec.introduction, "introduction");
  validateList(spec.conclusion, "conclusion");
  validateList(spec.chapters, "chapters", (chapter, path) => {
    validateSection(chapter, path);
    validateList(chapter.subsections, `${path}.subsections`, validateSection);
  });
  validateList(spec.sources, "sources", (source, path) => {
    const textPath = typeof source === "string" ? path : `${path}.text`;
    if (typeof source !== "string") requireObject(source, path);
    const text = typeof source === "string" ? source : source.text;
    requireText(text, textPath);
    if (!text.trim()) throw new Error(`${textPath}: expected a non-empty string`);
  });
  validateList(spec.appendices, "appendices", (appendix, path) => {
    requireObject(appendix, path);
    if (appendix.letter !== undefined) requireText(appendix.letter, `${path}.letter`);
    if (appendix.heading !== undefined) requireText(appendix.heading, `${path}.heading`);
    validateList(appendix.paragraphs, `${path}.paragraphs`);
  });
}

function checkKnownFields(spec) {
  function check(object, allowed, path) {
    for (const key of Object.keys(object)) {
      if (!allowed.includes(key)) throw new Error(`${path}.${key}: unknown field`);
    }
  }
  check(spec, ["profile", "abstract", "introduction", "chapters", "conclusion", "sources", "appendices"], "$");
  if (spec.abstract) check(spec.abstract, ["metadata", "keywords", "text"], "abstract");
  (spec.chapters || []).forEach((chapter, i) => {
    check(chapter, ["heading", "paragraphs", "subsections"], `chapters[${i}]`);
    (chapter.subsections || []).forEach((section, j) =>
      check(section, ["heading", "paragraphs"], `chapters[${i}].subsections[${j}]`));
  });
  (spec.sources || []).forEach((source, i) => {
    if (typeof source !== "string") check(source, ["text"], `sources[${i}]`);
  });
  (spec.appendices || []).forEach((item, i) => check(item, ["letter", "heading", "paragraphs"], `appendices[${i}]`));
}

function loadSpec(specPath, strict = false) {
  const contents = fs.readFileSync(specPath, "utf8");
  let spec;
  try {
    spec = JSON.parse(contents.replace(/^\uFEFF/, ""));
  } catch (error) {
    throw new Error(`Invalid JSON in ${specPath}: ${error.message}`);
  }
  validateSpec(spec);
  if (strict) checkKnownFields(spec);
  return spec;
}

module.exports = { loadSpec, PROFILES };

if (require.main === module) {
  const jsonOutput = process.argv.includes("--json");
  try {
    loadSpec(process.argv[2], process.argv.includes("--strict"));
    console.log(jsonOutput ? JSON.stringify({ schema_version: 1, ok: true, errors: [] }) : "Valid task JSON");
  } catch (error) {
    if (jsonOutput) {
      console.log(JSON.stringify({ schema_version: 1, ok: false, errors: [{ message: error.message }] }));
    } else {
      console.error(error.message);
    }
    process.exitCode = 1;
  }
}
