import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database

TOKEN = "8828024686:AAGI2h1rMP0FH1eDe7slicrMYIOU3_GIxSg"
ADMIN_ID = 8907034180
ADMIN_USERNAME = "@xamrayv_m"

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_admin_name = State()
    waiting_for_channel_link = State()
    waiting_for_channel_id = State()
    waiting_for_channel_name = State()
    waiting_for_broadcast = State()
    waiting_for_movie_id = State()
    waiting_for_parts_count = State()
    waiting_for_part_video = State()
    waiting_for_movie_title = State()
    waiting_for_movie_desc = State()
    waiting_for_movie_duration = State()
    waiting_for_movie_year = State()

class UserStates(StatesGroup):
    searching_by_id = State()
    searching_by_name = State()
    waiting_for_rating = State()
    waiting_for_comment = State()

def get_nav_keyboard(back_callback="cancel_process"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_process")]
    ])

@dp.callback_query(F.data == "cancel_process")
async def cancel_process(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Amal bekor qilindi.")
    except Exception:
        await callback.message.answer("❌ Amal bekor qilindi.")
    await callback.answer()

async def check_subscription(user_id: int):
    if db.get_sub_status() == 'OFF':
        return True, []
    channels = db.get_channels()
    not_subscribed = []
    for ch_id, ch_link, ch_name in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append((ch_name, ch_link))
        except Exception:
            pass
    return len(not_subscribed) == 0, not_subscribed

def get_main_keyboard(user_id):
    kb = [
        [KeyboardButton(text="🎬 Kino qidirish"), KeyboardButton(text="⭐ Sevimli kinolar")],
        [KeyboardButton(text="📜 Qidiruv tarixi"), KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="🛠 Adminga murojaat")]
    ]
    if db.is_admin(user_id):
        kb.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username)
    is_sub, not_sub_channels = await check_subscription(message.from_user.id)
    if not is_sub:
        builder = InlineKeyboardBuilder()
        for name, link in not_sub_channels:
            builder.add(InlineKeyboardButton(text=f"📢 {name}", url=link))
        builder.adjust(1)
        builder.row(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
        await message.answer("⚠️ Botdan foydalanish uchun quyidagi homiy kanallarga obuna bo'ling:", reply_markup=builder.as_markup())
        return

    username_str = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    await message.answer(f"Salom, {username_str}! Kino botiga xush kelibsiz.", reply_markup=get_main_keyboard(message.from_user.id))

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    is_sub, not_sub_channels = await check_subscription(callback.from_user.id)
    if not is_sub:
        await callback.answer("Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("Obuna tasdiqlandi!", reply_markup=get_main_keyboard(callback.from_user.id))

@dp.message(F.text == "🎬 Kino qidirish")
async def search_movie_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔢 ID orqali", callback_data="search_id"),
         InlineKeyboardButton(text="🔤 Nom orqali", callback_data="search_name")],
        [InlineKeyboardButton(text="🎲 Tasodifiy kino", callback_data="search_random")]
    ])
    await message.answer("Kinoni qidirish usulini tanlang:", reply_markup=kb)

@dp.callback_query(F.data == "search_id")
async def search_by_id_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kinoning ID raqamini kiriting (masalan: 1, 2, 3...):", reply_markup=get_nav_keyboard())
    await state.set_state(UserStates.searching_by_id)
    await callback.answer()

@dp.message(UserStates.searching_by_id)
async def process_search_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting!")
        return
    movie_id = int(message.text)
    movie = db.get_movie_by_id(movie_id)
    if not movie:
        await message.answer("❌ Bunday ID raqamli kino topilmadi.")
        await state.clear()
        return
    
    db.add_search_history(message.from_user.id, movie_id)
    await show_movie_info(message, movie)
    await state.clear()

@dp.callback_query(F.data == "search_name")
async def search_by_name_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kinoning nomini kiriting:", reply_markup=get_nav_keyboard())
    await state.set_state(UserStates.searching_by_name)
    await callback.answer()

@dp.message(UserStates.searching_by_name)
async def process_search_name(message: types.Message, state: FSMContext):
    movies = db.search_movies_by_name(message.text)
    if not movies:
        await message.answer("❌ Hech qanday kino topilmadi.")
        await state.clear()
        return
    kb = [[InlineKeyboardButton(text=f"{title} (⭐ {rating:.1f}) [ID: {m_id}]", callback_data=f"movie_{m_id}")] for m_id, title, views, rating in movies]
    await message.answer("🔍 Topilgan kinolar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.clear()

@dp.callback_query(F.data == "search_random")
async def search_random(callback: types.CallbackQuery):
    movie = db.get_random_movie()
    if not movie:
        await callback.answer("Hozircha bazada kinolar yo'q.", show_alert=True)
        return
    m_id = movie[0]
    db.add_search_history(callback.from_user.id, m_id)
    await show_movie_info_callback(callback, m_id)

async def show_movie_info(message: types.Message, movie):
    m_id, title, desc, duration, year, views, rating = movie
    db.increment_views(m_id)
    
    parts = db.get_movie_parts(m_id)
    kb = [InlineKeyboardButton(text=f"{p_num}-qism", callback_data=f"part_{p_id}") for p_id, p_num, file_id in parts]
    markup_kb = [kb[i:i+2] for i in range(0, len(kb), 2)] if kb else []
    markup_kb.append([InlineKeyboardButton(text="⭐ Sevimlilarga qo'shish", callback_data=f"fav_{m_id}"),
                      InlineKeyboardButton(text="💬 Baholash / Sharh", callback_data=f"review_{m_id}")])
    
    text = f"🎬 **{title}** (ID: `{m_id}`)\n\n📖 {desc}\n⏱ Davomiyligi: {duration}\n📅 Yili: {year}\n👀 Ko'rishlar: {views}\n⭐ Reyting: {rating:.1f}"
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_kb))

async def show_movie_info_callback(callback: types.CallbackQuery, m_id: int):
    movie = db.get_movie_by_id(m_id)
    if not movie:
        await callback.answer("Kino topilmadi.", show_alert=True)
        return
    m_id, title, desc, duration, year, views, rating = movie
    db.increment_views(m_id)
    db.add_search_history(callback.from_user.id, m_id)
    
    parts = db.get_movie_parts(m_id)
    kb = [InlineKeyboardButton(text=f"{p_num}-qism", callback_data=f"part_{p_id}") for p_id, p_num, file_id in parts]
    markup_kb = [kb[i:i+2] for i in range(0, len(kb), 2)] if kb else []
    markup_kb.append([InlineKeyboardButton(text="⭐ Sevimlilarga qo'shish", callback_data=f"fav_{m_id}"),
                      InlineKeyboardButton(text="💬 Baholash / Sharh", callback_data=f"review_{m_id}")])
    
    text = f"🎬 **{title}** (ID: `{m_id}`)\n\n📖 {desc}\n⏱ Davomiyligi: {duration}\n📅 Yili: {year}\n👀 Ko'rishlar: {views}\n⭐ Reyting: {rating:.1f}"
    
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_kb))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("movie_"))
async def callback_movie_select(callback: types.CallbackQuery):
    m_id = int(callback.data.split("_")[1])
    await show_movie_info_callback(callback, m_id)

@dp.callback_query(F.data.startswith("part_"))
async def callback_movie_part(callback: types.CallbackQuery):
    part_id = int(callback.data.split("_")[1])
    db.cursor.execute("SELECT file_id FROM movie_parts WHERE part_id = ?", (part_id,))
    res = db.cursor.fetchone()
    if res:
        await callback.message.answer_video(video=res[0])
    else:
        await callback.answer("Video topilmadi!", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("fav_"))
async def callback_add_favorite(callback: types.CallbackQuery):
    m_id = int(callback.data.split("_")[1])
    db.add_favorite(callback.from_user.id, m_id)
    await callback.answer("Kino sevimlilarga qo'shildi! ⭐", show_alert=True)

@dp.message(F.text == "⭐ Sevimli kinolar")
async def show_favorites(message: types.Message):
    favs = db.get_favorites(message.from_user.id)
    if not favs:
        await message.answer("Sizda sevimli kinolar yo'q.")
        return
    kb = [[InlineKeyboardButton(text=title, callback_data=f"movie_{m_id}")] for m_id, title in favs]
    await message.answer("Sizning sevimli kinolaringiz:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(F.text == "📜 Qidiruv tarixi")
async def show_search_history(message: types.Message):
    history = db.get_search_history(message.from_user.id)
    if not history:
        await message.answer("Siz hali hech qanday kino qidirmagansiz.")
        return
    kb = [[InlineKeyboardButton(text=f"{title} (ID: {m_id})", callback_data=f"movie_{m_id}")] for m_id, title in history]
    await message.answer("📜 **Sizning qidiruv tarixingiz:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(F.text == "ℹ️ Yordam")
async def help_menu(message: types.Message):
    await message.answer("Botdan foydalanish uchun '🎬 Kino qidirish' tugmasini bosing va kerakli kinoni ID yoki nomi orqali toping.")

@dp.message(F.text == "🛠 Adminga murojaat")
async def contact_admin(message: types.Message):
    await message.answer(f"Savollar bo'yicha adminga murojaat qiling: {ADMIN_USERNAME}")

@dp.callback_query(F.data.startswith("review_"))
async def review_movie_start(callback: types.CallbackQuery, state: FSMContext):
    m_id = int(callback.data.split("_")[1])
    await state.update_data(review_movie_id=m_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1", callback_data="rate_1"),
         InlineKeyboardButton(text="⭐⭐ 2", callback_data="rate_2"),
         InlineKeyboardButton(text="⭐⭐⭐ 3", callback_data="rate_3")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐ 4", callback_data="rate_4"),
         InlineKeyboardButton(text="⭐⭐⭐⭐⭐ 5", callback_data="rate_5")]
    ])
    await callback.message.answer("Kinoga necha yulduz berasiz?", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(movie_rating=rating)
    await callback.message.answer("Endi kinoga o'z izohingizni (sharhingizni) yozib qoldiring:")
    await state.set_state(UserStates.waiting_for_comment)
    await callback.answer()

@dp.message(UserStates.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.add_review(data['review_movie_id'], message.from_user.id, data['movie_rating'], message.text)
    await message.answer("Sharhingiz va bahoyingiz uchun rahmat! Qabul qilindi ✅")
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel(message: types.Message):
    if not db.is_admin(message.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_admins"),
         InlineKeyboardButton(text="📢 Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="🎬 Kinolar", callback_data="admin_movies")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar (Sub)", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📊 Statistikalar", callback_data="admin_stats"),
         InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_ads")]
    ])
    await message.answer("Admin panelga xush kelibsiz:", reply_markup=kb)

@dp.callback_query(F.data == "admin_menu_back")
async def back_to_admin_panel(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_admins"),
         InlineKeyboardButton(text="📢 Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="🎬 Kinolar", callback_data="admin_movies")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar (Sub)", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📊 Statistikalar", callback_data="admin_stats"),
         InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_ads")]
    ])
    await callback.message.edit_text("Admin panelga xush kelibsiz:", reply_markup=kb)

@dp.callback_query(F.data == "admin_movies")
async def admin_movies_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="add_movie_start")],
        [InlineKeyboardButton(text="❌ Kino o'chirish", callback_data="del_movie_list"),
         InlineKeyboardButton(text="👀 Kinolarni ko'rish", callback_data="view_movies_list")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_menu_back")]
    ])
    await callback.message.edit_text("Kinolarni boshqarish:", reply_markup=kb)

@dp.callback_query(F.data == "add_movie_start")
async def add_movie_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kinoga maxsus **ID raqam** kiriting (masalan: 1):", reply_markup=get_nav_keyboard())
    await state.set_state(AdminStates.waiting_for_movie_id)
    await callback.answer()

@dp.message(AdminStates.waiting_for_movie_id)
async def process_movie_id_input(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam ko'rinishida ID kiriting!")
        return
    await state.update_data(movie_id=int(message.text))
    await message.answer("Kino necha qismdan iborat? (Faqat raqam kiriting):")
    await state.set_state(AdminStates.waiting_for_parts_count)

@dp.message(AdminStates.waiting_for_parts_count)
async def process_parts_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, to'g'ri son kiriting!")
        return
    count = int(message.text)
    await state.update_data(parts_count=count, current_part=1, parts_data=[])
    await message.answer(f"1-qism uchun video faylni yuboring:")
    await state.set_state(AdminStates.waiting_for_part_video)

@dp.message(AdminStates.waiting_for_part_video, F.video)
async def process_part_video(message: types.Message, state: FSMContext):
    file_id = message.video.file_id
    data = await state.get_data()
    parts_data = data['parts_data']
    current_part = data['current_part']
    parts_count = data['parts_count']
    
    parts_data.append((current_part, file_id))
    await state.update_data(parts_data=parts_data)
    
    if current_part < parts_count:
        current_part += 1
        await state.update_data(current_part=current_part)
        await message.answer(f"{current_part}-qism uchun video faylni yuboring:")
    else:
        await message.answer("Endi kinoning nomini kiriting:")
        await state.set_state(AdminStates.waiting_for_movie_title)

@dp.message(AdminStates.waiting_for_part_video)
async def process_part_video_wrong(message: types.Message):
    await message.answer("Iltimos, video formatida yuboring!")

@dp.message(AdminStates.waiting_for_movie_title)
async def process_movie_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Kino haqida qisqacha ma'lumot kiriting:")
    await state.set_state(AdminStates.waiting_for_movie_desc)

@dp.message(AdminStates.waiting_for_movie_desc)
async def process_movie_desc(message: types.Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Kinoning davomiyligini kiriting (masalan: 1 soat 40 daqiqa):")
    await state.set_state(AdminStates.waiting_for_movie_duration)

@dp.message(AdminStates.waiting_for_movie_duration)
async def process_movie_duration(message: types.Message, state: FSMContext):
    await state.update_data(duration=message.text)
    await message.answer("Kinoning chiqarilgan yilini kiriting (masalan: 2026):")
    await state.set_state(AdminStates.waiting_for_movie_year)

@dp.message(AdminStates.waiting_for_movie_year)
async def process_movie_year(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        db.add_movie(data['movie_id'], data['title'], data['desc'], data['duration'], message.text)
        for p_num, f_id in data['parts_data']:
            db.add_movie_part(data['movie_id'], p_num, f_id)
        await message.answer(f"Kino muvaffaqiyatli saqlandi! ID: {data['movie_id']} ✅")
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi (Bunday ID oldindan mavjud bo'lishi mumkin): {e}")
    await state.clear()

@dp.callback_query(F.data == "view_movies_list")
async def view_movies_list(callback: types.CallbackQuery):
    movies = db.get_movies()
    if not movies:
        await callback.answer("Hozircha bazada kinolar yo'q.", show_alert=True)
        return
    kb = [[InlineKeyboardButton(text=f"{title} (ID: {m_id})", callback_data=f"movie_{m_id}")] for m_id, title, views, rating in movies]
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_movies")])
    await callback.message.edit_text("Bazadagi kinolar ro'yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "del_movie_list")
async def del_movie_list(callback: types.CallbackQuery):
    movies = db.get_movies()
    if not movies:
        await callback.answer("O'chirish uchun kinolar yo'q.", show_alert=True)
        return
    kb = [[InlineKeyboardButton(text=f"{title} (ID: {m_id})", callback_data=f"del_mov_{m_id}")] for m_id, title, views, rating in movies]
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_movies")])
    await callback.message.edit_text("O'chiriladigan kinoni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("del_mov_"))
async def confirm_del_movie(callback: types.CallbackQuery):
    m_id = int(callback.data.split("_")[2])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data=f"yes_del_mov_{m_id}"),
         InlineKeyboardButton(text="Yo'q", callback_data="admin_movies")]
    ])
    await callback.message.edit_text("Bu kinoni rostdan ham o'chirmoqchimisiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith("yes_del_mov_"))
async def yes_del_movie(callback: types.CallbackQuery):
    m_id = int(callback.data.split("_")[3])
    db.delete_movie(m_id)
    await callback.message.edit_text("Kino o'chirildi! ❌")

@dp.callback_query(F.data == "admin_admins")
async def admin_admins_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin")],
        [InlineKeyboardButton(text="❌ Admin o'chirish", callback_data="del_admin"),
         InlineKeyboardButton(text="👀 Adminlarni ko'rish", callback_data="view_admins")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_menu_back")]
    ])
    await callback.message.edit_text("Adminlarni boshqarish:", reply_markup=kb)

@dp.callback_query(F.data == "add_admin")
async def add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi adminning ID raqamini kiriting:", reply_markup=get_nav_keyboard())
    await state.set_state(AdminStates.waiting_for_admin_id)
    await callback.answer()

@dp.message(AdminStates.waiting_for_admin_id)
async def process_admin_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return
    await state.update_data(admin_id=int(message.text))
    await message.answer("Adminning ismini kiriting:")
    await state.set_state(AdminStates.waiting_for_admin_name)

@dp.message(AdminStates.waiting_for_admin_name)
async def process_admin_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.add_admin(data['admin_id'], message.text)
    await message.answer("Admin qo'shildi! ✅")
    await state.clear()

@dp.callback_query(F.data == "view_admins")
async def view_admins(callback: types.CallbackQuery):
    admins = db.get_admins()
    kb = [[InlineKeyboardButton(text=name, callback_data=f"admin_info_{a_id}")] for a_id, name in admins]
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_admins")])
    await callback.message.edit_text("Adminlar ro'yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("admin_info_"))
async def admin_info(callback: types.CallbackQuery):
    a_id = int(callback.data.split("_")[2])
    await callback.answer(f"Admin ID: {a_id}", show_alert=True)

@dp.callback_query(F.data == "del_admin")
async def del_admin_list(callback: types.CallbackQuery):
    admins = db.get_admins()
    # Asosiy adminni (8907034180) o'chirish ro'yxatidan chiqarib tashlaymiz
    kb = [[InlineKeyboardButton(text=name, callback_data=f"del_admin_{a_id}")] for a_id, name in admins if a_id != 8907034180]
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_admins")])
    await callback.message.edit_text("O'chiriladigan adminni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("del_admin_"))
async def confirm_del_admin(callback: types.CallbackQuery):
    a_id = int(callback.data.split("_")[2])
    if a_id == 8907034180:
        await callback.answer("Bosh adminni o'chirib bo'lmaydi!", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha", callback_data=f"yes_del_admin_{a_id}"),
         InlineKeyboardButton(text="Yo'q", callback_data="admin_admins")]
    ])
    await callback.message.edit_text("Bu adminni o'chirmoqchimisiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith("yes_del_admin_"))
async def yes_del_admin(callback: types.CallbackQuery):
    a_id = int(callback.data.split("_")[3])
    if a_id == 8907034180:
        await callback.answer("Xatolik: Bosh adminni o'chirib bo'lmaydi!", show_alert=True)
        return
    db.remove_admin(a_id)
    await callback.message.edit_text("Admin o'chirildi! ❌")

@dp.callback_query(F.data == "admin_channels")
async def admin_channels_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="❌ Kanal o'chirish", callback_data="del_channel"),
         InlineKeyboardButton(text="👀 Kanallarni ko'rish", callback_data="view_channels")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_menu_back")]
    ])
    await callback.message.edit_text("Kanallarni boshqarish:", reply_markup=kb)

@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kanal linkini kiriting (masalan: https://t.me/kanal_nomi):", reply_markup=get_nav_keyboard())
    await state.set_state(AdminStates.waiting_for_channel_link)
    await callback.answer()

@dp.message(AdminStates.waiting_for_channel_link)
async def process_ch_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await message.answer("Kanal ID raqamini kiriting (masalan: -100xxxxxxxxxx):")
    await state.set_state(AdminStates.waiting_for_channel_id)

@dp.message(AdminStates.waiting_for_channel_id)
async def process_ch_id(message: types.Message, state: FSMContext):
    if not message.text.startswith("-") and not message.text.isdigit():
        await message.answer("Kanal ID raqami to'g'ri emas!")
        return
    await state.update_data(ch_id=int(message.text))
    await message.answer("Kanal nomini kiriting:")
    await state.set_state(AdminStates.waiting_for_channel_name)

@dp.message(AdminStates.waiting_for_channel_name)
async def process_ch_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.add_channel(data['ch_id'], data['link'], message.text)
    await message.answer("Kanal qo'shildi! ✅")
    await state.clear()

@dp.callback_query(F.data == "view_channels")
async def view_channels(callback: types.CallbackQuery):
    channels = db.get_channels()
    if not channels:
        await callback.answer("Kanallar mavjud emas.", show_alert=True)
        return
    kb = [[InlineKeyboardButton(text=name, url=link)] for ch_id, link, name in channels]
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_channels")])
    await callback.message.edit_text("Kanallar ro'yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "del_channel")
async def del_channel_list(callback: types.CallbackQuery):
    channels = db.get_channels()
    if not channels:
        await callback.answer("O'chirish uchun kanallar yo'q.", show_alert=True)
        return
    kb = [[InlineKeyboardButton(text=name, callback_data=f"del_ch_{ch_id}")] for ch_id, link, name in channels]
    kb.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_channels")])
    await callback.message.edit_text("O'chiriladigan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("del_ch_"))
async def confirm_del_channel(callback: types.CallbackQuery):
    ch_id = int(callback.data.split("_")[2])
    db.remove_channel(ch_id)
    await callback.message.answer("Kanal o'chirildi! ❌")
    await callback.message.delete()

@dp.callback_query(F.data == "admin_settings")
async def admin_settings(callback: types.CallbackQuery):
    new_status = db.toggle_sub_status()
    await callback.answer(f"Majburiy obuna holati: {new_status}", show_alert=True)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    users_count = db.get_user_count()
    top_movies = db.get_top_movies()
    text = f"📊 **Statistika**\n\nJami foydalanuvchilar: {users_count} ta\n\n🔥 **Eng ko'p ko'rilganlar:**\n"
    if top_movies:
        for m_id, title, views, rating in top_movies[:5]:
            text += f"- {title} (ID: {m_id}): {views} marta (⭐ {rating:.1f})\n"
    else:
        text += "Hozircha kinolar yo'q."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_menu_back")]])
    await callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "admin_ads")
async def admin_ads_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Reklama xabarini yuboring (matn, rasm yoki video):", reply_markup=get_nav_keyboard())
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    users = db.get_all_users()
    success = 0
    for u_id in users:
        try:
            await message.send_copy(chat_id=u_id)
            await asyncio.sleep(0.05)
            success += 1
        except Exception:
            pass
    await message.answer(f"Reklama {success} ta foydalanuvchiga yuborildi! 🚀")
    await state.clear()

async def main():
    # Asosiy adminni bazaga kiritish
    if not db.is_admin(ADMIN_ID):
        db.add_admin(ADMIN_ID, "Bosh Admin")
    
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())