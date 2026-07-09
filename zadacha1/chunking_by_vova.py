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

SENTENCES_PER_CHUNK = 5
OVERLAP_SENTENCES = 1
INPUT_FOLDER = "documents"
OUTPUT_FILE = "chunks_output.json"  # Файл для сохранения результата


# ============================================================
# ФУНКЦИИ ДЛЯ ПАРСИНГА ФАЙЛОВ
# ============================================================

def parse_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='cp1251') as f:
            return f.read()
    except Exception:
        return ""


def parse_pdf(file_path):
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
    if not text:
        return ""

    text = re.sub(r'\n\s*\n', '\n', text)

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
    text = re.sub(r' +', ' ', text)
    text = text.replace('«', '"').replace('»', '"')
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('—', '-').replace('–', '-')
    text = re.sub(r'[^\w\s.,!?;:()"\'-]', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)

    return text.strip()


def split_into_sentences(text):
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z])', text)
    if len(sentences) <= 1:
        sentences = re.split(r'(?<=[.!?])\s+', text)

    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def split_text_into_chunks(text, sentences_per_chunk, overlap_sentences):
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
# ГЛАВНАЯ ФУНКЦИЯ - СОЗДАЕТ JSON С МЕТАДАННЫМИ
# ============================================================

def process_documents_to_json(folder_path="documents", output_file="chunks_output.json"):
    """
    Обрабатывает документы и сохраняет результат в JSON-файл.

    Возвращает:
        dict: Структура с метаданными и чанками
    """
    # Структура для JSON
    result = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'total_files': 0,
            'total_chunks': 0,
            'settings': {
                'sentences_per_chunk': SENTENCES_PER_CHUNK,
                'overlap_sentences': OVERLAP_SENTENCES
            }
        },
        'documents': []
    }

    # Проверяем папку
    if not os.path.exists(folder_path):
        print(f"❌ Папка '{folder_path}' не найдена!")
        result['metadata']['error'] = f"Папка '{folder_path}' не найдена"
        return result

    # Получаем список файлов
    files = [f for f in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, f))
             and not f.startswith('.')]

    if not files:
        print(f"❌ Папка '{folder_path}' пуста!")
        result['metadata']['error'] = "Папка пуста"
        return result

    print(f"📂 Найдено файлов: {len(files)}\n")
    result['metadata']['total_files'] = len(files)

    # Обрабатываем каждый файл
    for filename in files:
        file_path = os.path.join(folder_path, filename)

        # Загружаем документ
        doc = load_document(file_path)
        if doc is None:
            print(f"❌ Не удалось обработать: {filename}")
            continue

        print(f"✅ {filename} ({len(doc['content'])} символов)")

        # Очищаем текст
        cleaned_text = clean_text(doc['content'])
        if not cleaned_text:
            print(f"⚠️ После очистки текст пуст")
            continue

        # Разбиваем на чанки
        chunks = split_text_into_chunks(
            cleaned_text,
            SENTENCES_PER_CHUNK,
            OVERLAP_SENTENCES
        )

        print(f"📄 Создано чанков: {len(chunks)}")

        # Создаем структуру для документа
        doc_data = {
            'filename': filename,
            'file_type': doc['file_type'],
            'original_length': len(doc['content']),
            'cleaned_length': len(cleaned_text),
            'chunks_count': len(chunks),
            'chunks': []
        }

        # Добавляем каждый чанк с метаданными
        for i, chunk_text in enumerate(chunks, 1):
            doc_data['chunks'].append({
                'chunk_id': i,
                'text': chunk_text,
                'length': len(chunk_text),
                'sentences_count': len(split_into_sentences(chunk_text))
            })

        result['documents'].append(doc_data)

    # Обновляем общее количество чанков
    total_chunks = sum(doc['chunks_count'] for doc in result['documents'])
    result['metadata']['total_chunks'] = total_chunks

    print(f"\n📊 ИТОГО: {total_chunks} чанков из {len(result['documents'])} документов")

    # Сохраняем в JSON-файл
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 Результат сохранен в '{output_file}'")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")

    return result


# ============================================================
# ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ JSON В ОБРАТНОМ ПОРЯДКЕ
# ============================================================

def load_json_chunks(file_path="chunks_output.json"):
    """
    Загружает JSON-файл и возвращает список всех чанков.

    Возвращает:
        list: Список строк с текстом чанков
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = []
        for doc in data.get('documents', []):
            for chunk in doc.get('chunks', []):
                chunks.append(chunk['text'])

        return chunks
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return []


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    # Обрабатываем документы и сохраняем в JSON
    result = process_documents_to_json(
        folder_path=INPUT_FOLDER,
        output_file=OUTPUT_FILE
    )

    # Показываем структуру результата
    print("\n" + "=" * 60)
    print("СТРУКТУРА JSON:")
    print("=" * 60)

    print(f"\n📌 Метаданные:")
    print(f"   - Создано: {result['metadata']['created_at']}")
    print(f"   - Всего файлов: {result['metadata']['total_files']}")
    print(f"   - Всего чанков: {result['metadata']['total_chunks']}")
    print(f"   - Настроек: {result['metadata']['settings']}")

    if 'error' in result['metadata']:
        print(f"   - Ошибка: {result['metadata']['error']}")

    print(f"\n📌 Документы: {len(result['documents'])}")

    for doc in result['documents'][:3]:  # Показываем первые 3 документа
        print(f"\n   📄 {doc['filename']}")
        print(f"      - Чанков: {doc['chunks_count']}")
        if doc['chunks']:
            print(f"      - Первый чанк: {doc['chunks'][0]['text'][:100]}...")

    # Демонстрация загрузки обратно
    print("\n" + "=" * 60)
    print("ЗАГРУЗКА ЧАНКОВ ИЗ JSON:")
    print("=" * 60)

    loaded_chunks = load_json_chunks(OUTPUT_FILE)
    print(f"✅ Загружено чанков: {len(loaded_chunks)}")
    if loaded_chunks:
        print(f"📝 Первый чанк: {loaded_chunks[0][:150]}...")