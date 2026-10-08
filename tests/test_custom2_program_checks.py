import unittest
from unittest.mock import patch

from reasoning_agent.custom2.program_checks import (
    check_expression, describe_checks, numeric_equalities, requested_checks,
)


class ProgramCheckTests(unittest.TestCase):
    def test_exact_arithmetic_and_combinatorics(self):
        examples = {
            "1/3 + 2/3 == 1": "True",
            "comb(11, 3)": "165",
            "factorial(6)": "720",
            "gcd(54, 24)": "6",
            "2**(-3)": "1/8",
            "abs(-8) + 5//2 + 5%2": "11",
        }
        for expression, expected in examples.items():
            with self.subTest(expression=expression):
                check = check_expression(expression)
                self.assertEqual(check.status, "evaluated")
                self.assertEqual(check.result, expected)

    def test_bounded_enumeration_and_counterexamples(self):
        examples = {
            "sum(value * value for value in range(6))": "55",
            "all(value % 2 == 0 for value in range(6))": "False",
            "[value for value in range(6) if value % 2 != 0]": "(1, 3, 5)",
            "len({left + right for left in range(3) for right in range(3)})": "5",
            "sum(1 for pair in product(range(3), range(3)) if pair[0] < pair[1])": "3",
            "sum(1 for left, right in product(range(3), range(3)) if left < right)": "3",
            "sum(1 if value % 2 == 0 else 0 for value in range(6))": "3",
            "max([1, 8, 3]) == 8 and min([1, 8, 3]) == 1": "True",
        }
        for expression, expected in examples.items():
            with self.subTest(expression=expression):
                self.assertEqual(check_expression(expression).result, expected)

    def test_no_arbitrary_python_execution(self):
        expressions = [
            '__import__("os").getcwd()', 'open("/tmp/example")',
            "(1).__class__", "globals()", "eval('2+2')", "exec('pass')",
            "(lambda: 5)()", "value := 5", "[1] * 1000000", "range(stop=4)",
            "sum(value for value in unknown)",
        ]
        with patch("builtins.eval", side_effect=AssertionError("禁止 eval")), patch(
            "builtins.exec", side_effect=AssertionError("禁止 exec"),
        ):
            for expression in expressions:
                with self.subTest(expression=expression):
                    self.assertEqual(check_expression(expression).status, "unsupported")

    def test_resource_limits_are_reported_not_mathematical_failures(self):
        for expression in [
            "2**100000000", "2**(2**100)", "factorial(10000000)",
            "len(range(1000000000))", "comb(1000000000, 3)",
            "len(product(range(1000), range(1000)))",
            "sum(left*right for left in range(1000) for right in range(1000))",
        ]:
            with self.subTest(expression=expression):
                check = check_expression(expression)
                self.assertEqual(check.status, "limit")
                self.assertFalse(check.contradiction)
        self.assertEqual(check_expression("1+2", max_steps=1).status, "limit")
        self.assertEqual(check_expression("1+2", timeout=0).status, "limit")

    def test_errors_and_approximate_numbers_do_not_become_false(self):
        for expression in ["1/0", "factorial(-1)", "[1][4]"]:
            self.assertEqual(check_expression(expression).status, "error")
        self.assertEqual(check_expression("0.1+0.2==0.3").status, "unsupported")

    def test_extracts_only_explicit_numeric_equalities(self):
        text = r"计算 $\binom{8}{2}=28$ 和 $\frac{1}{3}+\frac{2}{3}=1$。变量 $value+2=3$ 不计算。"
        expressions = numeric_equalities(text)
        self.assertEqual(len(expressions), 2)
        self.assertTrue(all(check_expression(expression).result == "True" for expression in expressions))
        self.assertEqual(numeric_equalities("普通文字 value+2=3。"), [])
        self.assertEqual(numeric_equalities(r"$2+3\ne6$"), [])
        self.assertTrue(check_expression("2+3==6", "numeric_equality").contradiction)
        self.assertFalse(check_expression("2+3==6", "requested").contradiction)
        self.assertEqual(numeric_equalities(r"假设 $1=2$，得到矛盾。"), [])
        self.assertEqual(numeric_equalities(r"Suppose $1=2$. This is impossible."), [])
        self.assertEqual(numeric_equalities(r"计算 \(7*8=56\)。"), ["7*8==56"])
        expressions = numeric_equalities(r"$\boxed{7\times8=55}$")
        self.assertTrue(check_expression(expressions[0], "numeric_equality").contradiction)

    def test_requests_are_explicit_bounded_and_deduplicated(self):
        text = "```python\nopen('file')\n```\n```check\n2+3\n2+3\n4+5\n```"
        self.assertEqual(requested_checks(text), ["2+3", "4+5"])
        self.assertEqual(len(requested_checks("```check\n1\n2\n3\n4\n5\n```")), 4)
        self.assertIn("未执行", describe_checks([]))
        self.assertIn("不是证明", describe_checks([check_expression("2+3")]))


if __name__ == "__main__":
    unittest.main()
