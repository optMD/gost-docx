import sys
import unittest
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_docx import W, R, has_page_field, q
from apply_gost import ensure_footer


def footer(contents):
    return etree.fromstring(f'<w:ftr xmlns:w="{W}"><w:p>{contents}</w:p></w:ftr>')


class PageFieldTests(unittest.TestCase):
    def test_simple_commands(self):
        for command, expected in [("PAGE", True), (" page \\* MERGEFORMAT ", True),
                                  ("NUMPAGES", False), ("SECTIONPAGES", False),
                                  ('REF PAGE', False), ('QUOTE &quot;PAGE&quot;', False)]:
            with self.subTest(command=command):
                self.assertEqual(has_page_field(footer(
                    f'<w:fldSimple w:instr="{command}"/>')), expected)

    def test_complex_split_instructions(self):
        for chunks, expected in [([" PA", "GE "], True), ([" NUM", "PAGES "], False),
                                 (["PAGEREF bookmark"], False)]:
            with self.subTest(chunks=chunks):
                runs = ''.join(f'<w:r><w:instrText>{s}</w:instrText></w:r>' for s in chunks)
                node = footer('<w:r><w:fldChar w:fldCharType="begin"/></w:r>' + runs +
                              '<w:r><w:fldChar w:fldCharType="separate"/></w:r>' +
                              '<w:r><w:t>PAGE</w:t></w:r>' +
                              '<w:r><w:fldChar w:fldCharType="end"/></w:r>')
                self.assertEqual(has_page_field(node), expected)

    def test_formatter_adds_page_beside_numpages_only_once(self):
        sect = etree.fromstring(f'<w:sectPr xmlns:w="{W}" xmlns:r="{R}">'
                               '<w:footerReference w:type="default" r:id="footer"/>'
                               '</w:sectPr>')
        parts = {"word/footer.xml": etree.tostring(footer('<w:fldSimple w:instr="NUMPAGES"/>'))}
        self.assertFalse(has_page_field(etree.fromstring(parts["word/footer.xml"])))
        for _ in range(2):
            ensure_footer(None, {"footer": "footer.xml"}, parts, sect)
        result = etree.fromstring(parts["word/footer.xml"])
        self.assertTrue(has_page_field(result))
        self.assertEqual([f.get(q("instr")).strip() for f in result.iter(q("fldSimple"))],
                         ["NUMPAGES", "PAGE"])


if __name__ == "__main__":
    unittest.main()
