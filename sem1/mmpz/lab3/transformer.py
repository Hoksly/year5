from mealy import MealyAutomaton
from moore import MooreAutomaton


class Transformer:
    """Клас для перетворення автоматів Мілі в Мура та навпаки"""
    
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
    
    @staticmethod
    def moore_to_mealy(moore_automaton):
        """
        Конвертує автомат Мура в еквівалентний автомат Мілі.
        Для кожного переходу вихід визначається позначкою цільового стану.
        """
        
        A_moore = moore_automaton.states
        X = moore_automaton.inputs
        Y = moore_automaton.outputs
        start_moore = moore_automaton.start_state
        T_Moore = moore_automaton.transitions
        mu = moore_automaton.marking
        
        # 1. Множина станів залишається тією ж (або можна спростити)
        # Для простоти будемо використовувати ті ж стани
        A_mealy = A_moore
        
        # 2. Початковий стан залишається тим же
        start_mealy = start_moore
        
        # 3. Функція переходів та виходів для автомата Мілі
        T_Mealy = {}
        
        for state_curr in A_moore:
            if state_curr in T_Moore:
                for input_sym in T_Moore[state_curr]:
                    state_next = T_Moore[state_curr][input_sym]
                    
                    # Вихід для переходу в автоматі Мілі - це позначка наступного стану
                    output_sym = mu[state_next]
                    
                    if state_curr not in T_Mealy:
                        T_Mealy[state_curr] = {}
                    
                    T_Mealy[state_curr][input_sym] = (state_next, output_sym)
        
        # 4. Визначаємо initial_output_sym (беремо перший символ з алфавіту)
        initial_output_sym = Y[0] if Y else None
        
        return MealyAutomaton(A_mealy, X, Y, start_mealy, T_Mealy, initial_output_sym)