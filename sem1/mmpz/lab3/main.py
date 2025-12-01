import sys
from graphviz import Digraph
from mealy import MealyAutomaton
from moore import MooreAutomaton
from transformer import Transformer
from minimizator import Minimizator

import os
from argparse import ArgumentParser

def mealy_to_moore_with_minimization(input_filename):
    file_name =  "minimizer_" + input_filename.split('/')[-1].split('.')[0]
    folder_path = f"visualization/{file_name}/"
    os.makedirs(folder_path, exist_ok=True)

    minimizator = Minimizator()

    # 2. Зчитування автомата Мілі
    mealy_automaton = MealyAutomaton.from_file(input_filename)
    mealy_automaton.visualize(folder_path + "mealy_input")
    
    mealy_automaton.print_machine()
    # 3. Конвертація Mealy -> Moore
    moore_automaton = Transformer.mealy_to_moore(mealy_automaton)
    minimized_moore = minimizator.minimize_moore(moore_automaton)
    
    # 4. Виведення результату
    moore_automaton.print_machine()
    
    
    # Візуалізація автомата Мура
    moore_automaton.visualize(folder_path + "moore_output")
    minimized_moore.visualize(folder_path + "minimized_moore_output")
    minimized_moore.print_machine()
    
    print("\n" + "="*60)
    print("ПЕРЕТВОРЕННЯ MOORE -> MEALY (зворотне)")
    print("="*60)
    
    # 5. Конвертація Moore -> Mealy (зворотне перетворення)
    mealy_back = Transformer.moore_to_mealy(minimized_moore)
    mealy_back.print_machine()
    # Візуалізація зворотно перетвореного автомата Мілі
    mealy_back.visualize(folder_path + "mealy_back")

    minimized_mealy_back = minimizator.minimize_mealy(mealy_back)
    print("\n" + "="*60)
    print("МІНІМІЗОВАНИЙ АВТОМАТ МІЛІ (ЗВОРТНЕ ПЕРЕТВОРЕННЯ)")
    print("="*60)
    minimized_mealy_back.print_machine()
    minimized_mealy_back.visualize(folder_path + "minimized_mealy_back")


def moore_to_mealy_with_minimization(input_filename):
    print("="*60)
    print("ПЕРЕТВОРЕННЯ MOORE -> MEALY")
    print("="*60)
    file_name =  "minimizer_" + input_filename.split('/')[-1].split('.')[0]
    folder_path = f"visualization/{file_name}/"
    minimizator = Minimizator()

    # 2. Зчитування автомата Мура
    moore_automaton = MooreAutomaton.from_file(input_filename)
    
    # Візуалізація автомата Мура
    moore_automaton.visualize(f"{folder_path}moore_input")
    
    # 3. Конвертація Moore -> Mealy
    mealy_automaton = Transformer.moore_to_mealy(moore_automaton)
    minimized_mealy = minimizator.minimize_mealy(mealy_automaton)
    
    # 4. Виведення результату
    mealy_automaton.print_machine()
    
    
    # Візуалізація автомата Мілі
    mealy_automaton.visualize(f"{folder_path}mealy_output")
    minimized_mealy.visualize(f"{folder_path}minimized_mealy_output")
    
    print("\n" + "="*60)
    print("ПЕРЕТВОРЕННЯ MEALY -> MOORE (зворотне)")
    print("="*60)
    
    # 5. Конвертація Mealy -> Moore (зворотне перетворення)
    moore_back = Transformer.mealy_to_moore(mealy_automaton)
    
    # Візуалізація зворотно перетвореного автомата Мура
    moore_back.visualize(f"{folder_path}moore_back")
    minimized_moore_back = minimizator.minimize_moore(moore_back)
    minimized_moore_back.visualize(f"{folder_path}minimized_moore_back")


if __name__ == "__main__":

    arg_parser = ArgumentParser(description="Конвертер та мінімізатор автоматів Мілі та Мура")
    arg_parser.add_argument("mode", choices=["mealy", "moore"], help="Режим роботи: 'mealy' для Mealy->Moore, 'moore' для Moore->Mealy")    
    arg_parser.add_argument("input_file", help="Вхідний файл з описом автомата")
    args = arg_parser.parse_args()
    if args.mode == "mealy":
        mealy_to_moore_with_minimization(args.input_file)
    elif args.mode == "moore":
        moore_to_mealy_with_minimization(args.input_file)
