# handlers/post_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging
import time

from config import config
from services import UserService, PostService
from keyboards import main_menu, cancel_keyboard, confirm_keyboard
from states import SellItem
from database import AsyncSessionLocal, User

router = Router()
user_service = UserService()
post_service = PostService()


@router.callback_query(F.data == "sell")
async def start_sell(callback: CallbackQuery, state: FSMContext):
    try:
        logging.info(f"🔘 Callback 'sell' от пользователя {callback.from_user.id}")
        
        # Проверка бана
        if callback.from_user.id not in config.ADMIN_IDS:
            is_banned = await user_service.is_user_banned(callback.from_user.id)
            if is_banned:
                await callback.answer("🚫 Вы заблокированы и не можете использовать бота.", show_alert=True)
                return
        
        profile = await user_service.get_user_profile(callback.from_user.id)

        # Безопасная проверка профиля
        if not profile:
            await callback.answer("❌ Ошибка: профиль не найден. Попробуйте перезапустить бота /start", show_alert=True)
            return

        if profile['cooldown'] > 0:
            await callback.answer(f"⏰ Кулдаун: {profile['cooldown']} мин до следующего поста", show_alert=True)
            return

        await callback.answer()  # Убираем индикатор загрузки
        
        await callback.message.answer(
            "📸 <b>Пришлите 1 фотографию товара</b>\n\n"
            "Отправьте одно фото товара для объявления.\n\n"
            "<i>После отправки фото автоматически перейдем к следующему шагу</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(SellItem.photos)
        await state.update_data(last_photo_processed=0)

    except Exception as e:
        logging.error(f"Ошибка начала продажи для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки профиля. Попробуйте позже.", show_alert=True)


@router.message(SellItem.photos, F.photo)
async def process_photos(message: Message, state: FSMContext):
    try:
        # Получаем текущее время
        current_time = time.time()
        data = await state.get_data()

        # Проверяем, не обрабатывали ли мы это сообщение в последние 2 секунды
        last_processed = data.get('last_photo_processed', 0)
        if current_time - last_processed < 2:
            return

        # Обновляем время последней обработки
        await state.update_data(last_photo_processed=current_time)

        # Берем только самое качественное фото (последнее в списке)
        photo = message.photo[-1]
        photo_id = photo.file_id

        await state.update_data(photo_ids=[photo_id])

        await message.answer(
            "✅ <b>Фото добавлено</b>\n\n"
            "📝 Теперь введите название товара:",
            parse_mode="HTML"
        )
        await state.set_state(SellItem.title)

    except Exception as e:
        logging.error(f"Ошибка обработки фото: {e}")
        await message.answer("❌ Ошибка обработки фото. Попробуйте еще раз.")


@router.message(SellItem.photos)
async def process_photos_invalid(message: Message):
    await message.answer("❌ Пожалуйста, отправьте ОДНО фото товара:")


@router.message(SellItem.title)
async def process_title(message: Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer("❌ Название должно быть не менее 5 символов:")
        return

    await state.update_data(title=message.text)
    await message.answer("💰 Введите цену в рублях (или 'торг'):")
    await state.set_state(SellItem.price)


@router.message(SellItem.price)
async def process_price(message: Message, state: FSMContext):
    price_text = message.text.strip().lower()

    # Проверяем на "торг"
    if price_text == "торг":
        await state.update_data(price="торг")
        await message.answer("📄 Введите описание товара:")
        await state.set_state(SellItem.description)
        return

    # Проверяем на "бесплатно" или "даром"
    if price_text in ["бесплатно", "даром", "0"]:
        await state.update_data(price="бесплатно")
        await message.answer("📄 Введите описание товара:")
        await state.set_state(SellItem.description)
        return

    # Убираем все пробелы и лишние символы
    clean_price = price_text.replace(" ", "").replace("руб", "").replace("р.", "").replace("р", "").replace(",",
                                                                                                            "").replace(
        ".", "")

    # Проверяем, что остались только цифры
    if clean_price.isdigit():
        price_num = int(clean_price)
        if price_num > 0:
            # Сохраняем ЧИСТУЮ цифру, без "руб"
            await state.update_data(price=str(price_num))
            await message.answer("📄 Введите описание товара:")
            await state.set_state(SellItem.description)
            return
        else:
            await message.answer("❌ Цена должна быть больше 0. Введите цену цифрами или 'торг':")
            return

    # Если не цифры и не торг - ошибка
    await message.answer(
        "❌ Неверный формат цены.\n\n"
        "✅ <b>Допустимые форматы:</b>\n"
        "• <b>1500</b> (только цифры)\n"
        "• <b>торг</b>\n"
        "• <b>бесплатно</b>",
        parse_mode="HTML"
    )


@router.message(SellItem.description)
async def process_description(message: Message, state: FSMContext):
    if len(message.text) < 10:
        await message.answer("❌ Описание должно быть не менее 10 символов:")
        return

    await state.update_data(description=message.text)

    data = await state.get_data()
    user_profile = await user_service.get_user_profile(message.from_user.id)

    # Безопасное получение username
    username = user_profile.get('username', 'без username') if user_profile else 'без username'

    # Определяем эмодзи для привилегии
    privilege_emoji = {
        "user": "👤",
        "vip": "💎",
        "premium": "⭐",
        "god": "👑",
        "ultra_seller": "🔥"
    }
    user_privilege = user_profile.get('privilege', 'user') if user_profile else 'user'
    privilege_emoji_icon = privilege_emoji.get(user_privilege, "⭐")
    privilege_label = user_profile.get('privilege', 'USER').upper() if user_profile else 'USER'

    # Форматируем цену для превью
    price_display = data['price']
    price_line = ""

    # Если цена - "торг" или "бесплатно", показываем просто текст без "Цена:"
    if price_display.lower() == "торг":
        price_line = "🤝 <b>Торг</b>"
    elif price_display.lower() == "бесплатно":
        price_line = "🎁 <b>Бесплатно</b>"
    elif price_display.isdigit():
        # Если цена - цифры, показываем с "Цена:"
        price_line = f"💰 <b>Цена:</b> <code>{price_display}</code> ₽"
    else:
        # На всякий случай, если что-то другое
        price_line = f"💰 <b>Цена:</b> {price_display}"

    preview_text = f"""
━━━━━━━━━━━━━━━━━━━━
<b>📦 {data['title']}</b>
━━━━━━━━━━━━━━━━━━━━

{price_line}

━━━━━━━━━━━━━━━━━━━━
<b>📝 Описание:</b>
━━━━━━━━━━━━━━━━━━━━

{data['description']}

━━━━━━━━━━━━━━━━━━━━
{privilege_emoji_icon} <b>Статус продавца:</b> {privilege_label}
━━━━━━━━━━━━━━━━━━━━

💬 <b>Написать продавцу:</b> Нажмите кнопку ниже ⬇️
"""

    # Показываем превью поста
    await message.answer_photo(
        photo=data['photo_ids'][0],
        caption=preview_text,
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(SellItem.confirm)


@router.callback_query(F.data == "confirm")
async def confirm_post(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения поста - работает всегда"""
    try:
        # Проверяем, есть ли данные в состоянии
        data = await state.get_data()
        if not data.get('photo_ids'):
            await callback.answer("❌ Нет данных для публикации. Начните заново.", show_alert=True)
            await state.clear()
            return

        user_profile = await user_service.get_user_profile(callback.from_user.id)

        # Безопасное получение username
        username = user_profile.get('username', 'без username') if user_profile else 'без username'

        post_data = {
            'photo_ids': data['photo_ids'],
            'title': data['title'],
            'price': data['price'],
            'description': data['description'],
            'username': username,
            'user_id': callback.from_user.id
        }

        post_id = await post_service.publish_to_channel(
            post_data,
            user_profile['privilege'] if user_profile else 'user'
        )

        await post_service.create_post(callback.from_user.id, post_data)

        # Важное логирование
        logging.info(
            f"Опубликован пост: UserID={callback.from_user.id}, Title={data['title']}, Photos={len(data['photo_ids'])}")

        # Автоматическая выдача VIP за 50 постов
        if user_profile and await user_service.check_vip_eligibility(callback.from_user.id):
            await user_service.update_privilege(callback.from_user.id, "vip")
            await callback.message.answer("🎉 Поздравляем! Вы получили VIP статус!")
            logging.info(f"Получен VIP статус: UserID={callback.from_user.id}")

        await callback.message.answer("✅ Объявление опубликовано в канале!")

    except Exception as e:
        await callback.message.answer("❌ Ошибка при публикации. Попробуйте позже.")
        logging.error(f"Ошибка публикации: {e}")

    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены - работает всегда"""
    try:
        await state.clear()

        # Отправляем новое сообщение с главным меню вместо редактирования
        await callback.message.answer(
            "❌ Действие отменено",
            reply_markup=main_menu(callback.from_user.id, config.ADMIN_IDS)
        )

        # Пытаемся удалить или изменить превью поста
        try:
            await callback.message.delete()
        except Exception:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer("❌ Действие отменено")
            except Exception:
                pass

    except Exception as e:
        logging.error(f"Ошибка в обработчике отмены: {e}")
        await callback.answer("❌ Ошибка отмены", show_alert=True)