from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals" / "v5" / "pilot" / "manifest.json"


class V5PilotManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.tasks = cls.manifest["tasks"]

    def test_manifest_is_selection_only_and_non_claim_bearing(self) -> None:
        self.assertIs(self.manifest["claim_bearing"], False)
        self.assertEqual(self.manifest["execution_state"], "selection_only")
        self.assertEqual(len(self.tasks), 6)

    def test_tasks_and_upstream_prs_are_unique(self) -> None:
        task_ids = [task["task_id"] for task in self.tasks]
        upstream = [(task["repository"], task["pr_number"]) for task in self.tasks]
        shapes = [task["verification_shape"] for task in self.tasks]
        self.assertEqual(len(task_ids), len(set(task_ids)))
        self.assertEqual(len(upstream), len(set(upstream)))
        self.assertEqual(len(shapes), len(set(shapes)))

    def test_revisions_and_pr_urls_are_pinned(self) -> None:
        sha40 = re.compile(r"^[0-9a-f]{40}$")
        for task in self.tasks:
            with self.subTest(task=task["task_id"]):
                self.assertRegex(task["pre_fix_revision"], sha40)
                self.assertRegex(task["accepted_fix_revision"], sha40)
                owner_repo = task["repository"]
                self.assertEqual(
                    task["pr_url"],
                    f"https://github.com/{owner_repo}/pull/{task['pr_number']}",
                )

    def test_task_prompt_hashes_are_content_addressed(self) -> None:
        for task in self.tasks:
            with self.subTest(task=task["task_id"]):
                actual = hashlib.sha256(task["task_prompt"].encode("utf-8")).hexdigest()
                self.assertEqual(task["task_prompt_sha256"], actual)

    def test_every_task_has_reproducer_oracle_and_boundary(self) -> None:
        for task in self.tasks:
            with self.subTest(task=task["task_id"]):
                self.assertTrue(task["reproducer_command"].strip())
                self.assertTrue(task["oracle_refs"])
                self.assertTrue(task["production_paths"])
                self.assertTrue(task["upstream_test_paths"])
                self.assertTrue(task["expected_pre_fix"].strip())
                self.assertTrue(task["expected_post_fix"].strip())
                self.assertTrue(task["boundary_notes"].strip())

    def test_no_task_claims_execution_or_measured_results(self) -> None:
        forbidden = {
            "baseline",
            "showmewhy",
            "score",
            "metrics",
            "material_failure_recall",
            "verification_surface_reduction",
            "false_closure_rate",
        }
        for task in self.tasks:
            with self.subTest(task=task["task_id"]):
                self.assertEqual(task["selection_status"], "selected_unexecuted")
                self.assertEqual(task["execution_status"], "not_run")
                self.assertFalse(forbidden & set(task))

    def test_readme_preserves_publication_boundary(self) -> None:
        readme = (MANIFEST.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("we have not yet executed", readme)
        self.assertIn("oracle sources", readme)
        self.assertIn("No verification-reduction", readme)


if __name__ == "__main__":
    unittest.main()
