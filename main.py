import os
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки бота
API_TOKEN = os.getenv('BOT_TOKEN')
# Обновленная ссылка на вашу публичную группу
GROUP_USERNAME = "@Zayvka_na_auto"  # username вашей группы
CHANNEL_LINK = "https://t.me/auto_zakaz_dv"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Состояния диалога
class InterviewStates(StatesGroup):
    MODEL = State()
    SPECS = State()
    BUDGET = State()
    TIMEFRAME = State()
    NAME = State()
    PHONE = State()

# Валидация телефона
def format_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('8') and len(digits) == 11:
        return '+7' + digits[1:]
    elif digits.startswith('7') and len(digits) == 11:
        return '+' + digits
    elif digits.startswith('9') and len(digits) == 10:
        return '+7' + digits
    return phone

def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r'\D', '', phone)
    return len(digits) in (10, 11) and digits.isdigit()

# Обработчики сообщений
@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(InterviewStates.MODEL)
    await message.answer("Какие марки/модели авто вас интересуют? Укажите 1-3 варианта.")

@dp.message(InterviewStates.MODEL)
async def process_model(message: types.Message, state: FSMContext):
    await state.update_data(model=message.text)
    await state.set_state(InterviewStates.SPECS)
    await message.answer("Желаемые характеристики авто: год, объём двигателя, привод, пробег, цвет, комплектация и.т.д.")

@dp.message(InterviewStates.SPECS)
async def process_specs(message: types.Message, state: FSMContext):
    await state.update_data(specs=message.text)
    await state.set_state(InterviewStates.BUDGET)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 1 млн руб", callback_data="budget_1")],
        [InlineKeyboardButton(text="1-1.5 млн руб", callback_data="budget_1.5")],
        [InlineKeyboardButton(text="1.5-2 млн руб", callback_data="budget_2")],
        [InlineKeyboardButton(text="2-3 млн руб", callback_data="budget_3")],
        [InlineKeyboardButton(text="3-5 млн руб", callback_data="budget_5")],
        [InlineKeyboardButton(text="5+ млн руб", callback_data="budget_5plus")],
    ])
    
    await message.answer("Какой бюджет вы планируете на покупку авто с учетом таможенных расходов и доставки до РФ?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("budget_"))
async def process_budget(callback: types.CallbackQuery, state: FSMContext):
    budget_map = {
        "budget_1": "До 1 млн руб",
        "budget_1.5": "1-1.5 млн руб",
        "budget_2": "1.5-2 млн руб",
        "budget_3": "2-3 млн руб",
        "budget_5": "3-5 млн руб",
        "budget_5plus": "5+ млн руб"
    }
    
    await state.update_data(budget=budget_map[callback.data])
    await callback.message.edit_reply_markup(reply_markup=None)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Срочно (готов купить сейчас)", callback_data="time_now")],
        [InlineKeyboardButton(text="В ближайшую неделю", callback_data="time_week")],
        [InlineKeyboardButton(text="В этом месяце", callback_data="time_month")],
        [InlineKeyboardButton(text="Через 1-3 месяца", callback_data="time_1-3")],
        [InlineKeyboardButton(text="Пока смотрю варианты", callback_data="time_looking")],
    ])
    
    await callback.message.answer("Как срочно вы планируете покупку автомобиля?", reply_markup=keyboard)
    await state.set_state(InterviewStates.TIMEFRAME)

@dp.callback_query(F.data.startswith("time_"))
async def process_timeframe(callback: types.CallbackQuery, state: FSMContext):
    timeframe_map = {
        "time_now": "Срочно (готов купить сейчас)",
        "time_week": "В ближайшую неделю",
        "time_month": "В этом месяце",
        "time_1-3": "Через 1-3 месяца",
        "time_looking": "Пока смотрю варианты"
    }
    
    await state.update_data(timeframe=timeframe_map[callback.data])
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Проверяем релевантность по сроку покупки
    timeframe = callback.data
    if timeframe in ["time_now", "time_week", "time_month"]:
        # Релевантный клиент - продолжаем сбор данных
        await state.set_state(InterviewStates.NAME)
        await callback.message.answer("Укажите ваше имя:")
    else:
        # Не релевантный клиент - предлагаем подписаться на канал
        user_data = await state.get_data()
        await state.clear()
        
        await callback.message.answer(
            "Спасибо за ваши ответы! Пока вы рассматриваете варианты, "
            f"предлагаем вам подписаться на наш канал: {CHANNEL_LINK}\n\n"
            "Там мы регулярно публикуем актуальные предложения по авто из Китая. "
            "Когда будете готовы к покупке - возвращайтесь!",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(InterviewStates.NAME)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(InterviewStates.PHONE)
    await message.answer("Укажите ваш номер для связи")

@dp.message(InterviewStates.PHONE)
async def process_phone(message: types.Message, state: FSMContext):
    if not is_valid_phone(message.text):
        await message.answer("Пожалуйста, укажите корректный номер телефона")
        return
    
    formatted_phone = format_phone(message.text)
    user_data = await state.get_data()
    await state.clear()
    
    # Формируем сообщение для менеджера
    manager_message = (
        "🚨 НОВАЯ ЗАЯВКА\n\n"
        f"👤 Имя: {user_data.get('name', 'Не указано')}\n"
        f"📞 Телефон: {formatted_phone}\n"
        f"🚘 Модели: {user_data.get('model', 'Не указано')}\n"
        f"📋 Характеристики: {user_data.get('specs', 'Не указано')}\n"
        f"💰 Бюджет: {user_data.get('budget', 'Не указано')}\n"
        f"⏱ Срочность: {user_data.get('timeframe', 'Не указано')}\n\n"
        f"#заявка"
    )
    
    # Отправляем данные в группу
    try:
        await bot.send_message(chat_id=GROUP_USERNAME, text=manager_message)
        
        # Логируем успешную отправку
        logger.info(f"Заявка успешно отправлена в группу {GROUP_USERNAME}")
        
        await message.answer(
            "Спасибо, ваша заявка принята! Менеджер проведет мониторинг и калькуляцию "
            "по статистике интересующих вас авто и свяжется с вами в ближайшее время",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки заявки: {e}")
        
        # Сохраняем заявку в логах как резерв
        logger.info(f"НЕОТПРАВЛЕННАЯ ЗАЯВКА: {manager_message}")
        
        # Альтернативный способ связи
        await message.answer(
            "Спасибо за заявку! Наш менеджер свяжется с вами в ближайшее время "
            f"через {GROUP_USERNAME} или по указанному номеру телефона.",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(Command("cancel"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Диалог прерван. Для начала новой заявки используйте /start",
        reply_markup=ReplyKeyboardRemove()
    )

if __name__ == "__main__":
    logger.info("Запуск бота...")
    dp.run_polling(bot)