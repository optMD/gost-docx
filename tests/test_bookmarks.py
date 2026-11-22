import sys
import unittest
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_docx import W, q
from apply_gost import fix_citations


def document():
    return etree.fromstring(f'<w:document xmlns:w="{W}"><w:body>'
        '<w:p><w:bookmarkStart w:id="5" w:name="Author"/>'
        '<w:r><w:t>Text [1]</w:t></w:r><w:bookmarkEnd w:id="5"/></w:p>'
        '<w:p><w:r><w:t>Список использованных источников</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>1. Source</w:t></w:r></w:p></w:body></w:document>')


class BookmarkTests(unittest.TestCase):
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
