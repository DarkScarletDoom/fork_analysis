# import google.generativeai as genai
from google import genai
from google.genai import types
import time
import os
import json
from pathlib import Path
from datetime import datetime
import re
import sys

# Конфигурация
REQUEST_DELAY = 20  # Задержка между запросами (сек)
PROGRESS_FILE = "processed_forks.json"
OUTPUT_DIR = "model_responses"

def get_forks_export_list():
    file_paths = []
    forks_export_dir = Path("forks_export")

    if not forks_export_dir.exists():
        print(f"Папка {forks_export_dir} не найдена")
        exit()

    for txt_file in forks_export_dir.glob("*.txt"):
        file_path = f"forks_export/{txt_file.name}"
        file_paths.append(file_path)

    return file_paths

def system_prompt():    
    prompts_dir = Path("prompts")
    system_prompt_path = prompts_dir / "system_prompt.txt"
    
    if not system_prompt_path.exists():
        raise FileNotFoundError(f"Файл не найден: {system_prompt_path}")
    
    with open(system_prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def exercise_text():
    prompts_dir = Path("prompts")
    exercise_path = prompts_dir / "exercise_text.txt"
    
    if not exercise_path.exists():
        raise FileNotFoundError(f"Файл не найден: {exercise_path}")
    
    with open(exercise_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_prompt():
    return system_prompt() + "\n\n" + exercise_text()

def load_progress():
    """Загружает список уже обработанных форков"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_progress(processed):
    """Сохраняет прогресс"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(processed), f, ensure_ascii=False, indent=2)

def make_request(fork_export_file_path, model, client_instance):
    """Делает один запрос к модели"""
    # Подгружаем файл
    file = client_instance.files.upload(
        file=fork_export_file_path,
        config=types.UploadFileConfig(
            mime_type="text/plain"
        )
    )

    # Отправка запроса к модели
    start = time.time()
    response = client_instance.models.generate_content(
        model=model,
        contents=[
            get_prompt(),
            file
        ]
    )
    end = time.time()

    print(f"Время выполнения: {end - start:.4f} сек.")
    return response.text

def make_request_with_retry(fork_export_file_path, model_name, client_instance):
    """Делает запрос с экспоненциальной задержкой при ошибках"""
    base_wait = 60
    
    for attempt in range(5):
        try:
            response = make_request(fork_export_file_path, model_name, client_instance)
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"  Model {model_name}, attempt {attempt+1}/5 failed: {error_msg[:150]}")
            
            # Если ошибка квоты (429) с указанием retryDelay
            if "429" in error_msg and "retryDelay" in error_msg:
                delay_match = re.search(r'retryDelay[:\s]+(\d+)s', error_msg)
                delay = int(delay_match.group(1)) if delay_match else base_wait
                print(f"  Quota exceeded. Waiting {delay} seconds...")
                time.sleep(delay)
                continue
            
            # Если ошибка 503 (перегрузка) - ждём и пробуем снова
            if "503" in error_msg:
                wait_time = base_wait * (attempt + 1)
                print(f"  Server overload. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            # Другие ошибки
            if attempt < 4:
                wait_time = base_wait * (2 ** attempt)
                print(f"  Other error. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
    
    return None  # Все попытки неудачны

def save_model_response(response_text, author_name, output_dir=OUTPUT_DIR):
    """
    Сохраняет ответ модели в JSON файл.
    """
    # Создаём папку, если её нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Если ответа нет (ошибка) - сохраняем как ошибку
    if response_text is None:
        response_json = {
            "grade": "error",
            "comment": "Не удалось получить ответ от модели после всех попыток",
            "error": True
        }
    else:
        # Парсим JSON из ответа
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            # Если ответ не чистый JSON, пробуем извлечь JSON из строки
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    response_json = json.loads(json_match.group())
                except:
                    response_json = {
                        "grade": "error",
                        "comment": f"Не удалось распарсить JSON. Ответ: {response_text[:200]}",
                        "error": True
                    }
            else:
                response_json = {
                    "grade": "error", 
                    "comment": f"Не удалось распарсить JSON из ответа: {response_text[:200]}",
                    "error": True
                }
    
    # Формируем имя файла
    safe_name = "".join(c for c in author_name if c.isalnum() or c in ('-', '_'))
    filename = f"{safe_name}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Сохраняем в файл
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(response_json, f, ensure_ascii=False, indent=2)
    
    print(f"Сохранено: {filepath}")
    return filepath

def process_all_forks(forks_export_list, client_instance):
    """Основная функция с обработкой прогресса"""
    processed = load_progress()
    total = len(forks_export_list)
    
    print("=" * 60)
    print(f"Всего форков: {total}")
    print(f"Уже обработано: {len(processed)}")
    print(f"Осталось: {total - len(processed)}")
    print(f"Задержка между запросами: {REQUEST_DELAY} сек.")
    print("=" * 60)
    
    # Список моделей в порядке приоритета
    MODELS_TO_TRY = [
        "gemini-2.5-flash-lite",
        "gemma-4-31b-it",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]
    
    start_time = time.time()
    
    try:
        for i, fork_path in enumerate(forks_export_list):
            # Пропускаем уже обработанные
            if fork_path in processed:
                print(f"\n[{i+1}/{total}] SKIP (already processed): {os.path.basename(fork_path)}")
                continue
            
            print(f"\n[{i+1}/{total}] Processing: {os.path.basename(fork_path)}")
            
            # Пробуем модели по очереди
            response = None
            for model_name in MODELS_TO_TRY:
                print(f"  Trying model: {model_name}")
                response = make_request_with_retry(fork_path, model_name, client_instance)
                
                if response is not None:
                    print(f"  ✓ Success with {model_name}")
                    break
                else:
                    print(f"  ✗ Failed with {model_name}")
            
            # Сохраняем результат
            name_export = os.path.splitext(os.path.basename(fork_path))[0]
            save_model_response(response, name_export)
            
            # Отмечаем как обработанный
            processed.add(fork_path)
            save_progress(processed)
            
            # Задержка между запросами
            if i < total - 1:
                print(f"Sleeping {REQUEST_DELAY}s before next request...")
                time.sleep(REQUEST_DELAY)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("=== ПРЕРВАНО ПОЛЬЗОВАТЕЛЕМ ===")
        print(f"Обработано {len(processed)} из {total} форков")
        print(f"Прогресс сохранён в файле: {PROGRESS_FILE}")
        print("При следующем запуске скрипт продолжит с того же места.")
        print("=" * 60)
        return
    
    except Exception as e:
        print(f"\n\n!!! НЕОЖИДАННАЯ ОШИБКА: {e}")
        print(f"Обработано {len(processed)} из {total} форков")
        print(f"Прогресс сохранён. Перезапустите скрипт для продолжения.")
        raise
    
    finally:
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("=== ВЫПОЛНЕНИЕ ЗАВЕРШЕНО ===")
        print(f"Успешно обработано: {len(processed)} из {total}")
        print(f"Общее время: {elapsed/60:.1f} минут")
        print(f"Прогресс сохранён в: {PROGRESS_FILE}")
        print("=" * 60)

# Основной блок
if __name__ == "__main__":
    # Указываем api ключ
    API_KEY = "AIzaSyA3YuD8qXlzOO_POnqfvwslNu6tJZZd2O8"
    client = genai.Client(api_key=API_KEY)
    
    # Получаем список переконвертированных структур 
    forks_export_list = get_forks_export_list()
    
    if not forks_export_list:
        print("Нет файлов для обработки!")
        sys.exit(1)
    
    # Запускаем обработку
    process_all_forks(forks_export_list, client)

















