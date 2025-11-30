import collections
from mealy import MealyAutomaton
from moore import MooreAutomaton
from nfa import NFA
from dfa import DFA

class RegexParser:
    """Клас для парсингу та обробки регулярних виразів"""
    
    OPERATORS = {'|', '*', '.'}
    PRECEDENCE = {'|': 1, '.': 2, '*': 3}
    
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
            if char not in cls.PRECEDENCE and char not in {'(', ')'}:
                output.append(char)
            elif char == '(':
                operator_stack.append(char)
            elif char == ')':
                while operator_stack and operator_stack[-1] != '(':
                    output.append(operator_stack.pop())
                if operator_stack and operator_stack[-1] == '(':
                    operator_stack.pop()
            elif char in cls.PRECEDENCE:
                while (operator_stack and operator_stack[-1] != '(' and 
                       cls.PRECEDENCE.get(operator_stack[-1], 0) >= cls.PRECEDENCE.get(char, 0)):
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
            elif char == '|':
                nfa2 = nfa_stack.pop()
                nfa1 = nfa_stack.pop()
                nfa_stack.append(self._union(nfa1, nfa2))
            elif char == '.':
                nfa2 = nfa_stack.pop()
                nfa1 = nfa_stack.pop()
                nfa_stack.append(self._concat(nfa1, nfa2))
            elif char == '*':
                nfa = nfa_stack.pop()
                nfa_stack.append(self._star(nfa))
                
        return nfa_stack.pop() if nfa_stack else None


class RegexSynthesizer:
    """Клас для синтезу автоматів з регулярних виразів"""
    
    def __init__(self, regex, alphabet):
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


if __name__ == "__main__":
    # Регулярний вираз: (a | b)* a b
    # Приймає слова, що закінчуються на 'ab'
    regex_input = "(a|b)*ab"
    alphabet_input = ['a', 'b']
    
    print(f"Вхідний регулярний вираз (R): {regex_input}")
    
    # Використання нового класу
    synthesizer = RegexSynthesizer(regex_input, alphabet_input)
    
    mealy_result = synthesizer.to_mealy()
    moore_result = synthesizer.to_moore()
    
    print("\n--- Результат Синтезу: Автомат Мілі ---")
    mealy_result.print_machine()
    
    print("\n--- Результат Синтезу: Автомат Мура ---")
    moore_result.print_machine()
