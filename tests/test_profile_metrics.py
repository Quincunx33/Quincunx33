import importlib.util
import unittest
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "update_id_dashboard.py"
SPEC = importlib.util.spec_from_file_location("profile_updater", MODULE_PATH)
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


class ProfileMetricsTests(unittest.TestCase):
    def test_forks_are_excluded_from_star_total_and_original_list(self):
        user = {"public_repos": 3, "followers": 8, "following": 4}
        repos = [
            {"name": "original", "stargazers_count": 7, "fork": False},
            {"name": "another", "stargazers_count": 2},
            {"name": "forked", "stargazers_count": 100, "fork": True},
        ]
        result = updater.calculate_metrics(user, repos)
        self.assertEqual(result["stars"], 9)
        self.assertEqual([r["name"] for r in result["original_repos"]], ["original", "another"])
        self.assertEqual(result["fork_count"], 1)

    def test_language_bytes_are_aggregated_and_forks_skipped(self):
        repos = [
            {"name": "one", "fork": False},
            {"name": "two", "fork": False},
            {"name": "fork", "fork": True},
        ]
        responses = {
            "https://api.github.com/repos/Quincunx33/one/languages": {"Rust": 100, "HTML": 20},
            "https://api.github.com/repos/Quincunx33/two/languages": {"Rust": 50, "CSS": 30},
        }
        called = []
        def fake_get(url):
            called.append(url)
            return responses[url]
        result = updater.aggregate_language_bytes(repos, fake_get)
        self.assertEqual(result, Counter({"Rust": 150, "HTML": 20, "CSS": 30}))
        self.assertEqual(len(called), 2)
        self.assertFalse(any("/fork/" in url for url in called))

    def test_svg_helpers_select_exact_nodes(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg"><text class="metric" x="10">old</text></svg>'
        )
        node = updater.find_node(root, "text", **{"class": "metric", "x": "10"})
        node.text = "new"
        self.assertEqual(updater.find_text(root, "new").text, "new")

    def test_language_and_project_visuals_are_valid_svg(self):
        languages = updater.render_languages_svg(Counter({"Rust": 90, "C++": 30}))
        atlas = updater.render_project_atlas({
            "original_repos": [
                {"language": "Rust"}, {"language": "Rust"},
                {"language": "C++"}, {"language": None},
            ]
        })
        self.assertTrue(ET.fromstring(languages).tag.endswith("svg"))
        self.assertTrue(ET.fromstring(atlas).tag.endswith("svg"))
        self.assertIn("75.0%", languages)
        self.assertIn("4 original public repositories", atlas)


if __name__ == "__main__":
    unittest.main()
