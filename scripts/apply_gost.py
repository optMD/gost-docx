#!/usr/bin/env python3
"""Форматирует копию .docx по ГОСТ 7.32 и выбранной методичке. Исходный файл не меняется.

Использование: python apply_gost.py файл.docx [--out файл_gost.docx]
Результат по умолчанию: файл_gost.docx рядом с исходным.
Меняет: размер и поля страницы, нижний колонтитул с PAGE по центру, стиль Normal,
прямое оформление абзацев основного текста (интервалы, отступ, выравнивание, шрифт).
Заголовки, подписи, таблицы и титул не трогает.
"""
import argparse
import copy
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).parent))
from audit_docx import (  # noqa: E402
    A4, FIRST_INDENT, FONT, LINE_15, MARGINS, NS, R, SIZE_HALFPT, W,
    Audit, default_para_style_id, has_page_field, q, same_file,
)

PPR_ORDER = [
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
    "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
    "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
    "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
    "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
    "sectPr", "pPrChange",
]
RPR_ORDER = [
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
    "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
    "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
    "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath",
]
FOOTER_PART = "word/footer_gost.xml"
FOOTER_REL_ID = "rIdGostFooter"


def local(el):
    return etree.QName(el).localname


def put(parent, tag, order, **attrs):
    """Заменяет или добавляет дочерний элемент в позицию по схеме OOXML."""
    for old in parent.findall(q(tag)):
        parent.remove(old)
    el = etree.Element(q(tag))
    for k, v in attrs.items():
        el.set(q(k), v)
    pos = len(parent)
    my = order.index(tag)
    for i, child in enumerate(parent):
        name = local(child)
        if name in order and order.index(name) > my:
            pos = i
            break
    parent.insert(pos, el)
    return el


def set_fonts(rpr_parent_el):
    rpr = rpr_parent_el.find(q("rPr"))
    if rpr is None:
        rpr = etree.Element(q("rPr"))
        rpr_parent_el.insert(0 if rpr_parent_el.find(q("pPr")) is None else 1, rpr)
    fonts = put(rpr, "rFonts", RPR_ORDER)
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(q(attr), FONT)
    put(rpr, "sz", RPR_ORDER, val=str(SIZE_HALFPT))
    put(rpr, "szCs", RPR_ORDER, val=str(SIZE_HALFPT))


def fix_sect(sect):
    pg = sect.find(q("pgSz"))
    if pg is None:
        pg = etree.Element(q("pgSz"))
        sect.insert(0, pg)
    pg.set(q("w"), str(A4[0]))
    pg.set(q("h"), str(A4[1]))
    if pg.get(q("orient")) is not None:
        del pg.attrib[q("orient")]
    mar = sect.find(q("pgMar"))
    if mar is None:
        mar = etree.SubElement(sect, q("pgMar"))
    for side, val in MARGINS.items():
        mar.set(q(side), str(val))
    mar.set(q("header"), "709")
    mar.set(q("footer"), "709")
    mar.set(q("gutter"), "0")


def footer_xml():
    return etree.fromstring(
        f'<w:ftr xmlns:w="{W}"><w:p><w:pPr><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>'
        f'<w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'.encode()
    )


def ensure_footer(doc, rels, parts, sect):
    """Возвращает True, если колонтитул пришлось добавить (нужны rels и Content_Types)."""
    refs = [r for r in sect.findall(q("footerReference")) if r.get(q("type")) in (None, "default")]
    if not refs:
        ref = etree.Element(q("footerReference"))
        ref.set(q("type"), "default")
        ref.set(f"{{{R}}}id", FOOTER_REL_ID)
        sect.insert(0, ref)
        parts[FOOTER_PART] = etree.tostring(footer_xml(), xml_declaration=True, encoding="UTF-8", standalone=True)
        return True
    target = rels.get(refs[0].get(f"{{{R}}}id"))
    name = "word/" + target
    footer = etree.fromstring(parts[name]) if name in parts else None
    if footer is None:
        raise SystemExit(f"Колонтитул {name} указан, но не найден в архиве")
    if not has_page_field(footer):
        para = footer.find(q("p"))
        if para is None:
            para = etree.SubElement(footer, q("p"))
        fld = etree.SubElement(para, q("fldSimple"))
        fld.set(q("instr"), " PAGE ")
        etree.SubElement(etree.SubElement(fld, q("r")), q("t")).text = "1"
    for p in footer.iter(q("p")):
        ppr = p.find(q("pPr"))
        if ppr is None:
            ppr = etree.Element(q("pPr"))
            p.insert(0, ppr)
        put(ppr, "ind", PPR_ORDER, firstLine="0")
        put(ppr, "jc", PPR_ORDER, val="center")
    parts[name] = etree.tostring(footer, xml_declaration=True, encoding="UTF-8", standalone=True)
    return False


def register_footer(rels_bytes, ct_bytes):
    rels = etree.fromstring(rels_bytes)
    rel = etree.SubElement(rels, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
    rel.set("Id", FOOTER_REL_ID)
    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer")
    rel.set("Target", "footer_gost.xml")
    ct = etree.fromstring(ct_bytes)
    ov = etree.SubElement(ct, "{http://schemas.openxmlformats.org/package/2006/content-types}Override")
    ov.set("PartName", "/" + FOOTER_PART)
    ov.set("ContentType", "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml")
    kw = dict(xml_declaration=True, encoding="UTF-8", standalone=True)
    return etree.tostring(rels, **kw), etree.tostring(ct, **kw)


def fix_styles(styles):
    normal_id = default_para_style_id(styles) or "Normal"
    normal = styles.find(f"w:style[@w:styleId='{normal_id}']", NS)
    if normal is None:
        raise SystemExit("В styles.xml нет стиля Normal")
    ppr = normal.find(q("pPr"))
    if ppr is None:
        ppr = put(normal, "pPr", ["name", "basedOn", "next", "link", "uiPriority", "qFormat", "pPr", "rPr"])
    apply_ppr(ppr)
    rpr = normal.find(q("rPr"))
    if rpr is None:
        rpr = etree.SubElement(normal, q("rPr"))
    fonts = put(rpr, "rFonts", RPR_ORDER)
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(q(attr), FONT)
    put(rpr, "sz", RPR_ORDER, val=str(SIZE_HALFPT))
    put(rpr, "szCs", RPR_ORDER, val=str(SIZE_HALFPT))


def apply_ppr(ppr):
    put(ppr, "spacing", PPR_ORDER, before="0", after="0", line=str(LINE_15), lineRule="auto")
    put(ppr, "ind", PPR_ORDER, firstLine=str(FIRST_INDENT))
    put(ppr, "jc", PPR_ORDER, val="both")


def fix_body(audit):
    changed = 0
    for _, p in audit.body_paragraphs():
        ppr, pstyle, text = audit.paragraph_info(p)
        if not audit.is_body(ppr, pstyle, text):
            continue
        if ppr is None:
            ppr = etree.Element(q("pPr"))
            p.insert(0, ppr)
        apply_ppr(ppr)
        for r in p.iter(q("r")):
            if "".join(t.text or "" for t in r.iter(q("t"))).strip():
                set_fonts(r)
        changed += 1
    return changed


CITE_GROUP = re.compile(r"\[(\d+(?:\s*[,;–—\-]\s*\d+)*)\]")
BIB_HEAD = re.compile(r"список\s+(использованных\s+источников|литературы)", re.I)
BIB_ITEM = re.compile(r"^(\d+)\.\s")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def para_text(p):
    return "".join(t.text or "" for t in p.iter(q("t")))


def bib_anchor(n):
    return f"_RefSrc{n}"


def bibliography_paragraphs(doc):
    """Номер источника → абзац в списке литературы. Заголовок — последнее совпадение (до него в содержании может быть такой же)."""
    paras = list(doc.iter(q("p")))
    texts = [para_text(p).strip() for p in paras]
    heads = [i for i, t in enumerate(texts) if BIB_HEAD.fullmatch(t)]
    index = {}
    if not heads:
        return index
    for i in range(heads[-1] + 1, len(paras)):
        t = texts[i]
        m = BIB_ITEM.match(t)
        if m:
            index.setdefault(int(m.group(1)), paras[i])
        elif t and index:
            break
    return index


def add_bookmark(p, name, bm_id):
    start = etree.Element(q("bookmarkStart"))
    start.set(q("id"), str(bm_id))
    start.set(q("name"), name)
    end = etree.Element(q("bookmarkEnd"))
    end.set(q("id"), str(bm_id))
    p.insert(1 if p.find(q("pPr")) is not None else 0, start)
    p.append(end)


def split_citations(text, index):
    """Режет текст на куски (кусок, номер источника или None). Скобки остаются обычным текстом."""
    out, pos = [], 0
    for m in CITE_GROUP.finditer(text):
        out.append((text[pos:m.start()], None))
        group, cur = m.group(1), 0
        out.append(("[", None))
        for d in re.finditer(r"\d+", group):
            out.append((group[cur:d.start()], None))
            n = int(d.group())
            out.append((d.group(), n if n in index else None))
            cur = d.end()
        out.append((group[cur:], None))
        out.append(("]", None))
        pos = m.end()
    out.append((text[pos:], None))
    return out


def make_run(text, rpr):
    r = etree.Element(q("r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, q("t"))
    t.text = text
    t.set(XML_SPACE, "preserve")
    return r


def link_citations(doc, index):
    """Оборачивает [N] в w:hyperlink на закладку пункта списка литературы. Возвращает число ссылок."""
    links = 0
    for r in list(doc.iter(q("r"))):
        parent = r.getparent()
        if parent.tag != q("p"):
            continue
        kids = [c for c in r if c.tag != q("rPr")]
        if len(kids) != 1 or kids[0].tag != q("t") or not CITE_GROUP.search(kids[0].text or ""):
            continue
        pieces = split_citations(kids[0].text, index)
        if not any(n is not None for _, n in pieces):
            continue
        pos = parent.index(r)
        rpr = r.find(q("rPr"))
        parent.remove(r)
        for k, (s, n) in enumerate([x for x in pieces if x[0]]):
            run = make_run(s, rpr)
            if n is None:
                parent.insert(pos + k, run)
                continue
            h = etree.Element(q("hyperlink"))
            h.set(q("anchor"), bib_anchor(n))
            h.set(q("history"), "1")
            h.append(run)
            parent.insert(pos + k, h)
            links += 1
    return links


def fix_citations(doc):
    index = bibliography_paragraphs(doc)
    if not index:
        return 0, 0
    bm_id = max((int(b.get(q("id"))) for b in doc.iter(q("bookmarkStart"))), default=0) + 1
    for n, p in sorted(index.items()):
        add_bookmark(p, bib_anchor(n), bm_id)
        bm_id += 1
    return len(index), link_citations(doc, index)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--out", help="путь результата (по умолчанию файл_gost.docx рядом)")
    args = ap.parse_args()

    src = Path(args.docx)
    out = Path(args.out) if args.out else src.with_name(src.stem + "_gost.docx")
    if same_file(src, out):
        raise SystemExit("Результат совпадает с исходным файлом — оригинал не перезаписываю")

    audit = Audit(args.docx)
    parts = {n: audit.z.read(n) for n in audit.z.namelist()}
    order = audit.z.namelist()

    sects = list(audit.doc.iter(q("sectPr")))
    if not sects:
        raise SystemExit("В документе нет sectPr — не к чему применять поля страницы")
    for s in sects:
        fix_sect(s)
    added_footer = ensure_footer(audit.doc, audit.rels, parts, sects[0])
    first_ref = sects[0].find(q("footerReference"))
    for s in sects[1:]:
        if first_ref is not None and not s.findall(q("footerReference")):
            s.insert(0, copy.deepcopy(first_ref))

    parts["word/document.xml"] = etree.tostring(audit.doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    if audit.styles is None:
        raise SystemExit("Нет word/styles.xml — стиль Normal не задать")
    fix_styles(audit.styles)
    parts["word/styles.xml"] = etree.tostring(audit.styles, xml_declaration=True, encoding="UTF-8", standalone=True)

    n_bib, n_links = fix_citations(audit.doc)
    n_body = fix_body(audit)
    parts["word/document.xml"] = etree.tostring(audit.doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    if "word/settings.xml" in parts:
        settings = etree.fromstring(parts["word/settings.xml"])
        for zoom in settings.findall(q("zoom")):
            if zoom.get(q("percent")) is None:
                zoom.set(q("percent"), "100")
        parts["word/settings.xml"] = etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True)

    if added_footer:
        parts["word/_rels/document.xml.rels"], parts["[Content_Types].xml"] = register_footer(
            parts["word/_rels/document.xml.rels"], parts["[Content_Types].xml"])
        order.append(FOOTER_PART)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in order:
            z.writestr(name, parts[name])
    print(f"Готово: {out}. Абзацев основного текста оформлено: {n_body}.")
    print(f"Источников с закладками: {n_bib}. Ссылок [N] сделано кликабельными: {n_links}.")
    if added_footer:
        print("Колонтитул с номером страницы добавлен.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
