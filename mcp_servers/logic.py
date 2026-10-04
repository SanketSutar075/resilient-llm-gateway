"""Pure logic shared by the MCP servers AND the local (offline) tools. No MCP import here, so it is easy to test."""
import ast
import math
import operator
import re
from pathlib import Path

# ---------- calculator: deterministic math, never done by the LLM ----------
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UN = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
        return _UN[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(b) > 100 or abs(a) > 1e6):
            raise ValueError("exponent too large")
        return _BIN[type(node.op)](a, b)
    raise ValueError("only numbers and + - * / // % ** ( ) are allowed")


def safe_calc(expression: str) -> str:
    if len(expression) > 200:
        raise ValueError("expression too long")
    try:
        value = _eval(ast.parse(expression.strip(), mode="eval"))
    except ZeroDivisionError:
        raise ValueError("division by zero")
    except SyntaxError:
        raise ValueError("invalid expression")
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("result is not a finite number")
        value = round(value, 10)
        value = int(value) if value.is_integer() else value
    return str(value)


# ---------- docs search: simple keyword scoring over paragraphs (RAG with embeddings comes later) ----------
def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class DocIndex:
    def __init__(self, docs_dir: str | Path):
        self.chunks: list[tuple[str, str]] = []  # (file name, paragraph)
        for p in sorted(Path(docs_dir).glob("*")):
            if p.suffix.lower() in (".md", ".txt"):
                for para in re.split(r"\n\s*\n", p.read_text(encoding="utf-8")):
                    para = para.strip()
                    if para and not (para.startswith("#") and "\n" not in para):  # skip heading-only chunks
                        self.chunks.append((p.name, para))
        n = max(len(self.chunks), 1)
        df: dict[str, int] = {}
        for _, c in self.chunks:
            for t in set(_tokens(c)):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + n / d) for t, d in df.items()}

    def search(self, query: str, k: int = 3) -> str:
        q = set(_tokens(query))
        scored = []
        for name, chunk in self.chunks:
            toks = _tokens(chunk)
            score = sum(toks.count(t) * self.idf.get(t, 0) for t in q)
            if score > 0:
                scored.append((score, name, chunk))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return "No matching documents found."
        return "\n\n".join(f"[{name}] {chunk}" for _, name, chunk in scored[:max(1, min(k, 5))])
