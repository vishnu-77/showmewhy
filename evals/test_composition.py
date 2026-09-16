from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "skills" / "showmewhy" / "scripts" / "compose.py"
SKILLS = ROOT / "skills"

spec = spec_from_file_location("showmewhy_compose", COMPOSE)
compose = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(compose)


class CompositionTests(unittest.TestCase):
    def test_exact_multi_slash_example_stays_under_showmewhy(self):
        plan = compose.parse_arguments(
            "/monitor /showmewhy /i-have-adhd -- investigate why auth tests fail"
        )
        self.assertEqual(plan.stages, ("monitor", "verify", "focus"))
        self.assertEqual(plan.task, "investigate why auth tests fail")
        self.assertEqual(
            plan.source_tokens,
            ("/monitor", "/showmewhy", "/i-have-adhd"),
        )

    def test_showmewhy_is_the_only_top_level_skill(self):
        skill_dirs = sorted(
            path.name for path in SKILLS.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )
        self.assertEqual(skill_dirs, ["showmewhy"])

    def test_focus_aliases_do_not_require_external_skill_invocation(self):
        for alias in ("/focus", "/concise", "/i-have-adhd"):
            with self.subTest(alias=alias):
                plan = compose.parse_arguments(f"{alias} -- explain the failure")
                self.assertEqual(plan.stages, ("verify", "focus"))

    def test_monitor_then_why_inserts_verification(self):
        plan = compose.parse_arguments("/monitor /why -- inspect the session")
        self.assertEqual(plan.stages, ("monitor", "verify", "why"))

    def test_task_separator_protects_slashes_in_task_text(self):
        plan = compose.parse_arguments(
            "/monitor /showmewhy -- inspect /tmp/build and src/auth/test.py"
        )
        self.assertEqual(plan.stages, ("monitor", "verify"))
        self.assertEqual(
            plan.task,
            "inspect /tmp/build and src/auth/test.py",
        )

    def test_legacy_mode_syntax_is_not_reinterpreted(self):
        plan = compose.parse_arguments("why investigate auth failures")
        self.assertEqual(plan.stages, ("verify",))
        self.assertEqual(plan.task, "why investigate auth failures")
        self.assertEqual(plan.source_tokens, ())

    def test_unknown_stage_fails_closed(self):
        with self.assertRaises(compose.CompositionError):
            compose.parse_arguments("/unknown -- inspect auth")

    def test_task_text_before_separator_fails_closed(self):
        with self.assertRaises(compose.CompositionError):
            compose.parse_arguments("/monitor investigate auth")

    def test_monitor_must_be_first(self):
        with self.assertRaises(compose.CompositionError):
            compose.parse_arguments("/showmewhy /monitor -- inspect auth")

    def test_only_one_presentation_stage_is_allowed(self):
        with self.assertRaises(compose.CompositionError):
            compose.parse_arguments("/showmewhy /why /focus -- inspect auth")

    def test_json_is_terminal(self):
        with self.assertRaises(compose.CompositionError):
            compose.parse_arguments("/showmewhy /json /impact -- inspect auth")

    def test_adjacent_aliases_are_deduplicated_after_normalisation(self):
        plan = compose.parse_arguments(
            "/showmewhy /verify /focus -- inspect auth"
        )
        self.assertEqual(plan.stages, ("verify", "focus"))


if __name__ == "__main__":
    unittest.main()
