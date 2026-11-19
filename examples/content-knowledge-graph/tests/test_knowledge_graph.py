"""Offline smoke tests; run: python3 -m unittest discover -s tests -v"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "knowledge_graph.py"
spec = importlib.util.spec_from_file_location("content_graph", MODULE_PATH)
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)

class ContentGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.src = self.root / "documents"
        self.src.mkdir()
        self.doc = self.src / "example.md"
        self.doc.write_text("问题：如何提高复用率？\n观点：记录来源与证据。\n方案：做索引。\n", encoding="utf-8")
        self.db = self.root / "workspace"

    def tearDown(self):
        self.temp.cleanup()

    def test_ingest_extract_validate_idempotence(self):
        self.assertEqual(graph.ingest(self.db, self.src)["total_sources"], 1)
        self.assertEqual(graph.extract(self.db, "markers", "", "", False)["active_nodes"], 3)
        self.assertEqual(graph.extract(self.db, "markers", "", "", False)["new_nodes"], 0)
        self.assertTrue(graph.validate(self.db)["ok"])
        self.assertEqual(len(graph.store(self.db)[1]), 3)

    def test_approval_link_and_render(self):
        graph.ingest(self.db, self.src)
        graph.extract(self.db, "markers", "", "", False)
        units = graph.store(self.db)[1]
        q = next(x for x in units if x.startswith("QST"))
        o = next(x for x in units if x.startswith("OPI"))
        with self.assertRaises(ValueError):
            graph.link(self.db, q, "回应", o, "缺审核")
        graph.approve(self.db, q)
        graph.approve(self.db, o)
        graph.link(self.db, q, "回应", o, "人工校验")
        self.assertEqual(graph.validate(self.db)["links"], 1)
        page = self.root / "view.html"
        out = self.root / "outline.md"
        self.assertEqual(graph.graph(self.db, page)["nodes_displayed"], 3)
        self.assertEqual(graph.assemble(self.db, out, False)["included_nodes"], 2)
        self.assertIn("<svg", page.read_text(encoding="utf-8"))
        self.assertIn("人工校验", out.read_text(encoding="utf-8"))

    def test_update_marks_old_node_stale(self):
        graph.ingest(self.db, self.src)
        graph.extract(self.db, "markers", "", "", False)
        before = set(graph.store(self.db)[1])
        self.doc.write_text("问题：另一问题？\n观点：记录来源与证据。\n", encoding="utf-8")
        graph.ingest(self.db, self.src)
        graph.extract(self.db, "markers", "", "", False)
        units = graph.store(self.db)[1]
        self.assertTrue(any(units[x]["stale"] for x in before))
        self.assertEqual(graph.validate(self.db)["approved_active"], 0)

    def test_blocks_secrets_and_unapproved_ai_transfer(self):
        (self.src / "secret.md").write_text("api_key = demo\n观点：私人信息\n", encoding="utf-8")
        self.assertEqual(graph.ingest(self.db, self.src)["total_sources"], 1)
        with self.assertRaises(ValueError):
            graph.extract(self.db, "ai", "some-model", "https://api.example.com/v1", False)

if __name__ == "__main__":
    unittest.main()
