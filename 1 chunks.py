import os
import re
import json
from datetime import datetime

# Для парсинга PDF
try:
    import PyPDF2
except ImportError:
    print("PyPDF2 не установлен. Установи: pip install PyPDF2")
    PyPDF2 = None

# Для парсинга HTML
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("BeautifulSoup4 не установлен. Установи: pip install beautifulsoup4")
    BeautifulSoup = None

# ============================================================
# НАСТРОЙКИ
# ============================================================

SENTENCES_PER_CHUNK = 5  # Количество предложений в чанке
OVERLAP_SENTENCES = 1  # Перекрытие в предложениях
INPUT_FOLDER = "documents"  # Папка с файлами


# ============================================================
# ФУНКЦИИ ДЛЯ ПАРСИНГА ФАЙЛОВ
# ============================================================

def parse_txt(file_path):
    """Читает текстовый файл"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='cp1251') as f:
            return f.read()
    except Exception:
        return ""


def parse_pdf(file_path):
    """Извлекает текст из PDF"""
    if PyPDF2 is None:
        return ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
            return text
    except Exception:
        return ""


def parse_html(file_path):
    """Извлекает текст из HTML"""
    if BeautifulSoup is None:
        return ""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            return soup.get_text()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='cp1251') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                for script in soup(["script", "style", "noscript"]):
                    script.decompose()
                return soup.get_text()
        except Exception:
            return ""
    except Exception:
        return ""


def load_document(file_path):
    """Определяет тип файла и парсит его"""
    filename = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return None

    if ext == '.txt':
        content = parse_txt(file_path)
    elif ext == '.pdf':
        content = parse_pdf(file_path)
    elif ext in ['.html', '.htm']:
        content = parse_html(file_path)
    else:
        return None

    if not content or len(content.strip()) == 0:
        return None

    return {
        'filename': filename,
        'content': content.strip(),
        'file_type': ext.replace('.', '')
    }


# ============================================================
# ФУНКЦИИ ДЛЯ ОЧИСТКИ И ЧАНКИНГА
# ============================================================

def clean_text(text):
    """Очищает и нормализует текст"""
    if not text:
        return ""

    # Заменяем множественные переносы
    text = re.sub(r'\n\s*\n', '\n', text)

    # Обрабатываем переносы строк
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not re.search(r'[.!?…]$', line):
            cleaned_lines.append(line + ' ')
        else:
            cleaned_lines.append(line + '\n')

    text = ''.join(cleaned_lines)

    # Убираем множественные пробелы
    text = re.sub(r' +', ' ', text)

    # Нормализуем кавычки и тире
    text = text.replace('«', '"').replace('»', '"')
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('—', '-').replace('–', '-')

# Убираем непечатные символы
    text = re.sub(r'[^\w\s.,!?;:()"\'-]', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)

    return text.strip()


def split_into_sentences(text):
    """Разбивает текст на предложения"""
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z])', text)
    if len(sentences) <= 1:
        sentences = re.split(r'(?<=[.!?])\s+', text)

    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def split_text_into_chunks(text, sentences_per_chunk, overlap_sentences):
    """Разбивает текст на чанки по предложениям с перекрытием"""
    if not text:
        return []

    sentences = split_into_sentences(text)

    if not sentences:
        return []

    if len(sentences) <= sentences_per_chunk:
        return [' '.join(sentences)]

    chunks = []
    start = 0

    while start < len(sentences):
        end = start + sentences_per_chunk

        if end >= len(sentences):
            chunk_text = ' '.join(sentences[start:])
            if chunk_text.strip():
                chunks.append(chunk_text)
            break

        chunk_text = ' '.join(sentences[start:end])
        if chunk_text.strip():
            chunks.append(chunk_text)

        start = end - overlap_sentences

        if start <= 0:
            start = end

    return chunks


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ - ВОЗВРАЩАЕТ СПИСОК ЧАНКОВ
# ============================================================

def process_documents(folder_path="documents"):
    """
    Загружает документы, парсит, очищает, разбивает на чанки.

    Возвращает:
        list: Список строк (чанков) с текстом
    """
    chunks_list = []  # ← Это твой список!

    # Проверяем, существует ли папка
    if not os.path.exists(folder_path):
        print(f"Папка '{folder_path}' не найдена!")
        print(f"Создай папку '{folder_path}' и положи туда файлы.")
        return chunks_list

    # Получаем список файлов
    files = [f for f in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, f))
             and not f.startswith('.')]

    if not files:
        print(f"Папка '{folder_path}' пуста!")
        print("Положи туда файлы .txt, .pdf или .html")
        return chunks_list

    print(f"Найдено файлов: {len(files)}\n")

    # Обрабатываем каждый файл
    for filename in files:
        file_path = os.path.join(folder_path, filename)

        # Загружаем документ
        doc = load_document(file_path)
        if doc is None:
            print(f"❌ Не удалось обработать: {filename}")
            continue

        print(f"{filename} ({len(doc['content'])} символов)")

        # Очищаем текст
        cleaned_text = clean_text(doc['content'])
        if not cleaned_text:
            print(f"После очистки текст пуст")
            continue

        # Разбиваем на чанки
        chunks = split_text_into_chunks(
            cleaned_text,
            SENTENCES_PER_CHUNK,
            OVERLAP_SENTENCES
        )

        print(f"Создано чанков: {len(chunks)}")

        # Добавляем все чанки в общий список (главная цель!)
        for chunk in chunks:
            chunks_list.append(chunk)  # ← Здесь добавляем чанк в список

    print(f"\n ИТОГО: {len(chunks_list)} чанков создано")

    return chunks_list  # ← Возвращаем список чанков!


# ============================================================
# ЗАПУСК (для тестирования)
# ============================================================

if __name__ == "__main__":
    # Вызываем функцию и получаем список чанков
    chunks = process_documents()

    # Выводим результат
    print("\n" + "=" * 60)
    print("СПИСОК ЧАНКОВ:")
    print("=" * 60)

    if chunks:
        # Показываем первые 5 чанков
        for i, chunk in enumerate(chunks[:5], 1):
            print(f"\nЧанк {i} (длина: {len(chunk)} симв.):")
            print("-" * 40)
            print(chunk[:200] + "..." if len(chunk) > 200 else chunk)

if len(chunks) > 5:
    print(f"\n... и еще {len(chunks) - 5} чанков")

    # Сохраняем результат в файл (опционально)
    try:
        with open('documents/chunks_list.json', 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"\n Результат сохранен в 'chunks_list.json'")
    except Exception as e:
        print(f"\n Не удалось сохранить файл: {e}")
    else:
        print("Чанки не созданы. Проверь файлы в папке documents")

# Вызываешь функцию
chunks = process_documents()

# Получаешь список строк:
print(type(chunks))  # <class 'list'>
print(len(chunks))  # количество чанков

# Каждый элемент — это строка с текстом чанка
print(chunks)  # "Первое предложение. Второе предложение…”
