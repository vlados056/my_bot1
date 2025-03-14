import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from mistralai import Mistral
from pymongo import MongoClient
from datetime import datetime
from html import escape

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# API-ключи
MISTRAL_API_KEY = "QwNYwVDIn1twPdLuyC4duwKOlq2jdIff"
TELEGRAM_BOT_TOKEN = "7548078558:AAEgLod6Nz8w1URR1aD86C9sw7TN_9LShGs"
ADMIN_USER_ID = 7068066786
AGENTS = {
    "copywriting": "ag:6401fee4:20241209:kopirater:b3ebccc1",
    "rewriting": "ag:6401fee4:20241210:reraiter:86206ba7",
    "randomize": "ag:6401fee4:20241210:randomizator:620fd1b8",
    "keywords": "ag:6401fee4:20241210:kliuchevye:483580ed",
    "headlines": "ag:6401fee4:20241211:zagolovki:7f76e383",
}

# Инициализация Mistral
client = Mistral(api_key=MISTRAL_API_KEY)

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Прямые ссылки на изображения
IMAGE_URL_MENU = "https://imgur.com/EwRhwgH"
IMAGE_URL_COPYWRITTING = "https://imgur.com/q5ugZmu"
IMAGE_URL_REWRITTING = "https://imgur.com/l6BjPwN"
IMAGE_URL_RANDOMIZE = "https://imgur.com/kfK7Xw2"
IMAGE_URL_KEYWORDS = "https://imgur.com/sCFjVm2"
IMAGE_URL_HEADLINES = "https://imgur.com/wmWJQO5"
IMAGE_URL_ADDITIONAL = "https://imgur.com/Batathl"
IMAGE_URL_VERIFICATION = "https://imgur.com/TItnryq"
IMAGE_URL_PROMOTION = "https://imgur.com/AimcoqC"
IMAGE_URL_SUPPORT = "https://imgur.com/Ic58NtG"

# Функция для работы с Mistral AI
async def get_mistral_response(user_message: str, agent_id: str) -> str:
    try:
        chat_response = client.agents.complete(
            agent_id=agent_id,
            messages=[{"role": "user", "content": user_message}],
        )
        return chat_response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error interacting with Mistral AI: {e}")
        return "Произошла ошибка при взаимодействии с сервером."

# Функция для добавления пользователя в MongoDB
def add_user_to_db(user_id, user_name, username):
    uri = "mongodb+srv://mvstarcorp:UFnERtzkd9fwvqzm@cluster0.ihw7m.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=True"
    client = MongoClient(uri)

    try:
        database = client.get_database("DB_AA_BOT")
        users = database.get_collection("users_asist_avito")

        # Проверяем, есть ли пользователь в базе данных
        if users.count_documents({"user_id": user_id}) == 0:
            # Добавляем новый документ
            users.insert_one({
                "user_id": user_id,
                "user_name": user_name,
                "username": username,
                "registration_date": datetime.utcnow()
            })

    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя в базу данных: {e}")
    finally:
        client.close()

parse_mode = 'Markdown'

# Функция для проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id == ADMIN_USER_ID

@router.message(F.text.startswith("/send_message"))
async def send_message_to_all_users(message: Message):
    # Проверяем, является ли пользователь администратором
    if not is_admin(message.from_user.id):
        await message.answer("🚫 У вас нет прав для выполнения этой команды.")
        return

    # Получаем текст сообщения, убирая команду
    text = message.text.replace("/send_message", "").strip()

    if not text:
        await message.answer("❗ Пожалуйста, укажите сообщение, которое нужно отправить.")
        return

    # **Экранируем опасные символы в HTML**, чтобы избежать ошибок
    text = escape(text)

    # Подключение к базе данных MongoDB
    uri = "mongodb+srv://mvstarcorp:UFnERtzkd9fwvqzm@cluster0.ihw7m.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=True"
    client = MongoClient(uri)

    try:
        database = client.get_database("DB_AA_BOT")
        users = database.get_collection("users_asist_avito_1")

        # Получаем список всех пользователей
        user_ids = [user["user_id"] for user in users.find()]
        success_count = 0
        fail_count = 0

        for user_id in user_ids:
            try:
                # Отправляем сообщение пользователю
                await message.bot.send_message(user_id, text, parse_mode="HTML")
                success_count += 1
                await asyncio.sleep(0.5)  # Задержка для избежания флуд-контроля
            except Exception as e:
                logging.error(f"❌ Не удалось отправить сообщение пользователю {user_id}: {e}")
                fail_count += 1

    except Exception as e:
        logging.error(f"⚠ Ошибка при получении пользователей из базы данных: {e}")
    finally:
        client.close()

    # Отправляем подтверждение админу
    await message.answer(
        f"✅ <b>Сообщение успешно отправлено {success_count} пользователям.</b>\n❌ Ошибок: {fail_count}",
        parse_mode="HTML"
    )

# Функция для проверки подписки на канал
async def check_subscription(user_id: int) -> bool:
    CHANNEL_ID = '@vlad_avitolog_vn'  # Замените на ID вашего канала, например, '@mychannel' или '-1001234567890'
    try:
        user_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return user_status.status in ['member', 'creator', 'administrator']
    except Exception as e:
        logging.error(f"Ошибка при проверке подписки: {e}")
        return False

# Обработчик для команды /start
@router.message(F.text == "/start")
async def start_handler(message: types.Message):
    # Добавляем пользователя в базу данных
    add_user_to_db(message.from_user.id, message.from_user.full_name, message.from_user.username)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/+Qocmsf91GSNjMzFi")],
        [InlineKeyboardButton(text="Я уже подписан(а)", callback_data="check_subscription")]
    ])

    await message.answer("Привет! Подпишитесь на канал, чтобы получить доступ к боту.", reply_markup=keyboard)

# Обработчик для кнопки "Проверить подписку"
@router.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    await bot.answer_callback_query(callback.id)

    # Удаляем предыдущее сообщение и кнопки
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)

    # Отправляем сообщение о проверке подписки
    message = await bot.send_message(callback.message.chat.id, "Проверяю подписку...")

    # Задержка на 5 секунд
    await asyncio.sleep(5)

    # Удаляем сообщение о проверке подписки
    await bot.delete_message(callback.message.chat.id, message.message_id)

    if await check_subscription(user_id):
        await bot.send_message(callback.message.chat.id, "Вижу подписку. Держите доступ.")
        await open_main_menu(callback.message.chat.id)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/+Qocmsf91GSNjMzFi")],
            [InlineKeyboardButton(text="Я уже подписан(а)", callback_data="check_subscription")]
        ])
        await bot.send_message(callback.message.chat.id, "Подпишитесь на канал, чтобы получить доступ к боту.", reply_markup=keyboard)

# Обработчик для кнопки "Уже подписан"
@router.callback_query(F.data == "already_subscribed")
async def already_subscribed_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    await bot.answer_callback_query(callback.id)

    # Удаляем предыдущее сообщение и кнопки
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)

    # Отправляем сообщение о проверке подписки
    message = await bot.send_message(callback.message.chat.id, "Проверяю подписку...")

    # Задержка на 5 секунд
    await asyncio.sleep(5)

    # Удаляем сообщение о проверке подписки
    await bot.delete_message(callback.message.chat.id, message.message_id)

    if await check_subscription(user_id):
        await bot.send_message(callback.message.chat.id, "Вижу что ты подписался(лась) на мой канал. Вот доступ")
        await open_main_menu(callback.message.chat.id)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/+Qocmsf91GSNjMzFi")],
            [InlineKeyboardButton(text="Я уже подписан(а)", callback_data="check_subscription")]
        ])
        await bot.send_message(callback.message.chat.id, "Подпишитесь на канал, чтобы получить доступ к боту.", reply_markup=keyboard)

# Функция для открытия главного меню
async def open_main_menu(chat_id: int):
    await bot.send_photo(
        chat_id=chat_id,
        photo=IMAGE_URL_MENU,
        caption="Выберите нужную функцию в меню ниже.",
        reply_markup=get_main_menu()
    )

# Функция проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id == ADMIN_USER_ID

# Стартовое меню
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Дополнительные функции", callback_data="additional_functions")],
        [InlineKeyboardButton(text="📝 Копирайтинг", callback_data="copywriting")],
        [InlineKeyboardButton(text="✏️ Рерайтинг", callback_data="rewriting")],
        [InlineKeyboardButton(text="🔄 Рандомизация текста", callback_data="randomize")],
        [InlineKeyboardButton(text="🔍 Поиск ключевых запросов", callback_data="keywords")],
        [InlineKeyboardButton(text="📋 Подбор заголовков", callback_data="headlines")],
        [InlineKeyboardButton(text="⚡️ Написать в поддержку", callback_data="support")]
    ])

# Новое меню "Дополнительные функции"
def get_additional_functions_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Верификация профиля по ИП/ООО", callback_data="verification")],
        [InlineKeyboardButton(text="🔰 Продвижение на 50% дешевле", callback_data="promotion")],
        [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
    ])

# Обработчик для кнопки "Дополнительные функции"
@router.callback_query(F.data == "additional_functions")
async def additional_functions_handler(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_ADDITIONAL,
        caption="Выберите нужную функцию.",
        reply_markup=get_additional_functions_menu()
    )

# Обработка кнопки "✅ Верификация профиля по ИП/ООО"
@router.callback_query(F.data == "verification")
async def verification_handler(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_VERIFICATION,
        caption="Вы можете верифицировать новый профиль или уже имеющийся с помощью реквизитов ИП или ООО. \n\nДля получения подробной информации нажмите 'Узнать подробнее'.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Узнать подробнее", callback_data="verify_details")],
                [InlineKeyboardButton(text="Назад", callback_data="additional_functions"), InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Обработка кнопки "Узнать подробнее" в верификации профиля
@router.callback_query(F.data == "verify_details")
async def verify_details_handler(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_VERIFICATION,
        caption="Для получения информации и оплаты напишите, пожалуйста, @assit_avitoassis.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="additional_functions"), InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Обработка кнопки "🔰 Продвижение на 50% дешевле"
@router.callback_query(F.data == "promotion")
async def promotion_handler(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_PROMOTION,
        caption="С помощью данной методики Вы сможете покупать платные продвижения внутри Авито на 50% дешевле и экономить на этом рекламный бюджет до 40 - 50%! \n\nЭта методика не работает на новой функции продвижения с увеличением оплаты просмотра в товарке. \n\nДля получения подробной информации и оплаты нажмите 'Узнать подробнее'.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Узнать подробнее", callback_data="promotion_details")],
                [InlineKeyboardButton(text="Назад", callback_data="additional_functions"), InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Обработка кнопки "Узнать подробнее" в продвижении
@router.callback_query(F.data == "promotion_details")
async def promotion_details_handler(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_PROMOTION,
        caption="Для получения информации и оплаты напишите, пожалуйста, @assit_avitoassis.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="additional_functions"), InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Обработчик кнопки "Назад" или "Главное меню"
@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_MENU,
        caption="Выберите нужную функцию в меню ниже.",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "additional_functions")
async def back_to_additional_functions(callback: CallbackQuery):
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=IMAGE_URL_ADDITIONAL,
        caption="Выберите нужную функцию.",
        reply_markup=get_additional_functions_menu()
    )

# Callback-обработчик
@router.callback_query()
async def callback_handler(callback: CallbackQuery, state: FSMContext):
    action = callback.data

    if action in AGENTS:
        agent_id = AGENTS[action]
        await state.update_data(current_agent=agent_id)
        messages = {
            "copywriting": "Напишите нишу, характеристики и офферы для составления текста. \n\nНапишите как можно больше известной информации о Вашем товаре или услуге, чтобы я мог написать для Вас более детальный текст.",
            "rewriting": "Отправьте текст для рерайтинга.",
            "randomize": "С помощью данной функции вы можете подготовить текст для автозагрузки (масспостинга).\n\nОтправьте ваш текст для рандомизации.",
            "keywords": "Напишите 3 примера для подбора ключевых запросов.\n\nНапример: \nдоска обрезная, пиломатериалы бурс доска, пиломатериалы от производителя...",
            "headlines": "Напишите 3 примера заголовков для объявления.\n\nНапример: \nУстановка кондиционеров, Установка и продажа кондиционеров, Монтаж установка продажа кондиционера сплит систем...",
        }
        image_urls = {
            "copywriting": IMAGE_URL_COPYWRITTING,
            "rewriting": IMAGE_URL_REWRITTING,
            "randomize": IMAGE_URL_RANDOMIZE,
            "keywords": IMAGE_URL_KEYWORDS,
            "headlines": IMAGE_URL_HEADLINES,
        }

        # Удаляем старое сообщение
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)

        # Отправляем новое сообщение с картинкой и текстом
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=image_urls[action],
            caption=messages[action],
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]]
            )
        )
    elif action == "support":
        # Удаляем старое сообщение и отправляем информацию о поддержке
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=IMAGE_URL_SUPPORT,
            caption="Чтобы связаться с технической поддержкой, напишите пожалуйста @assit_avitoassis.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]]
            )
        )
    elif action == "main_menu":
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=IMAGE_URL_MENU,
            caption="Выберите нужную функцию в меню ниже.",
            reply_markup=get_main_menu()
        )
    elif action in {"like", "rewrite"}:
        # Удаляем сообщение с просьбой оценить результат
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)

        if action == "like":
            # Отправляем сообщение благодарности с кнопкой "Главное меню"
            await callback.message.answer(
                "Спасибо! Рад, что тебе понравилась моя работа!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]]
                )
            )
        elif action == "rewrite":
            # Отправляем сообщение о повторном запросе
            processing_message = await callback.message.answer("Одну минуту... Пишу новый вариант текста.")

            # Получаем данные для повторного запроса
            user_data = await state.get_data()
            agent_id = user_data.get("current_agent")
            user_message = user_data.get("user_message")

            if agent_id and user_message:
                response = await get_mistral_response(user_message, agent_id)

                # Удаляем сообщение о повторной обработке
                await bot.delete_message(chat_id=processing_message.chat.id, message_id=processing_message.message_id)

                # Отправляем новый результат
                max_length = 4096
                if len(response) > max_length:
                    for i in range(0, len(response), max_length):
                        await callback.message.answer(response[i:i + max_length])
                else:
                    await callback.message.answer(response)

                # Отправляем кнопки для новой оценки
                await callback.message.answer(
                    "Оцените результат:",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="Нравится", callback_data="like")],
                            [InlineKeyboardButton(text="Нужно переписать", callback_data="rewrite")],
                            [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
                        ]
                    )
                )
            else:
                await callback.message.answer("Ошибка: не удалось выполнить повторный запрос.")

# Обработка текстовых сообщений
@router.message()
async def text_message_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    agent_id = user_data.get("current_agent")

    if not agent_id:
        await message.answer("Выберите функцию в меню, прежде чем отправлять текст.")
        return

    user_message = message.text
    await state.update_data(user_message=user_message)

    # Отправляем сообщение "Обрабатываю запрос..." и сохраняем его
    processing_message = await message.answer("Обрабатываю запрос...")

    # Получаем результат от Mistral
    response = await get_mistral_response(user_message, agent_id)

    # Удаляем сообщение "Обрабатываю запрос..."
    await bot.delete_message(chat_id=processing_message.chat.id, message_id=processing_message.message_id)

    # Разбиваем длинный ответ, если необходимо
    max_length = 4096
    if len(response) > max_length:
        for i in range(0, len(response), max_length):
            await message.answer(response[i:i + max_length])
    else:
        await message.answer(response)

    # Отправляем кнопки для оценки результата
    await message.answer(
        "Оцените результат:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Нравится", callback_data="like")],
                [InlineKeyboardButton(text="Нужно переписать", callback_data="rewrite")],
                [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Основная функция
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
