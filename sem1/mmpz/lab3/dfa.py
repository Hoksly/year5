import collections
from mealy import MealyAutomaton
from moore import MooreAutomaton


class DFA:
    """Клас для представлення Детермінованого Скінченного Автомата (ДСА)"""
    
    def __init__(self, states, inputs, start_state, final_states, transitions):
        self.states = states
        self.inputs = inputs
        self.start_state = start_state
        self.final_states = final_states
        self.transitions = transitions

    @classmethod
    def from_nfa(cls, nfa):
        """
        Створює ДСА з НДСА за алгоритмом побудови підмножин (Subset Construction)
        """
        # Визначаємо алфавіт ДСА (без є-переходів)
        dfa_inputs = [s for s in nfa.alphabet if s != nfa.epsilon]
        
        # Початковий стан ДСА - є-замикання початкового стану НДСА
        start_dfa_set = nfa.epsilon_closure({nfa.start_state})
        
        # Множина станів ДСА (представлена множинами станів НДСА)
        dfa_states_map = {frozenset(start_dfa_set): 'D0'}
        dfa_transitions = collections.defaultdict(dict)
        
        unmarked_states = [frozenset(start_dfa_set)]
        dfa_next_id = 1
        dfa_final_states = set()
        
        while unmarked_states:
            current_set = unmarked_states.pop(0)
            current_name = dfa_states_map[current_set]
            
            # Перевірка на заключний стан
            if not nfa.final_states.isdisjoint(current_set):
                dfa_final_states.add(current_name)

            for symbol in dfa_inputs:
                # 1. Знаходимо цільові стани для символа
                targets_union = set()
                for nfa_state in current_set:
                    targets = nfa.transitions.get(nfa_state, {}).get(symbol)
                    if targets:
                        targets_union.update(targets)
                
                # 2. Обчислюємо є-замикання для об'єднаної множини
                next_dfa_set = nfa.epsilon_closure(targets_union)
                
                if not next_dfa_set:
                    continue
                    
                next_frozen = frozenset(next_dfa_set)
                
                # 3. Додаємо новий стан, якщо він ще невідомий
                if next_frozen not in dfa_states_map:
                    new_name = f'D{dfa_next_id}'
                    dfa_states_map[next_frozen] = new_name
                    unmarked_states.append(next_frozen)
                    dfa_next_id += 1
                
                # 4. Додаємо перехід
                next_name = dfa_states_map[next_frozen]
                dfa_transitions[current_name][symbol] = next_name
        
        return cls(
            states=set(dfa_states_map.values()),
            inputs=dfa_inputs,
            start_state='D0',
            final_states=dfa_final_states,
            transitions=dict(dfa_transitions)
        )

    def to_mealy_acceptor(self):
        """
        Конвертує ДСА в автомат Мілі з логікою акцептора.
        Вихід: '1' якщо перехід веде в заключний стан, '0' інакше.
        """
        Y_ACC = '1'
        Y_REJ = '0'
        
        mealy_transitions = collections.defaultdict(dict)
        
        for state, symbol_map in self.transitions.items():
            for symbol, next_state in symbol_map.items():
                output_sym = Y_ACC if next_state in self.final_states else Y_REJ
                mealy_transitions[state][symbol] = (next_state, output_sym)

        return MealyAutomaton(
            states=list(self.states),
            inputs=self.inputs,
            outputs=[Y_REJ, Y_ACC],
            start_state=self.start_state,
            transitions=dict(mealy_transitions),
            initial_output_sym=Y_REJ
        )

    def to_moore_acceptor(self):
        """
        Конвертує ДСА в автомат Мура з логікою акцептора.
        Вихід залежить від поточного стану (функція marking µ).
        """
        Y_ACC = '1'
        Y_REJ = '0'
        
        marking = {}
        for state in self.states:
            marking[state] = Y_ACC if state in self.final_states else Y_REJ

        return MooreAutomaton(
            states=list(self.states),
            inputs=self.inputs,
            outputs=[Y_REJ, Y_ACC],
            start_state=self.start_state,
            transitions=self.transitions,
            marking=marking
        )
