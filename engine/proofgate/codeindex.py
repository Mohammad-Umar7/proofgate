"""tree-sitter index of C sources at any revision: functions, call graph, reachability."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser

from .repo import Repo

C_LANGUAGE = Language(tsc.language())

# Public entry points: if a function is reachable from one of these, user input can get there.
ENTRY_POINTS = (
    "curl_easy_perform",
    "curl_multi_perform",
    "curl_multi_socket_action",
    "curl_easy_setopt",
    "curl_url_set",
    "curl_easy_recv",
    "curl_easy_send",
    "curl_ws_recv",
    "curl_ws_send",
    "main",
)

SOURCE_DIRS = ("lib", "src")


@dataclass
class Function:
    name: str
    file: str
    start: int  # 1-based line numbers
    end: int
    static: bool
    calls: list[str] = field(default_factory=list)


def _parser() -> Parser:
    return Parser(C_LANGUAGE)


def _declarator_name(node: Node | None) -> str | None:
    """Walk declarator chains (pointer_declarator -> function_declarator -> identifier)."""
    while node is not None:
        if node.type == "identifier":
            return node.text.decode("utf-8", "replace")
        if node.type in ("function_declarator", "pointer_declarator", "parenthesized_declarator"):
            node = node.child_by_field_name("declarator")
            continue
        return None
    return None


def _is_function_decl(node: Node | None) -> bool:
    while node is not None:
        if node.type == "function_declarator":
            return True
        if node.type in ("pointer_declarator", "parenthesized_declarator"):
            node = node.child_by_field_name("declarator")
            continue
        return False
    return False


def _calls_in(body: Node) -> list[str]:
    calls: list[str] = []
    stack = [body]
    while stack:
        node = stack.pop()
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn is not None and fn.type == "identifier":
                calls.append(fn.text.decode("utf-8", "replace"))
        stack.extend(node.children)
    return calls


def _table_refs(root: Node) -> dict[str, str]:
    """Functions stored in global initializers, e.g. `struct Curl_cftype Curl_cft_x = {..., f}`.

    curl dispatches protocol handlers and connection filters through such tables, so a function
    with no direct caller is still reachable through the table that holds it.
    """
    refs: dict[str, str] = {}
    top: list[Node] = []
    pending = list(root.children)
    while pending:  # top-level declarations, including those inside #if/#ifdef blocks
        node = pending.pop()
        if node.type.startswith("preproc_") and node.type not in ("preproc_def", "preproc_call"):
            pending.extend(node.children)
        elif node.type == "declaration":
            top.append(node)
    for decl in top:
        for init in decl.children:
            if init.type != "init_declarator":
                continue
            holder = _declarator_name(init.child_by_field_name("declarator")) or "table"
            value = init.child_by_field_name("value")
            if value is None or value.type != "initializer_list":
                continue
            stack = [value]
            while stack:
                node = stack.pop()
                if node.type == "identifier":
                    refs.setdefault(node.text.decode("utf-8", "replace"), holder)
                stack.extend(node.children)
    return refs


_C_KEYWORDS = {
    "if", "for", "while", "switch", "return", "sizeof", "defined", "else", "do", "case",
}
_DEF_START = re.compile(r"^(?!static\s+const\b)[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\(")
_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
_TABLE = re.compile(
    r"^(?:static\s+)?(?:const\s+)?struct\s+\w+\s+(\w+)(?:\[\])?\s*=\s*\{(.*?)^\};", re.S | re.M
)
_IDENT = re.compile(r"\b([A-Za-z_]\w*)\b")


def _style_scan(source: str, path: str) -> tuple[list[Function], dict[str, str]]:
    """Fallback for macro-heavy code tree-sitter misparses, using curl's layout conventions:
    definitions start at column 0 and their braces sit alone at column 0."""
    lines = source.splitlines()
    found: list[Function] = []
    i = 0
    while i < len(lines):
        match = _DEF_START.match(lines[i])
        if match and not lines[i].rstrip().endswith(";") and match.group(1) not in _C_KEYWORDS:
            j = i
            while j < min(i + 12, len(lines) - 1) and lines[j] != "{" and not lines[j].endswith(";"):
                j += 1
            if lines[j] == "{":
                k = j + 1
                while k < len(lines) and lines[k] != "}":
                    k += 1
                body = "\n".join(lines[j:k])
                calls = sorted({c for c in _CALL.findall(body) if c not in _C_KEYWORDS})
                start = i
                if i > 0 and lines[i - 1] and not lines[i - 1].startswith((" ", "#", "/", "*", "}")):
                    start = i - 1  # return type on its own line
                found.append(
                    Function(
                        name=match.group(1),
                        file=path,
                        start=start + 1,
                        end=k + 1,
                        static=lines[start].startswith("static"),
                        calls=calls,
                    )
                )
                i = k + 1
                continue
        i += 1
    refs = {}
    for holder, block in _TABLE.findall(source):
        for ident in _IDENT.findall(block):
            refs.setdefault(ident, holder)
    return found, refs


def parse_functions(source: str, path: str, refs: dict[str, str] | None = None) -> list[Function]:
    functions = _tree_sitter_functions(source, path, refs)
    seen = {f.name for f in functions}
    extra, extra_refs = _style_scan(source, path)
    functions.extend(f for f in extra if f.name not in seen)
    if refs is not None:
        for name, holder in extra_refs.items():
            refs.setdefault(name, holder)
    return sorted(functions, key=lambda f: f.start)


def _tree_sitter_functions(
    source: str, path: str, refs: dict[str, str] | None = None
) -> list[Function]:
    tree = _parser().parse(source.encode("utf-8", "replace"))
    if refs is not None:
        refs.update(_table_refs(tree.root_node))
    out: list[Function] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":
            declarator = node.child_by_field_name("declarator")
            name = _declarator_name(declarator) if _is_function_decl(declarator) else None
            if name:
                is_static = any(
                    child.type == "storage_class_specifier" and child.text == b"static"
                    for child in node.children
                )
                body = node.child_by_field_name("body")
                out.append(
                    Function(
                        name=name,
                        file=path,
                        start=node.start_point[0] + 1,
                        end=node.end_point[0] + 1,
                        static=is_static,
                        calls=sorted(set(_calls_in(body))) if body is not None else [],
                    )
                )
            continue
        stack.extend(node.children)
    return sorted(out, key=lambda f: f.start)


class CodeIndex:
    """All functions in lib/ and src/ at one revision, with a name-resolved call graph."""

    def __init__(self, repo: Repo, rev: str) -> None:
        self.repo = repo
        self.rev = rev
        self.functions: list[Function] = []
        self.by_name: dict[str, list[Function]] = defaultdict(list)
        self.table_refs: dict[str, str] = {}  # function name -> dispatch table holding it
        cached = _load_cache(repo, rev)
        if cached is not None:
            self.functions, self.table_refs = cached
        else:
            files = [
                f
                for f in repo.ls(rev)
                if f.endswith(".c") and f.split("/", 1)[0] in SOURCE_DIRS
            ]
            for path, source in repo.show_many(rev, files).items():
                self.functions.extend(parse_functions(source, path, self.table_refs))
            _save_cache(repo, rev, self.functions, self.table_refs)
        for fn in self.functions:
            self.by_name[fn.name].append(fn)
        self.table_refs = {k: v for k, v in self.table_refs.items() if k in self.by_name}
        self.callers: dict[str, set[str]] = defaultdict(set)
        for fn in self.functions:
            for callee in fn.calls:
                if callee in self.by_name:
                    self.callers[callee].add(fn.name)

    def lookup(self, name: str) -> list[Function]:
        return self.by_name.get(name, [])

    def near_names(self, name: str, limit: int = 3) -> list[str]:
        """Closest real function names, to show what a hallucinated name was probably mimicking."""
        from difflib import get_close_matches

        return get_close_matches(name, list(self.by_name), n=limit, cutoff=0.6)

    def path_from_entry(self, target: str, max_depth: int = 12) -> list[str] | None:
        """Shortest caller chain entry_point -> ... -> target, or None if unreachable.

        A function held in a dispatch table counts as reachable through that table; the chain
        then starts with a `table:<name>` element so the UI can say how it is reached.
        """
        if target not in self.by_name:
            return None
        if target in ENTRY_POINTS:
            return [target]
        seen = {target}
        queue: deque[list[str]] = deque([[target]])
        fallback: list[str] | None = None
        while queue:
            chain = queue.popleft()
            if len(chain) > max_depth:
                continue
            head = chain[-1]
            if fallback is None and head in self.table_refs:
                fallback = [f"table:{self.table_refs[head]}", *reversed(chain)]
            for caller in sorted(self.callers.get(head, ())):
                if caller in seen:
                    continue
                if caller in ENTRY_POINTS:
                    return [caller, *reversed(chain)]
                seen.add(caller)
                queue.append([*chain, caller])
        return fallback

    # -- export for the 3D code galaxy -----------------------------------

    def export_graph(self) -> dict:
        """Nodes laid out as file 'constellations' on a Fibonacci sphere, plus call edges."""
        files = sorted({fn.file for fn in self.functions})
        golden = math.pi * (3 - math.sqrt(5))
        centers: dict[str, tuple[float, float, float]] = {}
        for i, path in enumerate(files):
            y = 1 - (i / max(len(files) - 1, 1)) * 2
            r = math.sqrt(max(0.0, 1 - y * y))
            theta = golden * i
            radius = 60 if path.startswith("lib/") and path.count("/") == 1 else 85
            if path.startswith("src/"):
                radius = 40
            centers[path] = (math.cos(theta) * r * radius, y * radius, math.sin(theta) * r * radius)

        index: dict[tuple[str, str], int] = {}
        nodes = []
        per_file: dict[str, int] = defaultdict(int)
        counts: dict[str, int] = defaultdict(int)
        for fn in self.functions:
            counts[fn.file] += 1
        for fn in self.functions:
            k = per_file[fn.file]
            per_file[fn.file] += 1
            n = counts[fn.file]
            spread = 2.0 + math.sqrt(n) * 0.9
            # deterministic spiral inside the file's cluster
            phi = math.acos(1 - 2 * (k + 0.5) / n)
            theta = golden * k
            cx, cy, cz = centers[fn.file]
            pos = (
                round(cx + spread * math.sin(phi) * math.cos(theta), 2),
                round(cy + spread * math.cos(phi), 2),
                round(cz + spread * math.sin(phi) * math.sin(theta), 2),
            )
            index[(fn.file, fn.name)] = len(nodes)
            nodes.append(
                {
                    "id": len(nodes),
                    "name": fn.name,
                    "file": fn.file,
                    "line": fn.start,
                    "loc": fn.end - fn.start + 1,
                    "pos": pos,
                    "entry": fn.name in ENTRY_POINTS,
                }
            )
        first_by_name = {}
        for (path, name), idx in index.items():
            first_by_name.setdefault(name, idx)
        edges = []
        for fn in self.functions:
            src = index[(fn.file, fn.name)]
            for callee in fn.calls:
                # prefer a callee in the same file (static helpers), else the first definition
                dst = index.get((fn.file, callee), first_by_name.get(callee))
                if dst is not None and dst != src:
                    edges.append((src, dst))
        return {
            "project": self.repo.project,
            "rev": self.rev,
            "files": [{"path": p, "center": centers[p], "functions": counts[p]} for p in files],
            "nodes": nodes,
            "edges": edges,
        }


def _cache_file(repo: Repo, rev: str):
    from .config import get_settings

    folder = get_settings().cache_dir / "index"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{repo.project}-{rev.replace('/', '_')}.json"


def _load_cache(repo: Repo, rev: str) -> tuple[list[Function], dict[str, str]] | None:
    path = _cache_file(repo, rev)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Function(**f) for f in data["functions"]], data["table_refs"]


def _save_cache(repo: Repo, rev: str, functions: list[Function], refs: dict[str, str]) -> None:
    payload = {"functions": [asdict(f) for f in functions], "table_refs": refs}
    _cache_file(repo, rev).write_text(json.dumps(payload), encoding="utf-8")


@lru_cache(maxsize=4)
def get_index(repo: Repo, rev: str) -> CodeIndex:
    return CodeIndex(repo, rev)


def functions_in_file(repo: Repo, rev: str, path: str) -> list[Function]:
    return parse_functions(repo.show(rev, path), path)


def dump(obj: object) -> str:
    return json.dumps(asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj)
