import sys
from graphviz import Digraph
from constans import *

class MooreAutomaton:
    """Клас для представлення автомата Мура"""
    
    def __init__(self, states, inputs, outputs, start_state, transitions, marking):
        self.states = states
        self.inputs = inputs
        self.outputs = outputs
        self.start_state = start_state
        self.transitions = transitions
        self.marking = marking
    
    @classmethod
    def from_file(cls, filename):
        """
        Зчитує визначення автомата Мура з текстового файлу.
        
        Формат файлу:
        STATES: s0, s1, s2, ...
        INPUTS: a, b, ...
        OUTPUTS: 0, 1, ...
        START_STATE: s0
        MARKING: s0:y0, s1:y1, ...
        TRANSITIONS:
        s_curr, x: s_next
        ...
        
        Повертає екземпляр MooreAutomaton.
        """
        
        states = []
        inputs = []
        outputs = []
        start_state = None
        transitions = {}
        marking = {}

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
            elif line.startswith("MARKING:"):
                marking_str = line.split("MARKING:", 1)[1]
                for pair in marking_str.split(','):
                    if ':' in pair:
                        state, output = [p.strip() for p in pair.split(':', 1)]
                        marking[state] = output
                current_section = None
            elif line.startswith(TRANSITIONS_DELIMITER):
                current_section = "TRANSITIONS"
            elif current_section == "TRANSITIONS":
                try:
                    # Формат: s_curr, x: s_next
                    key_part, result_part = line.split(':', 1)
                    
                    # Парсинг s_curr, x
                    parts = [p.strip() for p in key_part.split(',', 1)]
                    if len(parts) == 2:
                        state_curr, input_sym = parts
                    else:
                        continue 
                    
                    state_next = result_part.strip()
                    
                    if state_curr not in transitions:
                        transitions[state_curr] = {}
                    
                    transitions[state_curr][input_sym] = state_next
                    
                except ValueError:
                    continue

        if not outputs:
            print("Помилка: Вихідний алфавіт порожній або не знайдено.")
            sys.exit(1)

        # Якщо marking не задано, встановлюємо перший вихідний символ для всіх станів
        if not marking:
            for state in states:
                marking[state] = outputs[0] if outputs else None
        
        return cls(states, inputs, outputs, start_state, transitions, marking)
    
    def print_machine(self):
        """
        Форматує та виводить структуру отриманого автомата Мура.
        """
        
        A_prime = self.states
        X = self.inputs
        start_B = self.start_state
        
        # Створюємо читабельні імена станів: (a0, y0) -> "a0/y0"
        state_names = {s: f"{s[0]}/{s[1]}" for s in A_prime}
        
        print("\n--- Автомат Мура ---")
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
