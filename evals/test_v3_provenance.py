import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from showmewhy_runtime.compare import compare_runs
from showmewhy_runtime.provenance import build_graph, persist_graph, validate_graph
from showmewhy_runtime.viewer import render_html


class V3ProvenanceTests(unittest.TestCase):
    def _digest(self):
        return {
            "version": "2.0",
            "run_id": "run-012345abcdef",
            "tool_name": "Bash",
            "kind": "test",
            "status": "failed",
            "summary": "pytest: 1 failed, 127 passed",
            "findings": ["FAILED tests/test_auth.py::test_expired_session"],
            "caveats": [],
            "raw_ref": "evidence://sha256/" + "a" * 64,
            "raw_tokens": 2000,
            "digest_tokens": 100,
            "tokens_avoided": 1900,
            "compression_pct": 95.0,
            "parser": {"name": "pytest", "confidence": "high", "complete": True},
        }

    def test_graph_has_stable_addresses(self):
        graph = build_graph(self._digest())
        addresses = {node["address"] for node in graph["nodes"]}
        self.assertIn("evidence://sha256/" + "a" * 64 + "#tool_response", addresses)
        self.assertIn("run://run-012345abcdef#summary", addresses)
        self.assertEqual(graph["confidence"], "HIGH")

    def test_graph_is_deterministic(self):
        self.assertEqual(build_graph(self._digest())["graph_id"], build_graph(self._digest())["graph_id"])
        self.assertEqual(build_graph(self._digest())["nodes"], build_graph(self._digest())["nodes"])

    def test_causation_requires_basis(self):
        graph = build_graph(self._digest())
        edge = dict(graph["edges"][0])
        edge["type"] = "CAUSED_BY"
        graph["edges"] = [edge]
        with self.assertRaises(ValueError):
            validate_graph(graph)
        edge["meta"] = {"causal_basis": "controlled regression test"}
        validate_graph(graph)

    def test_persistence(self):
        graph = build_graph(self._digest())
        with tempfile.TemporaryDirectory() as td:
            path = persist_graph(graph, td)
            self.assertTrue(path.exists())

    def test_run_comparison(self):
        before = dict(self._digest())
        after = dict(before)
        after["run_id"] = "run-fedcba543210"
        after["status"] = "passed"
        after["tokens_avoided"] = 2100
        after["compression_pct"] = 96.0
        after["findings"] = []
        delta = compare_runs(before, after)
        self.assertTrue(delta["status_changed"])
        self.assertEqual(delta["tokens_avoided_delta"], 200)
        self.assertIn("FAILED tests/test_auth.py::test_expired_session", delta["resolved_findings"])

    def test_static_viewer_escapes_content(self):
        graph = build_graph(self._digest())
        graph["nodes"][0]["label"] = "<script>alert(1)</script>"
        rendered = render_html(graph)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)


if __name__ == "__main__":
    unittest.main()
