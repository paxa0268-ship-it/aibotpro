import os
import random
import threading
import time

import schedule
import telebot
from google import genai


# --- SOZLAMALAR ---
def load_config():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    channel_id = os.getenv("CHANNEL_ID", "").strip()
    return token, gemini_key, channel_id


TELEGRAM_TOKEN, GEMINI_API_KEY, CHANNEL_ID = load_config()

# Mavzular ro'yxati (PUBG, MLBB, Gaming telefonlar va Noutbuklar)
TOPICS = [
    "PUBG Mobile'da so'nggi yangiliklar, 90fps va qulay sezgirlik (sensitivity) sozlamalari",
    "Mobile Legends (MLBB) meta qahramonlari va ularni qanday qilib tezroq Grandmaster/Mythic qilish sirlari",
    "Gaming telefonlar va Xiaomi kabi qurilmalarda qizishni oldini olish va o'yin unumdorligini oshirish",
    "O'yin va ish uchun arzon, lekin kuchli gaming noutbuklarni tanlash mezonlari",
    "Mobil kiberqurilmalar, quloqchinlar va o'yin aksessuarlarining afzalliklari",
]

bot = None
ai_client = None


def validate_config():
    missing = []
    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not CHANNEL_ID:
        missing.append("CHANNEL_ID")

    if missing:
        print("⚠️ Quyidagi muhit o'zgaruvchilari mavjud emas:")
        for key in missing:
            print(f"   - {key}")
        print("Masalan: set TELEGRAM_TOKEN=... ; set GEMINI_API_KEY=... ; set CHANNEL_ID=@your_channel")
        return False
    return True


def setup_clients():
    global bot, ai_client
    if not validate_config():
        raise SystemExit(1)

    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    ai_client = genai.Client(api_key=GEMINI_API_KEY)


def register_handlers():
    if bot is None:
        raise RuntimeError("Bot yaratilmagan. setup_clients() dan avval chaqirmang.")

    @bot.channel_post_handler(func=lambda message: True)
    def handle_channel_comments(message):
        user_text = message.text
        if not user_text:
            return

        prompt = (
            f"Foydalanuvchi gaming kanalidagi post ostida quyidagicha izoh qoldirdi: "
            f"'{user_text}'. Unga o'zbek tilida do'stona, gamerlar tilida qisqa va qiziqarli qilib javob yoz."
        )

        try:
            response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            bot.reply_to(message, response.text)
        except Exception as e:
            print(f"Izohga javob berishda xato: {e}")

    return handle_channel_comments


def generate_ai_post():
    """Sun'iy intellekt yordamida qiziqarli post yaratish"""
    if ai_client is None:
        return "🎮 Yangi gaming yangilik tez orada e'lon qilinadi! (AI klienti tayyorlanmagan)"

    topic = random.choice(TOPICS)
    prompt = f"""
    Sen professional gaming bloger va texnologiya ekspertisan.
    Mavzu: {topic}.
    Shu mavzuda o'zbek tilida, yoshlarbop, qiziqarli, emojilar va teglar bilan boyitilgan, kanal uchun bitta zo'r post yoz.
    Hajmi o'rtacha bo'lsin, o'qishga oson bo'lsin.
    """
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"🎮 Yangi gaming yangilik tez orada e'lon qilinadi! (Xatolik: {e})"


def send_scheduled_post():
    """Kanalga kuniga 5 mahal post yuborish funksiyasi"""
    if bot is None or CHANNEL_ID == "":
        print("⚠️ Telegram bot yoki kanal ID tayyor emas. Post yuborilmaydi.")
        return

    post_text = generate_ai_post()
    try:
        bot.send_message(CHANNEL_ID, post_text)
        print("✅ Post kanalga muvaffaqiyatli yuborildi!")
    except Exception as e:
        print(f"❌ Post yuborishda xatolik: {e}")


def run_schedule():
    """Kuniga 5 marta post chiqarish vaqtlari (Toshkent vaqti bilan)"""
    schedule.every().day.at("09:00").do(send_scheduled_post)
    schedule.every().day.at("13:00").do(send_scheduled_post)
    schedule.every().day.at("16:30").do(send_scheduled_post)
    schedule.every().day.at("20:00").do(send_scheduled_post)
    schedule.every().day.at("23:00").do(send_scheduled_post)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    try:
        setup_clients()
        register_handlers()
    except SystemExit:
        raise
    except Exception as e:
        print(f"🚫 Botni ishga tushirishda xatolik: {e}")
        raise SystemExit(1)

    print("🤖 Gaming AI Bot ishga tushdi va ishlamoqda...")
    print(f"📢 Kanal: {CHANNEL_ID}")

    # Schedulerni alohida oqimda (thread) ishga tushiramiz
    t = threading.Thread(target=run_schedule, daemon=True)
    t.start()

    # Botni doimiy eshitish rejimida qoldiramiz
    bot.infinity_polling()
