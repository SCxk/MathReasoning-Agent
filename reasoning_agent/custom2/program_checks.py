import ast
from dataclasses import dataclass
from fractions import Fraction
import itertools
import math
import re
import time


class CheckLimit(ValueError):
    pass


class UnsupportedCheck(ValueError):
    pass


@dataclass(frozen=True)
class ProgramCheck:
    expression: str
    source: str
    status: str
    result: str

    @property
    def contradiction(self) -> bool:
        return self.source == "numeric_equality" and self.status == "evaluated" and self.result == "False"


class BoundedCalculator:
    def __init__(self, max_steps: int = 20000, timeout: float = 1.0):
        self.remaining_steps = min(max(1, max_steps), 50000)
        self.deadline = time.monotonic() + min(max(0.0, timeout), 2.0)

    def _tick(self) -> None:
        self.remaining_steps -= 1
        if self.remaining_steps < 0 or time.monotonic() >= self.deadline:
            raise CheckLimit()

    def _bounded(self, value):
        if isinstance(value, (int, Fraction)):
            number = Fraction(value)
            if max(number.numerator.bit_length(), number.denominator.bit_length()) > 4096:
                raise CheckLimit()
        elif isinstance(value, (tuple, frozenset, range)):
            if len(value) > 2000:
                raise CheckLimit()
        else:
            raise UnsupportedCheck()
        return value

    def evaluate(self, expression: str):
        if len(expression) > 2000:
            raise CheckLimit()
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 500:
            raise CheckLimit()
        return self._eval(tree.body, {})

    def _eval(self, node, variables):
        self._tick()
        if isinstance(node, ast.Constant) and type(node.value) in {int, bool}:
            return self._bounded(node.value)
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            values = tuple(self._eval(item, variables) for item in node.elts)
            return self._bounded(frozenset(values) if isinstance(node, ast.Set) else values)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand, variables)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.USub):
                return self._bounded(-operand)
            if isinstance(node.op, ast.UAdd):
                return self._bounded(+operand)
        if isinstance(node, ast.BinOp):
            left = self._eval(node.left, variables)
            right = self._eval(node.right, variables)
            if not isinstance(left, (int, Fraction)) or not isinstance(right, (int, Fraction)):
                raise UnsupportedCheck()
            if isinstance(node.op, ast.Add):
                return self._bounded(left + right)
            if isinstance(node.op, ast.Sub):
                return self._bounded(left - right)
            if isinstance(node.op, ast.Mult):
                return self._bounded(left * right)
            if isinstance(node.op, ast.Div):
                return self._bounded(Fraction(left) / Fraction(right))
            if isinstance(node.op, ast.FloorDiv):
                return self._bounded(left // right)
            if isinstance(node.op, ast.Mod):
                return self._bounded(left % right)
            if isinstance(node.op, ast.Pow):
                base = Fraction(left)
                if type(right) is not int or abs(right) > 4096:
                    raise CheckLimit()
                if max(base.numerator.bit_length(), base.denominator.bit_length()) * abs(right) > 4096:
                    raise CheckLimit()
                return self._bounded(base ** right)
        if isinstance(node, ast.BoolOp):
            values = (self._eval(value, variables) for value in node.values)
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare):
            left = self._eval(node.left, variables)
            for operator, expression in zip(node.ops, node.comparators):
                right = self._eval(expression, variables)
                operations = {
                    ast.Eq: lambda: left == right, ast.NotEq: lambda: left != right,
                    ast.Lt: lambda: left < right, ast.LtE: lambda: left <= right,
                    ast.Gt: lambda: left > right, ast.GtE: lambda: left >= right,
                    ast.In: lambda: left in right, ast.NotIn: lambda: left not in right,
                }
                if type(operator) not in operations:
                    raise UnsupportedCheck()
                if not operations[type(operator)]():
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            branch = node.body if self._eval(node.test, variables) else node.orelse
            return self._eval(branch, variables)
        if isinstance(node, ast.Subscript):
            container = self._eval(node.value, variables)
            index = self._eval(node.slice, variables)
            if not isinstance(container, (tuple, range)) or type(index) is not int:
                raise UnsupportedCheck()
            return container[index]
        if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            if len(node.generators) > 3:
                raise CheckLimit()
            output = []

            def visit(position, scope):
                self._tick()
                if position == len(node.generators):
                    if len(output) >= 2000:
                        raise CheckLimit()
                    output.append(self._eval(node.elt, scope))
                    return
                generator = node.generators[position]
                if generator.is_async:
                    raise UnsupportedCheck()
                iterable = self._eval(generator.iter, scope)
                if not isinstance(iterable, (tuple, range, frozenset)):
                    raise UnsupportedCheck()
                for item in iterable:
                    self._tick()
                    child = dict(scope)
                    self._bind(generator.target, item, child)
                    if all(self._eval(condition, child) for condition in generator.ifs):
                        visit(position + 1, child)

            visit(0, variables)
            return self._bounded(frozenset(output) if isinstance(node, ast.SetComp) else tuple(output))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            arguments = [self._eval(argument, variables) for argument in node.args]
            return self._bounded(self._call(node.func.id, arguments))
        raise UnsupportedCheck()

    def _bind(self, target, value, scope):
        self._tick()
        if isinstance(target, ast.Name):
            scope[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, tuple) and len(target.elts) == len(value):
            for child, item in zip(target.elts, value):
                self._bind(child, item, scope)
            return
        raise UnsupportedCheck()

    def _call(self, name, arguments):
        if name == "range" and 1 <= len(arguments) <= 3 and all(type(value) is int for value in arguments):
            return range(*arguments)
        if name in {"comb", "factorial", "gcd"}:
            if any(type(value) is not int or abs(value) > 4096 for value in arguments):
                raise CheckLimit()
            if name == "factorial" and arguments and arguments[0] > 512:
                raise CheckLimit()
            return {"comb": math.comb, "factorial": math.factorial, "gcd": math.gcd}[name](*arguments)
        if name == "product" and 1 <= len(arguments) <= 3:
            if any(not isinstance(value, (tuple, range, frozenset)) for value in arguments):
                raise UnsupportedCheck()
            if math.prod(len(value) for value in arguments) > 2000:
                raise CheckLimit()
            return tuple(itertools.product(*arguments))
        if name in {"sum", "min", "max", "len", "all", "any"} and len(arguments) == 1:
            if not isinstance(arguments[0], (tuple, range, frozenset)):
                raise UnsupportedCheck()
            return {"sum": sum, "min": min, "max": max, "len": len, "all": all, "any": any}[name](arguments[0])
        if name == "abs" and len(arguments) == 1:
            return abs(arguments[0])
        raise UnsupportedCheck()


def check_expression(expression: str, source: str = "requested", *, max_steps: int = 20000, timeout: float = 1.0) -> ProgramCheck:
    try:
        value = BoundedCalculator(max_steps, timeout).evaluate(expression)
        result = str(value)
        if len(result) > 2000:
            raise CheckLimit()
        return ProgramCheck(expression, source, "evaluated", result)
    except CheckLimit:
        return ProgramCheck(expression, source, "limit", "资源限制，未完成验证")
    except (UnsupportedCheck, SyntaxError):
        return ProgramCheck(expression, source, "unsupported", "仅支持白名单数学表达式")
    except (ArithmeticError, ValueError, TypeError, IndexError, RecursionError):
        return ProgramCheck(expression, source, "error", "表达式无法计算，不能据此判定数学结论")


def requested_checks(text: str) -> list[str]:
    expressions = []
    for block in re.findall(r"```check[ \t]*\n([\s\S]*?)```", text, re.I):
        expressions.extend(line.strip() for line in block.splitlines() if line.strip())
    return list(dict.fromkeys(expressions))[:4]


def numeric_equalities(text: str) -> list[str]:
    text = re.sub(r"```[\s\S]*?```", "", text)
    formulas = re.finditer(
        r"\$\$([\s\S]*?)\$\$|(?<!\$)\$([^$\n]+)\$|\\\[([\s\S]*?)\\\]|\\\((.*?)\\\)", text,
    )
    expressions = []
    for match in formulas:
        context = text[max(0, match.start() - 60):match.start()] + text[match.end():match.end() + 40]
        if re.search(r"\b(?:suppose|assume|if|contradiction|impossible|false)\b|假设|反设|若|如果|矛盾|不成立|错误", context, re.I):
            continue
        formula = next((part for part in match.groups() if part), "").strip()
        if "=" not in formula or len(formula) > 500:
            continue
        formula = formula.replace(r"\times", "*").replace(r"\cdot", "*")
        for spacing in (r"\left", r"\right", r"\,", r"\!", r"\;", r"\quad"):
            formula = formula.replace(spacing, " ")
        for _ in range(4):
            formula = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", formula)
            formula = re.sub(r"\\binom\{([^{}]+)\}\{([^{}]+)\}", r"comb(\1,\2)", formula)
            formula = re.sub(r"\\boxed\{([^{}]+)\}", r"(\1)", formula)
        formula = formula.replace("^", "**").replace("{", "(").replace("}", ")")
        formula = formula.rstrip(".,; \n")
        if re.search(r"[^\d\s+*/%=().,\-comb]", formula):
            continue
        if not re.fullmatch(r"[^=]+(?:=[^=]+)+", formula):
            continue
        expressions.append(formula.replace("=", "=="))
    return list(dict.fromkeys(expressions))[:8]


def describe_checks(checks: list[ProgramCheck]) -> str:
    if not checks:
        return "未执行可用的程序计算；不得声称已经程序验证。"
    return "\n".join(
        f"[{check.source}/{check.status}] {check.expression} -> {check.result}" for check in checks
    ) + "\n这些结果仅验证所列表达式。建模、题意对应和一般性证明仍须核查；有限测试通过不是证明。"
