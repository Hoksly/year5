import itertools
import os
import re
from collections import OrderedDict

# Порядок бітів (зліва направо) за замовчуванням. Можна змінити, наприклад ['x','y','z','u']
DEFAULT_VAR_ORDER = ['x', 'y', 'z', 'u']

def calculate_dot_product(a, Z):
    """Обчислює скалярний добуток вектора коефіцієнтів 'a' та вхідного вектора 'Z'."""
    q = len(a)
    return sum(a[i] * Z[i] for i in range(q))


class ProblemSpec:
    """Парсер виразу виду: "x + 2y + u - 3z = 1" з файлу.

    Зберігає порядок змінних (var_order), список коефіцієнтів у цьому порядку
    (coefficients) та праву частину рівняння (constant_b).
    """
    def __init__(self, var_order, coefficients, constant_b):
        self.var_order = list(var_order)
        self.coefficients = list(coefficients)
        self.constant_b = int(constant_b)

    @staticmethod
    def parse_expression(expr_line: str):
        # видаляємо пробіли
        s = expr_line.strip()
        if '=' not in s:
            raise ValueError('Expression must contain =')
        lhs, rhs = s.split('=', 1)
        lhs = lhs.replace(' ', '')
        rhs = rhs.strip()
        const = int(rhs)

        # знайдемо терми: ([+-]?digits*)(var)
        token_re = re.compile(r'([+-]?\d*)([A-Za-z]\w*)')
        coeffs = OrderedDict()
        for m in token_re.finditer(lhs):
            coef_str = m.group(1)
            var = m.group(2)
            if coef_str in ('', '+', None):
                coef = 1
            elif coef_str == '-':
                coef = -1
            else:
                coef = int(coef_str)
            coeffs[var] = coeffs.get(var, 0) + coef

        var_order = list(coeffs.keys())
        coefficients = [coeffs[v] for v in var_order]
        return ProblemSpec(var_order, coefficients, const)

    @staticmethod
    def from_file(path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # first non-empty, non-comment line is the expression
                return ProblemSpec.parse_expression(line)
        raise ValueError('No expression found in file')

class Dfa:
    """Клас для представлення та візуалізації детерміністичного скінченного автомата."""
    def __init__(self, states, initial_state, final_states, transitions, variable_names=()):
        self.states = set(states)
        self.initial_state = initial_state
        self.final_states = set(final_states)
        self.transitions = transitions
        self.variable_names = tuple(variable_names)

    def to_dict(self):
        return {
            'states': self.states,
            'initial_state': self.initial_state,
            'final_states': self.final_states,
            'transitions': self.transitions,
            'variable_names': self.variable_names
        }

    def print_summary(self):
        print("\n" + "="*50)
        print("РЕЗУЛЬТАТ ПОБУДОВИ ДСА (АПР-ДСА)")
        print("==================================================")
        print(f"Кількість станів (A): {len(self.states)}")
        print(f"Множина станів: {sorted(list(self.states))}")
        print(f"Початковий стан: {self.initial_state}")
        print(f"Заключні стани (F): {self.final_states}")
        print("\nТАБЛИЦЯ ПЕРЕХОДІВ (f):")
        self.print_transitions()

    def print_transitions(self):
        var_names = self.variable_names
        for s, transitions_s in sorted(self.transitions.items()):
            print(f"\nСтан {s}:")
            for Z, j in sorted(transitions_s.items()):
                try:
                    bits_str = ''.join(str(int(b)) for b in Z)
                    num = int(bits_str, 2)
                    sub_map = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'}
                    sub = ''.join(sub_map.get(ch, ch) for ch in str(num))
                    zi = f'z{sub}'
                except Exception:
                    bits_str = str(Z)
                    zi = ''

                input_str = ', '.join(f'{name}={bit}' for name, bit in zip(var_names, Z))
                if zi:
                    print(f"  Вхід {bits_str} ({input_str}) -> {zi} -> Стан {j}")
                else:
                    print(f"  Вхід {bits_str} ({input_str}) -> Стан {j}")

    def to_dot_text(self):
        """Повернути DOT-представлення автомата."""
        lines = []
        lines.append('digraph G {')
        lines.append('  rankdir=LR;')
        lines.append('  size="10,6";')
        lines.append('  node [shape=circle];')

        states = sorted(self.states)
        finals = set(self.final_states)

        for s in states:
            if s in finals:
                lines.append(f'  "{s}" [shape=doublecircle];')
            else:
                lines.append(f'  "{s}" [shape=circle];')

        # invisible start
        lines.append('  "__start__" [shape=point,label=""];')
        lines.append(f'  "__start__" -> "{self.initial_state}";')

        # edges
        for src in states:
            trans_map = self.transitions.get(src, {})
            for Z, dst in sorted(trans_map.items()):
                try:
                    if hasattr(Z, '__iter__') and not isinstance(Z, (str, bytes)):
                        bits_str = ''.join(str(int(b)) for b in Z)
                        try:
                            num = int(bits_str, 2)
                        except Exception:
                            num = None
                        if num is not None:
                            sub_map = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'}
                            sub = ''.join(sub_map.get(ch, ch) for ch in str(num))
                            lbl = f"z{sub}"
                        else:
                            lbl = bits_str
                    else:
                        lbl = str(Z)
                except Exception:
                    lbl = str(Z)
                lines.append(f'  "{src}" -> "{dst}" [label="{lbl}"];')

        lines.append('}')
        return "\n".join(lines)

    def render(self, name='dfa_output', fmt='svg'):
        """Спробувати відрендерити DOT у SVG/PNG через python-graphviz, інакше записати .dot файл."""
        dot_text = self.to_dot_text()
        try:
            import graphviz
            dot = graphviz.Source(dot_text)
            out_path = dot.render(filename=name, format=fmt, cleanup=True)
            print(f"Візуалізація збережена у: {out_path}")
        except Exception as e:
            dot_file = f"{name}.dot"
            with open(dot_file, 'w', encoding='utf-8') as f:
                f.write(dot_text)
            print(f"Не вдалося автоматично відрендерити граф (error: {e}).")
            print(f"Записано DOT у файл: {dot_file}")
            print("Щоб згенерувати PNG локально, встановіть graphviz і виконайте:")
            print(f"  dot -Tpng {dot_file} -o {name}.png")


class AprDsa:
    """Клас, який інкапсулює параметри та побудову ДСА за алгоритмом АПР-ДСА."""
    def __init__(self, a, b, var_names=None):
        self.a = list(a)
        self.b = b
        self.q = len(a)
        self.var_names = tuple(var_names) if var_names is not None else None

    def build(self) -> Dfa:
        # Визначаємо імена змінних/порядок бітів
        if self.var_names is None:
            if len(DEFAULT_VAR_ORDER) >= self.q:
                var_names = tuple(DEFAULT_VAR_ORDER[:self.q])
            else:
                var_names = tuple(f'z{i}' for i in range(self.q))
        else:
            var_names = tuple(self.var_names)

        states = set()
        final_states = {0}
        initial_state = self.b
        working_set = {initial_state}
        states.add(initial_state)
        transitions = {}

        input_alphabet = list(itertools.product((0, 1), repeat=self.q))

        print(f"Запущено АПР-ДСА для коефіцієнтів a={self.a}, константи b={self.b}")
        print(f"Кількість змінних q={self.q}. Вхідний алфавіт має {2**self.q} символів.\n")

        while working_set:
            s = working_set.pop()
            if s not in transitions:
                transitions[s] = {}

            for Z in input_alphabet:
                s_dot_Z = calculate_dot_product(self.a, Z)
                numerator = s - s_dot_Z
                if numerator % 2 == 0:
                    j = numerator // 2
                    transitions[s][Z] = j
                    if j not in states:
                        states.add(j)
                        working_set.add(j)

        return Dfa(states=states, initial_state=initial_state, final_states=final_states.intersection(states),
                   transitions=transitions, variable_names=var_names)


class Transformer:
    """Місце для логіки трансформацій автоматів (обгортка для AprDsa.build)."""
    @staticmethod
    def apr_to_dfa(apr: AprDsa) -> Dfa:
        return apr.build()

from argparse import ArgumentParser

if __name__ == '__main__':
    parser = ArgumentParser(description="Побудова ДСА за алгоритмом АПР-ДСА з файлу специфікації.")
    parser.add_argument('input_file', help='Шлях до файлу зі специфікацією задачі (наприклад, problem.txt)')
    args = parser.parse_args()
    file = args.input_file
    
    spec = ProblemSpec.from_file(file)
    coefficients = spec.coefficients
    constant_b = spec.constant_b

    apr = AprDsa(coefficients, constant_b)
    dfa = Transformer.apr_to_dfa(apr)


    dfa.print_summary()
    dfa.render(name='apr_dsa', fmt='svg')