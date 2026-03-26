from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from database import (
    add_user, is_admin, get_setting, get_channels, get_movie,
    increment_views, get_tariffs, cleanup_expired_premium
)
from keyboards import main_admin_keyboard, main_user_keyboard, subscribe_keyboard
from states import get_state, clear_state
import states as st
import admin_handlers as adm
import movie_handlers as mv_h
import channel_handlers as ch_h
import tariff_handlers as tr_h
import broadcast_handlers as bc_h


async def admin_check(user_id: int) -> bool:
    return await is_admin(user_id)


async def check_subscription(bot, user_id: int, channels: list) -> list:
    not_subscribed = []
    for ch in channels:
        if ch['channel_type'] == 'link':
            continue
        try:
            member = await bot.get_chat_member(ch['channel_id'], user_id)
            if member.status in ['left', 'kicked', 'banned']:
                not_subscribed.append(ch)
        except TelegramError:
            not_subscribed.append(ch)
    return not_subscribed


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user(user.id, user.username or '', user.full_name or '')
    clear_state(user.id)
    await cleanup_expired_premium()

    args = context.args
    if args:
        await send_movie(update, context, args[0])
        return

    is_adm = await admin_check(user.id)
    if is_adm:
        await adm.show_statistics(update, context)
        return

    welcome = await get_setting('welcome_message')
    welcome = welcome.format(name=user.first_name) if welcome else f'👋 Assalomu alaykum {user.first_name}!\n\nKino kodini yuboring.'
    await update.message.reply_text(welcome, reply_markup=main_user_keyboard())


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    user = update.effective_user

    sub_required = await get_setting('subscription_required')
    if sub_required == '1':
        channels = await get_channels()
        if channels:
            not_sub = await check_subscription(context.bot, user.id, channels)
            if not_sub:
                await update.message.reply_text(
                    '⚠️ Kinoni ko\'rish uchun quyidagi kanallarga obuna bo\'ling:',
                    reply_markup=subscribe_keyboard(not_sub)
                )
                return

    movie = await get_movie(code)
    if not movie:
        await update.message.reply_text('❌ Bunday kodli kino topilmadi!')
        return

    await increment_views(code)
    caption = movie['caption'] or movie['title']
    try:
        if movie['file_type'] == 'video':
            await update.message.reply_video(movie['file_id'], caption=caption)
        elif movie['file_type'] == 'document':
            await update.message.reply_document(movie['file_id'], caption=caption)
        elif movie['file_type'] == 'photo':
            await update.message.reply_photo(movie['file_id'], caption=caption)
        else:
            await update.message.reply_video(movie['file_id'], caption=caption)
    except TelegramError as e:
        await update.message.reply_text(f'❌ Xatolik: {e}')


async def show_user_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tariffs = await get_tariffs(include_inactive=False)
    payment_card = await get_setting('payment_card') or 'sozlanmagan'
    payment_note = await get_setting('payment_note') or ''

    if tariffs:
        lines = []
        for t in tariffs[:20]:
            days = 'Lifetime' if int(t['duration_days']) <= 0 else f"{t['duration_days']} kun"
            lines.append(f"• <b>{t['name']}</b> — {days} — {t['price']:,} so'm")
        tariffs_text = '\n'.join(lines)
    else:
        tariffs_text = 'Hozircha tariflar qo\'shilmagan.'

    text = (
        '⭐ <b>Premium tariflar</b>\n\n'
        f'{tariffs_text}\n\n'
        f'💳 To\'lov kartasi: <code>{payment_card}</code>\n'
        f'📝 {payment_note}'
    )

    if update.message:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=main_user_keyboard())
    else:
        await update.callback_query.edit_message_text(text, parse_mode='HTML')


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    text = update.message.text or ''
    state = get_state(user.id)['state']
    is_adm = await admin_check(user.id)

    if text == '🏠 Boshqaruv' and is_adm:
        clear_state(user.id)
        await adm.show_statistics(update, context)
        return
    if text == '📊 Statistika' and is_adm:
        await adm.show_statistics(update, context)
        return
    if text == '📨 Xabar yuborish' and is_adm:
        await bc_h.start_broadcast(update, context)
        return
    if text == '🎬 Kinolar' and is_adm:
        await mv_h.movies_menu(update, context)
        return
    if text == '🔐 Kanallar' and is_adm:
        await ch_h.channels_menu(update, context)
        return
    if text == '👮 Adminlar' and is_adm:
        await adm.admins_menu(update, context)
        return
    if text == '⚙️ Sozlamalar' and is_adm:
        await adm.settings_menu(update, context)
        return

    if text == '⭐ Premium' and not is_adm:
        await show_user_premium(update, context)
        return
    if text == '🎬 Kinolar' and not is_adm:
        await update.message.reply_text('Kino kodini yuboring.', reply_markup=main_user_keyboard())
        return

    if state == st.WAITING_MOVIE_FILE:
        await mv_h.handle_movie_file(update, context)
        return
    if state == st.WAITING_MOVIE_CODE:
        await mv_h.handle_movie_code(update, context)
        return
    if state == st.WAITING_MOVIE_TITLE:
        await mv_h.handle_movie_title(update, context)
        return
    if state == st.WAITING_MOVIE_CAPTION:
        await mv_h.handle_movie_caption(update, context)
        return
    if state == st.WAITING_MOVIE_EDIT_CODE:
        await mv_h.handle_edit_code(update, context)
        return
    if state == st.WAITING_MOVIE_EDIT_VALUE:
        await mv_h.handle_edit_value(update, context)
        return
    if state == st.WAITING_MOVIE_DELETE_CODE:
        await mv_h.handle_delete_code(update, context)
        return
    if state == st.WAITING_CHANNEL_ID:
        await ch_h.handle_channel_id(update, context)
        return
    if state == st.WAITING_CHANNEL_NAME:
        await ch_h.handle_channel_name(update, context)
        return
    if state == st.WAITING_CHANNEL_LINK:
        await ch_h.handle_channel_link(update, context)
        return
    if state == st.WAITING_ADMIN_ID:
        await adm.handle_add_admin(update, context)
        return
    if state == st.WAITING_ADMIN_REMOVE_ID:
        await adm.handle_remove_admin(update, context)
        return
    if state == st.WAITING_BROADCAST_MSG:
        await bc_h.handle_broadcast_message(update, context)
        return
    if state == st.WAITING_TARIFF_NAME:
        await tr_h.handle_tariff_name(update, context)
        return
    if state == st.WAITING_TARIFF_DAYS:
        await tr_h.handle_tariff_days(update, context)
        return
    if state == st.WAITING_TARIFF_PRICE:
        await tr_h.handle_tariff_price(update, context)
        return
    if state == st.WAITING_TARIFF_EDIT_VALUE:
        await tr_h.handle_tariff_edit_value(update, context)
        return
    if state == st.WAITING_GIVE_PREMIUM_ID:
        await adm.handle_give_premium_id(update, context)
        return
    if state == st.WAITING_GIVE_PREMIUM_DAYS:
        await adm.handle_give_premium_days(update, context)
        return
    if state == st.WAITING_PAYMENT_CARD:
        await adm.handle_payment_card(update, context)
        return
    if state == st.WAITING_PAYMENT_NOTE:
        await adm.handle_payment_note(update, context)
        return

    if text and not text.startswith('/'):
        await send_movie(update, context, text.strip())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data == 'check_sub':
        channels = await get_channels()
        not_sub = await check_subscription(context.bot, user.id, channels)
        if not_sub:
            await query.edit_message_text(
                '⚠️ Hali ham obuna bo\'lmagansiz!\n\nQuyidagi kanallarga obuna bo\'ling:',
                reply_markup=subscribe_keyboard(not_sub)
            )
        else:
            await query.edit_message_text('✅ Rahmat! Endi kino kodini yuboring.')
        return

    is_adm = await admin_check(user.id)
    if not is_adm:
        await query.answer('❌ Ruxsat yo\'q!', show_alert=True)
        return

    if data in {'admin_back', 'stat'}:
        await adm.show_statistics(update, context)
    elif data == 'broadcast':
        await bc_h.start_broadcast(update, context)
    elif data == 'broadcast_normal':
        await bc_h.set_broadcast_normal(update, context)
    elif data == 'broadcast_forward':
        await bc_h.set_broadcast_forward(update, context)
    elif data == 'movies':
        await mv_h.movies_menu(update, context)
    elif data == 'movie_add':
        await mv_h.start_add_movie(update, context)
    elif data == 'movie_list':
        await mv_h.show_movie_list(update, context)
    elif data == 'movie_edit':
        await mv_h.start_edit_movie(update, context)
    elif data == 'movie_delete':
        await mv_h.start_delete_movie(update, context)
    elif data.startswith('mv_del_confirm_'):
        await mv_h.do_delete_movie(update, context, data.replace('mv_del_confirm_', ''))
    elif data.startswith('mv_del_'):
        await mv_h.confirm_delete_movie(update, context, data.replace('mv_del_', ''))
    elif data.startswith('mv_edit_title_'):
        await mv_h.edit_title(update, context, data.replace('mv_edit_title_', ''))
    elif data.startswith('mv_edit_caption_'):
        await mv_h.edit_caption(update, context, data.replace('mv_edit_caption_', ''))
    elif data.startswith('mv_'):
        await mv_h.show_movie_detail(update, context, data.replace('mv_', ''))
    elif data == 'channels':
        await ch_h.channels_menu(update, context)
    elif data == 'ch_add':
        await ch_h.start_add_channel(update, context)
    elif data.startswith('chtype_'):
        await ch_h.set_channel_type(update, context, data.replace('chtype_', ''))
    elif data == 'ch_list':
        await ch_h.show_channel_list(update, context)
    elif data == 'ch_delete':
        await ch_h.start_delete_channel(update, context)
    elif data.startswith('ch_del_confirm_'):
        await ch_h.do_delete_channel(update, context, data.replace('ch_del_confirm_', ''))
    elif data.startswith('ch_'):
        await ch_h.show_channel_detail(update, context, data.replace('ch_', ''))
    elif data == 'admins':
        await adm.admins_menu(update, context)
    elif data == 'admin_add':
        await adm.start_add_admin(update, context)
    elif data == 'admin_remove':
        await adm.start_remove_admin(update, context)
    elif data == 'admin_list':
        await adm.show_admin_list(update, context)
    elif data == 'settings':
        await adm.settings_menu(update, context)
    elif data == 'toggle_sharing':
        await adm.toggle_sharing(update, context)
    elif data == 'payment_settings':
        await adm.payment_settings(update, context)
    elif data == 'set_payment_card':
        await adm.start_set_payment_card(update, context)
    elif data == 'set_payment_note':
        await adm.start_set_payment_note(update, context)
    elif data == 'premium_settings':
        await adm.premium_settings_menu(update, context)
    elif data == 'toggle_premium':
        await adm.toggle_premium(update, context)
    elif data == 'premium_users':
        await adm.show_premium_users(update, context)
    elif data == 'premium_tariffs':
        await tr_h.show_tariffs(update, context)
    elif data == 'tariff_add':
        await tr_h.start_add_tariff(update, context)
    elif data.startswith('tariff_edit_name_'):
        await tr_h.edit_tariff_field(update, context, int(data.replace('tariff_edit_name_', '')), 'name')
    elif data.startswith('tariff_edit_days_'):
        await tr_h.edit_tariff_field(update, context, int(data.replace('tariff_edit_days_', '')), 'duration_days')
    elif data.startswith('tariff_edit_price_'):
        await tr_h.edit_tariff_field(update, context, int(data.replace('tariff_edit_price_', '')), 'price')
    elif data.startswith('tariff_toggle_'):
        await tr_h.toggle_tariff(update, context, int(data.replace('tariff_toggle_', '')))
    elif data.startswith('tariff_del_'):
        await tr_h.delete_tariff(update, context, int(data.replace('tariff_del_', '')))
    elif data.startswith('tariff_'):
        await tr_h.show_tariff_detail(update, context, int(data.replace('tariff_', '')))
    elif data == 'give_premium':
        await adm.start_give_premium(update, context)
    elif data == 'clear_cache':
        await adm.clear_cache_menu(update, context)
