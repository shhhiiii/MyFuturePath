import telebot
from telebot import types
from config import BOT_TOKEN
from db import DBManager
from api import GigaChatAPI


bot = telebot.TeleBot(BOT_TOKEN)
db = DBManager()
gigachat = GigaChatAPI()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("👤 My profile")
    btn2 = types.KeyboardButton("📌 Add data")
    btn3 = types.KeyboardButton("⭐ My interests")
    btn4 = types.KeyboardButton("❓ FAQ")
    btn5 = types.KeyboardButton("🎯 Choose a career")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "👋 Hi! This is MyFuturePath - a bot that helps you choose a career.\n\n"
        "📌 Use the buttons below to get started."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == "📌 Add data")
@bot.message_handler(commands=['add'])
def add(message):
    user = db.get_user(message.chat.id)
    if user:
        bot.send_message(message.chat.id, "⚠️ You already have a profile. Use /update to change it.")
        return

    msg = bot.send_message(message.chat.id, "✍️ Enter your data separated by commas (Name, Profession, Experience, Interests):")
    bot.register_next_step_handler(msg, save_user_data)


def save_user_data(message):
    try:
        data = [x.strip() for x in message.text.split(",")]
        if len(data) != 4:
            bot.send_message(message.chat.id, "❌ You need to enter exactly 4 values separated by commas.")
            return

        name, profession, experience, interests = data
        db.add_user(message.chat.id, name, profession, experience, interests)
        bot.send_message(message.chat.id, "✅ Profile created successfully!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text == "🎯 Choose a career")
def start_career_test(message):
    db.init_career_progress(message.chat.id)
    send_career_question(message.chat.id, 1)

def send_career_question(chat_id, qid):
    qdata = db.get_career_question(qid)
    if not qdata:
        finish_career_test(chat_id)
        return
    text = f"❓ {qdata['question']}"
    markup = types.InlineKeyboardMarkup()
    for oid, opt_text in qdata["options"]:
        markup.add(types.InlineKeyboardButton(opt_text, callback_data=f"career_opt:{qid}:{oid}"))
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("career_opt:"))
def handle_career_answer(call):
    _, qid, oid = call.data.split(":")
    qid, oid = int(qid), int(oid)

    progress = db.get_progress(call.message.chat.id)
    if not progress:
        return

    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT career_ids FROM career_options WHERE id = ?", (oid,))
        row = cursor.fetchone()
        if row and row[0]:
            new_ids = [int(x) for x in row[0].split(",") if x.isdigit()]
            selected = list(set(progress["selected_careers"] + new_ids))
        else:
            selected = progress["selected_careers"]

    next_q = qid + 1
    db.update_progress(call.message.chat.id, next_q, selected)

    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_career_question(call.message.chat.id, next_q)

def finish_career_test(chat_id):
    progress = db.get_progress(chat_id)
    if not progress:
        bot.send_message(chat_id, "⚠ Error: no progress found.")
        return

    ids = list(set(progress["selected_careers"]))
    if not ids:
        bot.send_message(chat_id, "😕 Unfortunately, no careers were found.")
    else:
        careers = db.get_career_by_ids(ids)
        text = "🔥 These careers might suit you:\n\n"
        for name, url in careers:
            text += f"💼 {name}\n🔗 {url}\n\n"
        bot.send_message(chat_id, text)

    db.clear_progress(chat_id)


@bot.message_handler(commands=['update'])
def update(message):
    user = db.get_user(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "❌ You don't have a profile yet. First create it with /add.")
        return

    msg = bot.send_message(message.chat.id, "🔄 Enter new data (Name, Profession, Experience, Interests separated by commas):")
    bot.register_next_step_handler(msg, update_user_data)

def update_user_data(message):
    try:
        name, profession, experience, interests = [x.strip() for x in message.text.split(",")]
        db.update_user(message.chat.id, name, profession, experience, interests)
        bot.send_message(message.chat.id, "✅ Profile updated successfully!")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error updating profile. Please check the format.")


@bot.message_handler(func=lambda m: m.text == "👤 My profile")
@bot.message_handler(commands=['profile'])
def profile(message):
    user = db.get_user(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "❌ You don't have a profile yet. Use /add to create one.")
        return

    text = (
        f"👤 Name: {user['name']}\n"
        f"💼 Profession: {user['profession']}\n"
        f"📚 Experience: {user['experience']}\n"
        f"✨ Interests: {user['interests']}"
    )
    bot.send_message(message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "edit_interests")
def edit_interests(call):
    bot.send_message(call.message.chat.id, "Enter your interests:")
    bot.register_next_step_handler(call.message, save_interests)

def save_interests(message):
    db.update_interests(message.chat.id, message.text)
    bot.send_message(message.chat.id, "⭐ Interests updated!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "⭐ My interests")
def show_interests(message):
    interests = db.get_interests(message.chat.id)
    if interests:
        bot.send_message(message.chat.id, f"⭐ Your interests:\n{interests}")
    else:
        bot.send_message(message.chat.id, "You don't have any saved interests yet. Add them in your profile!")


@bot.message_handler(func=lambda m: m.text == "❓ FAQ")
def faq_section(message):
    faq_list = db.get_faq()
    text = "📖 Frequently asked questions:\n\n"
    for q, a in faq_list:
        text += f"❓ {q}\n💡 {a}\n\n"

    markup = types.InlineKeyboardMarkup()
    btn_generate = types.InlineKeyboardButton("✨ Generate tips", callback_data="generate_advices")
    btn_settings = types.InlineKeyboardButton("⚙ Settings", callback_data="faq_settings")
    markup.add(btn_generate, btn_settings)

    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "generate_advices")
def generate_advices(call):
    user = db.get_user(call.message.chat.id)
    if user:
        _, _, name, profession, experience, interests, *_ = user
        user_data = {
            "name": name,
            "profession": profession,
            "experience": experience,
            "interests": interests
        }
    else:
        user_data = {}

    sent = bot.send_message(call.message.chat.id, "✨ Generating personalized tips...")
    try:
        answer = gigachat.ask(
            "Generate 3 useful career tips for me.", 
            user_data=user_data
        )
        if not answer: 
            raise ValueError("empty response")

        bot.delete_message(call.message.chat.id, sent.message_id)
        bot.send_message(call.message.chat.id, f"💡 {answer}")

    except Exception as e:
        import traceback
        traceback.print_exc()  
        bot.delete_message(call.message.chat.id, sent.message_id)
        bot.send_message(call.message.chat.id,  "Failed to generate tips.")









@bot.callback_query_handler(func=lambda call: call.data == "faq_settings")
def faq_settings(call):
    status = db.get_expert_mode(call.message.chat.id)
    markup = types.InlineKeyboardMarkup()
    if status:
        btn = types.InlineKeyboardButton("🔴 Disable expert", callback_data="toggle_expert")
    else:
        btn = types.InlineKeyboardButton("🟢 Enable expert", callback_data="toggle_expert")
    markup.add(btn)
    bot.send_message(call.message.chat.id, "⚙ Question mode settings:", reply_markup=markup)







@bot.callback_query_handler(func=lambda call: call.data == "toggle_expert")
def toggle_expert(call):
    user_id = call.message.chat.id
    current = db.get_expert_mode(user_id)
    db.set_expert_mode(user_id, not current)

    if not current:
        bot.answer_callback_query(call.id, "🟢 Expert enabled")
        bot.send_message(user_id, "You can now ask questions and the expert will reply.")
    else:
        bot.answer_callback_query(call.id, "🔴 Expert disabled")
        bot.send_message(user_id, "Expert disabled.")


@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_user_message(message):
    user = db.get_user(message.chat.id)
    if not user:
        return

    if user.get("expert_mode"):
        db.add_message(message.chat.id, "user", message.text)

        history = db.get_history(message.chat.id, limit=20)

        sent = bot.send_message(message.chat.id, "🤔 Expert is thinking...")
        try:

            answer = gigachat.ask(history)

            db.add_message(message.chat.id, "assistant", answer)

            bot.delete_message(message.chat.id, sent.message_id)
            bot.send_message(message.chat.id, f"🧠 Expert: {answer}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            bot.delete_message(message.chat.id, sent.message_id)
            bot.send_message(message.chat.id, "⚠ Error while contacting the expert.")
    else:
        return



if __name__ == "__main__":
    bot.polling(none_stop=True)
