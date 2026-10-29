import pathlib, re, unittest

ROOT = pathlib.Path(__file__).parent.parent.parent
CSS = (ROOT / "shared/design/tokens.css").read_text()
SRC = ROOT / "build/src"


def color_ids():
    # chrome://theme/colors.css names each ColorId kColorFooBar as --color-foo-bar.
    ids = set()
    for h in ("ui/color/color_id.h", "chrome/browser/ui/color/chrome_color_id.h"):
        for name in re.findall(r"\bE_CPONLY\((kColor\w+)|\bE\((kColor\w+)", (SRC / h).read_text()):
            n = (name[0] or name[1])[len("kColor"):]
            ids.add("--color-" + re.sub(r"(?<!^)(?=[A-Z])", "-", n).lower())
    return ids


class TokenTests(unittest.TestCase):
    @unittest.skipUnless((SRC / "ui/color/color_id.h").exists(), "needs build/src")
    def test_theme_colors_exist(self):
        ids = color_ids()
        used = set(re.findall(r"var\((--color-[a-z0-9-]+)", CSS))
        self.assertTrue(used)
        self.assertEqual(used - ids, set())

    def test_no_fixed_hue(self):
        # Only neutral white/black overlays may be literal; every hue comes from the theme.
        for rgb in re.findall(r"rgb\(([^)]*)\)", CSS):
            self.assertRegex(rgb, r"^(255 255 255|0 0 0) /", rgb)
        self.assertNotRegex(CSS, r"#[0-9a-fA-F]{3,8}\b|hsl\(")

    def test_tokens_defined_once_and_referenced_tokens_exist(self):
        root = CSS.split("@media")[0]
        defined = re.findall(r"(--hp-[a-z0-9-]+):", root)
        self.assertEqual(len(defined), len(set(defined)))
        self.assertEqual(set(re.findall(r"var\((--hp-[a-z0-9-]+)", CSS)) - set(defined), set())


if __name__ == "__main__":
    unittest.main()
