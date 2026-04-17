import subprocess
import os
from github import Github
import filecmp
import get_forks
import cloning_forks

# 1. Получаем список форков
forks = get_forks.get_forks()

# 2. Клонируем
cloning_forks.cloning_forks(forks)

# 3. Оцениваем все решения по шкале ['плохо', 'средне', 'хорошо'] и сохраняем в папку ответы
# evaluate_solutions.evaluate_solutions()

# 4. Отфильтровать и выбрать работы с оценкой ['хорошо']


# 5. Методом Турнир + Losers bracket выявить 5 лучших работ


# 6. Выбрать топ 5 решений и отсмотреть вручную
