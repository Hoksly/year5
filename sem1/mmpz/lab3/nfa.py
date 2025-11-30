class NFA:
    """Клас для представлення Недетермінованого Скінченного Автомата (НДСА)"""
    
    EPSILON = 'epsilon'  # Константа для є-переходів
    
    def __init__(self, states, alphabet, transitions, start_state, final_states):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.final_states = final_states
        self.epsilon = self.EPSILON

    def epsilon_closure(self, states_set):
        """Обчислює є-замикання множини станів"""
        closure = set(states_set)
        stack = list(states_set)
        
        while stack:
            state = stack.pop()
            epsilon_targets = self.transitions.get(state, {}).get(self.epsilon)
            
            if epsilon_targets:
                for target in epsilon_targets:
                    if target not in closure:
                        closure.add(target)
                        stack.append(target)
        return closure
