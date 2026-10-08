"""AST-to-SymPy construction. Never eval, sympify or parse_expr user strings."""

import ast
import io
import re
import tokenize


class PolicyRejected(ValueError):
    pass


FUNCTIONS = {"sin": 1, "cos": 1, "tan": 1, "exp": 1, "log": 1,
             "sqrt": 1, "Abs": 1, "Eq": 2}


def parse(expression, variables):
    try:
        for token in tokenize.generate_tokens(io.StringIO(expression).readline):
            if token.type == tokenize.NUMBER:
                if (not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", token.string)
                        or sum(char.isdigit() for char in token.string) > 100):
                    raise PolicyRejected("numeric_literal_limit")
                exponent = re.search(r"[eE]([+-]?\d+)$", token.string)
                if exponent and abs(int(exponent.group(1))) > 100:
                    raise PolicyRejected("numeric_magnitude_limit")
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, tokenize.TokenError, RecursionError):
        raise PolicyRejected("invalid_expression") from None
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise PolicyRejected("node_limit")
    allowed = (ast.Expression, ast.Constant, ast.Name, ast.Load, ast.UnaryOp, ast.UAdd,
               ast.USub, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
               ast.Mod, ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Call)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise PolicyRejected("unsupported_syntax")
        if isinstance(node, ast.Constant) and type(node.value) not in {int, float}:
            raise PolicyRejected("unsupported_literal")
        if isinstance(node, ast.Name) and node.id not in {*variables, *FUNCTIONS}:
            raise PolicyRejected("undeclared_symbol")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name)
                or node.func.id not in FUNCTIONS or node.keywords
                or len(node.args) != FUNCTIONS[node.func.id]):
            raise PolicyRejected("unsupported_function")
        if isinstance(node, ast.Compare) and len(node.ops) != 1:
            raise PolicyRejected("chained_relation")
    return tree.body


def calculate(arguments):
    import sympy as sp

    variables = arguments["variables"]
    if set(variables).intersection(FUNCTIONS):
        raise PolicyRejected("reserved_symbol")
    tree = parse(arguments["expression"], variables)
    symbols = {name: sp.Symbol(name, **{flag: True for flag in arguments["assumptions"]})
               for name in variables}
    functions = {name: getattr(sp, name) for name in FUNCTIONS}
    operators = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
                 ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
                 ast.Mod: sp.Mod}
    relations = {ast.Eq: sp.Eq, ast.NotEq: sp.Ne, ast.Lt: sp.Lt, ast.LtE: sp.Le,
                 ast.Gt: sp.Gt, ast.GtE: sp.Ge}

    def build(node):
        if isinstance(node, ast.Constant):
            # The validated numeric token is converted to an exact decimal Rational.
            text = ast.get_source_segment(arguments["expression"], node)
            value = sp.Rational(text)
            if max(value.p.bit_length(), value.q.bit_length()) > 4096:
                raise PolicyRejected("numeric_magnitude_limit")
            return value
        if isinstance(node, ast.Name) and node.id in symbols:
            return symbols[node.id]
        if isinstance(node, ast.UnaryOp):
            value = build(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = build(node.left), build(node.right)
            if isinstance(node.op, ast.Pow):
                if not right.is_number or right.is_real is not True or abs(right) > 100:
                    raise PolicyRejected("exponent_limit")
                return left ** right
            return operators[type(node.op)](left, right)
        if isinstance(node, ast.Compare):
            return relations[type(node.ops[0])](build(node.left), build(node.comparators[0]))
        if isinstance(node, ast.Call):
            return functions[node.func.id](*[build(child) for child in node.args])
        raise PolicyRejected("invalid_symbol_use")

    expression = build(tree)
    operation = arguments["operation"]
    if operation == "solve":
        value = sp.solve(expression, symbols[variables[0]])
    elif operation == "differentiate":
        value = sp.diff(expression, symbols[variables[0]])
    elif operation == "integrate":
        value = sp.integrate(expression, symbols[variables[0]])
    elif operation == "numeric":
        value = sp.N(expression, 30)
    else:
        value = sp.simplify(expression)
    result = {"value": str(value), "normalized_expression": str(expression),
              "conditions": list(arguments["assumptions"]), "warnings": []}
    if any(len(result[key]) > 8000 for key in ("value", "normalized_expression")):
        raise PolicyRejected("result_limit")
    if operation in {"solve", "integrate"}:
        result["warnings"] = ["Local algebraic result only; inspect domains, excluded denominators and integration constants."]
    return result
