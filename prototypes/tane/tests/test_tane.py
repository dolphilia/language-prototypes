import io
from pathlib import Path
import subprocess
import sys
import unittest

import tane


ROOT = Path(__file__).resolve().parents[1]


class TaneTests(unittest.TestCase):
    def execute(self, source):
        output = io.StringIO()
        counters = tane.run(tane.compile_source(source), output)
        return output.getvalue(), counters

    def test_examples(self):
        for name, expected in (("countdown", "3\n2\n1\n"),
                               ("add", "5\n"), ("multiply", "12\n")):
            with self.subTest(name=name):
                source = (ROOT / "examples" / f"{name}.tane").read_text()
                self.assertEqual(self.execute(source)[0], expected)

    def test_zero_initialization_and_saturating_decrement(self):
        output, counters = self.execute("dec x\ndec x\nprint x")
        self.assertEqual(output, "0\n")
        self.assertEqual(counters["x"], 0)

    def test_zero_loop_skips_nested_body(self):
        source = "while x\ninc x\nwhile x\ninc x\nend\nend\nprint x"
        self.assertEqual(self.execute(source)[0], "0\n")

    def test_loop_observes_updated_condition(self):
        source = "inc x\nwhile x\ndec x\ninc y\nend\nprint y\nprint x"
        self.assertEqual(self.execute(source)[0], "1\n0\n")

    def test_multiplication_for_small_inputs(self):
        body = (ROOT / "examples" / "multiply.tane").read_text()
        body = body[body.index("while x"):]
        for x in range(6):
            for y in range(6):
                with self.subTest(x=x, y=y):
                    source = "inc x\n" * x + "inc y\n" * y + body + "\nprint y"
                    output, counters = self.execute(source)
                    self.assertEqual(output, f"{x * y}\n{y}\n")
                    self.assertEqual(counters.get("x", 0), 0)
                    self.assertEqual(counters.get("temporary", 0), 0)

    def test_comments_whitespace_and_case_sensitive_names(self):
        source = "# 注釈\r\n\tinc x_2 # 増加\r\n print x_2\r\n"
        self.assertEqual(self.execute(source)[0], "1\n")
        with self.assertRaises(tane.TaneError):
            tane.compile_source("inc X")

    def test_runs_start_with_fresh_counters(self):
        code = tane.compile_source("inc x\nprint x")
        for _ in range(2):
            output = io.StringIO()
            tane.run(code, output)
            self.assertEqual(output.getvalue(), "1\n")

    def test_empty_program(self):
        self.assertEqual(self.execute("# empty\n"), ("", {}))

    def test_invalid_source_has_line_number(self):
        for source, line in (("end", 1), ("while x", 1),
                             ("inc x\nwhile y\nwhile z\nend", 2),
                             ("inc x 3", 1), ("print 1", 1),
                             ("inc x\nunknown y", 2), ("end x", 1),
                             ("inc _x", 1), ("inc 日本語", 1)):
            with self.subTest(source=source):
                with self.assertRaisesRegex(tane.TaneError, f"line {line}:"):
                    tane.compile_source(source)

    def test_cli_rejects_whole_program_before_execution(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tane.py"), "/dev/stdin"],
            input="inc x\nprint x\nwhile y\n", capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("line 3: while without end", result.stderr)


if __name__ == "__main__":
    unittest.main()
