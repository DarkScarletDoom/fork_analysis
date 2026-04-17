import os
from pathlib import Path
from typing import List, Tuple
import json
from evaluate_solutions import save_model_response
from google import genai
from google.genai import types
import time
import os
import json
from pathlib import Path
from datetime import datetime
import re
import sys
from google import genai
from google.genai import types
import time
import os
import re
from pathlib import Path

def get_excellent_grades():
    """
    Перебирает все json файлы в папке model_responces и возвращает список файлов,
    где поле "grade" содержит значение "отлично"
    
    Returns:
        list: Список имен файлов с оценкой "отлично"
    """
    model_responses_dir = Path("model_responses")
    
    if not model_responses_dir.exists():
        raise FileNotFoundError(f"Папка не найдена: {model_responses_dir}")
    
    excellent_files = []
    
    for json_file in model_responses_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Проверяем, содержит ли поле "grade" значение "отлично"
                if data.get("grade") == "отлично":
                    excellent_files.append(json_file.name)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Ошибка при чтении файла {json_file.name}: {e}")
            continue
    
    return excellent_files


from pathlib import Path
from typing import List, Tuple

def group_solutions(names: List[str], group_size: int = 4) -> List[List[Tuple[str, Path]]]:
    """
    Разбивает решения на группы.
    
    Args:
        names: Список имён (например, ['AitkulovTimur', 'Akkato47', ...])
        group_size: Размер группы (по умолчанию 4)
    
    Returns:
        Список групп. Каждая группа содержит список кортежей (путь_до_txt)
    """
    forks_export_dir = Path("forks_export")
    groups = []
    
    for i in range(0, len(names), group_size):
        group = []
        group_names = names[i:i + group_size]
        
        for name in group_names:
            # Ищем файл, который начинается с этого имени и заканчивается на .txt
            # Паттерн: имя_*.txt
            pattern = f"{name}_*.txt"
            matching_files = list(forks_export_dir.glob(pattern))
            
            if not matching_files:
                print(f"Предупреждение: Файл для имени '{name}' не найден")
                continue
            
            # Берем первый найденный файл (гарантируется, что нет дубликатов)
            txt_file_path = matching_files[0]
            group.append((str(txt_file_path)))
        
        if group:  # Добавляем только непустые группы
            groups.append(group)
    
    return groups



# def group_solutions(json_files: List[str], group_size: int = 4) -> List[List[Tuple[str, Path]]]:
#     """
#     Разбивает решения на группы.

#     Args:
#         json_files: Список имён JSON файлов (например, ['AitkulovTimur_export_20260414_011445.json', ...])
#         group_size: Размер группы (по умолчанию 4)
    
#     Returns:
#         Список групп. Каждая группа содержит список кортежей (имя_без_json, путь_до_txt)
#     """
#     forks_export_dir = Path("forks_export")
#     groups = []
    
#     for i in range(0, len(json_files), group_size):
#         group = []
#         group_items = json_files[i:i + group_size]
        
#         for json_file in group_items:
#             # Убираем расширение .json
#             name_without_ext = json_file.replace('.json', '')
            
#             # Формируем путь к .txt файлу
#             txt_file_name = name_without_ext + '.txt'
#             txt_file_path = forks_export_dir / txt_file_name
            
#             # Проверяем, существует ли файл
#             if not txt_file_path.exists():
#                 print(f"Предупреждение: Файл {txt_file_path} не найден")
#                 continue
            
#             group.append((str(txt_file_path)))
        
#         if group:  # Добавляем только непустые группы
#             groups.append(group)
    
#     return groups

def get_system_prompt():
    prompt_path = Path("tournament_prompts/system_prompt.txt")
    if not prompt_path.exists():
        raise FileNotFoundError(f"Файл не найден: {prompt_path}")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_exercise_text():
    exercise_path = Path("prompts/exercise_text.txt")
    if not exercise_path.exists():
        raise FileNotFoundError(f"Файл не найден: {exercise_path}")
    with open(exercise_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_full_prompt():
    return get_system_prompt() + "\n\n" + get_exercise_text()

def make_request_with_retry(file_paths, model_name, client_instance):
    """Отправляет запрос с несколькими файлами к модели"""
    base_wait = 60
    
    for attempt in range(5):
        try:
            # Загружаем все файлы
            uploaded_files = []
            for file_path in file_paths:
                file = client_instance.files.upload(
                    file=str(file_path),
                    config=types.UploadFileConfig(mime_type="text/plain")
                )
                uploaded_files.append(file)
            
            # Отправляем запрос
            start = time.time()
            response = client_instance.models.generate_content(
                model=model_name,
                contents=[get_full_prompt()] + uploaded_files
            )
            end = time.time()
            
            print(f"Время выполнения: {end - start:.4f} сек.")
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            print(f"Model {model_name}, attempt {attempt+1}/5 failed: {error_msg[:150]}")
            
            if "429" in error_msg and "retryDelay" in error_msg:
                delay_match = re.search(r'retryDelay[:\s]+(\d+)s', error_msg)
                delay = int(delay_match.group(1)) if delay_match else base_wait
                print(f"Quota exceeded. Waiting {delay} seconds...")
                time.sleep(delay)
                continue
            
            if "503" in error_msg:
                wait_time = base_wait * (attempt + 1)
                print(f"Server overload. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            if attempt < 4:
                wait_time = base_wait * (2 ** attempt)
                print(f"Other error. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
    
    return None

def compare_solutions_in_group(group, client_instance):
    """
    Сравнивает группу решений (до 4 файлов).
    
    Args:
        group: Список путей к txt файлам (как Path объекты или строки)
        client_instance: Клиент Gemini API
    
    Returns:
        Ответ модели с выбором лучшего решения
    """
    if not group:
        print("Пустая группа, пропускаем")
        return None
    
    # Модели в порядке приоритета
    MODELS_TO_TRY = [
        "gemini-2.5-flash-lite",
        "gemma-4-31b-it",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]
    
    # Преобразуем в строки, если нужно
    file_paths = [str(p) if not isinstance(p, str) else p for p in group]
    
    print(f"Сравниваем {len(file_paths)} решений...")
    
    for model_name in MODELS_TO_TRY:
        print(f"Trying model: {model_name}")
        response = make_request_with_retry(file_paths, model_name, client_instance)
        
        if response is not None:
            print(f"✓ Success with {model_name}")
            return response
    
    print("✗ Все модели не сработали")
    return None

def procces_groups(groups, dir_for_responses):
    for idx, group in enumerate(groups):
        print(f"\nГруппа {idx + 1}:")
        # сравниваем 4 решения в одном запросе
        response = compare_solutions_in_group(group, client) 

        if response:
            print("\n=== РЕЗУЛЬТАТ ===")
            print(response)

            save_model_response(response, 'group_' + str(idx + 1), dir_for_responses)
        else:
            print("Не удалось получить ответ")


# Настройка клиента
API_KEY = "AIzaSyA3YuD8qXlzOO_POnqfvwslNu6tJZZd2O8"
client = genai.Client(api_key=API_KEY)

# #Разбиваем 54 лучших решения на группы по 4
# excellent_reps = get_excellent_grades()
# names = [rep.split('_')[0] for rep in excellent_reps]
# groups = group_solutions(names, group_size=4)

# # Запускаем обработку
# procces_groups(groups, 'tournament_responses')


# Вручную отобрал победителей из 14 групп предыдущего этапа
# names = [
#     'AitkulovTimur',
#     'beloan',
#     'Daantis',
#     'Dukukkb',
#     'GhoosToy',
#     'ibuildrun',
#     'lenderq',
#     'Lygin04',
#     'MagaSabir',
#     'mr1cloud',
#     'NSIshmekeev',
#     'scmbr',
#     'thesmithmode',
#     'vovatengu'
# ]
# groups = group_solutions(names, group_size=4)
# procces_groups(groups, 'final_tournament_responses')

names = [
    'AitkulovTimur',
    'GhoosToy',
    'MagaSabir',
    'thesmithmode'
]

groups = group_solutions(names, group_size=4)
procces_groups(groups, 'final_tournament_responses')
