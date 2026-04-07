import os
import time
import asyncio
import tempfile
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import gc
import colorsys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = "8759564785:AAHiPiuZt3ordHtefr3MQSYofSs8hNfFAsg"

# Файл для сохранения настроек пользователей
USER_DATA_FILE = "user_settings.json"


def load_user_settings():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_user_settings(settings):
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(settings, f)
    except:
        pass


user_settings_db = load_user_settings()

DEFAULT_SETTINGS = {
    "threshold": 128,
    "cell_size": 8,
    "max_size": 150,
    "mode": "color"
}

# Расширенная палитра цветов
DIGIT_COLORS = {
    1: (255, 0, 0), 2: (255, 69, 0), 3: (255, 165, 0),
    4: (255, 215, 0), 5: (255, 255, 0), 6: (173, 255, 47),
    7: (0, 255, 0), 8: (0, 255, 127), 9: (0, 255, 255),
    10: (0, 191, 255), 11: (0, 0, 255), 12: (75, 0, 130),
    13: (138, 43, 226), 14: (160, 32, 240), 15: (199, 21, 133),
    16: (255, 20, 147), 17: (255, 105, 180), 0: (255, 255, 255)
}


def get_digit_by_color(rgb_color):
    r, g, b = rgb_color
    if r < 50 and g < 50 and b < 50:
        return "0", (40, 40, 40)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.2:
        if v > 0.7:
            return "0", (255, 255, 255)
        else:
            return "0", (100, 100, 100)
    else:
        hue_deg = h * 360
        if hue_deg < 20:
            return "1", DIGIT_COLORS[1]
        elif hue_deg < 40:
            return "2", DIGIT_COLORS[2]
        elif hue_deg < 50:
            return "3", DIGIT_COLORS[3]
        elif hue_deg < 65:
            return "4", DIGIT_COLORS[4]
        elif hue_deg < 80:
            return "5", DIGIT_COLORS[5]
        elif hue_deg < 100:
            return "6", DIGIT_COLORS[6]
        elif hue_deg < 130:
            return "7", DIGIT_COLORS[7]
        elif hue_deg < 160:
            return "8", DIGIT_COLORS[8]
        elif hue_deg < 180:
            return "9", DIGIT_COLORS[9]
        elif hue_deg < 200:
            return "10", DIGIT_COLORS[10]
        elif hue_deg < 230:
            return "11", DIGIT_COLORS[11]
        elif hue_deg < 260:
            return "12", DIGIT_COLORS[12]
        elif hue_deg < 280:
            return "13", DIGIT_COLORS[13]
        elif hue_deg < 300:
            return "14", DIGIT_COLORS[14]
        elif hue_deg < 320:
            return "15", DIGIT_COLORS[15]
        elif hue_deg < 340:
            return "16", DIGIT_COLORS[16]
        else:
            return "17", DIGIT_COLORS[17]


def _process_image(input_path, output_path, settings):
    img_color = Image.open(input_path).convert('RGB')
    orig_width, orig_height = img_color.size
    max_sz = settings.get("max_size", 150)
    if orig_width >= orig_height:
        nw = min(orig_width, max_sz)
        nh = int(orig_height * (nw / orig_width))
    else:
        nh = min(orig_height, max_sz)
        nw = int(orig_width * (nh / orig_height))
    nw, nh = max(1, nw), max(1, nh)
    img_resized = img_color.resize((nw, nh), Image.Resampling.LANCZOS)
    pixels = np.array(img_resized)
    img_gray = img_color.convert('L')
    img_gray_resized = img_gray.resize((nw, nh), Image.Resampling.LANCZOS)
    gray_pixels = np.array(img_gray_resized)
    threshold = settings.get("threshold", 128)
    h, w, _ = pixels.shape
    cell_size = settings.get("cell_size", 8)
    result_img = Image.new('RGB', (w * cell_size, h * cell_size), color=(0, 0, 0))
    draw = ImageDraw.Draw(result_img)
    mode = settings.get("mode", "color")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", cell_size - 2)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", cell_size - 2)
        except:
            font = ImageFont.load_default()
    for i in range(h):
        for j in range(w):
            x = j * cell_size
            y = i * cell_size
            if gray_pixels[i, j] > threshold:
                if mode == "bw":
                    draw.text((x, y), '1', fill=(255, 255, 255), font=font)
                else:
                    pixel_color = tuple(pixels[i, j])
                    digit, digit_color = get_digit_by_color(pixel_color)
                    draw.text((x, y), digit, fill=digit_color, font=font)
            else:
                draw.text((x, y), '0', fill=(40, 40, 40), font=font)
    result_img.save(output_path, 'JPEG', quality=85)
    del img_color, img_resized, pixels, draw
    gc.collect()


# HTTP-сервер для Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(("0.0.0.0", port), HealthHandler)
    httpd.serve_forever()


Thread(target=run_health_server, daemon=True).start()


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    text = (
        "🎨 *Главное меню*\n\n"
        "Я анализирую цвета на твоём фото и превращаю их в цифры!\n\n"
        "📷 *Просто отправь мне любое фото*"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(update.effective_user.id)

    if uid in user_settings_db:
        s = user_settings_db[uid]
    else:
        s = DEFAULT_SETTINGS.copy()
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)

    mode_text = "🌈 Цветной" if s.get("mode", "color") == "color" else "⚫ Чёрно-белый"

    keyboard = [
        [InlineKeyboardButton(f"🎚 Яркость ({s['threshold']})", callback_data="edit_thr")],
        [InlineKeyboardButton(f"📏 Размер цифры ({s['cell_size']}px)", callback_data="edit_cell")],
        [InlineKeyboardButton(f"📐 Детализация ({s['max_size']})", callback_data="edit_max")],
        [InlineKeyboardButton(f"🎨 Режим: {mode_text}", callback_data="toggle_mode")],
        [InlineKeyboardButton("◀️ Назад", callback_data="main")]
    ]
    await query.edit_message_text(
        f"⚙️ *Настройки*\n\n"
        f"🎚 Яркость: {s['threshold']} (чем выше, тем светлее)\n"
        f"📏 Размер цифры: {s['cell_size']}px\n"
        f"📐 Детализация: {s['max_size']}\n"
        f"🎨 Режим: {mode_text}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main")]]
    await query.edit_message_text(
        "❓ *Как пользоваться*\n\n"
        "1️⃣ Отправь фото\n"
        "2️⃣ Настрой параметры в меню\n"
        "3️⃣ Получи результат\n\n"
        "*Что означают настройки:*\n"
        "• Яркость — чем выше, тем светлее\n"
        "• Размер цифры — величина символов\n"
        "• Детализация — чёткость изображения\n"
        "• Режим — цветной или чёрно-белый\n\n"
        "⚙️ Настройки сохраняются автоматически!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid in user_settings_db:
        s = user_settings_db[uid]
    else:
        s = DEFAULT_SETTINGS.copy()
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)

    msg = await update.message.reply_text("🎨 *Обрабатываю фото...*", parse_mode='Markdown')
    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        tmp = tempfile.gettempdir()
        inp = os.path.join(tmp, f"in_{uid}.jpg")
        out = os.path.join(tmp, f"out_{uid}.jpg")
        await file.download_to_drive(inp)
        await asyncio.to_thread(_process_image, inp, out, s)
        with open(out, 'rb') as f:
            await update.message.reply_photo(
                photo=f,
                caption=f"✅ *Готово!*\n\n"
                        f"🎚 Яркость: {s['threshold']}\n"
                        f"📏 Размер: {s['cell_size']}px\n"
                        f"🎨 Режим: {'Цветной' if s.get('mode', 'color') == 'color' else 'Чёрно-белый'}"
            )
        await msg.delete()
        for p in (inp, out):
            try:
                os.remove(p)
            except:
                pass
        gc.collect()
        await show_main_menu(update, context)
    except Exception as e:
        await msg.edit_text(f"❌ *Ошибка*", parse_mode='Markdown')


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = str(update.effective_user.id)

    if uid in user_settings_db:
        s = user_settings_db[uid]
    else:
        s = DEFAULT_SETTINGS.copy()
        user_settings_db[uid] = s

    # Навигация
    if data == "main":
        await show_main_menu(update, context)
    elif data == "settings":
        await settings_menu(update, context)
    elif data == "help":
        await help_menu(update, context)

    # Редактирование яркости
    elif data == "edit_thr":
        keyboard = [
            [InlineKeyboardButton("⬆️ Увеличить +10", callback_data="thr_inc"),
             InlineKeyboardButton("➖ Уменьшить -10", callback_data="thr_dec")],
            [InlineKeyboardButton("⬆️ Увеличить +25", callback_data="thr_inc25"),
             InlineKeyboardButton("➖ Уменьшить -25", callback_data="thr_dec25")],
            [InlineKeyboardButton("🎯 128 (стандарт)", callback_data="thr_128")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ]
        await q.edit_message_text(
            f"🎚 *Настройка яркости*\n\nТекущее значение: **{s['threshold']}**\n\n"
            f"• **Увеличить** → изображение светлее\n"
            f"• **Уменьшить** → изображение темнее\n\n"
            f"Выбери изменение:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Редактирование размера цифры
    elif data == "edit_cell":
        keyboard = [
            [InlineKeyboardButton("➕ Увеличить +1", callback_data="cell_inc"),
             InlineKeyboardButton("➖ Уменьшить -1", callback_data="cell_dec")],
            [InlineKeyboardButton("➕ Увеличить +3", callback_data="cell_inc3"),
             InlineKeyboardButton("➖ Уменьшить -3", callback_data="cell_dec3")],
            [InlineKeyboardButton("📏 8 (стандарт)", callback_data="cell_8")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ]
        await q.edit_message_text(
            f"📏 *Настройка размера цифры*\n\nТекущий размер: **{s['cell_size']}px**\n\n"
            f"Выбери изменение:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Редактирование детализации
    elif data == "edit_max":
        keyboard = [
            [InlineKeyboardButton("⬆️ Увеличить +25", callback_data="max_inc25"),
             InlineKeyboardButton("➖ Уменьшить -25", callback_data="max_dec25")],
            [InlineKeyboardButton("⬆️ Увеличить +50", callback_data="max_inc50"),
             InlineKeyboardButton("➖ Уменьшить -50", callback_data="max_dec50")],
            [InlineKeyboardButton("📐 150 (стандарт)", callback_data="max_150")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ]
        await q.edit_message_text(
            f"📐 *Настройка детализации*\n\nТекущее значение: **{s['max_size']}**\n\n"
            f"Выбери изменение:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Изменение яркости (УВЕЛИЧЕНИЕ = СВЕТЛЕЕ)
    elif data == "thr_inc":
        s['threshold'] = min(255, s['threshold'] + 10)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)  # Остаёмся в меню настроек
    elif data == "thr_dec":
        s['threshold'] = max(0, s['threshold'] - 10)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "thr_inc25":
        s['threshold'] = min(255, s['threshold'] + 25)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "thr_dec25":
        s['threshold'] = max(0, s['threshold'] - 25)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "thr_128":
        s['threshold'] = 128
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)

    # Изменение размера цифры
    elif data == "cell_inc":
        s['cell_size'] = min(20, s['cell_size'] + 1)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "cell_dec":
        s['cell_size'] = max(4, s['cell_size'] - 1)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "cell_inc3":
        s['cell_size'] = min(20, s['cell_size'] + 3)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "cell_dec3":
        s['cell_size'] = max(4, s['cell_size'] - 3)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "cell_8":
        s['cell_size'] = 8
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)

    # Изменение детализации
    elif data == "max_inc25":
        s['max_size'] = min(300, s['max_size'] + 25)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "max_dec25":
        s['max_size'] = max(30, s['max_size'] - 25)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "max_inc50":
        s['max_size'] = min(300, s['max_size'] + 50)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "max_dec50":
        s['max_size'] = max(30, s['max_size'] - 50)
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)
    elif data == "max_150":
        s['max_size'] = 150
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)

    # Переключение режима
    elif data == "toggle_mode":
        if s.get("mode", "color") == "color":
            s['mode'] = "bw"
        else:
            s['mode'] = "color"
        user_settings_db[uid] = s
        save_user_settings(user_settings_db)
        await settings_menu(update, context)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(callback))
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print("=" * 50)
    app.run_polling()


if __name__ == "__main__":
    main()