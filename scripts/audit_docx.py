#!/usr/bin/env python3
"""Аудит .docx по правилам ГОСТ 7.32 и выбранной методички. Только чтение.

Использование: python audit_docx.py файл.docx [--out отчёт.md]
Код возврата: 0 — нарушений нет, 1 — есть ошибки, 2 — файл не открыт.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}

A4 = (11906, 16838)
A3 = (16838, 23811)
MARGINS = {"left": 1701, "right": 851, "top": 1134, "bottom": 1134}
MARGIN_TOL = 30
FIRST_INDENT = 709
FIRST_INDENT_TOL = 40
FONT = "Times New Roman"
SIZE_HALFPT = 28
LINE_15 = 360

PRONOUNS = re.compile(r"(?<![\wё])(я|мы|мне|меня|нам|нас|наш|наша|наше|наши|нами|мной)(?![\wё])", re.I)
CAPTION = re.compile(r"^(Рисунок|Таблица)\s+[А-ЯA-Z]?\.?\d+(\.\d+)?\s*[-–—]\s+\S")
CAPTION_START = re.compile(r"^(Рисунок|Таблица)\s")


def q(tag):
    return "{%s}%s" % (W, tag)


def has_page_field(root):
    """Recognize PAGE commands, including instructions split across runs."""
    if root is None:
        return False

    def is_page(instruction):
        tokens = instruction.split()
        return bool(tokens and tokens[0].upper() == "PAGE")

    fields = []
    for element in root.iter():
        if element.tag == q("fldSimple"):
            if is_page(element.get(q("instr"), "")):
                return True
        elif element.tag == q("fldChar"):
            kind = element.get(q("fldCharType"))
            if kind == "begin":
                fields.append([])
            elif kind in ("separate", "end") and fields:
                if fields[-1] is not None and is_page("".join(fields[-1])):
                    return True
                if kind == "end":
                    fields.pop()
                else:
                    fields[-1] = None
        elif element.tag == q("instrText") and fields and fields[-1] is not None:
            fields[-1].append(element.text or "")
    return False


def same_file(source: Path, destination: Path) -> bool:
    if source.resolve() == destination.resolve():
        return True
    try:
        return source.samefile(destination)
    except FileNotFoundError:
        return False


def default_para_style_id(styles):
    if styles is None:
        return None
    for st in styles.findall("w:style", NS):
        if st.get(q("type")) == "paragraph" and st.get(q("default")) in ("1", "true"):
            return st.get(q("styleId"))
    return None


class Audit:
    def __init__(self, path):
        self.path = path
        try:
            self.z = zipfile.ZipFile(path)
            self.doc = etree.fromstring(self.z.read("word/document.xml"))
        except (OSError, zipfile.BadZipFile, KeyError, etree.XMLSyntaxError) as e:
            raise SystemExit(f"Не удалось открыть docx: {e}")
        self.styles = self._xml("word/styles.xml")
        self.rels = self._rels()
        self.findings = []  # (уровень, место, текст)

    def _xml(self, name):
        return etree.fromstring(self.z.read(name)) if name in self.z.namelist() else None

    def _rels(self):
        rels = self._xml("word/_rels/document.xml.rels")
        if rels is None:
            return {}
        return {r.get("Id"): r.get("Target") for r in rels}

    def add(self, level, where, msg):
        self.findings.append((level, where, msg))

    # ---- эффективные свойства: прямые → стиль абзаца → Normal → docDefaults ----

    def style_child(self, sid, child):
        if self.styles is None or sid is None:
            return None
        if sid == "Normal":
            sid = default_para_style_id(self.styles)
        st = self.styles.find(f"w:style[@w:styleId='{sid}']", NS)
        return st.find(q(child)) if st is not None else None

    def chain(self, direct, pstyle, child):
        defaults = None
        if self.styles is not None:
            defaults = self.styles.find(f"w:docDefaults/w:{'pPrDefault' if child == 'pPr' else 'rPrDefault'}/w:{child}", NS)
        return [direct, self.style_child(pstyle, child), self.style_child("Normal", child), defaults]

    @staticmethod
    def first(chain, tag, attr):
        for c in chain:
            if c is None:
                continue
            e = c.find(q(tag))
            if e is not None and e.get(q(attr)) is not None:
                return e.get(q(attr))
        return None

    # ---- проверки ----

    def check_sections(self):
        sects = list(self.doc.iter(q("sectPr")))
        if not sects:
            self.add("ошибка", "документ", "нет ни одного sectPr (нет настроек страницы)")
            return
        for i, s in enumerate(sects, 1):
            where = f"раздел {i}"
            pg = s.find(q("pgSz"))
            if pg is None:
                self.add("ошибка", where, "нет размера страницы")
            else:
                w, h = int(pg.get(q("w"))), int(pg.get(q("h")))
                dims = (w, h)
                if all(abs(a - b) <= 30 for a, b in zip(dims, A4)):
                    pass
                elif all(abs(a - b) <= 30 for a, b in zip(dims, A3)) or all(
                    abs(a - b) <= 30 for a, b in zip(dims, (A3[1], A3[0]))
                ):
                    self.add("предупреждение", where,
                             "используется формат A3; проверьте, что он нужен для большого количества таблиц/иллюстраций или приложения (ГОСТ 7.32, 6.1.1, 6.17.5)")
                else:
                    self.add("ошибка", where, f"формат {w}×{h} twips, нужен A4 или допустимый A3 (ГОСТ 7.32, 6.1.1)")
                orient = pg.get(q("orient"))
                if orient == "landscape":
                    self.add("предупреждение", where, "альбомная ориентация; проверьте, что она нужна для таблиц/иллюстраций или приложения (ГОСТ 7.32, 6.1.1, 6.17.5)")
            mar = s.find(q("pgMar"))
            if mar is None:
                self.add("ошибка", where, "нет полей страницы")
            else:
                for side, want in MARGINS.items():
                    got = int(mar.get(q(side), "0"))
                    if abs(got - want) > MARGIN_TOL:
                        self.add("ошибка", where, f"поле {side}: {got / 56.69:.1f} мм, нужно {want / 56.69:.1f} мм (30/15/20/20 мм)")
            self.check_footer(s, where)
            self.check_first_page_footer(s, where)

    def _footer_has_page(self, footer):
        return has_page_field(footer)

    def check_first_page_footer(self, sect, where):
        """Check that the counted title page has no visible page number."""
        title_pg = sect.find(q("titlePg")) is not None
        first_refs = [r for r in sect.findall(q("footerReference")) if r.get(q("type")) == "first"]
        if not title_pg:
            self.add("предупреждение", where,
                     "не задан отдельный режим первой страницы; отсутствие номера на титуле нельзя подтвердить автоматически (ГОСТ 7.32, 6.3.2)")
            return
        if not first_refs:
            self.add("предупреждение", where,
                     "для первой страницы нет отдельного колонтитула; проверьте, что номер на титуле скрыт визуально (ГОСТ 7.32, 6.3.2)")
            return
        target = self.rels.get(first_refs[0].get(f"{{{R}}}id"))
        footer = self._xml("word/" + target) if target else None
        if footer is None:
            self.add("ошибка", where, "колонтитул первой страницы указан, но файл не найден")
        elif self._footer_has_page(footer):
            self.add("ошибка", where, "на первой странице найдено поле PAGE; номер титульного листа должен быть скрыт (ГОСТ 7.32, 6.3.2)")

    def check_footer(self, sect, where):
        refs = [r for r in sect.findall(q("footerReference")) if r.get(q("type")) in (None, "default")]
        if not refs:
            self.add("ошибка", where, "нет нижнего колонтитула с номером страницы (ГОСТ 7.32, 6.3.1)")
            return
        target = self.rels.get(refs[0].get(f"{{{R}}}id"))
        footer = self._xml("word/" + target) if target else None
        if footer is None:
            self.add("ошибка", where, "колонтитул указан, но файл не найден")
            return
        has_page = has_page_field(footer)
        if not has_page:
            self.add("ошибка", where, "в колонтитуле нет поля PAGE — номер страницы не выводится")
        centered = any(
            (p.find("w:pPr/w:jc", NS) is not None and p.find("w:pPr/w:jc", NS).get(q("val")) == "center")
            for p in footer.iter(q("p"))
        )
        if not centered:
            self.add("ошибка", where, "номер страницы не по центру (ГОСТ 7.32, 6.3.1)")

    def body_paragraphs(self):
        for idx, p in enumerate(self.doc.iter(q("p"))):
            if any(a.tag == q("tbl") for a in p.iterancestors()):
                continue
            yield idx, p

    def paragraph_info(self, p):
        ppr = p.find(q("pPr"))
        pstyle_el = ppr.find(q("pStyle")) if ppr is not None else None
        pstyle = pstyle_el.get(q("val")) if pstyle_el is not None else "Normal"
        text = "".join(t.text or "" for t in p.iter(q("t")))
        return ppr, pstyle, text

    def is_body(self, ppr, pstyle, text):
        stripped = text.strip()
        if not stripped or pstyle.lower().startswith(("heading", "title", "toc", "caption")):
            return False
        if CAPTION_START.match(stripped) or stripped.startswith("Примечание"):
            return False
        if stripped.upper() in {
            "ТИТУЛЬНЫЙ ЛИСТ", "РЕФЕРАТ", "СОДЕРЖАНИЕ", "ВВЕДЕНИЕ", "ЗАКЛЮЧЕНИЕ",
            "ТЕРМИНЫ И ОПРЕДЕЛЕНИЯ", "ПЕРЕЧЕНЬ СОКРАЩЕНИЙ И ОБОЗНАЧЕНИЙ",
            "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", "ПРИЛОЖЕНИЕ",
        }:
            return False
        jc = self.first([ppr, self.style_child(pstyle, "pPr"), self.style_child("Normal", "pPr")], "jc", "val")
        return jc not in ("center", "right")

    def check_body_format(self):
        bad_indent, bad_line, bad_space, bad_jc = [], [], [], []
        for idx, p in self.body_paragraphs():
            ppr, pstyle, text = self.paragraph_info(p)
            if not self.is_body(ppr, pstyle, text):
                continue
            pc = [ppr, self.style_child(pstyle, "pPr"), self.style_child("Normal", "pPr"), self.pdefault()]
            ind = self.first(pc, "ind", "firstLine")
            line = self.first(pc, "spacing", "line")
            before = self.first(pc, "spacing", "before") or "0"
            after = self.first(pc, "spacing", "after") or "0"
            jc = self.first(pc, "jc", "val")
            snippet = text.strip()[:50]
            if ind is None or abs(int(ind) - FIRST_INDENT) > FIRST_INDENT_TOL:
                bad_indent.append((idx, snippet, ind))
            if line is None or abs(int(line) - LINE_15) > 5:
                bad_line.append((idx, snippet, line))
            if int(before) or int(after):
                bad_space.append((idx, snippet, before, after))
            if jc != "both":
                bad_jc.append((idx, snippet, jc))
        for label, items, fmt in [
            ("абзацный отступ не 1,25 см (709 twips)", bad_indent, lambda x: f"отступ {x[2]}"),
            ("межстрочный интервал не 1,5", bad_line, lambda x: f"интервал {x[2]}"),
            ("есть интервалы до/после абзаца (должны быть 0)", bad_space, lambda x: f"до {x[2]} / после {x[3]}"),
            ("выравнивание не «по ширине»", bad_jc, lambda x: f"jc={x[2]}"),
        ]:
            if items:
                self.add("ошибка", f"основной текст, {len(items)} абз.", f"{label}; примеры: " + "; ".join(
                    f"абз.{i[0]} «{i[1]}…» ({fmt(i)})" for i in items[:5]))

    def pdefault(self):
        if self.styles is None:
            return None
        return self.styles.find("w:docDefaults/w:pPrDefault/w:pPr", NS)

    def check_fonts(self):
        bad = []
        for idx, p in self.body_paragraphs():
            ppr, pstyle, text = self.paragraph_info(p)
            if not self.is_body(ppr, pstyle, text):
                continue
            for r in p.iter(q("r")):
                rt = "".join(t.text or "" for t in r.iter(q("t")))
                if not rt.strip():
                    continue
                rpr = r.find(q("rPr"))
                rc = [rpr, self.style_child(pstyle, "rPr"), self.style_child("Normal", "rPr"), self.rdefault()]
                font = self.first(rc, "rFonts", "ascii")
                size = self.first(rc, "sz", "val")
                if font != FONT or size != str(SIZE_HALFPT):
                    bad.append((idx, rt.strip()[:40], font, size))
        if bad:
            self.add("ошибка", f"основной текст, {len(bad)} фрагм.",
                     "шрифт не Times New Roman 14 пт; примеры: " + "; ".join(
                         f"абз.{b[0]} «{b[1]}» ({b[2] or '?'}, {int(b[3]) / 2 if b[3] else '?'} пт)" for b in bad[:5]))

    def rdefault(self):
        if self.styles is None:
            return None
        return self.styles.find("w:docDefaults/w:rPrDefault/w:rPr", NS)

    def check_headings(self):
        for idx, p in self.body_paragraphs():
            _, _, text = self.paragraph_info(p)
            t = text.strip()
            if re.match(r"^\d+(\.\d+)*\s+\S", t) and len(t) < 120 and t.endswith("."):
                self.add("предупреждение", f"абз.{idx}", f"заголовок «{t[:60]}» заканчивается точкой (ГОСТ 7.32, 6.2.3)")

    def check_main_section_breaks(self):
        """Main sections must start on a new page (ГОСТ 7.32, 6.2.1)."""
        for idx, p in self.body_paragraphs():
            ppr, _, text = self.paragraph_info(p)
            title = text.strip()
            if not re.match(r"^\d+\s+\S", title):
                continue
            if ppr is None or ppr.find(q("pageBreakBefore")) is None:
                self.add("ошибка", f"абз.{idx}",
                         f"раздел «{title[:70]}» не начинается с новой страницы (ГОСТ 7.32, 6.2.1)")

    def check_structural_elements(self):
        """Check common report elements without rejecting specialized profiles."""
        texts = [self.paragraph_info(p)[2].strip().upper() for _, p in self.body_paragraphs()]
        if "ТИТУЛЬНЫЙ ЛИСТ" not in texts:
            self.add("предупреждение", "структура", "не найдена титульная страница-заглушка; для существующего персонального титула проверьте документ визуально")
        if "ВВЕДЕНИЕ" in texts and "ЗАКЛЮЧЕНИЕ" not in texts:
            self.add("ошибка", "структура", "есть «ВВЕДЕНИЕ», но отсутствует «ЗАКЛЮЧЕНИЕ»")
        if "ЗАКЛЮЧЕНИЕ" in texts and not any("ИСТОЧНИК" in t for t in texts):
            self.add("предупреждение", "структура", "есть «ЗАКЛЮЧЕНИЕ», но не найден список использованных источников")

    def check_abbreviations_threshold(self):
        """The separate list is required only for more than three symbols."""
        heading = "ПЕРЕЧЕНЬ СОКРАЩЕНИЙ И ОБОЗНАЧЕНИЙ"
        paragraphs = list(self.body_paragraphs())
        for pos, (idx, p) in enumerate(paragraphs):
            if self.paragraph_info(p)[2].strip().upper() != heading:
                continue
            entries = 0
            for _, next_p in paragraphs[pos + 1:]:
                value = self.paragraph_info(next_p)[2].strip()
                if not value:
                    continue
                if value.upper() in {"ВВЕДЕНИЕ", "ЗАКЛЮЧЕНИЕ", "СОДЕРЖАНИЕ", "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"} or re.match(r"^\d+\s+", value):
                    break
                entries += 1
            if 1 <= entries <= 3:
                self.add("предупреждение", f"абз.{idx}",
                         f"перечень содержит {entries} обозначений; отдельный перечень обязателен только при количестве более трёх (ГОСТ 7.32, 5.6.2–5.6.3)")

    def check_captions(self):
        for idx, p in self.body_paragraphs():
            _, _, text = self.paragraph_info(p)
            t = text.strip()
            if not CAPTION_START.match(t):
                continue
            if not CAPTION.match(t):
                self.add("ошибка", f"абз.{idx}", f"подпись «{t[:60]}» не в формате «Рисунок N – Название» / «Таблица N – Название» (ГОСТ 7.32, 6.5.7, 6.6.3)")
            elif t.endswith("."):
                self.add("предупреждение", f"абз.{idx}", f"подпись «{t[:60]}» заканчивается точкой (ГОСТ 7.32, 6.5.8)")

    def check_citations(self):
        order = []
        for idx, p in self.body_paragraphs():
            _, _, text = self.paragraph_info(p)
            for group in re.findall(r"\[(\d+(?:\s*[,;–—\-]\s*\d+)*)\]", text):
                for n in re.findall(r"\d+", group):
                    order.append((int(n), idx))
        seen = []
        for n, idx in order:
            if n not in seen:
                if n != (max(seen) + 1 if seen else 1):
                    self.add("ошибка", f"абз.{idx}", f"ссылка [{n}] появляется раньше [{max(seen) + 1 if seen else 1}] — нарушен порядок ссылок (методичка, «Ссылки на источники»)")
                seen.append(n)

    def check_pronouns(self):
        hits = []
        for idx, p in self.body_paragraphs():
            _, _, text = self.paragraph_info(p)
            for m in PRONOUNS.finditer(text):
                hits.append((idx, m.group(0), text[max(0, m.start() - 25):m.end() + 25]))
        for idx, word, ctx in hits[:20]:
            self.add("ошибка", f"абз.{idx}", f"местоимение «{word}» в тексте (задание, 3-е лицо): …{ctx}…")

    def check_bookmarks(self):
        from collections import Counter
        starts = list(self.doc.iter(q("bookmarkStart")))
        names = Counter(b.get(q("name")) for b in starts)
        ids = Counter(b.get(q("id")) for b in starts)
        ends = Counter(b.get(q("id")) for b in self.doc.iter(q("bookmarkEnd")))
        for name, count in names.items():
            if name and count > 1:
                self.add("ошибка", "закладки", f"повторяется имя закладки {name}")
        for ident in ids.keys() | ends.keys():
            if ident is None or ids[ident] != 1 or ends[ident] != 1:
                self.add("ошибка", "закладки", f"некорректная пара начала и конца закладки {ident}")
        for link in self.doc.iter(q("hyperlink")):
            anchor = link.get(q("anchor"))
            # External links may also carry a fragment belonging to their URL.
            if anchor and not link.get(f"{{{R}}}id") and anchor not in names:
                self.add("ошибка", "ссылки", f"не найдена целевая закладка {anchor}")

    def check_bullets(self):
        for idx, p in self.body_paragraphs():
            _, _, text = self.paragraph_info(p)
            if "•" in text:
                self.add("ошибка", f"абз.{idx}", "символ «•» как маркер списка (методичка: использовать тире)")

    def run(self):
        self.check_sections()
        self.check_body_format()
        self.check_fonts()
        self.check_headings()
        self.check_main_section_breaks()
        self.check_structural_elements()
        self.check_abbreviations_threshold()
        self.check_captions()
        self.check_citations()
        self.check_bookmarks()
        self.check_pronouns()
        self.check_bullets()
        return self.findings


def render(path, findings):
    lines = [f"# Аудит: {path}", ""]
    errs = [f for f in findings if f[0] == "ошибка"]
    warns = [f for f in findings if f[0] == "предупреждение"]
    lines.append(f"Ошибок: {len(errs)}, предупреждений: {len(warns)}")
    lines.append("")
    if not findings:
        lines.append("Нарушений по проверенным правилам не найдено.")
    for level, title in (("ошибка", "Ошибки"), ("предупреждение", "Предупреждения")):
        items = [f for f in findings if f[0] == level]
        if items:
            lines.append(f"## {title}")
            lines.append("")
            for _, where, msg in items:
                lines.append(f"- **{where}** — {msg}")
            lines.append("")
    lines.append("Проверка охватывает поля, формат, колонтитул, шрифт, интервалы, отступ, выравнивание, подписи, ссылки, местоимения и маркеры. Не проверяются: содержание (TOC) по страницам, рисунки/таблицы в колонтитулах, нумерация разделов и формулы — их проверяют глазами после рендера.")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--out", help="сохранить отчёт в .md (оригинал не меняется)")
    ap.add_argument("--json", action="store_true", help="вывести машиночитаемый отчёт")
    ap.add_argument("--fail-on-warning", action="store_true", help="считать предупреждения причиной неуспешной проверки")
    args = ap.parse_args()
    if args.out and same_file(Path(args.docx), Path(args.out)):
        ap.error("Путь отчёта совпадает с исходным файлом")
    try:
        findings = Audit(args.docx).run()
    except (SystemExit, etree.XMLSyntaxError, ValueError, KeyError) as e:
        if args.json:
            print(json.dumps({"schema_version": 1, "ok": False, "completed": False,
                              "findings": [], "errors": [{"message": str(e)}]}, ensure_ascii=False))
        else:
            print(e, file=sys.stderr)
        return 2
    ok = not any(f[0] == "ошибка" or (args.fail_on_warning and f[0] == "предупреждение")
                 for f in findings)
    report = (json.dumps({"schema_version": 1, "ok": ok, "completed": True,
                          "findings": [{"severity": "error" if level == "ошибка" else "warning",
                                        "location": where, "message": message}
                                       for level, where, message in findings], "errors": []},
                         ensure_ascii=False, indent=2) + "\n") if args.json else render(args.docx, findings)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
