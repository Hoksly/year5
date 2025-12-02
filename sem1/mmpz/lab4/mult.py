import collections
import itertools
import os
from argparse import ArgumentParser

class Automaton:
    """Представляє скінченний Х-автомат (А, X, f, a0, F)."""
    
    def __init__(self, name, states, alphabet, initial_state, final_states, transitions):
        self.name = name
        self.states = states
        self.alphabet = alphabet
        self.initial_state = initial_state
        self.final_states = final_states
        self.transitions = transitions
        
    @staticmethod
    def from_file(filename):
        """Зчитує дані автомата зі вказаного файлу."""
        states = set()
        alphabet = set()
        initial_state = None
        final_states = set()
        transitions = {}

        try:
            with open(filename, 'r') as f:
                current_section = None
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line or raw_line.startswith('#'):
                        continue

                    # Підтримка двох форматів:
                    # 1) "section: value1, value2" — секція і значення в одному рядку
                    # 2) "section:" потім значення на наступних рядках
                    if ':' in raw_line:
                        key, rest = raw_line.split(':', 1)
                        key = key.strip()
                        rest = rest.strip()
                        current_section = key
                        if rest:
                            # Є значення після двокрапки — обробляємо їх як вміст секції
                            line = rest
                        else:
                            # Значення будуть на наступних рядках
                            continue
                    else:
                        line = raw_line

                    if current_section == 'states':
                        states.update(x.strip() for x in line.split(',') if x.strip())
                    elif current_section == 'alphabet':
                        alphabet.update(x.strip() for x in line.split(',') if x.strip())
                    elif current_section == 'initial':
                        initial_state = line.strip()
                    elif current_section == 'final':
                        final_states.update(x.strip() for x in line.split(',') if x.strip())
                    elif current_section == 'transitions':
                        # Очікуємо рівно 3 частини: q_current, symbol, q_next
                        parts = [part.strip() for part in line.split(',') if part.strip()]
                        if len(parts) == 3:
                            q, x, q_prime = parts
                            transitions[(q, x)] = q_prime
                        elif len(parts) > 0:
                            print(f"Попередження: Некоректний перехід у файлі {filename}: {line}")
        
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл {filename} не знайдено.")
        except Exception as e:
            raise Exception(f"Помилка при обробці файлу {filename}: {e}")

        # Визначаємо ім'я автомата з імені файлу (без розширення та шляху)
        import os
        name = os.path.splitext(os.path.basename(filename))[0]
        
        return Automaton(name, states, alphabet, initial_state, final_states, transitions)

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
        for (src, sym), dst in sorted(self.transitions.items()):
            lines.append(f'  "{src}" -> "{dst}" [label="{sym}"];')

        lines.append('}')
        return "\n".join(lines)

    def render(self, name=None, fmt='svg'):
        """Спробувати відрендерити DOT у SVG/PNG через python-graphviz, інакше записати .dot файл."""
        if name is None:
            name = self.name
        # Створити папку visualization, якщо її немає
        os.makedirs('visualization', exist_ok=True)
        filepath = os.path.join('visualization', name)
        dot_text = self.to_dot_text()
        try:
            import graphviz
            dot = graphviz.Source(dot_text)
            out_path = dot.render(filename=filepath, format=fmt, cleanup=True)
            print(f"Візуалізація автомата '{self.name}' збережена у: {out_path}")
        except Exception as e:
            dot_file = f"{filepath}.dot"
            with open(dot_file, 'w', encoding='utf-8') as f:
                f.write(dot_text)
            print(f"Не вдалося автоматично відрендерити граф для '{self.name}' (error: {e}).")
            print(f"Записано DOT у файл: {dot_file}")
            print("Щоб згенерувати PNG локально, встановіть graphviz і виконайте:")
            print(f"  dot -Tpng {dot_file} -o {filepath}.png")

    def __repr__(self):
        return f"Автомат('{self.name}', {len(self.states)} станів)"


class AsynchronousProductBuilder:
    """Реалізує алгоритм побудови Асинхронного добутку автоматів."""

    @staticmethod
    def build_product(automata_list):
        if not automata_list:
            raise ValueError("Мережа автоматів не може бути порожньою.")

        N = len(automata_list)
        
        full_alphabet = set()
        for A in automata_list:
            full_alphabet.update(A.alphabet)
        
        state_combinations = list(itertools.product(*(A.states for A in automata_list)))
        
        new_states = set() 
        new_transitions = {}
        
        initial_state = tuple(A.initial_state for A in automata_list)
        
        queue = collections.deque([initial_state])
        new_states.add(initial_state)

        while queue:
            current_state_tuple = queue.popleft() 
            
            for x in full_alphabet:
                next_state_list = list(current_state_tuple)
                is_transition_valid = True
                
                for i in range(N):
                    A_i = automata_list[i]
                    a_i = current_state_tuple[i]
                    
                    if x in A_i.alphabet:
                        # 2.1. Символ належить алфавіту Ai -> виконуємо перехід
                        a_i_prime = A_i.transitions.get((a_i, x))
                        
                        if a_i_prime is None:
                            # 2.2. Перехід не визначений, хоча символ належить алфавіту Ai
                            is_transition_valid = False
                            break
                        
                        next_state_list[i] = a_i_prime
                    else:
                        # 2.3. Символ не належить алфавіту Aj -> залишаємося в тому ж стані
                        next_state_list[i] = a_i

                if is_transition_valid:
                    next_state_tuple = tuple(next_state_list)
                    
                    new_transitions[(current_state_tuple, x)] = next_state_tuple
                    
                    if next_state_tuple not in new_states:
                        new_states.add(next_state_tuple)
                        queue.append(next_state_tuple)

        # 3. Визначення заключних станів F
        new_final_states_raw = set()
        for state_tuple in new_states:
            is_final = True
            for i in range(N):
                a_i = state_tuple[i]
                F_i = automata_list[i].final_states
                if a_i not in F_i:
                    is_final = False
                    break
            if is_final:
                new_final_states_raw.add(state_tuple)

        # 4. Фінальна конвертація в рядок
        state_map = {s: f"({','.join(map(str, s))})" for s in new_states}
        
        final_transitions = {}
        for (current_s, x), next_s in new_transitions.items():
            final_transitions[(state_map[current_s], x)] = state_map[next_s]
            
        final_initial = state_map[initial_state]
        final_states_set = {state_map[s] for s in new_final_states_raw}
        
        return Automaton(
            name="AsyncProduct",
            states=set(state_map.values()),
            alphabet=full_alphabet,
            initial_state=final_initial,
            final_states=final_states_set,
            transitions=final_transitions
        )


# ==============================================================================
# ПРИКЛАД ВИКОРИСТАННЯ
# ==============================================================================

if __name__ == "__main__":
    
    parser = ArgumentParser(description="Асинхронний добуток автоматів з візуалізацією.")
    parser.add_argument('input_files', nargs='+', help='Шляхи до файлів автоматів для асинхронного добутку')
    args = parser.parse_args()

    print("--- Асинхронний Добуток Автоматів ---")

    # Зчитування автоматів з файлів
    automata = [Automaton.from_file(f) for f in args.input_files]
    
    if len(automata) < 2:
        print("Потрібно вказати принаймні два файли автоматів.")
        exit(1)
    
    print(f"Мережа: {', '.join(str(a) for a in automata)}")
    combined_alphabet = set()
    for a in automata:
        combined_alphabet.update(a.alphabet)
    print(f"Об'єднаний алфавіт: {combined_alphabet}")
    
    # Візуалізація вхідних автоматів
    for i, auto in enumerate(automata):
        auto.render(name=f'input_{auto.name}', fmt='svg')
    
    # Запуск алгоритму
    product_automaton = AsynchronousProductBuilder.build_product(automata)
    
    print("\nРезультат:")
    print(product_automaton)
    print(f"Кількість досяжних станів: {len(product_automaton.states)}")
    print(f"Початковий стан: {product_automaton.initial_state}")
    print(f"Заключні стани: {product_automaton.final_states}")
    
    # Візуалізація вихідного автомата (продукту)
    product_automaton.render(name='output_product', fmt='svg')
