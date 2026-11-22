import sys
import unittest
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_docx import Audit, W, R, q
from apply_gost import fix_citations


def document():
    return etree.fromstring(f'<w:document xmlns:w="{W}"><w:body>'
        '<w:p><w:bookmarkStart w:id="5" w:name="Author"/>'
        '<w:r><w:t>Text [1]</w:t></w:r><w:bookmarkEnd w:id="5"/></w:p>'
        '<w:p><w:r><w:t>Список использованных источников</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>1. Source</w:t></w:r></w:p></w:body></w:document>')


class BookmarkTests(unittest.TestCase):
    def audit_links(self, doc):
        audit = Audit.__new__(Audit)
        audit.doc = doc
        audit.findings = []
        audit.check_bookmarks()
        return str(audit.findings)

    def test_audit_accepts_repaired_document(self):
        doc = document()
        fix_citations(doc)
        self.assertEqual(self.audit_links(doc), "[]")

    def test_audit_reports_broken_links_and_unpaired_bookmarks(self):
        doc = document()
        next(doc.iter(q("bookmarkEnd"))).getparent().remove(next(doc.iter(q("bookmarkEnd"))))
        link = etree.SubElement(doc, q("hyperlink"))
        link.set(q("anchor"), "Missing")
        findings = self.audit_links(doc)
        self.assertIn("пара начала и конца", findings)
        self.assertIn("не найдена целевая закладка Missing", findings)
        link.set(f"{{{R}}}id", "external")
        self.assertNotIn("Missing", self.audit_links(doc))

    def test_audit_reports_duplicate_names(self):
        doc = document()
        start = etree.SubElement(doc, q("bookmarkStart"))
        start.set(q("name"), "Author")
        start.set(q("id"), "6")
        self.assertIn("повторяется имя закладки Author", self.audit_links(doc))

    def test_repeated_format_repairs_duplicates_and_preserves_author_bookmark(self):
        doc = document()
        fix_citations(doc)
        from copy import deepcopy
        start = next(b for b in doc.iter(q("bookmarkStart")) if b.get(q("name")) == "_RefSrc1")
        duplicate = deepcopy(start)
        duplicate.set(q("id"), "99")
        start.getparent().append(duplicate)
        end = etree.SubElement(start.getparent(), q("bookmarkEnd"))
        end.set(q("id"), "99")
        fix_citations(doc)
        fix_citations(doc)
        starts = list(doc.iter(q("bookmarkStart")))
        self.assertCountEqual([b.get(q("name")) for b in starts], ["Author", "_RefSrc1"])
        self.assertCountEqual([b.get(q("id")) for b in starts],
                              [b.get(q("id")) for b in doc.iter(q("bookmarkEnd"))])
        self.assertTrue(any(h.get(q("anchor")) == "_RefSrc1" for h in doc.iter(q("hyperlink"))))

    def test_author_name_collision_is_reported(self):
        doc = document()
        next(doc.iter(q("bookmarkStart"))).set(q("name"), "_RefSrc1")
        with self.assertRaisesRegex(SystemExit, "вне записи"):
            fix_citations(doc)
