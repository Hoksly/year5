import sys
from graphviz import Digraph

# Константи для парсингу вхідного файлу
STATE_DELIMITER = "STATES:"
INPUT_DELIMITER = "INPUTS:"
OUTPUT_DELIMITER = "OUTPUTS:"
START_STATE_DELIMITER = "START_STATE:"
TRANSITIONS_DELIMITER = "TRANSITIONS:"


class MealyAutomaton:
    """Клас для представлення автомата Мілі"""
    
    def __init__(self, states, inputs, outputs, start_state, transitions, initial_output_sym):
        self.states = states
        self.inputs = inputs
        self.outputs = outputs
        self.start_state = start_state
        self.transitions = transitions
        self.initial_output_sym = initial_output_sym
    
    @classmethod
    def from_file(cls, filename):
        """
        Зчитує визначення автомата Мілі з текстового файлу.
        
        Повертає екземпляр MealyAutomaton.
        """
        
        states = []
        inputs = []
        outputs = []
        start_state = None
        transitions = {}

        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
        except IOError:
            print(f"Помилка: Не вдалося відкрити файл {filename}")
            sys.exit(1)

        current_section = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith(STATE_DELIMITER):
                states_str = line.split(STATE_DELIMITER, 1)[1]
                states = [s.strip() for s in states_str.split(',')]
                current_section = None
            elif line.startswith(INPUT_DELIMITER):
                inputs_str = line.split(INPUT_DELIMITER, 1)[1]
                inputs = [x.strip() for x in inputs_str.split(',')]
                current_section = None
            elif line.startswith(OUTPUT_DELIMITER):
                outputs_str = line.split(OUTPUT_DELIMITER, 1)[1]
                outputs = [y.strip() for y in outputs_str.split(',')]
                current_section = None
            elif line.startswith(START_STATE_DELIMITER):
                start_state = line.split(START_STATE_DELIMITER, 1)[1].strip()
                current_section = None
            elif line.startswith(TRANSITIONS_DELIMITER):
                current_section = "TRANSITIONS"
            elif current_section == "TRANSITIONS":
                try:
                    # Формат: s_curr, x: s_next/y_out
                    key_part, result_part = line.split(':', 1)
                    
                    # Парсинг s_curr, x
                    parts = [p.strip() for p in key_part.split(',', 1)]
                    if len(parts) == 2:
                        state_curr, input_sym = parts
                    else:
                        continue 
                    
                    # Парсинг s_next/y_out
                    state_next, output_sym = [p.strip() for p in result_part.split('/', 1)]
                    
                    if state_curr not in transitions:
                        transitions[state_curr] = {}
                    
                    transitions[state_curr][input_sym] = (state_next, output_sym)
                    
                except ValueError:
                    continue

        if not outputs:
            print("Помилка: Вихідний алфавіт порожній або не знайдено.")
            sys.exit(1)

        initial_output_sym = outputs[0] if outputs else None
        
        return cls(states, inputs, outputs, start_state, transitions, initial_output_sym)
    
    def visualize(self, filename="mealy_input"):
        """
        Візуалізує автомат Мілі за допомогою graphviz.
        Зберігає результат у файл mealy_input.png
        """
        dot = Digraph(comment='Mealy Automaton')
        dot.attr(rankdir='LR')
        
        # Додаємо всі стани
        for state in self.states:
            if state == self.start_state:
                dot.node(state, state, shape='circle', style='bold')
            else:
                dot.node(state, state, shape='circle')
        
        # Додаємо invisible стартовий вузол
        dot.node('', shape='none')
        dot.edge('', self.start_state)
        
        # Додаємо переходи
        for state_curr in self.transitions:
            for input_sym in self.transitions[state_curr]:
                state_next, output_sym = self.transitions[state_curr][input_sym]
                label = f"{input_sym}/{output_sym}"
                dot.edge(state_curr, state_next, label=label)
        
        # Зберігаємо тільки PNG
        dot.render(filename, format='png', cleanup=True)
        print(f"Візуалізацію Mealy автомата збережено у файл {filename}.png")


class MooreAutomaton:
    """Клас для представлення автомата Мура"""
    
    def __init__(self, states, inputs, outputs, start_state, transitions, marking):
        self.states = states
        self.inputs = inputs
        self.outputs = outputs
        self.start_state = start_state
        self.transitions = transitions
        self.marking = marking
    
    def print_machine(self):
        """
        Форматує та виводить структуру отриманого автомата Мура.
        """
        
        A_prime = self.states
        X = self.inputs
        start_B = self.start_state
        
        # Створюємо читабельні імена станів: (a0, y0) -> "a0/y0"
        state_names = {s: f"{s[0]}/{s[1]}" for s in A_prime}
        
        print("\n--- Результат перетворення: Автомат Мура ---")
        print("Алфавіт вхідних символів (X):", ", ".join(X))
        print("Алфавіт вихідних символів (Y):", ", ".join(self.outputs))
        
        print("\nСтани (A'):")
        # Виводимо стани (A x Y) та їхню позначку µ
        for s in sorted(A_prime, key=lambda x: (x[0], x[1])):
            marking = self.marking[s]
            print(f"  {state_names[s]} (Вихід/Позначка µ): {marking}")

        print("\nПочатковий стан (A0):", state_names[start_B])

        print("\nТаблиця переходів (f') та виходів (g(a,x) = µ(f'(a,x))):")
        
        sorted_A_prime = sorted(A_prime, key=lambda x: (x[0], x[1]))
        
        # Форматування заголовка таблиці
        header = "Поточний стан | " + " | ".join(f"Вхід {x}" for x in X)
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        for s_curr in sorted_A_prime:
            row = f"{state_names[s_curr]:<13} |"
            
            for x in X:
                s_next = self.transitions.get(s_curr, {}).get(x)
                
                if s_next:
                    # Наступний стан і вихід (який є µ(s_next))
                    next_state_name = state_names[s_next]
                    output_sym = self.marking[s_next]
                    row += f" {next_state_name} ({output_sym}) |"
                else:
                    row += f" - |"
            print(row)
        print("-" * len(header))
    
    def visualize(self, filename="moore_output"):
        """
        Візуалізує автомат Мура за допомогою graphviz.
        Зберігає результат у файл moore_output.png
        """
        dot = Digraph(comment='Moore Automaton')
        dot.attr(rankdir='LR')
        
        # Створюємо читабельні імена станів
        state_names = {s: f"{s[0]}/{s[1]}" for s in self.states}
        
        # Додаємо всі стани з їхніми мітками (виходами)
        for state in self.states:
            state_name = state_names[state]
            output = self.marking[state]
            label = f"{state_name}\n({output})"
            
            if state == self.start_state:
                dot.node(state_name, label, shape='circle', style='bold')
            else:
                dot.node(state_name, label, shape='circle')
        
        # Додаємо invisible стартовий вузол
        dot.node('', shape='none')
        dot.edge('', state_names[self.start_state])
        
        # Додаємо переходи
        for state_curr in self.transitions:
            for input_sym in self.transitions[state_curr]:
                state_next = self.transitions[state_curr][input_sym]
                dot.edge(state_names[state_curr], state_names[state_next], label=input_sym)
        
        # Зберігаємо тільки PNG
        dot.render(filename, format='png', cleanup=True)
        print(f"Візуалізацію Moore автомата збережено у файл {filename}.png")


class Transformer:
    """Клас для перетворення автомата Мілі в автомат Мура"""
    
    @staticmethod
    def mealy_to_moore(mealy_automaton):
        """
        Конвертує автомат Мілі в еквівалентний автомат Мура.
        Використовує метод A' = A x Y.
        """
        
        A = mealy_automaton.states
        X = mealy_automaton.inputs
        Y = mealy_automaton.outputs
        start_A = mealy_automaton.start_state
        T_Mealy = mealy_automaton.transitions
        y_default = mealy_automaton.initial_output_sym
        
        # 1. Нова множина станів A' = A x Y.
        A_prime = []
        for a in A:
            for y in Y:
                A_prime.append((a, y))
                
        # 2. Функція позначок µ: A' -> Y.
        mu = {s: s[1] for s in A_prime}
        
        # 3. Нова функція переходів f'
        T_Moore = {}

        for (a, y) in A_prime:
            for x in X:
                if a in T_Mealy and x in T_Mealy[a]:
                    # Знаходимо наступний стан (a') та вихід (y') в автоматі Мілі
                    a_prime, y_prime = T_Mealy[a][x]
                    
                    # Наступний стан Мура-автомата є (a', y')
                    new_state = (a_prime, y_prime)
                    
                    if (a, y) not in T_Moore:
                        T_Moore[(a, y)] = {}
                    
                    T_Moore[(a, y)][x] = new_state
                
        # 4. Визначаємо початковий стан Мура-автомата
        start_B = (start_A, y_default)

        return MooreAutomaton(A_prime, X, Y, start_B, T_Moore, mu)


def generate_example_input_file(filename="mealy_input.txt"):
    """
    Генерує приклад вхідного файлу для демонстрації.
    Використовує приклад, схожий на Автомат Б із Завдання 19.
    """
    sample_content = """
# Приклад автомата Мілі
STATES: a0, a1
INPUTS: 0, 1
OUTPUTS: y0, y1
START_STATE: a0

TRANSITIONS:
# a0 --0--> a1 / y0
a0, 0: a1/y0
# a0 --1--> a0 / y0
a0, 1: a0/y0
# a1 --0--> a1 / y1
a1, 0: a1/y1
# a1 --1--> a0 / y0
a1, 1: a0/y0
"""
    with open(filename, 'w') as f:
        f.write(sample_content.strip())
    print(f"Згенеровано приклад вхідного файлу: {filename}")


if __name__ == "__main__":
    
    input_filename = "mealy_input.txt"
    generate_example_input_file(input_filename)
    
    # 2. Зчитування автомата Мілі
    mealy_automaton = MealyAutomaton.from_file(input_filename)
    
    # Візуалізація автомата Мілі
    mealy_automaton.visualize("mealy_input")
    
    # 3. Конвертація
    moore_automaton = Transformer.mealy_to_moore(mealy_automaton)
    
    # 4. Виведення результату
    moore_automaton.print_machine()
    
    # Візуалізація автомата Мура
    moore_automaton.visualize("moore_output")