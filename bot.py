from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from database import (
    create_database,
    save_user,
    save_rank,
    get_user,
    get_rank,
    is_banned,
    create_party,
    get_active_party,
    get_party,
    cancel_active_party,
    get_active_parties_for_rank,
    get_available_users_for_party,
    add_party_match,
    get_match,
    set_match_status,
    count_accepted_players,
    count_pending_players,
    mark_party_filled,
    can_create_request,
    expire_old_parties,
    get_all_users,
    ban_user,
    unban_user,
    get_all_active_parties,
    admin_cancel_party,
    save_admin_message,
    get_admin_messages,
    mark_admin_message_answered,
    get_statistics
)


# =========================================================
# TOKEN
# =========================================================

import os

TOKEN = os.getenv("BOT_TOKEN")
application = ApplicationBuilder().token(TOKEN).build()


# =========================================================
# ADMIN
# =========================================================
#
# اینجا Telegram ID خودت را قرار بده.
#
# مثال:
# ADMIN_IDS = {908592959}
#
# =========================================================

ADMIN_IDS = {
    908592959
}


# =========================================================
# RANKS
# =========================================================

RANKS = {
    "iron": "Iron",
    "bronze": "Bronze",
    "silver": "Silver",
    "gold": "Gold",
    "platinum": "Platinum",
    "diamond": "Diamond",
    "ascendant": "Ascendant",
    "immortal": "Immortal",
    "radiant": "Radiant"
}


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎯 رنک من",
                callback_data="my_rank"
            ),
            InlineKeyboardButton(
                "👤 پروفایل من",
                callback_data="profile"
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 پیدا کردن یار",
                callback_data="find_player"
            )
        ],
        [
            InlineKeyboardButton(
                "📩 ارتباط با ادمین",
                callback_data="contact_admin"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو درخواست",
                callback_data="cancel_request"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ راهنما",
                callback_data="help"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# RANK MENU
# =========================================================

def rank_menu(prefix):

    keyboard = []
    row = []

    for key, name in RANKS.items():

        row.append(
            InlineKeyboardButton(
                name,
                callback_data=f"{prefix}_{key}"
            )
        )

        if len(row) == 3:

            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="main_menu"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    return user_id in ADMIN_IDS


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    save_user(
        user.id,
        user.username or user.first_name
    )

    context.user_data.clear()

    expire_old_parties()

    if is_banned(user.id):

        await update.message.reply_text(
            "🚫 حساب شما از استفاده از ربات محروم شده است.\n\n"
            "در صورت اعتراض با ادمین ارتباط بگیرید."
        )

        return

    await update.message.reply_text(
        "🎮 سلام!\n\n"
        "به Valorant Party Finder خوش اومدی.\n\n"
        "🎯 رنکت رو ثبت کن\n"
        "🔎 هم‌تیمی پیدا کن\n"
        "🎮 Party بساز و کد رو ارسال کن",
        reply_markup=main_menu()
    )


# =========================================================
# MY RANK
# =========================================================

async def show_my_rank(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if is_banned(query.from_user.id):
        await query.edit_message_text(
            "🚫 حساب شما Ban شده است."
        )
        return

    await query.edit_message_text(
        "🎯 رنک خودت رو انتخاب کن:",
        reply_markup=rank_menu("myrank")
    )


# =========================================================
# SAVE MY RANK
# =========================================================

async def save_my_rank(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if is_banned(user_id):

        await query.edit_message_text(
            "🚫 حساب شما Ban شده است."
        )

        return

    rank_key = query.data.replace(
        "myrank_",
        ""
    )

    rank_name = RANKS.get(rank_key)

    if not rank_name:
        return

    save_rank(
        user_id,
        rank_name
    )

    # بررسی Partyهای فعال
    # با رنک انتخاب‌شده

    active_parties = get_active_parties_for_rank(
        rank_name
    )

    notified = False

    for party in active_parties:

        party_id = party[0]
        creator_id = party[1]
        players_needed = party[3]

        if creator_id == user_id:
            continue

        accepted = count_accepted_players(
            party_id
        )

        pending = count_pending_players(
            party_id
        )

        if accepted + pending >= players_needed:
            continue

        if get_match(
            party_id,
            user_id
        ):
            continue

        try:

            keyboard = [[
                InlineKeyboardButton(
                    "✅ قبول می‌کنم",
                    callback_data=f"accept_{party_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد می‌کنم",
                    callback_data=f"reject_{party_id}"
                )
            ]]

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🔥 یک Party مناسب برایت پیدا شد!\n\n"
                    f"🎯 رنک موردنیاز: {rank_name}\n\n"
                    "آیا می‌خواهی به این Party ملحق شوی؟\n\n"
                    "با قبول کردن، Party Code برایت ارسال می‌شود."
                ),
                reply_markup=InlineKeyboardMarkup(
                    keyboard
                )
            )

            add_party_match(
                party_id,
                user_id
            )

            notified = True

            break

        except Exception:
            continue

    text = (
        "✅ رنکت با موفقیت ثبت شد!\n\n"
        f"🎯 رنک: {rank_name}"
    )

    if notified:

        text += (
            "\n\n🔥 یک Party مناسب برایت پیدا شد."
        )

    await query.edit_message_text(
        text,
        reply_markup=main_menu()
    )


# =========================================================
# FIND PLAYER
# =========================================================

async def find_player(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if is_banned(user_id):

        await query.edit_message_text(
            "🚫 حساب شما Ban شده است."
        )

        return

    context.user_data.clear()

    active_party = get_active_party(
        user_id
    )

    if active_party:

        await query.edit_message_text(
            "⚠️ تو در حال حاضر یک Party فعال داری.\n\n"
            "اول درخواست فعلی رو لغو کن.",
            reply_markup=main_menu()
        )

        return

    allowed, remaining = can_create_request(
        user_id
    )

    if not allowed:

        await query.edit_message_text(
            "🛡️ کمی صبر کن!\n\n"
            f"⏳ {remaining} ثانیه دیگه "
            "می‌تونی درخواست جدید بسازی.",
            reply_markup=main_menu()
        )

        return

    # شروع انتخاب رنک‌ها

    context.user_data[
        "required_ranks"
    ] = []

    await show_required_ranks(
        query,
        context
    )


# =========================================================
# REQUIRED RANKS - MAX 3
# =========================================================

async def show_required_ranks(
    query,
    context
):

    selected = context.user_data.get(
        "required_ranks",
        []
    )

    keyboard = []
    row = []

    for key, name in RANKS.items():

        if name in selected:
            text = f"✅ {name}"
        else:
            text = name

        row.append(
            InlineKeyboardButton(
                text,
                callback_data=f"reqrank_{key}"
            )
        )

        if len(row) == 3:

            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # تعداد انتخاب
    keyboard.append([
        InlineKeyboardButton(
            f"✅ تأیید رنک‌ها ({len(selected)}/3)",
            callback_data="confirm_ranks"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="main_menu"
        )
    ])

    selected_text = (
        "، ".join(selected)
        if selected
        else "هنوز انتخاب نشده"
    )

    await query.edit_message_text(
        "🎯 رنک موردنیاز را انتخاب کن.\n\n"
        "حداکثر ۳ رنک می‌توانی انتخاب کنی.\n\n"
        f"انتخاب‌شده: {selected_text}",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# SELECT REQUIRED RANK
# =========================================================

async def select_required_rank(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    rank_key = query.data.replace(
        "reqrank_",
        ""
    )

    rank_name = RANKS.get(rank_key)

    if not rank_name:
        return

    selected = context.user_data.get(
        "required_ranks",
        []
    )

    # اگر قبلاً انتخاب شده بود
    if rank_name in selected:

        selected.remove(rank_name)

    else:

        if len(selected) >= 3:

            await query.answer(
                "❌ حداکثر ۳ رنک می‌توانی انتخاب کنی.",
                show_alert=True
            )

            return

        selected.append(rank_name)

    context.user_data[
        "required_ranks"
    ] = selected

    await show_required_ranks(
        query,
        context
    )


# =========================================================
# CONFIRM RANKS
# =========================================================

async def confirm_required_ranks(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    selected = context.user_data.get(
        "required_ranks",
        []
    )

    if not selected:

        await query.answer(
            "❌ حداقل یک رنک انتخاب کن.",
            show_alert=True
        )

        return

    keyboard = [
        [
            InlineKeyboardButton(
                "1 نفر",
                callback_data="players_1"
            ),
            InlineKeyboardButton(
                "2 نفر",
                callback_data="players_2"
            )
        ],
        [
            InlineKeyboardButton(
                "3 نفر",
                callback_data="players_3"
            ),
            InlineKeyboardButton(
                "4 نفر",
                callback_data="players_4"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="find_player"
            )
        ]
    ]

    ranks_text = " + ".join(selected)

    await query.edit_message_text(
        "🎯 رنک‌های موردنیاز:\n\n"
        f"{ranks_text}\n\n"
        "👥 چند نفر هم‌تیمی می‌خوای؟",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# NUMBER OF PLAYERS
# =========================================================

async def choose_players(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    players_needed = int(
        query.data.replace(
            "players_",
            ""
        )
    )

    context.user_data[
        "players_needed"
    ] = players_needed

    required_ranks = context.user_data.get(
        "required_ranks"
    )

    if not required_ranks:

        context.user_data.clear()

        await query.edit_message_text(
            "❌ اطلاعات درخواست پیدا نشد.",
            reply_markup=main_menu()
        )

        return

    context.user_data[
        "waiting_for_party_code"
    ] = True

    ranks_text = " + ".join(
        required_ranks
    )

    await query.edit_message_text(
        "🔑 حالا Party Code ولورانت رو بفرست.\n\n"
        f"🎯 رنک‌ها: {ranks_text}\n"
        f"👥 تعداد نفر: {players_needed}\n\n"
        "فقط خود کد رو ارسال کن."
    )


# =========================================================
# SEND PARTY OFFER
# =========================================================

async def send_party_offer(
    bot,
    party_id,
    user_id
):

    party = get_party(
        party_id
    )

    if not party:
        return False

    if party[5] != "active":
        return False

    required_rank = party[2]

    keyboard = [[
        InlineKeyboardButton(
            "✅ قبول می‌کنم",
            callback_data=f"accept_{party_id}"
        ),
        InlineKeyboardButton(
            "❌ رد می‌کنم",
            callback_data=f"reject_{party_id}"
        )
    ]]

    try:

        await bot.send_message(
            chat_id=user_id,
            text=(
                "🔥 Party مناسب برایت پیدا شد!\n\n"
                f"🎯 رنک موردنیاز:\n"
                f"{required_rank}\n\n"
                "آیا می‌خواهی به Party ملحق شوی؟\n\n"
                "🔑 Party Code بعد از قبول نمایش داده می‌شود."
            ),
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        add_party_match(
            party_id,
            user_id
        )

        return True

    except Exception:

        return False


# =========================================================
# FILL PARTY OFFERS
# =========================================================

async def fill_party_offers(
    bot,
    party_id
):

    party = get_party(
        party_id
    )

    if not party:
        return

    if party[5] != "active":
        return

    creator_id = party[1]
    required_rank = party[2]
    players_needed = party[3]

    accepted = count_accepted_players(
        party_id
    )

    pending = count_pending_players(
        party_id
    )

    remaining = (
        players_needed
        - accepted
        - pending
    )

    if remaining <= 0:
        return

    users = get_available_users_for_party(
        required_rank,
        creator_id,
        party_id,
        remaining
    )

    for user in users:

        user_id = user[0]

        await send_party_offer(
            bot,
            party_id,
            user_id
        )


# =========================================================
# RECEIVE PARTY CODE
# =========================================================

async def receive_party_code(
    update,
    context
):

    user = update.effective_user
    user_id = user.id

    if is_banned(user_id):

        await update.message.reply_text(
            "🚫 حساب شما Ban شده است."
        )

        return

    if context.user_data.get(
        "admin_reply_user"
    ):

        if not is_admin(user_id):

            context.user_data.clear()

        else:

            target_id = context.user_data[
                "admin_reply_user"
            ]

            text = update.message.text.strip()

            try:

                await context.bot.send_message(
                    chat_id=target_id,
                    text=(
                        "👑 پاسخ ادمین:\n\n"
                        f"{text}"
                    )
                )

                await update.message.reply_text(
                    "✅ پیام برای کاربر ارسال شد.",
                    reply_markup=admin_menu()
                )

                context.user_data.clear()

                return

            except Exception:

                await update.message.reply_text(
                    "❌ ارسال پیام انجام نشد.",
                    reply_markup=admin_menu()
                )

                context.user_data.clear()

                return

    # پیام کاربر به ادمین

    if context.user_data.get(
        "contact_admin"
    ):

        text = update.message.text.strip()

        message_id = save_admin_message(
            user_id,
            text
        )

        await update.message.reply_text(
            "✅ پیام شما برای ادمین ارسال شد.\n\n"
            "به‌زودی پاسخ دریافت می‌کنی.",
            reply_markup=main_menu()
        )

        # ارسال به تمام ادمین‌ها

        username = (
            f"@{user.username}"
            if user.username
            else user.first_name
        )

        for admin_id in ADMIN_IDS:

            try:

                keyboard = [[
                    InlineKeyboardButton(
                        "💬 پاسخ",
                        callback_data=f"adminreply_{user_id}"
                    ),
                    InlineKeyboardButton(
                        "🚫 Ban",
                        callback_data=f"adminban_{user_id}"
                    )
                ]]

                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "📩 پیام جدید از کاربر\n\n"
                        f"🆔 ID: {user_id}\n"
                        f"👤 {username}\n\n"
                        f"💬 {text}"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        keyboard
                    )
                )

            except Exception:
                pass

        context.user_data.clear()

        return

    # Party Code

    if not context.user_data.get(
        "waiting_for_party_code"
    ):

        await update.message.reply_text(
            "از منوی زیر یک گزینه رو انتخاب کن:",
            reply_markup=main_menu()
        )

        return

    party_code = update.message.text.strip()

    if len(party_code) < 3 or len(party_code) > 50:

        await update.message.reply_text(
            "❌ Party Code معتبر نیست.\n\n"
            "کد رو دوباره ارسال کن."
        )

        return

    required_ranks = context.user_data.get(
        "required_ranks"
    )

    players_needed = context.user_data.get(
        "players_needed"
    )

    if not required_ranks or not players_needed:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ اطلاعات درخواست از بین رفته.",
            reply_markup=main_menu()
        )

        return

    existing_party = get_active_party(
        user_id
    )

    if existing_party:

        context.user_data.clear()

        await update.message.reply_text(
            "⚠️ تو یک Party فعال داری.",
            reply_markup=main_menu()
        )

        return

    allowed, remaining = can_create_request(
        user_id
    )

    if not allowed:

        context.user_data.clear()

        await update.message.reply_text(
            f"🛡️ کمی صبر کن.\n\n"
            f"⏳ {remaining} ثانیه باقی مونده.",
            reply_markup=main_menu()
        )

        return

    # برای دیتابیس فعلی
    # رنک‌ها را با + ذخیره می‌کنیم

    required_ranks_text = " + ".join(
        required_ranks
    )

    party_id = create_party(
        creator_id=user_id,
        required_rank=required_ranks_text,
        players_needed=players_needed,
        party_code=party_code
    )

    context.user_data.clear()

    # ارسال Offer به بازیکنان مناسب
    #
    # برای چند رنک، هر رنک را جدا بررسی می‌کنیم.
    #
    # فعلاً ساختار DB یک رشته مثل:
    # Gold + Platinum + Diamond
    #
    # را نگه می‌دارد.

    all_users = get_all_users()

    sent_count = 0

    for matched_user in all_users:

        matched_id = matched_user[0]
        matched_rank = matched_user[2]
        matched_banned = matched_user[4]

        if matched_id == user_id:
            continue

        if matched_banned:
            continue

        if matched_rank not in required_ranks:
            continue

        accepted = count_accepted_players(
            party_id
        )

        pending = count_pending_players(
            party_id
        )

        if accepted + pending >= players_needed:
            break

        if get_match(
            party_id,
            matched_id
        ):
            continue

        success = await send_party_offer(
            context.bot,
            party_id,
            matched_id
        )

        if success:
            sent_count += 1

    ranks_text = " + ".join(
        required_ranks
    )

    if sent_count:

        status_text = (
            f"🔥 درخواست برای {sent_count} بازیکن ارسال شد."
        )

    else:

        status_text = (
            "🔎 فعلاً بازیکن مناسبی پیدا نشد.\n\n"
            "اگر بازیکن جدیدی با این رنک وارد شود، "
            "درخواست بررسی خواهد شد."
        )

    await update.message.reply_text(
        "✅ Party Finder ساخته شد!\n\n"
        f"🎯 رنک‌های موردنیاز:\n"
        f"{ranks_text}\n\n"
        f"👥 تعداد: {players_needed}\n\n"
        f"{status_text}\n\n"
        "⏱️ اعتبار درخواست: ۱۵ دقیقه",
        reply_markup=main_menu()
    )


# =========================================================
# ACCEPT
# =========================================================

async def accept_party(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if is_banned(user_id):

        await query.edit_message_text(
            "🚫 حساب شما Ban شده است."
        )

        return

    party_id = int(
        query.data.replace(
            "accept_",
            ""
        )
    )

    party = get_party(
        party_id
    )

    if not party:

        await query.edit_message_text(
            "❌ Party پیدا نشد.",
            reply_markup=main_menu()
        )

        return

    creator_id = party[1]
    required_rank = party[2]
    players_needed = party[3]
    party_code = party[4]
    status = party[5]

    if status != "active":

        await query.edit_message_text(
            "⏱️ این Party دیگر فعال نیست.",
            reply_markup=main_menu()
        )

        return

    match = get_match(
        party_id,
        user_id
    )

    if not match:

        await query.edit_message_text(
            "❌ دعوت پیدا نشد.",
            reply_markup=main_menu()
        )

        return

    if match[3] != "pending":

        await query.edit_message_text(
            "ℹ️ قبلاً به این دعوت پاسخ داده‌ای.",
            reply_markup=main_menu()
        )

        return

    accepted_count = count_accepted_players(
        party_id
    )

    if accepted_count >= players_needed:

        mark_party_filled(
            party_id
        )

        await query.edit_message_text(
            "❌ ظرفیت Party تکمیل شده.",
            reply_markup=main_menu()
        )

        return

    # قبول
    set_match_status(
        party_id,
        user_id,
        "accepted"
    )

    new_count = count_accepted_players(
        party_id
    )

    await query.edit_message_text(
        "✅ با موفقیت قبول کردی!\n\n"
        f"🎯 رنک موردنیاز:\n"
        f"{required_rank}\n\n"
        f"🔑 Party Code:\n"
        f"`{party_code}`\n\n"
        "وارد Valorant شو و با این کد به Party ملحق شو.",
        parse_mode="Markdown"
    )

    # اطلاع سازنده

    try:

        username = (
            f"@{query.from_user.username}"
            if query.from_user.username
            else query.from_user.first_name
        )

        await context.bot.send_message(
            chat_id=creator_id,
            text=(
                "🔥 یک بازیکن Party را قبول کرد!\n\n"
                f"👤 {username}\n"
                f"🎯 {query.from_user.id}\n\n"
                f"👥 ظرفیت:\n"
                f"{new_count}/{players_needed}"
            )
        )

    except Exception:
        pass

    # Party کامل شد

    if new_count >= players_needed:

        mark_party_filled(
            party_id
        )

        try:

            await context.bot.send_message(
                chat_id=creator_id,
                text=(
                    "🎉 Party تکمیل شد!\n\n"
                    f"👥 {players_needed} نفر قبول کردند."
                )
            )

        except Exception:
            pass

    else:

        # اگر هنوز جا دارد، بازیکن جایگزین پیدا کن
        await fill_party_offers(
            context.bot,
            party_id
        )


# =========================================================
# REJECT
# =========================================================

async def reject_party(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if is_banned(user_id):

        await query.edit_message_text(
            "🚫 حساب شما Ban شده است."
        )

        return

    party_id = int(
        query.data.replace(
            "reject_",
            ""
        )
    )

    match = get_match(
        party_id,
        user_id
    )

    if not match:

        await query.edit_message_text(
            "❌ دعوت پیدا نشد.",
            reply_markup=main_menu()
        )

        return

    if match[3] != "pending":

        await query.edit_message_text(
            "ℹ️ قبلاً پاسخ داده‌ای.",
            reply_markup=main_menu()
        )

        return

    set_match_status(
        party_id,
        user_id,
        "rejected"
    )

    await query.edit_message_text(
        "❌ درخواست Party رد شد.",
        reply_markup=main_menu()
    )

    # نفر جایگزین
    await fill_party_offers(
        context.bot,
        party_id
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = get_user(
        query.from_user.id
    )

    if not user:

        await query.edit_message_text(
            "❌ پروفایل پیدا نشد.",
            reply_markup=main_menu()
        )

        return

    telegram_id = user[0]
    username = user[1]
    rank = user[2]

    if not rank:
        rank = "ثبت نشده"

    active_party = get_active_party(
        telegram_id
    )

    party_status = (
        "🟢 Party فعال داری"
        if active_party
        else
        "⚪ Party فعالی نداری"
    )

    await query.edit_message_text(
        "👤 پروفایل من\n\n"
        f"👤 Username: "
        f"@{username if username else 'ندارد'}\n"
        f"🎯 Rank: {rank}\n\n"
        f"{party_status}",
        reply_markup=main_menu()
    )


# =========================================================
# CANCEL REQUEST
# =========================================================

async def cancel_request(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    cancelled = cancel_active_party(
        query.from_user.id
    )

    if cancelled:

        message = (
            "✅ درخواست Party لغو شد."
        )

    else:

        message = (
            "ℹ️ درخواست فعال نداری."
        )

    await query.edit_message_text(
        message,
        reply_markup=main_menu()
    )


# =========================================================
# CONTACT ADMIN
# =========================================================

async def contact_admin(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if is_banned(query.from_user.id):

        await query.edit_message_text(
            "🚫 حساب شما Ban شده است."
        )

        return

    context.user_data.clear()

    context.user_data[
        "contact_admin"
    ] = True

    await query.edit_message_text(
        "📩 پیام خودت برای ادمین رو بنویس.\n\n"
        "هر چیزی که ارسال کنی برای ادمین فرستاده می‌شود.\n\n"
        "❌ برای لغو، /start را بزن."
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "ℹ️ راهنمای Valorant Party Finder\n\n"

        "🎯 رنک من\n"
        "رنک خودت را ثبت کن.\n\n"

        "🔎 پیدا کردن یار\n"
        "می‌توانی حداکثر ۳ رنک موردنیاز انتخاب کنی.\n\n"

        "مثال:\n"
        "Gold + Platinum + Diamond\n\n"

        "بعد تعداد بازیکنان و Party Code را وارد کن.\n\n"

        "🤖 ربات بازیکنان مناسب را پیدا می‌کند.\n\n"

        "✅ قبول\n"
        "Party Code برایت نمایش داده می‌شود.\n\n"

        "❌ رد\n"
        "دعوت رد می‌شود.\n\n"

        "📩 ارتباط با ادمین\n"
        "پیام مستقیم برای ادمین ارسال کن.",
        reply_markup=main_menu()
    )


# =========================================================
# ADMIN MENU
# =========================================================

def admin_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats"
            ),
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                "📩 پیام‌های کاربران",
                callback_data="admin_messages"
            )
        ],
        [
            InlineKeyboardButton(
                "🎮 Partyهای فعال",
                callback_data="admin_parties"
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 مدیریت Ban",
                callback_data="admin_ban_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# /ADMIN
# =========================================================

async def admin_command(
    update,
    context
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await update.message.reply_text(
            "⛔ دسترسی غیرمجاز."
        )

        return

    await update.message.reply_text(
        "👑 پنل مدیریت\n\n"
        "به پنل ادمین خوش آمدی.",
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN STATS
# =========================================================

async def admin_stats(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    total_users, banned_users, active_parties, total_parties = get_statistics()

    await query.edit_message_text(
        "📊 آمار ربات\n\n"
        f"👥 کل کاربران: {total_users}\n"
        f"🚫 کاربران Ban شده: {banned_users}\n"
        f"🎮 Party فعال: {active_parties}\n"
        f"🎮 کل Partyها: {total_parties}",
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN USERS
# =========================================================

async def admin_users(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    users = get_all_users()

    if not users:

        text = "👥 هنوز کاربری وجود ندارد."

    else:

        text = "👥 کاربران:\n\n"

        for user in users[:30]:

            telegram_id = user[0]
            username = user[1] or "ندارد"
            rank = user[2] or "ثبت نشده"
            banned = "🚫" if user[4] else "🟢"

            text += (
                f"{banned} @{username}\n"
                f"ID: {telegram_id}\n"
                f"Rank: {rank}\n\n"
            )

        if len(users) > 30:

            text += (
                f"نمایش ۳۰ نفر از {len(users)} کاربر."
            )

    await query.edit_message_text(
        text,
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN MESSAGES
# =========================================================

async def admin_messages(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    messages = get_admin_messages()

    if not messages:

        await query.edit_message_text(
            "📭 پیام جدیدی وجود ندارد.",
            reply_markup=admin_menu()
        )

        return

    keyboard = []

    for message in messages[:20]:

        message_id = message[0]
        user_id = message[1]

        keyboard.append([
            InlineKeyboardButton(
                f"💬 پیام {user_id}",
                callback_data=f"adminmsg_{message_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="admin_back"
        )
    ])

    await query.edit_message_text(
        f"📩 {len(messages)} پیام پاسخ‌داده‌نشده وجود دارد.",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# ADMIN SHOW MESSAGE
# =========================================================

async def admin_show_message(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    message_id = int(
        query.data.replace(
            "adminmsg_",
            ""
        )
    )

    messages = get_admin_messages()

    selected = None

    for message in messages:

        if message[0] == message_id:

            selected = message
            break

    if not selected:

        await query.edit_message_text(
            "❌ پیام پیدا نشد.",
            reply_markup=admin_menu()
        )

        return

    user_id = selected[1]
    message_text = selected[2]

    keyboard = [
        [
            InlineKeyboardButton(
                "💬 پاسخ",
                callback_data=f"adminreply_{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 Ban",
                callback_data=f"adminban_{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="admin_messages"
            )
        ]
    ]

    await query.edit_message_text(
        "📩 پیام کاربر\n\n"
        f"🆔 ID: {user_id}\n\n"
        f"💬 {message_text}",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    mark_admin_message_answered(
        message_id
    )


# =========================================================
# ADMIN REPLY
# =========================================================

async def admin_reply(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    user_id = int(
        query.data.replace(
            "adminreply_",
            ""
        )
    )

    context.user_data.clear()

    context.user_data[
        "admin_reply_user"
    ] = user_id

    await query.edit_message_text(
        "💬 پاسخ به کاربر\n\n"
        f"🆔 User ID: {user_id}\n\n"
        "پیامت رو ارسال کن."
    )


# =========================================================
# ADMIN BAN
# =========================================================

async def admin_ban(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    user_id = int(
        query.data.replace(
            "adminban_",
            ""
        )
    )

    if user_id in ADMIN_IDS:

        await query.answer(
            "❌ نمی‌توانی ادمین را Ban کنی.",
            show_alert=True
        )

        return

    ban_user(
        user_id
    )

    try:

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🚫 حساب شما توسط مدیریت Ban شد.\n\n"
                "در صورت اعتراض با ادمین ارتباط بگیرید."
            )
        )

    except Exception:
        pass

    await query.edit_message_text(
        f"🚫 کاربر {user_id} Ban شد.",
        reply_markup=admin_menu()
    )


# =========================================================
# ADMIN BAN MENU
# =========================================================

async def admin_ban_menu(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    users = get_all_users()

    keyboard = []

    for user in users:

        user_id = user[0]
        username = user[1] or str(user_id)
        banned = user[4]

        if banned:

            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Unban @{username}",
                    callback_data=f"adminunban_{user_id}"
                )
            ])

        else:

            keyboard.append([
                InlineKeyboardButton(
                    f"🚫 Ban @{username}",
                    callback_data=f"adminban_{user_id}"
                )
            ])

        if len(keyboard) >= 30:
            break

    keyboard.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="admin_back"
        )
    ])

    await query.edit_message_text(
        "🚫 مدیریت کاربران\n\n"
        "کاربر موردنظر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# ADMIN UNBAN
# =========================================================

async def admin_unban(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    user_id = int(
        query.data.replace(
            "adminunban_",
            ""
        )
    )

    unban_user(
        user_id
    )

    try:

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ حساب شما از Ban خارج شد.\n\n"
                "دوباره می‌توانی از ربات استفاده کنی."
            )
        )

    except Exception:
        pass

    await admin_ban_menu(
        update,
        context
    )


# =========================================================
# ADMIN PARTIES
# =========================================================

async def admin_parties(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    parties = get_all_active_parties()

    if not parties:

        await query.edit_message_text(
            "🎮 هیچ Party فعالی وجود ندارد.",
            reply_markup=admin_menu()
        )

        return

    keyboard = []

    text = "🎮 Partyهای فعال:\n\n"

    for party in parties:

        party_id = party[0]
        creator_id = party[1]
        ranks = party[2]
        needed = party[3]

        accepted = count_accepted_players(
            party_id
        )

        text += (
            f"🎮 Party #{party_id}\n"
            f"👤 Creator: {creator_id}\n"
            f"🎯 {ranks}\n"
            f"👥 {accepted}/{needed}\n\n"
        )

        keyboard.append([
            InlineKeyboardButton(
                f"❌ لغو Party #{party_id}",
                callback_data=f"admincancelparty_{party_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 برگشت",
            callback_data="admin_back"
        )
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# ADMIN CANCEL PARTY
# =========================================================

async def admin_cancel_party_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    party_id = int(
        query.data.replace(
            "admincancelparty_",
            ""
        )
    )

    party = get_party(
        party_id
    )

    success = admin_cancel_party(
        party_id
    )

    if success and party:

        creator_id = party[1]

        try:

            await context.bot.send_message(
                chat_id=creator_id,
                text=(
                    "⚠️ Party شما توسط ادمین لغو شد."
                )
            )

        except Exception:
            pass

    await admin_parties(
        update,
        context
    )


# =========================================================
# ADMIN BACK
# =========================================================

async def admin_back(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(query.from_user.id):
        return

    await query.edit_message_text(
        "👑 پنل مدیریت",
        reply_markup=admin_menu()
    )


# =========================================================
# MAIN MENU CALLBACK
# =========================================================

async def main_menu_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "🎮 منوی اصلی:",
        reply_markup=main_menu()
    )


# =========================================================
# BUTTON ROUTER
# =========================================================

async def button_handler(
    update,
    context
):

    query = update.callback_query

    data = query.data

    if data == "my_rank":

        await show_my_rank(
            update,
            context
        )

    elif data.startswith("myrank_"):

        await save_my_rank(
            update,
            context
        )

    elif data == "find_player":

        await find_player(
            update,
            context
        )

    elif data.startswith("reqrank_"):

        await select_required_rank(
            update,
            context
        )

    elif data == "confirm_ranks":

        await confirm_required_ranks(
            update,
            context
        )

    elif data.startswith("players_"):

        await choose_players(
            update,
            context
        )

    elif data.startswith("accept_"):

        await accept_party(
            update,
            context
        )

    elif data.startswith("reject_"):

        await reject_party(
            update,
            context
        )

    elif data == "profile":

        await profile(
            update,
            context
        )

    elif data == "cancel_request":

        await cancel_request(
            update,
            context
        )

    elif data == "contact_admin":

        await contact_admin(
            update,
            context
        )

    elif data == "help":

        await help_command(
            update,
            context
        )

    elif data == "admin_stats":

        await admin_stats(
            update,
            context
        )

    elif data == "admin_users":

        await admin_users(
            update,
            context
        )

    elif data == "admin_messages":

        await admin_messages(
            update,
            context
        )

    elif data.startswith("adminmsg_"):

        await admin_show_message(
            update,
            context
        )

    elif data.startswith("adminreply_"):

        await admin_reply(
            update,
            context
        )

    elif data.startswith("adminban_"):

        await admin_ban(
            update,
            context
        )

    elif data == "admin_ban_menu":

        await admin_ban_menu(
            update,
            context
        )

    elif data.startswith("adminunban_"):

        await admin_unban(
            update,
            context
        )

    elif data == "admin_parties":

        await admin_parties(
            update,
            context
        )

    elif data.startswith(
        "admincancelparty_"
    ):

        await admin_cancel_party_callback(
            update,
            context
        )

    elif data == "admin_back":

        await admin_back(
            update,
            context
        )

    elif data == "main_menu":

        await main_menu_callback(
            update,
            context
        )


# =========================================================
# ERROR
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "ERROR:",
        context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    create_database()

    expire_old_parties()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # ADMIN
    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    # BUTTONS
    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # TEXT
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_party_code
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "Valorant Party Finder Bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
