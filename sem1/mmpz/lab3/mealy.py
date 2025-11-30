import sys
from graphviz import Digraph
from constans import *

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
        
        # Створюємо відображення станів у рядки (для випадку, якщо стани - кортежі)
        state_to_str = {}
        for state in self.states:
            if isinstance(state, tuple):
                state_to_str[state] = f"{state[0]}/{state[1]}"
            else:
                state_to_str[state] = str(state)
        
        # Додаємо всі стани
        for state in self.states:
            state_name = state_to_str[state]
            if state == self.start_state:
                dot.node(state_name, state_name, shape='circle', style='bold')
            else:
                dot.node(state_name, state_name, shape='circle')
        
        # Додаємо invisible стартовий вузол
        dot.node('', shape='none')
        dot.edge('', state_to_str[self.start_state])
        
        # Додаємо переходи
        for state_curr in self.transitions:
            for input_sym in self.transitions[state_curr]:
                state_next, output_sym = self.transitions[state_curr][input_sym]
                label = f"{input_sym}/{output_sym}"
                dot.edge(state_to_str[state_curr], state_to_str[state_next], label=label)
        
        # Зберігаємо тільки PNG
        dot.render(filename, format='png', cleanup=True)
        print(f"Візуалізацію Mealy автомата збережено у файл {filename}.png")

    def print_machine(self):
        """
        Виводить автомат Мілі у текстовому форматі.
        """
        print("=" * 50)
        print("АВТОМАТ МІЛІ")
        print("=" * 50)
        
        print(f"Стани: {', '.join(str(s) for s in self.states)}")
        print(f"Вхідний алфавіт: {', '.join(self.inputs)}")
        print(f"Вихідний алфавіт: {', '.join(self.outputs)}")
        print(f"Початковий стан: {self.start_state}")
        print(f"Початковий вихідний символ: {self.initial_output_sym}")
        
        print("\nТаблиця переходів:")
        print("-" * 50)
        
        # Заголовок таблиці
        header = "Стан\\Вхід".ljust(15)
        for input_sym in self.inputs:
            header += f"| {input_sym}".ljust(15)
        print(header)
        print("-" * 50)
        
        # Рядки таблиці
        for state in self.states:
            row = str(state).ljust(15)
            for input_sym in self.inputs:
                if state in self.transitions and input_sym in self.transitions[state]:
                    next_state, output_sym = self.transitions[state][input_sym]
                    cell = f"{next_state}/{output_sym}"
                else:
                    cell = "-"
                row += f"| {cell}".ljust(15)
            print(row)
        
        print("=" * 50)
