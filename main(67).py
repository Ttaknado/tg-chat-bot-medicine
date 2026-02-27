import csv
from fuzzywuzzy import fuzz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import re

# Настройки телеграм-бота
TOKEN = "7632206824:AAEU950_-62_ZjiMYl4BUaYQhUTbtvlswmQ"

def load_questions_from_file(file_path):
    """Функция для загрузки типовых вопросов из CSV-файла."""
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        questions = []
        for row in reader:
            questions.append({
                'category': row['category'],
                'question_text': row['question_text'],
                'answer_text': row['answer_text'],
                'keywords': row['keywords']
            })
        return questions

def load_questions():
    """Загрузка всех вопросов из файла."""
    return load_questions_from_file('sample_questions.csv')

def sanitize_callback_data(text):
    """Удаление недопустимых символов и ограничение длины callback_data."""
    text = re.sub(r'[^a-zA-Z0-9_]', '', text)  # Оставляем только буквы, цифры и подчеркивание
    return text[:60]  # Ограничиваем длину до 60 символов

def find_answer(user_question, questions):
    """
    Функция поиска ответа на вопрос пользователя.
    Ищет совпадения по ключевым словам, а при их отсутствии,
    использует нечеткий поиск.
    """
    best_match = None
    best_score = 0
    user_keywords = user_question.lower().split()

    for question in questions:
        keywords_list = question['keywords'].lower().split(",") if question['keywords'] else []
        score = sum([1 for keyword in user_keywords if keyword in keywords_list])  # Совпадение слов
        if score > best_score:
            best_score = score
            best_match = question
    if not best_match:  # Если совпадений по ключевым словам нет - fuzzy search
        for question in questions:
            fuzzy_score = fuzz.ratio(user_question.lower(), question['question_text'].lower())
            if fuzzy_score > best_score:
                best_score = fuzzy_score
                best_match = question
    return best_match

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("Социальная помощь", callback_data='social_help')],
        [InlineKeyboardButton("Юридические вопросы", callback_data='legal_issues')],
        [InlineKeyboardButton("Общие вопросы", callback_data='general')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Проверка, есть ли callback_query, если да - используем его
    if update.callback_query:
        await update.callback_query.message.edit_text(
            "Здравствуйте! Я чат-бот для консультации молодых родителей. Выберите категорию вопросов.",
            reply_markup=reply_markup
        )
    elif update.message:
        # Если вызов через текстовое сообщение (например, /start)
        await update.message.reply_text(
            "Здравствуйте! Я чат-бот для консультации молодых родителей. Выберите категорию вопросов.",
            reply_markup=reply_markup
        )

async def show_category_questions(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    """Отображение списка вопросов в выбранной категории"""
    questions = load_questions()
    filtered_questions = [q for q in questions if q['category'] == category]

    if filtered_questions:
        keyboard = [
            [InlineKeyboardButton(q['question_text'], callback_data=f'question_{index}')] for index, q in enumerate(filtered_questions)
        ]
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_categories')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(
            f"Вопросы по категории '{category}':",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.reply_text(f"Вопросы для категории '{category}' не найдены.")

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений."""
    user_question = update.message.text
    questions = load_questions()
    answer = find_answer(user_question, questions)
    if answer:
        keyboard = [[InlineKeyboardButton("К вопросам", callback_data='back_to_categories')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Возможно, вас интересует: \n\n{answer['question_text']}\n\n{answer['answer_text']}",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Извините, я не знаю ответа на этот вопрос. Попробуйте перефразировать.")

async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /questions для вывода списка вопросов."""
    questions = load_questions()
    if questions:
        keyboard = [[InlineKeyboardButton(q['question_text'], callback_data=f'question_{index}')] for index, q in enumerate(questions)]
        keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_categories')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Выберите вопрос, на который хотите получить ответ:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Пока нет доступных вопросов.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    data = query.data
    questions = load_questions()

    if data.startswith("question_"):
        question_index = int(data[len("question_"):])  # Извлекаем индекс
        question = questions[question_index] if 0 <= question_index < len(questions) else None
        if question:
            keyboard = [[InlineKeyboardButton("К вопросам", callback_data='back_to_categories')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Вопрос: {question['question_text']}\nОтвет: {question['answer_text']}",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Ответ не найден.")
    elif data == "social_help":
        await show_category_questions(update, context, 'Социальная помощь')
    elif data == "legal_issues":
        await show_category_questions(update, context, 'Юридические вопросы')
    elif data == "general":
        await show_category_questions(update, context, 'Общие вопросы')
    elif data == "back_to_categories":
        await start_command(update, context)

def main():
    # Создаем объект приложения
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('questions', list_questions))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    application.add_handler(CallbackQueryHandler(button_click))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
