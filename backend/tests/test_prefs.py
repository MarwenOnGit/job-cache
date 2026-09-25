import os
import tempfile
import unittest

import prefs as prefs_mod
from normalize import TARGET_CITIES


class TestDefaults(unittest.TestCase):
    def test_empty_means_all(self):
        # An empty preference is the broadest search: every location + every family.
        self.assertEqual(prefs_mod.target_locations(prefs_mod.DEFAULTS), set(TARGET_CITIES))
        self.assertEqual(prefs_mod.target_role_families(prefs_mod.DEFAULTS),
                         {"offensive_security", "appsec", "blue_team", "cloud_grc",
                          "security_other", "ai_ml", "swe"})

    def test_specific_selection(self):
        prefs = {"locations": ["paris", "remote-eu"], "role_families": ["offensive_security"]}
        self.assertEqual(prefs_mod.target_locations(prefs), {"paris", "remote-eu"})
        self.assertEqual(prefs_mod.target_role_families(prefs), {"offensive_security"})


class TestNormalize(unittest.TestCase):
    def test_drops_unknown_tokens(self):
        raw = {"locations": ["paris", "atlantis", "berlin"],
               "role_families": ["swe", "astronaut"],
               "titles": [" Backend Engineer ", "backend engineer"],  # dedupe case-insensitive
               "keywords": ["Python", "python", ""]}
        p = prefs_mod._normalize(raw)
        self.assertEqual(p["locations"], ["paris", "berlin"])
        self.assertEqual(p["role_families"], ["swe"])
        self.assertEqual(p["titles"], ["Backend Engineer"])
        self.assertEqual(p["keywords"], ["Python"])

    def test_extra_keywords_merges_titles(self):
        prefs = {"keywords": ["Rust", "python"], "titles": ["Backend Engineer", "rust"]}
        kw = prefs_mod.extra_keywords(prefs)
        self.assertIn("rust", kw)
        self.assertIn("python", kw)
        self.assertIn("backend engineer", kw)
        self.assertEqual(len(kw), len(set(kw)))            # deduped, all lowercase


class TestRoundTrip(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            orig = prefs_mod.PREFS_JSON_PATH
            prefs_mod.PREFS_JSON_PATH = os.path.join(d, "preferences.json")
            try:
                self.assertFalse(os.path.exists(prefs_mod.PREFS_JSON_PATH))
                self.assertEqual(prefs_mod.load_structured(), prefs_mod.DEFAULTS)
                prefs_mod.save_structured({"locations": ["london"], "keywords": ["kafka"]})
                loaded = prefs_mod.load_structured()
                self.assertEqual(loaded["locations"], ["london"])
                self.assertEqual(loaded["keywords"], ["kafka"])
            finally:
                prefs_mod.PREFS_JSON_PATH = orig


if __name__ == "__main__":
    unittest.main()
