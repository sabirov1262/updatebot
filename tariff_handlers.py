from telegram import Update
from telegram.ext import ContextTypes

from database import (
    add_tariff, get_tariffs, get_tariff, update_tariff, soft_delete_tariff
)
from keyboards import tariff_list_keyboard, tariff_manage_keyboard, back_keyboard, main_admin_keyboard
from states import set_state, clear_state, get_data, update_data
import states as st


async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tariffs = await get_tariffs(include_inactive=True)
    text = '📋 <b>Premium tariflar</b>\n\nIstalgan kun va istalgan summa bilan tarif qo\'shishingiz mumkin.'
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=tariff_list_keyboard(tariffs))


async def show_tariff_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_id: int):
    tariff = await get_tariff(tariff_id)
    if not tariff:
        await update.callback_query.edit_message_text('❌ Tarif topilmadi!', reply_markup=back_keyboard('premium_tariffs'))
        return

    days = 'Lifetime' if int(tariff['duration_days']) <= 0 else f"{tariff['duration_days']} kun"
    desc = tariff['description'] or 'Yo\'q'
    text = (
        f"📦 <b>{tariff['name']}</b>\n\n"
        f"📅 Muddat: {days}\n"
        f"💰 Narx: {tariff['price']:,} so'm\n"
        f"📝 Izoh: {desc}\n"
        f"💠 Holat: {'🟢 Faol' if tariff['is_active'] else '🔴 Nofaol'}"
    )
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=tariff_manage_keyboard(tariff_id))


async def start_add_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_state(update.effective_user.id, st.WAITING_TARIFF_NAME)
    await update.callback_query.edit_message_text(
        '➕ <b>Tarif qo\'shish</b>\n\nTarif nomini yuboring.\nMisol: 1 oylik premium',
        parse_mode='HTML', reply_markup=back_keyboard('premium_tariffs')
    )


async def handle_tariff_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or '').strip()
    if len(name) < 2:
        await update.message.reply_text('❌ Tarif nomi juda qisqa.')
        return
    update_data(update.effective_user.id, tariff_name=name)
    set_state(update.effective_user.id, st.WAITING_TARIFF_DAYS)
    await update.message.reply_text(
        '✅ Nom saqlandi.\n\nNecha kunlik?\n'
        'Masalan: <code>30</code>\n'
        'Lifetime uchun: <code>0</code>',
        parse_mode='HTML'
    )


async def handle_tariff_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or '').strip()
    try:
        days = int(raw)
    except ValueError:
        await update.message.reply_text('❌ Kunni raqam bilan kiriting. Lifetime uchun 0 yuboring.')
        return
    if days < 0:
        await update.message.reply_text('❌ Manfiy qiymat bo\'lmaydi.')
        return
    update_data(update.effective_user.id, tariff_days=days)
    set_state(update.effective_user.id, st.WAITING_TARIFF_PRICE)
    day_text = 'Lifetime' if days == 0 else f'{days} kun'
    await update.message.reply_text(f'✅ Muddat: <b>{day_text}</b>\n\nNarxini kiriting (so\'m):', parse_mode='HTML')


async def handle_tariff_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or '').strip().replace(' ', '').replace(',', '')
    try:
        price = int(raw)
    except ValueError:
        await update.message.reply_text('❌ Narxni raqamda kiriting!')
        return
    if price < 0:
        await update.message.reply_text('❌ Manfiy narx bo\'lmaydi!')
        return

    data = get_data(update.effective_user.id)
    name = data.get('tariff_name', '')
    days = data.get('tariff_days', 30)
    await add_tariff(name, days, price)
    clear_state(update.effective_user.id)
    day_text = 'Lifetime' if days == 0 else f'{days} kun'
    await update.message.reply_text(
        f"✅ <b>Tarif qo'shildi!</b>\n\n📦 {name}\n📅 {day_text}\n💰 {price:,} so'm",
        parse_mode='HTML', reply_markup=main_admin_keyboard()
    )


async def edit_tariff_field(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_id: int, field: str):
    update_data(update.effective_user.id, tariff_id=tariff_id, field=field)
    set_state(update.effective_user.id, st.WAITING_TARIFF_EDIT_VALUE)
    hints = {
        'name': 'yangi nom',
        'duration_days': 'yangi muddat (kun, lifetime uchun 0)',
        'price': 'yangi narx (so\'m)',
    }
    await update.callback_query.edit_message_text(
        f"✏️ {hints.get(field, field)}ni yuboring:",
        reply_markup=back_keyboard(f'tariff_{tariff_id}')
    )


async def handle_tariff_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_data(update.effective_user.id)
    tariff_id = data.get('tariff_id')
    field = data.get('field')
    value = (update.message.text or '').strip()

    if field in ['duration_days', 'price']:
        try:
            value = int(value.replace(' ', '').replace(',', ''))
        except ValueError:
            await update.message.reply_text('❌ Raqam kiriting!')
            return
        if value < 0:
            await update.message.reply_text('❌ Manfiy qiymat bo\'lmaydi!')
            return

    await update_tariff(tariff_id, field, value)
    clear_state(update.effective_user.id)
    await update.message.reply_text('✅ Tarif o\'zgartirildi!', reply_markup=main_admin_keyboard())


async def toggle_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_id: int):
    tariff = await get_tariff(tariff_id)
    if not tariff:
        await update.callback_query.edit_message_text('❌ Tarif topilmadi!')
        return
    new_status = 0 if tariff['is_active'] else 1
    await update_tariff(tariff_id, 'is_active', new_status)
    await show_tariff_detail(update, context, tariff_id)


async def delete_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_id: int):
    await soft_delete_tariff(tariff_id)
    await update.callback_query.edit_message_text('✅ Tarif o\'chirildi!', reply_markup=back_keyboard('premium_tariffs'))
