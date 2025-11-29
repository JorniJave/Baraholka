from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from config import config
from services import AdminService
from keyboards import (admin_menu, privileges_management_keyboard,
                       privilege_edit_keyboard, cooldown_keyboard, price_keyboard)

router = Router()
admin_service = AdminService()


# ✅ СОСТОЯНИЯ ДЛЯ КАСТОМНЫХ ЗНАЧЕНИЙ
class PrivilegeStates(StatesGroup):
    waiting_custom_price = State()
    waiting_custom_cooldown = State()


@router.callback_query(F.data == "admin_privileges")
async def admin_privileges(callback: CallbackQuery):
    """Главное меню управления привилегиями"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        text = "⚙️ <b>Управление привилегиями</b>\n\n"
        text += "Выберите привилегию для настройки:"

        await callback.message.edit_text(text, reply_markup=privileges_management_keyboard(), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка управления привилегиями: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("edit_privilege_"))
async def edit_privilege(callback: CallbackQuery):
    """Редактирование конкретной привилегии"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        privilege_type = callback.data.replace("edit_privilege_", "")

        if privilege_type not in config.PRIVILEGES:
            await callback.answer("❌ Привилегия не найдена")
            return

        privilege_info = config.PRIVILEGES[privilege_type]

        text = f"<b>⚙️ Редактирование {privilege_info['label']}</b>\n\n"
        text += f"💰 Текущая цена: {privilege_info['price']} руб\n"
        text += f"⏰ Текущий кулдаун: {privilege_info['cooldown']} мин\n\n"
        text += "Выберите что изменить:"

        await callback.message.edit_text(text, reply_markup=privilege_edit_keyboard(privilege_type), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка редактирования привилегии: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("set_price_"))
async def set_price_menu(callback: CallbackQuery, state: FSMContext):
    """Меню установки цены"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        privilege_type = callback.data.replace("set_price_", "")

        privilege_info = config.PRIVILEGES[privilege_type]

        text = f"<b>💰 Установка цены для {privilege_info['label']}</b>\n\n"
        text += f"Текущая цена: {privilege_info['price']} руб\n\n"
        text += "Выберите новую цену или введите свою:"

        await callback.message.edit_text(text, reply_markup=price_keyboard(privilege_type), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка установки цены: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("set_cooldown_"))
async def set_cooldown_menu(callback: CallbackQuery, state: FSMContext):
    """Меню установки кулдауна"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        privilege_type = callback.data.replace("set_cooldown_", "")

        privilege_info = config.PRIVILEGES[privilege_type]

        text = f"<b>⏰ Установка кулдауна для {privilege_info['label']}</b>\n\n"
        text += f"Текущий кулдаун: {privilege_info['cooldown']} мин\n\n"
        text += "Выберите новое значение или введите свое:"

        await callback.message.edit_text(text, reply_markup=cooldown_keyboard(privilege_type), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка установки кулдауна: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("apply_price_"))
async def apply_price(callback: CallbackQuery):
    """Применение выбранной цены"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        data = callback.data.replace("apply_price_", "").split("_")
        privilege_type = data[0]
        price = int(data[1])

        # ✅ ОБНОВЛЯЕМ ЦЕНУ В КОНФИГЕ
        config.PRIVILEGES[privilege_type]["price"] = price

        privilege_info = config.PRIVILEGES[privilege_type]

        await callback.answer(f"✅ Цена установлена: {price} руб")

        # Возвращаемся к редактированию привилегии
        await edit_privilege(callback)

    except Exception as e:
        logging.error(f"Ошибка применения цены: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("apply_cooldown_"))
async def apply_cooldown(callback: CallbackQuery):
    """Применение выбранного кулдауна"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        data = callback.data.replace("apply_cooldown_", "").split("_")
        privilege_type = data[0]
        cooldown = int(data[1])

        # ✅ ОБНОВЛЯЕМ КУЛДАУН В КОНФИГЕ
        config.PRIVILEGES[privilege_type]["cooldown"] = cooldown

        privilege_info = config.PRIVILEGES[privilege_type]

        await callback.answer(f"✅ Кулдаун установлен: {cooldown} мин")

        # Возвращаемся к редактированию привилегии
        await edit_privilege(callback)

    except Exception as e:
        logging.error(f"Ошибка применения кулдауна: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("custom_price_"))
async def custom_price_input(callback: CallbackQuery, state: FSMContext):
    """Запрос кастомной цены"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        privilege_type = callback.data.replace("custom_price_", "")

        await state.set_state(PrivilegeStates.waiting_custom_price)
        await state.update_data(privilege_type=privilege_type)

        privilege_info = config.PRIVILEGES[privilege_type]

        text = f"<b>💰 Введите свою цену для {privilege_info['label']}</b>\n\n"
        text += f"Текущая цена: {privilege_info['price']} руб\n\n"
        text += "Отправьте число (только цифры):"

        await callback.message.edit_text(text, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка запроса кастомной цены: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("custom_cooldown_"))
async def custom_cooldown_input(callback: CallbackQuery, state: FSMContext):
    """Запрос кастомного кулдауна"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        privilege_type = callback.data.replace("custom_cooldown_", "")

        await state.set_state(PrivilegeStates.waiting_custom_cooldown)
        await state.update_data(privilege_type=privilege_type)

        privilege_info = config.PRIVILEGES[privilege_type]

        text = f"<b>⏰ Введите свой кулдаун для {privilege_info['label']}</b>\n\n"
        text += f"Текущий кулдаун: {privilege_info['cooldown']} мин\n\n"
        text += "Отправьте число (минуты, только цифры):"

        await callback.message.edit_text(text, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка запроса кастомного кулдауна: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(PrivilegeStates.waiting_custom_price)
async def process_custom_price(message: Message, state: FSMContext):
    """Обработка кастомной цены"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            await state.clear()
            return

        data = await state.get_data()
        privilege_type = data.get('privilege_type')

        if not message.text.isdigit():
            await message.answer("❌ Введите только цифры:")
            return

        price = int(message.text)

        if price <= 0:
            await message.answer("❌ Цена должна быть больше 0:")
            return

        # ✅ ОБНОВЛЯЕМ ЦЕНУ В КОНФИГЕ
        config.PRIVILEGES[privilege_type]["price"] = price

        privilege_info = config.PRIVILEGES[privilege_type]

        await message.answer(f"✅ Цена для {privilege_info['label']} установлена: {price} руб")

        # Возвращаемся к редактированию привилегии
        await edit_privilege_from_message(message, privilege_type)

        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка обработки кастомной цены: {e}")
        await message.answer("❌ Ошибка установки цены")
        await state.clear()


@router.message(PrivilegeStates.waiting_custom_cooldown)
async def process_custom_cooldown(message: Message, state: FSMContext):
    """Обработка кастомного кулдауна"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            await state.clear()
            return

        data = await state.get_data()
        privilege_type = data.get('privilege_type')

        if not message.text.isdigit():
            await message.answer("❌ Введите только цифры:")
            return

        cooldown = int(message.text)

        if cooldown <= 0:
            await message.answer("❌ Кулдаун должен быть больше 0:")
            return

        # ✅ ОБНОВЛЯЕМ КУЛДАУН В КОНФИГЕ
        config.PRIVILEGES[privilege_type]["cooldown"] = cooldown

        privilege_info = config.PRIVILEGES[privilege_type]

        await message.answer(f"✅ Кулдаун для {privilege_info['label']} установлен: {cooldown} мин")

        # Возвращаемся к редактированию привилегии
        await edit_privilege_from_message(message, privilege_type)

        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка обработки кастомного кулдауна: {e}")
        await message.answer("❌ Ошибка установки кулдауна")
        await state.clear()


async def edit_privilege_from_message(message: Message, privilege_type: str):
    """Вспомогательная функция для возврата к редактированию привилегии"""
    privilege_info = config.PRIVILEGES[privilege_type]

    text = f"<b>⚙️ Редактирование {privilege_info['label']}</b>\n\n"
    text += f"💰 Текущая цена: {privilege_info['price']} руб\n"
    text += f"⏰ Текущий кулдаун: {privilege_info['cooldown']} мин\n\n"
    text += "Выберите что изменить:"

    await message.answer(text, reply_markup=privilege_edit_keyboard(privilege_type), parse_mode="HTML")