import sys
import unittest
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_docx import document_part, W, R, has_page_field
from apply_gost import ensure_footer


class FooterPathTests(unittest.TestCase):
    def test_package_relative_and_absolute_paths(self):
        for target, expected in [("footer.xml", "word/footer.xml"),
                                 ("/word/footer.xml", "word/footer.xml"),
                                 ("./footers/../footer.xml", "word/footer.xml"),
                                 ("../footer.xml", "footer.xml"),
                                 ("footer%20one.xml", "word/footer one.xml")]:
            self.assertEqual(document_part(target), expected)

    def test_invalid_relationships_are_rejected(self):
        for target in (None, "../../outside.xml", "https://example.com/footer", "file:///tmp/footer", "foo\\bar"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                document_part(target)

    def test_formatter_uses_normalized_footer_path(self):
        sect = etree.fromstring(f'<w:sectPr xmlns:w="{W}" xmlns:r="{R}">'
                               '<w:footerReference w:type="default" r:id="footer"/></w:sectPr>')
        for target in ("/word/footer.xml", "./footer.xml"):
            parts = {"word/footer.xml": f'<w:ftr xmlns:w="{W}"><w:p/></w:ftr>'.encode()}
            self.assertFalse(ensure_footer(None, {"footer": target}, parts, sect))
            self.assertTrue(has_page_field(etree.fromstring(parts["word/footer.xml"])))
