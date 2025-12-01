import collections
from mealy import MealyAutomaton
from moore import MooreAutomaton
from nfa import NFA
from dfa import DFA
from constans import *
import os
OPERATORS = {KLEENE_STAR, CONCAT_SYMBOL, UNION_SYMBOL}
PRECEDENCE = {UNION_SYMBOL: 1, CONCAT_SYMBOL: 2, KLEENE_STAR: 3}

class RegexParser:
    """Клас для парсингу та обробки регулярних виразів"""    
    @staticmethod
    def preprocess(regex):
        """Додає явні символи конкатенації ('.')"""
        result = []
        concat_needed = set(regex) - {'|', '*', '(', '.'}
        
        for i, char in enumerate(regex):
            result.append(char)
            if i + 1 < len(regex):
                next_char = regex[i + 1]
                
                if char in concat_needed or char == '*' or char == ')':
                    if next_char not in {'|', '*', ')'}:
                        result.append('.')
                elif char == '(' and next_char not in {'|', '*', ')'}:
                    pass
                elif next_char == '(' and char not in {'|', '.'}:
                    result.append('.')
        
        return "".join(result)

    @classmethod
    def to_postfix(cls, regex):
        """Конвертує інфіксний вираз у постфіксний"""
        output = []
        operator_stack = []
        regex = cls.preprocess(regex)
        
        for char in regex:
            if char not in PRECEDENCE and char not in {'(', ')'}:
                output.append(char)
            elif char == '(':
                operator_stack.append(char)
            elif char == ')':
                while operator_stack and operator_stack[-1] != '(':
                    output.append(operator_stack.pop())
                if operator_stack and operator_stack[-1] == '(':
                    operator_stack.pop()
            elif char in PRECEDENCE:
                while (operator_stack and operator_stack[-1] != '(' and 
                       PRECEDENCE.get(operator_stack[-1], 0) >= PRECEDENCE.get(char, 0)):
                    output.append(operator_stack.pop())
                operator_stack.append(char)
                
        while operator_stack:
            output.append(operator_stack.pop())
            
        return "".join(output)


class ThompsonBuilder:
    """Реалізує конструкцію Томпсона для побудови НДСА з регулярного виразу"""
    
    def __init__(self, alphabet):
        self.next_state_id = 0
        self.alphabet = alphabet
        self.epsilon = NFA.EPSILON
    
    def _new_state(self):
        """Створює новий унікальний стан"""
        state = f's{self.next_state_id}'
        self.next_state_id += 1
        return state

    def _atom(self, symbol):
        """Створює базовий НДСА для одного символа"""
        start = self._new_state()
        end = self._new_state()
        transitions = {start: {symbol: {end}}}
        return NFA({start, end}, self.alphabet, transitions, start, {end})

    def _union(self, nfa1, nfa2):
        """Об'єднання двох НДСА (операція |)"""
        start = self._new_state()
        end = self._new_state()
        
        transitions = collections.defaultdict(dict, nfa1.transitions)
        transitions.update(nfa2.transitions)
        
        transitions[start] = {self.epsilon: {nfa1.start_state, nfa2.start_state}}
        
        for final in nfa1.final_states:
            if self.epsilon in transitions.get(final, {}):
                transitions[final][self.epsilon].add(end)
            else:
                transitions[final][self.epsilon] = {end}
        
        for final in nfa2.final_states:
            if self.epsilon in transitions.get(final, {}):
                transitions[final][self.epsilon].add(end)
            else:
                transitions[final][self.epsilon] = {end}

        states = nfa1.states.union(nfa2.states).union({start, end})
        return NFA(states, self.alphabet, dict(transitions), start, {end})

    def _concat(self, nfa1, nfa2):
        """Конкатенація двох НДСА (операція .)"""
        transitions = collections.defaultdict(dict, nfa1.transitions)
        transitions.update(nfa2.transitions)
        
        for final in nfa1.final_states:
            if self.epsilon in transitions.get(final, {}):
                transitions[final][self.epsilon].add(nfa2.start_state)
            else:
                transitions[final][self.epsilon] = {nfa2.start_state}

        states = nfa1.states.union(nfa2.states)
        return NFA(states, self.alphabet, dict(transitions), nfa1.start_state, nfa2.final_states)

    def _star(self, nfa):
        """Замикання Кліні (операція *)"""
        start = self._new_state()
        end = self._new_state()
        
        transitions = collections.defaultdict(dict, nfa.transitions)
        transitions[start] = {self.epsilon: {nfa.start_state, end}}
        
        for final in nfa.final_states:
            if self.epsilon in transitions.get(final, {}):
                transitions[final][self.epsilon].update({nfa.start_state, end})
            else:
                transitions[final][self.epsilon] = {nfa.start_state, end}
        
        states = nfa.states.union({start, end})
        return NFA(states, self.alphabet, dict(transitions), start, {end})

    def build(self, postfix_regex):
        """Будує НДСА з постфіксного регулярного виразу"""
        nfa_stack = []
        terminals = [s for s in self.alphabet if s != self.epsilon]

        for char in postfix_regex:
            if char in terminals:
                nfa_stack.append(self._atom(char))
            elif char == UNION_SYMBOL:
                nfa2 = nfa_stack.pop()
                nfa1 = nfa_stack.pop()
                nfa_stack.append(self._union(nfa1, nfa2))
            elif char == CONCAT_SYMBOL:
                nfa2 = nfa_stack.pop()
                nfa1 = nfa_stack.pop()
                nfa_stack.append(self._concat(nfa1, nfa2))
            elif char == KLEENE_STAR:
                nfa = nfa_stack.pop()
                nfa_stack.append(self._star(nfa))
                
        return nfa_stack.pop() if nfa_stack else None


class RegexSynthesizer:
    """Клас для синтезу автоматів з регулярних виразів"""
    
    def __init__(self, regex = None, alphabet = None):
        self.regex = regex
        self.alphabet = alphabet
        self._nfa = None
        self._dfa = None
    
    @property
    def nfa(self):
        """Повертає НДСА (з кешуванням)"""
        if self._nfa is None:
            postfix = RegexParser.to_postfix(self.regex)
            builder = ThompsonBuilder(self.alphabet + [NFA.EPSILON])
            self._nfa = builder.build(postfix)
        return self._nfa
    
    @property
    def dfa(self):
        """Повертає ДСА (з кешуванням)"""
        if self._dfa is None:
            self._dfa = DFA.from_nfa(self.nfa)
        return self._dfa
    
    def to_mealy(self):
        """Синтезує автомат Мілі з регулярного виразу"""
        return self.dfa.to_mealy_acceptor()
    
    def to_moore(self):
        """Синтезує автомат Мура з регулярного виразу"""
        return self.dfa.to_moore_acceptor()

    def read_from_file(self, filename):
        """Зчитує регулярний вираз з файлу"""
        try:
            with open(filename, 'r') as f:
                # Зчитуємо перший рядок як регулярний вираз
                self.regex = f.readline().strip()
                self.alphabet = list(set(self.regex) - OPERATORS - {'(', ')'})
        except IOError:
            print(f"Помилка: Не вдалося відкрити файл {filename}")
            sys.exit(1) 


class AutomataAnalyzer:
    """
    Клас для аналізу автоматів та генерації регулярних виразів.
    Використовує метод видалення станів (State Elimination Method).
    """
    
    def __init__(self):
        self.EMPTY = '∅'  # Порожня множина (немає переходу)
        self.EPSILON = 'ε'  # Порожнє слово
    
    def _simplify_regex(self, regex):
        """Спрощує регулярний вираз"""
        if regex is None or regex == self.EMPTY:
            return self.EMPTY
        
        # Видаляємо зайві дужки та спрощуємо
        regex = regex.replace(f'({self.EPSILON})', self.EPSILON)
        regex = regex.replace(f'{self.EPSILON}|', '')
        regex = regex.replace(f'|{self.EPSILON}', '')
        regex = regex.replace(f'{self.EPSILON}.', '')
        regex = regex.replace(f'.{self.EPSILON}', '')
        regex = regex.replace(f'{self.EMPTY}|', '')
        regex = regex.replace(f'|{self.EMPTY}', '')
        
        # Якщо результат порожній після спрощення
        if not regex or regex == '()':
            return self.EPSILON
            
        return regex
    
    def _concat(self, r1, r2):
        """Конкатенація двох регулярних виразів"""
        if r1 == self.EMPTY or r2 == self.EMPTY:
            return self.EMPTY
        if r1 == self.EPSILON:
            return r2
        if r2 == self.EPSILON:
            return r1
        
        # Додаємо дужки якщо потрібно
        if '|' in r1:
            r1 = f'({r1})'
        if '|' in r2:
            r2 = f'({r2})'
            
        return f'{r1}{r2}'
    
    def _union(self, r1, r2):
        """Об'єднання двох регулярних виразів"""
        if r1 == self.EMPTY:
            return r2
        if r2 == self.EMPTY:
            return r1
        if r1 == r2:
            return r1
            
        return f'({r1}|{r2})'
    
    def _star(self, r):
        """Замикання Кліні для регулярного виразу"""
        if r == self.EMPTY or r == self.EPSILON:
            return self.EPSILON
        
        # Якщо вже є зірочка, не додаємо ще одну
        if r.endswith('*'):
            return r
            
        # Додаємо дужки якщо потрібно
        if len(r) > 1 and not (r.startswith('(') and r.endswith(')')):
            return f'({r})*'
            
        return f'{r}*'

    
    def _state_elimination(self, dfa_struct):
        """
        Метод видалення станів для генерації регулярного виразу.
        
        Алгоритм:
        1. Додаємо новий початковий стан q_start з ε-переходом до старого початкового
        2. Додаємо новий фінальний стан q_final з ε-переходами від старих фінальних
        3. Послідовно видаляємо всі стани крім q_start та q_final
        4. Регулярний вираз - це мітка ребра від q_start до q_final
        """
        
        states = set(dfa_struct['states'])
        start = dfa_struct['start_state']
        finals = set(dfa_struct['final_states'])
        transitions = dfa_struct['transitions']
        alphabet = dfa_struct['alphabet']
        
        # Якщо немає фінальних станів, мова порожня
        if not finals:
            return self.EMPTY
        
        # Створюємо матрицю регулярних виразів для переходів
        # R[i][j] = регулярний вираз для переходу з i в j
        R = {s: {t: self.EMPTY for t in states} for s in states}
        
        # Заповнюємо початкові переходи
        for state in states:
            R[state][state] = self.EPSILON  # Петля з ε
            if state in transitions:
                for sym, next_state in transitions[state].items():
                    if R[state][next_state] == self.EMPTY:
                        R[state][next_state] = sym
                    elif R[state][next_state] == self.EPSILON:
                        R[state][next_state] = self._union(self.EPSILON, sym)
                    else:
                        R[state][next_state] = self._union(R[state][next_state], sym)
        
        # Додаємо новий початковий та фінальний стани
        q_start = '_START_'
        q_final = '_FINAL_'
        
        all_states = states | {q_start, q_final}
        
        # Розширюємо матрицю
        for s in all_states:
            if s not in R:
                R[s] = {}
            for t in all_states:
                if t not in R[s]:
                    R[s][t] = self.EMPTY
        
        # ε-перехід від нового початкового до старого
        R[q_start][start] = self.EPSILON
        R[q_start][q_start] = self.EPSILON
        R[q_final][q_final] = self.EPSILON
        
        # ε-переходи від старих фінальних до нового фінального
        for f in finals:
            R[f][q_final] = self.EPSILON
        
        # Видаляємо стани один за одним
        states_to_remove = list(states)
        
        for q_rip in states_to_remove:
            # Для кожної пари станів (q_i, q_j) оновлюємо R[q_i][q_j]
            remaining_states = [s for s in all_states if s != q_rip]
            
            for q_i in remaining_states:
                for q_j in remaining_states:
                    # R[q_i][q_j] = R[q_i][q_j] | R[q_i][q_rip] . R[q_rip][q_rip]* . R[q_rip][q_j]
                    
                    r_ii_to_rip = R[q_i].get(q_rip, self.EMPTY)
                    r_rip_to_rip = R[q_rip].get(q_rip, self.EMPTY)
                    r_rip_to_jj = R[q_rip].get(q_j, self.EMPTY)
                    r_ii_to_jj = R[q_i].get(q_j, self.EMPTY)
                    
                    if r_ii_to_rip != self.EMPTY and r_rip_to_jj != self.EMPTY:
                        # Будуємо новий шлях через q_rip
                        middle = self._star(r_rip_to_rip)
                        new_path = self._concat(r_ii_to_rip, self._concat(middle, r_rip_to_jj))
                        R[q_i][q_j] = self._union(r_ii_to_jj, new_path)
            
            # Видаляємо q_rip з матриці
            all_states = all_states - {q_rip}
        
        # Результат - регулярний вираз від q_start до q_final
        result = R[q_start].get(q_final, self.EMPTY)
        
        return self._simplify_regex(result)
    
    def _mealy_to_dfa_structure(self, mealy, accepting_output='1'):
            """
            Конвертує автомат Мілі в структуру ДСА.
            accepting_output: символ виходу, який означає акцептацію (за замовчуванням '1')
            """
            states = set(mealy.states)
            start_state = mealy.start_state
            transitions = {}
            final_states = set()
            
            for state in mealy.states:
                transitions[state] = {}
                if state in mealy.transitions:
                    for input_sym, (next_state, output) in mealy.transitions[state].items():
                        transitions[state][input_sym] = next_state
                        
                        if output == accepting_output:
                            final_states.add(next_state)
            
            return {
                'states': states,
                'start_state': start_state,
                'final_states': final_states,
                'transitions': transitions,
                'alphabet': mealy.inputs
            }

    # Потрібно також оновити виклик цього методу
    def from_mealy(self, mealy, accepting_output='1'):
        dfa_struct = self._mealy_to_dfa_structure(mealy, accepting_output)
        return self._state_elimination(dfa_struct)

    # Аналогічно для Мура, якщо там використовуються нестандартні позначки
    def _moore_to_dfa_structure(self, moore, accepting_mark='1'):
        states = set(moore.states)
        start_state = moore.start_state
        transitions = {}
        final_states = set()
        
        for state in moore.states:
            transitions[state] = {}
            # ВИПРАВЛЕННЯ: Перевірка позначки
            if moore.marking.get(state) == accepting_mark:
                final_states.add(state)
            
            if state in moore.transitions:
                for input_sym, next_state in moore.transitions[state].items():
                    transitions[state][input_sym] = next_state
        
        return {
            'states': states,
            'start_state': start_state,
            'final_states': final_states,
            'transitions': transitions,
            'alphabet': moore.inputs
        }

    def from_moore(self, moore, accepting_mark='1'):
        dfa_struct = self._moore_to_dfa_structure(moore, accepting_mark)
        return self._state_elimination(dfa_struct)
        

from argparse import ArgumentParser
if __name__ == "__main__":
    parser = ArgumentParser(description="Синтез автоматів Мілі та Мура з регулярного виразу")
    parser.add_argument("input_file", help="Вхідний файл з регулярним виразом")
    parser.add_argument("-m", "--mode", choices=["regex", "mealy", "moore"], default="regex",
                        help="Режим роботи: 'regex' для синтезу з регулярного виразу (за замовчуванням)")
    
    # file name without folders and extension
    args = parser.parse_args()
    file_name = "regex_" + args.input_file.split('/')[-1].split('.')[0]
    os.makedirs(f"visualization/{file_name}", exist_ok=True)
    if args.mode == "regex":
        synthesizer = RegexSynthesizer()
        synthesizer.read_from_file(args.input_file)
        
        print(f"Вхідний регулярний вираз: {synthesizer.regex}")
        print(f"Алфавіт: {synthesizer.alphabet}")
        
        mealy_result = synthesizer.to_mealy()
        moore_result = synthesizer.to_moore()
        
        print("\n--- Результат Синтезу: Автомат Мілі ---")
        mealy_result.print_machine()
        mealy_result.visualize(filename=f"visualization/{file_name}/mealy_output")

        print("\n--- Результат Синтезу: Автомат Мура ---")
        moore_result.print_machine()
        moore_result.visualize(filename=f"visualization/{file_name}/moore_output")
        
        # Демонстрація зворотного перетворення
        print("\n--- Зворотне перетворення: Автомат -> Регулярний вираз ---")
        analyzer = AutomataAnalyzer()
        
        regex_from_mealy = analyzer.from_mealy(mealy_result)
        print(f"Регулярний вираз з автомата Мілі: {regex_from_mealy}")
        
        regex_from_moore = analyzer.from_moore(moore_result)
        print(f"Регулярний вираз з автомата Мура: {regex_from_moore}")
    
    if args.mode == "mealy":
        automata = MealyAutomaton.from_file(args.input_file)
        print("\n--- Автомат Мілі ---")
        automata.print_machine()
        automata.visualize(filename=f"visualization/{file_name}/mealy_input")
        analyzer = AutomataAnalyzer() 
        regex_from_mealy = analyzer.from_mealy(automata, 'y1')
        print(f"Регулярний вираз з автомата Мілі: {regex_from_mealy}")

    if args.mode == "moore":
        automata = MooreAutomaton.from_file(args.input_file)
        print("\n--- Автомат Мура ---")
        automata.print_machine()
        automata.visualize(filename=f"visualization/{file_name}/moore_input")
        analyzer = AutomataAnalyzer() 
        regex_from_moore = analyzer.from_moore(automata)
        print(f"Регулярний вираз з автомата Мура: {regex_from_moore}")