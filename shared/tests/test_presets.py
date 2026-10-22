import json, pathlib, unittest

D = json.loads((pathlib.Path(__file__).parent.parent / "presets.json").read_text())
S, P = D["settings"], D["presets"]
ORDER = ["usability", "medium", "maximum"]


class PresetTests(unittest.TestCase):
    def test_three_modes_in_display_order(self):
        self.assertEqual(set(P), set(ORDER))
        self.assertEqual(D["order"], ORDER)

    def test_recommended_is_medium(self):
        self.assertEqual(D["recommended"], "medium")

    def test_complete_and_valid(self):
        for name, p in P.items():
            self.assertEqual(set(p), set(S), name)
            for k, v in p.items():
                self.assertIn(v, S[k]["values"], f"{name}.{k}")

    def test_cookie_rule(self):
        # user decision: usability and medium keep cookies after close; maximum deletes them at close
        self.assertFalse(P["usability"]["session_only_cookies"])
        self.assertFalse(P["medium"]["session_only_cookies"])
        self.assertTrue(P["maximum"]["session_only_cookies"])

    def test_blocker_level_not_a_setting(self):
        # uBlock Origin stays at its defaults in every mode
        self.assertNotIn("blocker_level", S)

    def test_security_floor(self):
        for name, p in P.items():
            for k, d in S.items():
                if d.get("floor"):
                    self.assertTrue(p[k], f"{name}.{k}")

    def test_no_mode_enables_optional_telemetry(self):
        for p in P.values():
            self.assertFalse(p["optional_telemetry"])

    def test_monotonic_ladder(self):
        for k, d in S.items():
            if not d["ordinal"]:
                continue
            idx = [d["values"].index(P[n][k]) for n in ORDER]
            self.assertEqual(idx, sorted(idx), k)

    def test_every_used_value_has_visible_explanation(self):
        # the chooser shows what each mode does, so no used value may lack text
        for name, p in P.items():
            for k, v in p.items():
                self.assertTrue(S[k]["effects"].get(json.dumps(v)), f"{name}.{k}={v}")
            self.assertTrue(all(D["meta"][name].values()), name)
        for k, d in S.items():
            self.assertTrue(d["label"], k)


if __name__ == "__main__":
    unittest.main()
