import sys
import re
import os
from typing import Tuple, Dict, Optional, List
import graphviz

# --- Data Structures (Graph Nodes) ---

class Term:
    """Represents a node in the labeled acyclic graph (DAG)."""
    def __init__(self, name: str, args: Optional[List['Term']] = None):
        self.name = name
        self.args = args if args is not None else []
        # A simple heuristic: variables are lowercase with no arguments
        self.is_var = (len(self.args) == 0 and self.name.islower())
        self.rep = self  # Representative for graph Identification (Union-Find)

    def find(self) -> 'Term':
        """Finds the actual representative of the node (resolving Identify merges)."""
        if self.rep != self:
            self.rep = self.rep.find()
        return self.rep

    def mark(self) -> str:
        """Returns the function symbol or variable name."""
        return self.name

    def sons(self) -> List['Term']:
        """Returns the children (arguments) of the node."""
        return self.args

    def __str__(self):
        if not self.args:
            return self.name
        return f"{self.name}({', '.join(str(a) for a in self.args)})"

# --- Algorithm Helper Functions ---

def identify(u: Term, v: Term):
    """Merges two nodes in the graph (Identify(G, u, v) from the text)."""
    u_root = u.find()
    v_root = v.find()
    if u_root != v_root:
        u_root.rep = v_root

def occurs_in(u: Term, v: Term) -> bool:
    """Checks if variable u occurs in term v to prevent cycles."""
    u = u.find()
    v = v.find()
    if u == v:
        return True
    for son in v.sons():
        if occurs_in(u, son):
            return True
    return False

def compose_substitutions(sig1: Dict[str, Term], sig2: Dict[str, Term]) -> Dict[str, Term]:
    """Composes two substitutions: sig1 * sig2"""
    res = {}
    
    def apply_subst(term: Term, sig: Dict[str, Term]) -> Term:
        term = term.find()
        if term.is_var:
            return sig.get(term.name, term)
        new_args = [apply_subst(a, sig) for a in term.args]
        return Term(term.name, new_args)

    for k, v in sig2.items():
        res[k] = apply_subst(v, sig1)
    for k, v in sig1.items():
        if k not in res:
            res[k] = v
    return res

# --- Core RG-Unify Algorithm ---

def rg_unify(v1: Term, v2: Term) -> Tuple[bool, Dict[str, Term]]:
    """
    Implementation of the RG-Unify algorithm from the textbook.
    Returns a tuple: (Success Boolean, Substitution Dictionary).
    """
    v1 = v1.find()
    v2 = v2.find()

    if v1 == v2:
        return True, {}

    # "if (one of terms u is variable, second term v is term) then..."
    if v1.is_var or v2.is_var:
        u, v = (v1, v2) if v1.is_var else (v2, v1)
        
        # "...if (u occurs in v) then bool = 0"
        if occurs_in(u, v):
            return False, {}
        else:
            # "...else \sigma = {u -> v}; bool = 1; Identify(G, u, v)"
            sigma = {u.name: v}
            identify(u, v)
            return True, sigma
    else:
        # "...if mark(v1) != mark(v2) then bool = 0"
        if v1.mark() != v2.mark() or len(v1.sons()) != len(v2.sons()):
            return False, {}
        else:
            # "...else let m - number of sons for node v1 and v2"
            m = len(v1.sons())
            k = 0
            bool_val = True
            sigma = {}
            
            # "...while (k < m and bool) do"
            while k < m and bool_val:
                t = v1.sons()[k].find()
                t_prime = v2.sons()[k].find()
                
                # "...if t != t' then (bool, \sigma_1) = Unify(t, t')"
                if t != t_prime:
                    bool_val, sigma1 = rg_unify(t, t_prime)
                    # "...if bool then \sigma = \sigma_1 * \sigma; fi"
                    if bool_val:
                        sigma = compose_substitutions(sigma1, sigma)
                k += 1
            return bool_val, sigma

# --- Parser and I/O ---

def tokenize_infix(s: str) -> List[str]:
    """
    Tokenizes an infix expression into a list of tokens.
    Handles multi-character identifiers/numbers and single-char operators.
    """
    token_re = re.compile(r'\s*([a-zA-Z_]\w*|\d+(?:\.\d+)?|[+\-*/^()])\s*')
    tokens = token_re.findall(s)
    return tokens


def parse_infix_term(s: str) -> Term:
    """
    Parses a standard infix expression string into a Term DAG.
    Supports operators: + - * / with standard precedence.
    Atoms are identifiers (variables/constants) and integer/float literals.

    Grammar (precedence, low to high):
        expr   -> term   (('+' | '-') term)*
        term   -> factor (('*' | '/') factor)*
        factor -> ATOM
               | '(' expr ')'
               | '-' factor          (unary minus, represented as unary_minus(x))
    """
    tokens = tokenize_infix(s)
    pos = [0]  # mutable position pointer

    def peek() -> Optional[str]:
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def consume() -> str:
        tok = tokens[pos[0]]
        pos[0] += 1
        return tok

    def parse_expr() -> Term:
        node = parse_term_expr()
        while peek() in ('+', '-'):
            op = consume()
            right = parse_term_expr()
            node = Term(op, [node, right])
        return node

    def parse_term_expr() -> Term:
        node = parse_factor()
        while peek() in ('*', '/'):
            op = consume()
            right = parse_factor()
            node = Term(op, [node, right])
        return node

    def parse_factor() -> Term:
        tok = peek()
        if tok is None:
            raise ValueError(f"Unexpected end of expression: '{s}'")
        if tok == '(':
            consume()  # '('
            node = parse_expr()
            if peek() != ')':
                raise ValueError(f"Expected ')' in expression: '{s}'")
            consume()  # ')'
            return node
        if tok == '-':
            # Unary minus
            consume()
            operand = parse_factor()
            return Term('unary_minus', [operand])
        # Atom: identifier or number
        consume()
        # Check for function-call notation: name(arg1, arg2, ...)
        if peek() == '(':
            consume()  # '('
            args = []
            if peek() != ')':
                args.append(parse_expr())
                while peek() == ',':
                    consume()  # ','
                    args.append(parse_expr())
            if peek() != ')':
                raise ValueError(f"Expected ')' after function arguments in: '{s}'")
            consume()  # ')'
            return Term(tok, args)
        return Term(tok)

    result = parse_expr()
    if pos[0] != len(tokens):
        raise ValueError(
            f"Unexpected token '{tokens[pos[0]]}' at position {pos[0]} in: '{s}'"
        )
    return result


# --- Visualization ---

_node_counter = 0

def _fresh_id(prefix: str = "n") -> str:
    global _node_counter
    _node_counter += 1
    return f"{prefix}_{_node_counter}"


def _add_term_to_graph(
    dot: graphviz.Digraph,
    term: Term,
    highlight_vars: Optional[set] = None,
    node_id: Optional[str] = None,
) -> str:
    """
    Recursively adds *term* to *dot* and returns the node id of the root.
    *highlight_vars*: set of variable names to colour differently (unified vars).
    """
    if node_id is None:
        node_id = _fresh_id()

    is_op = len(term.args) > 0
    label = term.name

    if is_op:
        # Operator / function node
        dot.node(node_id, label=label,
                 shape="ellipse",
                 style="filled",
                 fillcolor="#AED6F1",
                 fontname="Helvetica")
    elif highlight_vars and term.name in highlight_vars:
        # Variable that participates in the MGU
        dot.node(node_id, label=label,
                 shape="circle",
                 style="filled",
                 fillcolor="#A9DFBF",
                 fontname="Helvetica Bold")
    else:
        # Ordinary atom / constant
        dot.node(node_id, label=label,
                 shape="circle",
                 style="filled",
                 fillcolor="#FAD7A0",
                 fontname="Helvetica")

    for child in term.args:
        child_id = _add_term_to_graph(dot, child, highlight_vars)
        dot.edge(node_id, child_id)

    return node_id


def _make_equation_graph(
    term1: Term,
    term2: Term,
    title: str,
    highlight_vars: Optional[set] = None,
    mgu: Optional[Dict[str, Term]] = None,
) -> graphviz.Digraph:
    """
    Builds a Digraph for one equation (two trees + optional MGU substitution edges).
    """
    global _node_counter
    _node_counter = 0  # reset per graph so ids stay short

    dot = graphviz.Digraph(comment=title)
    dot.attr(rankdir="TB", label=title, labelloc="t",
             fontsize="16", fontname="Helvetica Bold",
             bgcolor="white")
    dot.attr("node", fontsize="13")
    dot.attr("edge", fontsize="10", color="#555555")

    # Left-hand side sub-graph
    with dot.subgraph(name="cluster_lhs") as lhs:
        lhs.attr(label="LHS", style="rounded,filled", fillcolor="#EBF5FB",
                 color="#2E86C1", fontname="Helvetica")
        lhs_root = _add_term_to_graph(lhs, term1, highlight_vars)

    # Right-hand side sub-graph
    with dot.subgraph(name="cluster_rhs") as rhs:
        rhs.attr(label="RHS", style="rounded,filled", fillcolor="#EAFAF1",
                 color="#1E8449", fontname="Helvetica")
        rhs_root = _add_term_to_graph(rhs, term2, highlight_vars)

    # Invisible edge to keep LHS left of RHS
    dot.edge(lhs_root, rhs_root, style="invis")

    # Draw MGU substitution arrows (var -> bound term) if provided
    if mgu:
        with dot.subgraph(name="cluster_mgu") as mg:
            mg.attr(label="MGU (σ)", style="rounded,filled",
                    fillcolor="#FEF9E7", color="#B7950B", fontname="Helvetica")
            prev_id: Optional[str] = None
            for var_name, bound_term in mgu.items():
                mgu_node_id = _fresh_id("mgu")
                bound_str = str(bound_term)
                mg.node(mgu_node_id,
                        label=f"{var_name}  →  {bound_str}",
                        shape="plaintext",
                        fontname="Courier",
                        fontsize="12")
                if prev_id:
                    mg.edge(prev_id, mgu_node_id, style="invis")
                prev_id = mgu_node_id

    return dot


def visualize_line(
    line_num: int,
    term1: Term,
    term2: Term,
    success: bool,
    mgu: Dict[str, Term],
    out_dir: str,
):
    """Saves input and output SVG files for one equation line."""
    os.makedirs(out_dir, exist_ok=True)

    # --- Input graph (plain, no highlighting) ---
    g_input = _make_equation_graph(
        term1, term2,
        title=f"Line {line_num} — Input",
    )
    input_path = os.path.join(out_dir, f"line_{line_num}_input")
    g_input.render(input_path, format="svg", cleanup=True)

    # --- Output graph ---
    if success:
        highlighted = set(mgu.keys())
        result_label = f"Line {line_num} — Output  [SUCCESS]"
    else:
        highlighted = None
        result_label = f"Line {line_num} — Output  [FAILED]"

    g_output = _make_equation_graph(
        term1, term2,
        title=result_label,
        highlight_vars=highlighted,
        mgu=mgu if success else None,
    )
    output_path = os.path.join(out_dir, f"line_{line_num}_output")
    g_output.render(output_path, format="svg", cleanup=True)

    print(f"  Saved: {input_path}.svg")
    print(f"  Saved: {output_path}.svg")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <input_file.txt>")
        sys.exit(1)

    filename = sys.argv[1]

    # Derive the visualization output directory:
    #   visualization/<stem_of_input_file>/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_stem = os.path.splitext(os.path.basename(filename))[0]
    vis_dir = os.path.join(script_dir, "visualization", input_stem)

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find file {filename}")
        sys.exit(1)

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # Assuming the input format separates the two terms with an equals sign '='
        if '=' not in line:
            print(f"Line {line_num} skipped (No '=' found): {line}")
            continue

        left_str, right_str = line.split('=', 1)
        try:
            term1 = parse_infix_term(left_str.strip())
            term2 = parse_infix_term(right_str.strip())
        except ValueError as e:
            print(f"Line {line_num} parse error: {e}")
            continue

        success, MGU = rg_unify(term1, term2)

        print(f"--- Line {line_num}: {line} ---")
        if success:
            formatted_mgu = ", ".join(f"{k} -> {v}" for k, v in MGU.items())
            print(f"Result: SUCCESS")
            print(f"MGU Substitution (σ): {{{formatted_mgu}}}")
        else:
            print(f"Result: FAILED to unify.")

        visualize_line(line_num, term1, term2, success, MGU, vis_dir)
        print()


if __name__ == "__main__":
    main()
