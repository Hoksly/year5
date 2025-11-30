from moore import MooreAutomaton
from mealy import MealyAutomaton

class Minimizator:
    """Клас для мінімізації автоматів Мілі та Мура за алгоритмом Хопкрофта"""
    @staticmethod
    def minimize_moore(moore_automaton):
        """
        Мінімізує автомат Мура за алгоритмом Хопкрофта.
        
        Алгоритм:
        0. Видалення недосяжних станів
        1. Початкове розбиття станів за вихідними символами (позначками)
        2. Ітеративне уточнення розбиття на основі переходів
        3. Об'єднання еквівалентних станів
        """
        from collections import defaultdict
        
        states = moore_automaton.states
        inputs = moore_automaton.inputs
        transitions = moore_automaton.transitions
        marking = moore_automaton.marking
        start_state = moore_automaton.start_state
        outputs = moore_automaton.outputs
        
        # Крок 1: Початкове розбиття за вихідними символами
        partition = defaultdict(list)
        for state in states:
            output = marking[state]
            partition[output].append(state)
        
        # Перетворюємо у список класів еквівалентності
        equivalence_classes = list(partition.values())
        
        # Крок 2: Уточнення розбиття
        changed = True
        while changed:
            changed = False
            new_equivalence_classes = []
            
            # Створюємо відображення стану -> номер класу для поточного розбиття
            state_to_class = {}
            for class_id, eq_class in enumerate(equivalence_classes):
                for state in eq_class:
                    state_to_class[state] = class_id
            
            for eq_class in equivalence_classes:
                # Групуємо стани в класі за їхніми переходами
                transition_signatures = defaultdict(list)
                
                for state in eq_class:
                    # Створюємо сигнатуру переходів для цього стану
                    signature = []
                    for input_sym in inputs:
                        if state in transitions and input_sym in transitions[state]:
                            next_state = transitions[state][input_sym]
                            next_class = state_to_class.get(next_state, -1)
                            signature.append(next_class)
                        else:
                            signature.append(None)
                    
                    signature_tuple = tuple(signature)
                    transition_signatures[signature_tuple].append(state)
                
                # Якщо клас розбився на підкласи
                if len(transition_signatures) > 1:
                    changed = True
                    for sub_class in transition_signatures.values():
                        new_equivalence_classes.append(sub_class)
                else:
                    new_equivalence_classes.append(eq_class)
            
            # Оновлюємо класи еквівалентності
            equivalence_classes = new_equivalence_classes
        
        # Крок 3: Побудова мінімізованого автомата
        # Створюємо фінальне відображення стану -> номер класу
        state_to_class = {}
        for class_id, eq_class in enumerate(equivalence_classes):
            for state in eq_class:
                state_to_class[state] = class_id
        
        # Вибираємо представника для кожного класу
        class_representatives = {}
        for class_id, eq_class in enumerate(equivalence_classes):
            representative = eq_class[0]
            class_representatives[class_id] = representative
        
        # Нові стани - це представники класів
        new_states = list(class_representatives.values())
        
        # Нова функція переходів
        new_transitions = {}
        for class_id, representative in class_representatives.items():
            if representative in transitions:
                new_transitions[representative] = {}
                for input_sym in inputs:
                    if input_sym in transitions[representative]:
                        old_next_state = transitions[representative][input_sym]
                        new_next_class = state_to_class[old_next_state]
                        new_next_state = class_representatives[new_next_class]
                        new_transitions[representative][input_sym] = new_next_state
        
        # Нова функція позначок
        new_marking = {}
        for representative in new_states:
            new_marking[representative] = marking[representative]
        
        # Новий початковий стан
        start_class = state_to_class[start_state]
        new_start_state = class_representatives[start_class]
        
        return MooreAutomaton(
            new_states,
            inputs,
            outputs,
            new_start_state,
            new_transitions,
            new_marking
        )
    
    @staticmethod
    def minimize_mealy(mealy_automaton):
        """
        Мінімізує автомат Мілі за алгоритмом Хопкрофта.
        
        Алгоритм:
        0. Видалення недосяжних станів
        1. Початкове розбиття станів за вихідними функціями
        2. Ітеративне уточнення розбиття на основі переходів
        3. Об'єднання еквівалентних станів
        """
        from collections import defaultdict
        
        states = mealy_automaton.states
        inputs = mealy_automaton.inputs
        outputs = mealy_automaton.outputs
        transitions = mealy_automaton.transitions
        start_state = mealy_automaton.start_state
        initial_output_sym = mealy_automaton.initial_output_sym
        
        # Крок 1: Початкове розбиття за вихідними функціями
        # Два стани в одному класі, якщо мають однакові виходи для всіх входів
        output_signatures = defaultdict(list)
        
        for state in states:
            # Створюємо сигнатуру виходів для кожного стану
            if state in transitions:
                signature = []
                for input_sym in inputs:
                    if input_sym in transitions[state]:
                        _, output_sym = transitions[state][input_sym]
                        signature.append(output_sym)
                    else:
                        signature.append(None)
                signature_tuple = tuple(signature)
                output_signatures[signature_tuple].append(state)
            else:
                # Стан без переходів
                output_signatures[()].append(state)
        
        equivalence_classes = list(output_signatures.values())
        
        # Створюємо відображення стану -> номер класу
        state_to_class = {}
        for class_id, eq_class in enumerate(equivalence_classes):
            for state in eq_class:
                state_to_class[state] = class_id
        
        # Крок 2: Уточнення розбиття
        changed = True
        while changed:
            changed = False
            new_equivalence_classes = []
            
            # Створюємо відображення стану -> номер класу для поточного розбиття
            state_to_class = {}
            for class_id, eq_class in enumerate(equivalence_classes):
                for state in eq_class:
                    state_to_class[state] = class_id
            
            for eq_class in equivalence_classes:
                # Групуємо стани в класі за їхніми переходами
                transition_signatures = defaultdict(list)
                
                for state in eq_class:
                    # Створюємо сигнатуру переходів для цього стану
                    # Виходи не включаємо, бо вони вже однакові після початкового розбиття
                    signature = []
                    for input_sym in inputs:
                        if state in transitions and input_sym in transitions[state]:
                            next_state, _ = transitions[state][input_sym]
                            next_class = state_to_class.get(next_state, -1)
                            signature.append(next_class)
                        else:
                            signature.append(None)
                    
                    signature_tuple = tuple(signature)
                    transition_signatures[signature_tuple].append(state)
                
                # Якщо клас розбився на підкласи
                if len(transition_signatures) > 1:
                    changed = True
                    for sub_class in transition_signatures.values():
                        new_equivalence_classes.append(sub_class)
                else:
                    new_equivalence_classes.append(eq_class)
            
            # Оновлюємо класи еквівалентності
            equivalence_classes = new_equivalence_classes
        
        # Крок 3: Побудова мінімізованого автомата
        # Створюємо фінальне відображення стану -> номер класу
        state_to_class = {}
        for class_id, eq_class in enumerate(equivalence_classes):
            for state in eq_class:
                state_to_class[state] = class_id
        
        # Вибираємо представника для кожного класу
        class_representatives = {}
        for class_id, eq_class in enumerate(equivalence_classes):
            representative = eq_class[0]
            class_representatives[class_id] = representative
        
        # Нові стани - це представники класів
        new_states = list(class_representatives.values())
        
        # Нова функція переходів
        new_transitions = {}
        for class_id, representative in class_representatives.items():
            if representative in transitions:
                new_transitions[representative] = {}
                for input_sym in inputs:
                    if input_sym in transitions[representative]:
                        old_next_state, output_sym = transitions[representative][input_sym]
                        new_next_class = state_to_class[old_next_state]
                        new_next_state = class_representatives[new_next_class]
                        new_transitions[representative][input_sym] = (new_next_state, output_sym)
        
        # Новий початковий стан
        start_class = state_to_class[start_state]
        new_start_state = class_representatives[start_class]

        return MealyAutomaton(
            new_states,
            inputs,
            outputs,
            new_start_state,
            new_transitions,
            initial_output_sym
        )