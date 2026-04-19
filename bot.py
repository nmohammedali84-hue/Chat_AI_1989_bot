import os
import asyncio
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MODEL_META = {
    "claude":   {"name": "Claude",   "persona": "أنت Claude من Anthropic. شخصيتك: تحليلي عميق، صادق، تهتم بالدقة والأخلاقيات. أجب باللغة العربية بأسلوب تحليلي واضح ومختصر.", "emoji": "🟣"},
    "chatgpt":  {"name": "ChatGPT",  "persona": "أنت ChatGPT من OpenAI. شخصيتك: عملي جداً، تحب التنظيم، تعطي خطوات واضحة قابلة للتطبيق. أجب باللغة العربية بإيجاز.", "emoji": "🟢"},
    "gemini":   {"name": "Gemini",   "persona": "أنت Gemini من Google. شخصيتك: إبداعي، تبحث في زوايا غير متوقعة، تستخدم أمثلة واقعية. أجب باللغة العربية.", "emoji": "🔵"},
    "grok":     {"name": "Grok",     "persona": "أنت Grok من xAI. شخصيتك: جريء ومباشر، لا تخاف من قول الحقيقة الصعبة، تتحدى الافتراضات. أجب باللغة العربية بصراحة.", "emoji": "⚫"},
    "llama":    {"name": "Llama",    "persona": "أنت Llama من Meta. شخصيتك: متوازن وموضوعي، تعطي وجهات نظر متعددة بدون تحيز. أجب باللغة العربية.", "emoji": "🟠"},
    "mistral":  {"name": "Mistral",  "persona": "أنت Mistral AI. شخصيتك: دقيق ومنطقي، تحب الكفاءة وتتجنب التكرار. أجب باللغة العربية بإيجاز وعمق.", "emoji": "🟤"},
}

user_sessions = {}

def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "selected_models": ["claude", "chatgpt", "gemini"],
            "rounds": 2,
            "waiting_question": False,
        }
    return user_sessions[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً! أنا *Multi AI Debate Bot*\n\n"
        "أجمع أذكى النماذج في نقاش واحد وأطلع لك أفضل إجابة 🔥\n\n"
        "الأوامر:\n"
        "🤖 /models — اختاري النماذج\n"
        "🔄 /rounds — عدد الجولات\n"
        "💬 /ask — ابدأي النقاش\n"
        "ℹ️ /status — إعداداتك الحالية",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_session(update.effective_user.id)
    models_txt = " | ".join([f"{MODEL_META[m]['emoji']} {MODEL_META[m]['name']}" for m in s["selected_models"]])
    await update.message.reply_text(
        f"⚙️ *إعداداتك الحالية:*\n\n"
        f"🤖 النماذج: {models_txt}\n"
        f"🔄 الجولات: {s['rounds']}",
        parse_mode="Markdown"
    )

async def models_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_session(update.effective_user.id)
    keyboard = []
    row = []
    for key, m in MODEL_META.items():
        selected = key in s["selected_models"]
        label = f"{'✅' if selected else '⬜'} {m['emoji']} {m['name']}"
        row.append(InlineKeyboardButton(label, callback_data=f"toggle_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✔️ حفظ", callback_data="save_models")])
    await update.message.reply_text(
        "🤖 اختاري النماذج (2 على الأقل):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def rounds_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("1 جولة", callback_data="rounds_1"),
            InlineKeyboardButton("2 جولتين", callback_data="rounds_2"),
            InlineKeyboardButton("3 جولات", callback_data="rounds_3"),
        ]
    ]
    await update.message.reply_text(
        "🔄 اختاري عدد الجولات:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_session(update.effective_user.id)
    s["waiting_question"] = True
    await update.message.reply_text("✍️ اكتبي سؤالك أو مهمتك:")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    s = get_session(query.from_user.id)
    data = query.data

    if data.startswith("toggle_"):
        model = data.replace("toggle_", "")
        if model in s["selected_models"]:
            if len(s["selected_models"]) > 2:
                s["selected_models"].remove(model)
        else:
            s["selected_models"].append(model)
        keyboard = []
        row = []
        for key, m in MODEL_META.items():
            selected = key in s["selected_models"]
            label = f"{'✅' if selected else '⬜'} {m['emoji']} {m['name']}"
            row.append(InlineKeyboardButton(label, callback_data=f"toggle_{key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("✔️ حفظ", callback_data="save_models")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "save_models":
        names = " | ".join([f"{MODEL_META[m]['emoji']} {MODEL_META[m]['name']}" for m in s["selected_models"]])
        await query.edit_message_text(f"✅ تم الحفظ!\nالنماذج المختارة: {names}")

    elif data.startswith("rounds_"):
        s["rounds"] = int(data.replace("rounds_", ""))
        await query.edit_message_text(f"✅ تم الحفظ! عدد الجولات: {s['rounds']}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_session(update.effective_user.id)
    if not s["waiting_question"]:
        await update.message.reply_text("💬 استخدمي /ask لبدء النقاش، أو /models لتغيير النماذج.")
        return

    s["waiting_question"] = False
    question = update.message.text
    models = s["selected_models"]
    rounds = s["rounds"]

    await update.message.reply_text(
        f"🚀 بدأ النقاش!\n"
        f"النماذج: {' | '.join([MODEL_META[m]['emoji']+' '+MODEL_META[m]['name'] for m in models])}\n"
        f"الجولات: {rounds}\n\nانتظري قليلاً... ⏳"
    )

    history = []

    for r in range(1, rounds + 1):
        await update.message.reply_text(f"━━━━━━━━━━━━━\n🔄 *جولة {r} من {rounds}*", parse_mode="Markdown")
        for model in models:
            m = MODEL_META[model]
            if r == 1:
                prompt = question
            else:
                prev = "\n\n".join([f"{MODEL_META[h['model']]['name']}: {h['text']}" for h in history])
                prompt = f"السؤال: {question}\n\nما قاله النماذج الأخرى:\n{prev}\n\nردّ على النقاش وقدّم رأيك المحسّن:"

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                system=m["persona"],
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            history.append({"model": model, "text": text})

            await update.message.reply_text(
                f"{m['emoji']} *{m['name']}* — جولة {r}\n\n{text}",
                parse_mode="Markdown"
            )

    await update.message.reply_text("⚖️ *الحَكَم يستخلص أفضل إجابة...*", parse_mode="Markdown")

    all_text = "\n\n---\n\n".join([f"{MODEL_META[h['model']]['name']}:\n{h['text']}" for h in history])
    final = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system="أنت حَكَم محايد وخبير. استخلص أفضل إجابة شاملة من النقاش. أجب باللغة العربية.",
        messages=[{"role": "user", "content": f"السؤال: {question}\n\nالنقاش:\n{all_text}\n\nاستخلص الإجابة المثلى:"}]
    )
    final_text = final.content[0].text

    await update.message.reply_text(
        f"🏆 *الإجابة المثلى*\n\n{final_text}",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("models", models_cmd))
    app.add_handler(CommandHandler("rounds", rounds_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
