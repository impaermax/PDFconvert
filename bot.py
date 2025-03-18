import telebot
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import requests
from io import BytesIO
from PIL import Image
import csv
from datetime import datetime

# Инициализация бота
bot = telebot.TeleBot("8096350827:AAFDwVRdhemiSSqs5-w6-U6HBpcEO9Y_RDU")
ADMIN_ID = 1200223081
CHANNEL_ID = "@impaermax"

# Регистрация шрифтов с поддержкой кириллицы
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))  # Укажите путь к файлу шрифта
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))  # Жирный шрифт

# Глобальные переменные
user_data = {}  # Для контента PDF
users_db = {}   # База пользователей

# Создание клавиатуры
def main_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton("Text -> PDF"))
    keyboard.add(telebot.types.KeyboardButton("Photo -> PDF"))
    keyboard.add(telebot.types.KeyboardButton("Flexible -> PDF"))
    return keyboard

# Админская клавиатура
def admin_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton("Рассылка"))
    keyboard.add(telebot.types.KeyboardButton("Выгрузить базу"))
    keyboard.add(telebot.types.KeyboardButton("Вернуться в главное меню"))
    return keyboard

# Инлайн клавиатура для подписки
def subscription_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("Подписаться", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    keyboard.add(telebot.types.InlineKeyboardButton("Проверить подписку", callback_data="check_subscription"))
    return keyboard

# Функция создания PDF
def create_pdf(user_id):
    filename = f"output_{user_id}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    y_position = height - 50

    c.setFont("DejaVuSans", 12)  # Устанавливаем шрифт по умолчанию

    for item in user_data[user_id].get('content', []):
        if isinstance(item, str) and not item.startswith('http'):  # Текст
            lines = item.split('\n')
            for line in lines:
                if line.strip().startswith('**') and line.strip().endswith('**'):
                    c.setFont("DejaVuSans-Bold", 12)  # Жирный шрифт
                    text = line.strip()[2:-2]  # Убираем ** с начала и конца
                else:
                    c.setFont("DejaVuSans", 12)  # Обычный шрифт
                    text = line
                c.drawString(50, y_position, text[:100])  # Ограничиваем длину строки
                y_position -= 20
        elif item.startswith('http'):  # Фото по URL
            try:
                response = requests.get(item)
                img = Image.open(BytesIO(response.content))
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                temp_img = f"temp_{user_id}.jpg"
                img.save(temp_img)
                img_width, img_height = img.size
                max_width = width - 100
                if img_width > max_width:
                    ratio = max_width / img_width
                    img_width = max_width
                    img_height = int(img_height * ratio)
                if y_position - img_height < 50:
                    c.showPage()
                    y_position = height - 50
                    c.setFont("DejaVuSans", 12)  # Восстанавливаем шрифт после новой страницы
                c.drawImage(temp_img, 50, y_position - img_height, 
                          width=img_width, height=img_height)
                y_position -= (img_height + 20)
            except Exception as e:
                c.setFont("DejaVuSans", 12)
                c.drawString(50, y_position, f"Ошибка загрузки фото: {str(e)}")
                y_position -= 20

    c.save()
    users_db[user_id]['requests'] += 1  # Увеличиваем счетчик запросов
    return filename

# Проверка подписки
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# Стартовая команда
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    
    if user_id not in users_db:
        users_db[user_id] = {
            'username': username,
            'reg_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'requests': 0
        }
    
    user_data[user_id] = {'content': []}
    
    if check_subscription(user_id) or user_id == ADMIN_ID:
        bot.reply_to(message, "Привет! Это сервис для конвертации текста и фото в PDF-формат.\n\nСоздано by @impaermax (admin - @maks_truestore)\n\nВыбери, что хочешь сделать:\n", 
                    reply_markup=main_keyboard())
    else:
        bot.reply_to(message, "Привет! Чтобы использовать бота, подпишись на наш канал:", 
                    reply_markup=subscription_keyboard())

# Команда админ-панели
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        bot.reply_to(message, "Добро пожаловать в админ-панель!", reply_markup=admin_keyboard())
    else:
        bot.reply_to(message, "Эта команда доступна только администратору.")

# Обработка проверки подписки
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def handle_subscription_check(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.edit_message_text("Отлично! Ты подписан. Выбери, что хочешь сделать:\n\nДля жирного текста используй **текст**\n\nАдмин? Используй /admin", 
                            call.message.chat.id, call.message.message_id, 
                            reply_markup=main_keyboard())
    else:
        bot.answer_callback_query(call.id, "Ты еще не подписан! Подпишись и проверь снова.")

# Обработка админ-команд
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text in ["Рассылка", "Выгрузить базу", "Вернуться в главное меню"])
def admin_commands(message):
    if message.text == "Рассылка":
        bot.reply_to(message, "Отправь сообщение для рассылки:")
        bot.register_next_step_handler(message, process_broadcast)
    elif message.text == "Выгрузить базу":
        with open('users_db.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Username', 'Registration Date', 'Requests'])
            for user_id, data in users_db.items():
                writer.writerow([user_id, data['username'], data['reg_date'], data['requests']])
        with open('users_db.csv', 'rb') as f:
            bot.send_document(message.chat.id, f)
        bot.reply_to(message, "База выгружена!", reply_markup=admin_keyboard())
    elif message.text == "Вернуться в главное меню":
        bot.reply_to(message, "Возвращаемся в главное меню!", reply_markup=main_keyboard())

def process_broadcast(message):
    for user_id in users_db.keys():
        try:
            bot.send_message(user_id, message.text)
        except:
            continue
    bot.reply_to(message, "Рассылка завершена!", reply_markup=admin_keyboard())

# Обработка кнопок
@bot.message_handler(func=lambda message: message.text in ["Text -> PDF", "Photo -> PDF", "Flexible -> PDF"])
def handle_buttons(message):
    user_id = message.from_user.id
    if not check_subscription(user_id) and user_id != ADMIN_ID:
        bot.reply_to(message, "Пожалуйста, подпишись на канал:", reply_markup=subscription_keyboard())
        return
    
    user_data[user_id] = {'content': []}
    
    if message.text == "Text -> PDF":
        bot.reply_to(message, "Отправь текст для PDF RU/EN")
        bot.register_next_step_handler(message, process_text_only)
    elif message.text == "Photo -> PDF":
        bot.reply_to(message, "Отправь фото или ссылку на фото (можно несколько)")
        bot.register_next_step_handler(message, process_photos_only)
    elif message.text == "Flexible -> PDF":
        bot.reply_to(message, "Отправляй текст, фото или ссылки в любом порядке. Выделение **жирным** появится позже. Напиши 'готово', когда закончишь")
        bot.register_next_step_handler(message, process_flexible)

# Обработка текста для Text -> PDF
def process_text_only(message):
    user_id = message.from_user.id
    user_data[user_id]['content'].append(message.text)
    pdf_file = create_pdf(user_id)
    with open(pdf_file, 'rb') as pdf:
        bot.send_document(message.chat.id, pdf, reply_markup=main_keyboard())
    bot.send_message(message.chat.id, "Готово! Что дальше?", reply_markup=main_keyboard())

# Обработка фото для Photo -> PDF
def process_photos_only(message):
    user_id = message.from_user.id
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        user_data[user_id]['content'].append(photo_url)
    elif message.text and message.text.startswith('http'):
        user_data[user_id]['content'].append(message.text)
    elif message.text.lower() == 'готово':
        pdf_file = create_pdf(user_id)
        with open(pdf_file, 'rb') as pdf:
            bot.send_document(message.chat.id, pdf, reply_markup=main_keyboard())
        bot.send_message(message.chat.id, "Готово! Что дальше?", reply_markup=main_keyboard())
        return
    
    bot.reply_to(message, "Отправь еще фото или напиши 'готово'")
    bot.register_next_step_handler(message, process_photos_only)

# Обработка гибкого ввода
def process_flexible(message):
    user_id = message.from_user.id
    
    if message.text and message.text.lower() == 'готово':
        if not user_data[user_id]['content']:
            bot.reply_to(message, "Ты ничего не отправил! Отправь текст или фото.")
            bot.register_next_step_handler(message, process_flexible)
            return
        pdf_file = create_pdf(user_id)
        with open(pdf_file, 'rb') as pdf:
            bot.send_document(message.chat.id, pdf, reply_markup=main_keyboard())
        bot.send_message(message.chat.id, "Готово! Что дальше?", reply_markup=main_keyboard())
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        user_data[user_id]['content'].append(photo_url)
        bot.reply_to(message, "Добавлено фото. Продолжай или напиши 'готово'")
        bot.register_next_step_handler(message, process_flexible)
    elif message.text and message.text.startswith('http'):
        user_data[user_id]['content'].append(message.text)
        bot.reply_to(message, "Добавлена ссылка на фото. Продолжай или напиши 'готово'")
        bot.register_next_step_handler(message, process_flexible)
    elif message.text:
        user_data[user_id]['content'].append(message.text)
        bot.reply_to(message, "Добавлен текст. Продолжай или напиши 'готово'")
        bot.register_next_step_handler(message, process_flexible)

# Запуск бота
bot.polling()
