from telegram import Update
from telegram.ext import ContextTypes

from database import (
    get_user_count, get_movie_count, get_total_views, get_premium_user_count,
    get_premium_users, get_admins, add_admin, remove_admin, get_setting,
    set_setting, get_user, set_premium, remove_premium as db_remove_premium,
    compact_database, cleanup_expired_premium,
)
from keyboards import (
    admins_keyboard, settings_keyboard, premium_settings_keyboard,
    payment_settings_keyboard, back_keyboard, main_admin_keyboard,
    admin_panel_inline,
)
from states import set_state, clear_state, get_data, update_data, clear_all_states
import states as st
from config import SUPER_ADMIN_ID


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_expired_premium()
    user_count = await get_user_count()
    movie_count = await get_movie_count()
    total_views = await get_total_views()
    premium_count = await get_premium_user_count()

    text = (
        '📊 <b>Statistika</b>\n\n'
        f'👥 Jami foydalanuvchilar: <b>{user_count}</b>\n'
        f'🎬 Jami kinolar: <b>{movie_count}</b>\n'
        f'👁 Jami ko\'rishlar: <b>{total_views}</b>\n'
        f'⭐ Premium foydalanuvchilar: <b>{premium_count}</b>\n\n'
        'Kerakli bo\'limni pastdagi tugmalardan tanlang.'
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=admin_panel_inline())
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=main_admin_keyboard())


async def admins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        '👮 <b>Adminlar bo\'limi</b>\n\n'
        'Bu yerda yangi admin qo\'shish, o\'chirish va ro\'yxatini ko\'rish mumkin.'
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=admins_keyboard())
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=main_admin_keyboard())


async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_state(update.effective_user.id, st.WAITING_ADMIN_ID)
    await update.callback_query.edit_message_text(
        '➕ Admin qo\'shish\n\nAdmin qilmoqchi bo\'lgan foydalanuvchi ID sini yuboring.',
        reply_markup=back_keyboard('admins')
    )


async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_admin_id = int((update.message.text or '').strip())
    except ValueError:
        await update.message.reply_text('❌ To\'g\'ri ID kiriting.')
        return

    user = await get_user(new_admin_id)
    if not user:
        await update.message.reply_text('❌ Bu foydalanuvchi hali botga start bermagan.')
        return

    await add_admin(new_admin_id, user['username'] or '', user['full_name'] or '')
    clear_state(update.effective_user.id)
    await update.message.reply_text('✅ Admin qo\'shildi.', reply_markup=main_admin_keyboard())


async def start_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_state(update.effective_user.id, st.WAITING_ADMIN_REMOVE_ID)
    await update.callback_query.edit_message_text(
        '➖ Adminni o\'chirish\n\nO\'chirmoqchi bo\'lgan admin ID sini yuboring.',
        reply_markup=back_keyboard('admins')
    )


async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int((update.message.text or '').strip())
    except ValueError:
        await update.message.reply_text('❌ To\'g\'ri ID kiriting.')
        return

    if target_id == SUPER_ADMIN_ID:
        await update.message.reply_text('❌ Asosiy adminni o\'chirib bo\'lmaydi.')
        return

    await remove_admin(target_id)
    clear_state(update.effective_user.id)
    await update.message.reply_text('✅ Admin o\'chirildi.', reply_markup=main_admin_keyboard())


async def show_admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = await get_admins()
    lines = [f'👑 Asosiy admin: <code>{SUPER_ADMIN_ID}</code>']
    for admin in admins:
        lines.append(f"• <code>{admin['user_id']}</code> — {admin['full_name'] or admin['username'] or 'Admin'}")
    text = '👮 <b>Adminlar ro\'yxati</b>\n\n' + '\n'.join(lines)
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=back_keyboard('admins'))


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sharing_on = (await get_setting('sharing_enabled')) == '1'
    premium_on = (await get_setting('premium_enabled')) == '1'
    card = await get_setting('payment_card') or 'sozlanmagan'
    text = (
        '⚙️ <b>Sozlamalar</b>\n\n'
        f'↗️ Ulashish: <b>{"Ruxsat etilgan" if sharing_on else "Taqiqlangan"}</b>\n'
        f'⭐ Premium: <b>{"Faol" if premium_on else "O\'chiq"}</b>\n'
        f'💳 To\'lov kartasi: <code>{card}</code>\n\n'
        'Kerakli bo\'limni tanlang.'
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode='HTML', reply_markup=settings_keyboard(sharing_on, premium_on)
        )
    else:
        await update.message.reply_text(
            text, parse_mode='HTML', reply_markup=main_admin_keyboard()
        )


async def toggle_sharing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = (await get_setting('sharing_enabled')) == '1'
    await set_setting('sharing_enabled', '0' if current else '1')
    await settings_menu(update, context)


async def payment_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card = await get_setting('payment_card') or 'sozlanmagan'
    note = await get_setting('payment_note') or 'yo\'q'
    text = (
        '💳 <b>To\'lov tizimlari</b>\n\n'
        f'Karta: <code>{card}</code>\n'
        f'Izoh: {note}\n\n'
        'Karta raqamini yoki foydalanuvchiga ko\'rinadigan izohni o\'zgartirish mumkin.'
    )
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=payment_settings_keyboard())


async def start_set_payment_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_state(update.effective_user.id, st.WAITING_PAYMENT_CARD)
    await update.callback_query.edit_message_text(
        '💳 Yangi karta raqamini yuboring.\nMasalan: <code>9860 1234 5678 9012</code>',
        parse_mode='HTML', reply_markup=back_keyboard('payment_settings')
    )


async def handle_payment_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card = (update.message.text or '').strip()
    if len(card) < 8:
        await update.message.reply_text('❌ Karta raqami juda qisqa.')
        return
    await set_setting('payment_card', card)
    clear_state(update.effective_user.id)
    await update.message.reply_text('✅ To\'lov kartasi saqlandi.', reply_markup=main_admin_keyboard())


async def start_set_payment_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_state(update.effective_user.id, st.WAITING_PAYMENT_NOTE)
    await update.callback_query.edit_message_text(
        '📝 To\'lovdan keyin foydalanuvchiga ko\'rinadigan izohni yuboring.',
        reply_markup=back_keyboard('payment_settings')
    )


async def handle_payment_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = (update.message.text or '').strip()
    await set_setting('payment_note', note)
    clear_state(update.effective_user.id)
    await update.message.reply_text('✅ To\'lov izohi saqlandi.', reply_markup=main_admin_keyboard())


async def premium_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    premium_on = (await get_setting('premium_enabled')) == '1'
    text = (
        '⭐ <b>Premium sozlamalari</b>\n\n'
        f'Holat: <b>{"Faol" if premium_on else "O\'chiq"}</b>\n\n'
        'Tariflar, foydalanuvchilar va qo\'lda premium berishni shu bo\'limdan boshqaring.'
    )
    await update.callback_query.edit_message_text(
        text, parse_mode='HTML', reply_markup=premium_settings_keyboard(premium_on)
    )


async def toggle_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = (await get_setting('premium_enabled')) == '1'
    await set_setting('premium_enabled', '0' if current else '1')
    await premium_settings_menu(update, context)


async def show_premium_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_expired_premium()
    users = await get_premium_users()
    if not users:
        text = '👥 Premium foydalanuvchilar yo\'q.'
    else:
        lines = []
        for u in users[:50]:
            expire = u['premium_expire'] or 'Lifetime'
            lines.append(f"• <code>{u['user_id']}</code> — {u['full_name'] or u['username'] or 'User'}\n  ⏳ {expire}")
        text = '👥 <b>Premium foydalanuvchilar</b>\n\n' + '\n'.join(lines)
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=back_keyboard('premium_settings'))


async def start_give_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_state(update.effective_user.id, st.WAITING_GIVE_PREMIUM_ID)
    await update.callback_query.edit_message_text(
        '➕ Premium berish\n\nFoydalanuvchi ID sini yuboring.',
        reply_markup=back_keyboard('premium_settings')
    )


async def handle_give_premium_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int((update.message.text or '').strip())
    except ValueError:
        await update.message.reply_text('❌ To\'g\'ri ID kiriting.')
        return

    user = await get_user(target_id)
    if not user:
        await update.message.reply_text('❌ Bu foydalanuvchi hali botga start bermagan.')
        return

    update_data(update.effective_user.id, premium_target_id=target_id)
    set_state(update.effective_user.id, st.WAITING_GIVE_PREMIUM_DAYS)
    await update.message.reply_text(
        'Necha kun premium berilsin?\n'
        'Masalan: <code>30</code>\n'
        'Lifetime uchun: <code>0</code>',
        parse_mode='HTML'
    )


async def handle_give_premium_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or '').strip()
    try:
        days = int(raw)
    except ValueError:
        await update.message.reply_text('❌ Kunni raqamda kiriting. Lifetime uchun 0 yuboring.')
        return

    data = get_data(update.effective_user.id)
    target_id = data.get('premium_target_id')
    if not target_id:
        clear_state(update.effective_user.id)
        await update.message.reply_text('❌ Jarayon bekor qilindi.', reply_markup=main_admin_keyboard())
        return

    if days < 0:
        await db_remove_premium(target_id)
        label = 'Premium olib tashlandi'
    else:
        await set_premium(target_id, None if days == 0 else days)
        label = 'Lifetime premium berildi' if days == 0 else f'{days} kun premium berildi'

    clear_state(update.effective_user.id)
    await update.message.reply_text(f'✅ {label}.', reply_markup=main_admin_keyboard())


async def clear_cache_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    states_cleared = clear_all_states()
    await compact_database()
    text = (
        '🧹 <b>Kesh tozalandi</b>\n\n'
        f'• State cache: {states_cleared} ta tozalandi\n'
        '• Database optimizatsiya qilindi\n'
        '• Muddati tugagan premiumlar tozalandi'
    )
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=back_keyboard('settings'))
