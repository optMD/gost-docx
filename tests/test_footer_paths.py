import sys
import unittest
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_docx import document_part, W, R, has_page_field, q
from apply_gost import ensure_footer, prepare_footers


class FooterPathTests(unittest.TestCase):
    def test_creation_avoids_collisions_and_preserves_first_page_references(self):
        sects = [etree.fromstring(f'<w:sectPr xmlns:w="{W}" xmlns:r="{R}">'
                 '<w:footerReference w:type="first" r:id="first"/></w:sectPr>') for _ in range(2)]
        parts = {"word/footer_gost.xml": b"keep original",
                 "word/_rels/document.xml.rels": b'<Relationships><Relationship Id="rIdGostFooter1"/></Relationships>',
                 "[Content_Types].xml": b'<Types/>'}
        added = prepare_footers(None, {}, parts, sects)
        self.assertEqual(added, "word/footer_gost2.xml")
        self.assertEqual(parts["word/footer_gost.xml"], b"keep original")
        for sect in sects:
            refs = {r.get(q("type")): r.get(f"{{{R}}}id") for r in sect.findall(q("footerReference"))}
            self.assertEqual(refs, {"first": "first", "default": "rIdGostFooter2"})

    def test_each_existing_default_footer_is_formatted(self):
        sects = [etree.fromstring(f'<w:sectPr xmlns:w="{W}" xmlns:r="{R}">'
                 f'<w:footerReference w:type="default" r:id="f{i}"/></w:sectPr>') for i in range(2)]
        parts = {"word/_rels/document.xml.rels": b'<Relationships/>', "[Content_Types].xml": b'<Types/>'}
        for i in range(2):
            parts[f"word/f{i}.xml"] = f'<w:ftr xmlns:w="{W}"><w:p/></w:ftr>'.encode()
        self.assertIsNone(prepare_footers(None, {"f0": "f0.xml", "f1": "f1.xml"}, parts, sects))
        for i in range(2):
            self.assertTrue(has_page_field(etree.fromstring(parts[f"word/f{i}.xml"])))

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
