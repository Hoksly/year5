import itertools

# Порядок бітів (зліва направо) за замовчуванням. Можна змінити, наприклад ['x','y','z','u']
DEFAULT_VAR_ORDER = ['x', 'y', 'z', 'u']

def calculate_dot_product(a, Z):
    """Обчислює скалярний добуток вектора коефіцієнтів 'a' та вхідного вектора 'Z'."""
    q = len(a)
    return sum(a[i] * Z[i] for i in range(q))

def apr_dsa_algorithm(a, b, var_names=None):
    """
    Реалізує алгоритм АПР-ДСА для побудови ДСА, 
    який акцептує розв'язки лінійної рівності (a, x) = b.
    
    Використовується умова: перехід можливий лише, якщо s - (a, Z) парне.
    Наступний стан: j = (s - (a, Z)) / 2.
    """
    q = len(a)
    
    # Множина всіх знайдених станів (ключові об'єкти ДСА)
    states = set() 
    
    # Єдиний заключний стан: 0 (згідно з АПР-ДСА) [1]
    final_states = {0}   
    
    # Початковий стан: b [1]
    initial_state = b
    
    # Робоча множина (стани, які потрібно обробити)
    working_set = {initial_state}
    states.add(initial_state)
    
    # Функція переходів: {стан_початку: {вектор_входу: стан_кінця}}
    transitions = {}

    # Визначаємо імена змінних/порядок бітів
    if var_names is None:
        # використовуємо глобальний порядок, обрізаючи або доповнюючи при потребі
        if len(DEFAULT_VAR_ORDER) >= q:
            var_names = tuple(DEFAULT_VAR_ORDER[:q])
        else:
            # якщо DEFAULT_VAR_ORDER короткий, генеруємо імена z0, z1, ...
            var_names = tuple(f'z{i}' for i in range(q))

    # Генерація вхідного алфавіту (всі 2^q двійкових векторів)
    # q=4, 2^4 = 16 векторів
    input_alphabet = list(itertools.product((0, 1), repeat=q))

    print(f"Запущено АПР-ДСА для коефіцієнтів a={a}, константи b={b}")
    print(f"Кількість змінних q={q}. Вхідний алфавіт має {2**q} символів.\n")
    
    # Основний цикл генерації станів та переходів
    while working_set:
        # Беремо стан для обробки
        s = working_set.pop()
        
        if s not in transitions:
            transitions[s] = {}

        for Z in input_alphabet:
            
            # 1. Обчислюємо (a, Z)
            s_dot_Z = calculate_dot_product(a, Z)
            
            # 2. Обчислюємо чисельник для переходу (s - (a, Z))
            numerator = s - s_dot_Z
            
            # 3. Перевірка умови: чисельник повинен бути парним
            if numerator % 2 == 0:
                j = numerator // 2
                
                # 4. Зберігаємо перехід
                transitions[s][Z] = j
                
                # 5. Якщо знайдено новий стан, додаємо його до робочої множини
                if j not in states:
                    states.add(j)
                    working_set.add(j)
                    # print(f"Новий стан знайдено: {j}") # Коментуємо для чистого фінального виводу
            # Інакше (якщо непарний), перехід не визначений (частковий ДСА)
            
    return {
        'states': states,
        'initial_state': initial_state,
        'final_states': final_states.intersection(states),
        'transitions': transitions,
        'variable_names': tuple(var_names)
    }

# --- Виконання прикладу: x + 2y + u - 3z = 1 ---
coefficients = [1, 2, 1, -3]
constant_b = 1

# Запуск алгоритму
dfa_result = apr_dsa_algorithm(coefficients, constant_b)

# --- Виведення результату ---
print("\n" + "="*50)
print("РЕЗУЛЬТАТ ПОБУДОВИ ДСА (АПР-ДСА)")
print("==================================================")
print(f"Кількість станів (A): {len(dfa_result['states'])}")
print(f"Множина станів: {sorted(list(dfa_result['states']))}")
print(f"Початковий стан: {dfa_result['initial_state']}")
print(f"Заключні стани (F): {dfa_result['final_states']}")
print("\nТАБЛИЦЯ ПЕРЕХОДІВ (f):")

# Виведення переходів у читабельному форматі
variable_names = dfa_result['variable_names']
for s, transitions_s in sorted(dfa_result['transitions'].items()):
    print(f"\nСтан {s}:")
    for Z, j in sorted(transitions_s.items()):
        # Перетворення вектора Z на читабельний рядок
        # формуємо біт-рядок у згаданому порядку змінних
        try:
            bits_str = ''.join(str(int(b)) for b in Z)
            num = int(bits_str, 2)
            # unicode subscript for nicer print
            sub_map = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'}
            sub = ''.join(sub_map.get(ch, ch) for ch in str(num))
            zi = f'z{sub}'
        except Exception:
            bits_str = str(Z)
            zi = ''

        input_str = ', '.join(f'{name}={bit}' for name, bit in zip(variable_names, Z))
        if zi:
            print(f"  Вхід {bits_str} ({input_str}) -> {zi} -> Стан {j}")
        else:
            print(f"  Вхід {bits_str} ({input_str}) -> Стан {j}")

print("\n" + "="*50)


# ==============================================================================
# ВІЗУАЛІЗАЦІЯ (Graphviz) для ДСА
# ==============================================================================
def dfa_to_dot_text(dfa):
    """Побудова DOT-представлення для ДСА (детерміністичний автомат).

    dfa: словник з ключами 'states', 'initial_state', 'final_states', 'transitions', 'variable_names'
    """
    lines = []
    lines.append('digraph G {')
    lines.append('  rankdir=LR;')
    lines.append('  size="10,6";')
    lines.append('  node [shape=circle];')

    states = sorted(dfa['states'])
    finals = set(dfa.get('final_states', ()))

    for s in states:
        if s in finals:
            lines.append(f'  "{s}" [shape=doublecircle];')
        else:
            lines.append(f'  "{s}" [shape=circle];')

    # invisible start
    lines.append('  "__start__" [shape=point,label=""];')
    lines.append(f'  "__start__" -> "{dfa["initial_state"]}";')

    var_names = dfa.get('variable_names', ())

    # edges
    for src in states:
        trans_map = dfa['transitions'].get(src, {})
        # group by destination with labels if multiple inputs go to same dest
        for Z, dst in sorted(trans_map.items()):
            # format label as concatenated bits like '0101' when Z is an iterable of bits
            try:
                if hasattr(Z, '__iter__') and not isinstance(Z, (str, bytes)):
                    bits_str = ''.join(str(int(b)) for b in Z)
                    # номер, який кодує цей біт-повідомлення
                    try:
                        num = int(bits_str, 2)
                    except Exception:
                        num = None
                    # формуємо мітку у вигляді zₙ (зі значенням під індексом), якщо можливо
                    if num is not None:
                        # перетворимо цифри у підрядкові символи Unicode для кращого відображення
                        sub_map = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'}
                        sub = ''.join(sub_map.get(ch, ch) for ch in str(num))
                        lbl = f"z{sub}"
                    else:
                        lbl = bits_str
                else:
                    lbl = str(Z)
            except Exception:
                lbl = str(Z)
            lines.append(f'  "{src}" -> "{dst}" [label="{lbl}"];')

    lines.append('}')
    return "\n".join(lines)


def render_dfa(dfa, name='dfa_output'):
    """Спробувати відрендерити DOT у PNG через python-graphviz, інакше записати .dot файл."""
    dot_text = dfa_to_dot_text(dfa)
    try:
        import graphviz
        dot = graphviz.Source(dot_text)
        out_path = dot.render(filename=name, format='svg', cleanup=True)
        print(f"Візуалізація збережена у: {out_path}")
    except Exception as e:
        dot_file = f"{name}.dot"
        with open(dot_file, 'w', encoding='utf-8') as f:
            f.write(dot_text)
        print(f"Не вдалося автоматично відрендерити граф (error: {e}).")
        print(f"Записано DOT у файл: {dot_file}")
        print("Щоб згенерувати PNG локально, встановіть graphviz і виконайте:")
        print(f"  dot -Tpng {dot_file} -o {name}.png")


# Спробуємо згенерувати візуалізацію для отриманого ДСА
try:
    render_dfa(dfa_result, name='apr_dsa')
except Exception as _e:
    print('Помилка при збереженні візуалізації (перевірте встановлення graphviz).')