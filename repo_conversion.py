from pathlib import Path
from datetime import datetime
import os

def create_repo_export(repo_path, output_filename=None):
    """
    Рекурсивно парсит папку и создает txt файл со структурой и содержимым всех файлов.
    
    Args:
        repo_path: относительный путь к папке с репозиторием
        output_filename: имя выходного файла (если None, то создается как repo_name_export.txt)
    """
    
    # Расширения файлов, которые нужно исключить (бинарники, медиа, архивы)
    EXCLUDED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',  # изображения
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',  # медиа
        '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',  # архивы
        '.exe', '.dll', '.so', '.dylib', '.bin',  # бинарники
        '.pyc', '.pyo', '.pyd',  # python байт-код
        '.db', '.sqlite', '.sqlite3',  # базы данных
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',  # документы
        '.ttf', '.otf', '.woff', '.woff2', '.eot',  # шрифты
    }
    
    # Папки, которые нужно исключить
    EXCLUDED_DIRS = {
        '.git', '.idea', '.vscode', '__pycache__',
        'node_modules', 'vendor', 'dist', 'build',
        'target', 'bin', 'obj', '.venv', 'venv',
        'env', 'virtualenv', '.pytest_cache', '.mypy_cache'
    }
    
    # Файлы, которые нужно исключить по имени
    EXCLUDED_FILES = {
        '.DS_Store', 'Thumbs.db', 'desktop.ini',
        '.gitignore', '.gitattributes', '.gitmodules',
        '.dockerignore', '.env.local', '.env.example'
    }
    
    # Максимальный размер файла для чтения (5 МБ)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    def should_exclude_file(file_path, rel_path):
        """Проверяет, нужно ли исключить файл"""
        # Проверка по расширению
        if any(file_path.suffix.lower() == ext for ext in EXCLUDED_EXTENSIONS):
            return True
        
        # Проверка по имени файла
        if file_path.name in EXCLUDED_FILES:
            return True
        
        # Проверка размера
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return True
        
        # Проверка по пути (скрытые файлы .*)
        if file_path.name.startswith('.') and file_path.name not in {'.env', '.dockerignore'}:
            return True
        
        return False
    
    def get_file_content(file_path):
        """Безопасно читает содержимое файла"""
        try:
            # Пробуем прочитать как текст в UTF-8
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Ограничиваем размер содержимого для очень больших текстовых файлов
                if len(content) > 500000:  # 500KB на файл
                    content = content[:500000] + "\n... [Файл обрезан из-за большого размера] ..."
                return content
        except UnicodeDecodeError:
            # Если не UTF-8, пробуем другие кодировки
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()[:200000] + "\n... [Файл обрезан] ..."
            except:
                return "[НЕВОЗМОЖНО ПРОЧИТАТЬ: бинарный или неподдерживаемый формат]"
        except Exception as e:
            return f"[ОШИБКА ЧТЕНИЯ: {str(e)}]"
    
    # Конвертируем путь в объект Path
    repo_path = Path(repo_path).resolve()
    
    if not repo_path.exists():
        raise FileNotFoundError(f"Папка не найдена: {repo_path}")
    
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Путь не является папкой: {repo_path}")
    
    # Создаем папку forks_export в корне проекта
    project_root = Path.cwd()
    export_root = project_root / "forks_export"
    export_root.mkdir(exist_ok=True)
    
    # Создаем имя выходного файла
    if output_filename is None:
        output_filename = f"{repo_path.name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    output_path = export_root / output_filename
    
    print(f"Начинаем экспорт репозитория: {repo_path}")
    print(f"Выходной файл: {output_path}")
    
    files_processed = 0
    files_skipped = 0
    
    with open(output_path, 'w', encoding='utf-8') as out_file:
        # Заголовок
        out_file.write(f"=" * 80 + "\n")
        out_file.write(f"ЭКСПОРТ РЕПОЗИТОРИЯ: {repo_path.name}\n")
        out_file.write(f"Путь: {repo_path}\n")
        out_file.write(f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out_file.write(f"=" * 80 + "\n\n")
        
        # Рекурсивный обход папки
        for root, dirs, files in os.walk(repo_path):
            # Пропускаем исключенные папки
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            current_dir = Path(root)
            rel_dir = current_dir.relative_to(repo_path)
            
            # Если это корневая папка
            if str(rel_dir) == '.':
                dir_structure = f"{repo_path.name}/"
            else:
                dir_structure = f"{repo_path.name}/{rel_dir}/"
            
            out_file.write(f"\n{'=' * 80}\n")
            out_file.write(f"📁 ПАПКА: {dir_structure}\n")
            out_file.write(f"{'=' * 80}\n")
            
            # Обрабатываем файлы в текущей папке
            for file in sorted(files):
                file_path = current_dir / file
                rel_file_path = file_path.relative_to(repo_path)
                
                # Проверяем, нужно ли исключить файл
                if should_exclude_file(file_path, rel_file_path):
                    files_skipped += 1
                    out_file.write(f"\n[ПРОПУЩЕН] {file} (бинарный/служебный/слишком большой)\n")
                    continue
                
                files_processed += 1
                file_size = file_path.stat().st_size
                
                out_file.write(f"\n{'─' * 80}\n")
                out_file.write(f"📄 ФАЙЛ: {rel_file_path}\n")
                out_file.write(f"Размер: {file_size:,} байт\n")
                out_file.write(f"{'─' * 80}\n")
                
                # Читаем и записываем содержимое файла
                content = get_file_content(file_path)
                out_file.write(content)
                out_file.write("\n")  # Добавляем перенос строки после содержимого
                
                # Прогресс
                if files_processed % 20 == 0:
                    print(f"  Обработано файлов: {files_processed}, пропущено: {files_skipped}")
        
        # Финальная статистика
        out_file.write(f"\n{'=' * 80}\n")
        out_file.write(f"СТАТИСТИКА ЭКСПОРТА\n")
        out_file.write(f"{'=' * 80}\n")
        out_file.write(f"Всего обработано файлов: {files_processed}\n")
        out_file.write(f"Всего пропущено файлов: {files_skipped}\n")
        out_file.write(f"Общий размер выходного файла: {output_path.stat().st_size:,} байт\n")
    
    print(f"\n✅ Экспорт завершен!")
    print(f"📊 Обработано файлов: {files_processed}")
    print(f"⏭️  Пропущено файлов: {files_skipped}")
    print(f"📁 Выходной файл: {output_path}")
    print(f"📏 Размер файла: {output_path.stat().st_size / (1024*1024):.2f} МБ")
    
    return str(output_path)

def get_forks_list():
    """
    Сканирует папку 'forks' и возвращает список путей к папкам авторов.
    
    Returns:
        list: Список строк вида ["forks/Akkato47/", "forks/arthurbadretdinov/", ...]
    """
    
    # Определяем путь к папке forks
    current_dir = Path.cwd()
    forks_path = current_dir / "forks"
    
    # Проверяем, существует ли папка forks
    if not forks_path.exists():
        raise FileNotFoundError(f"Папка 'forks' не найдена по пути: {forks_path}")
    
    if not forks_path.is_dir():
        raise NotADirectoryError(f"Путь не является папкой: {forks_path}")
    
    # Собираем имена папок (исключая файлы и скрытые папки)
    author_folders = []
    
    for item in forks_path.iterdir():
        # Проверяем, что это папка и не скрытая (не начинается с .)
        if item.is_dir() and not item.name.startswith('.'):
            # Формируем путь в нужном формате
            folder_path = f"forks/{item.name}/"
            author_folders.append(folder_path)
    
    # Сортируем для консистентности
    author_folders.sort()
    
    return author_folders

# Конвертируем папки репозиториев в текстовые структуры с содержанием кода
forks_list = get_forks_list()
for fork_path in forks_list:
    create_repo_export(fork_path)