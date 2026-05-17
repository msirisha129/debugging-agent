import os
import re
import time
import json
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#   CONFIG — set via environment variables
# ─────────────────────────────────────────────


from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

MODELS = [

    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",

    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

HISTORY_FILE = "chat_history.json"


# ─────────────────────────────────────────────
#   ERROR DETECTION
# ─────────────────────────────────────────────

def detect_error_info(error: str) -> dict:
    e = error.lower()

    if any(k in e for k in ["traceback", "nameerror", "typeerror", "syntaxerror",
                              "indentationerror", "importerror", "attributeerror",
                              "keyerror", "indexerror", "valueerror", "zerodivisionerror"]):
        lang = "Python"
    elif any(k in e for k in ["referenceerror", "cannot read", "undefined", "node_modules"]):
        lang = "JavaScript"
    elif any(k in e for k in ["nullpointerexception", "classnotfound", "java.lang"]):
        lang = "Java"
    elif any(k in e for k in ["segmentation fault", "undefined reference", "gcc"]):
        lang = "C/C++"
    else:
        lang = "General"

    if any(k in e for k in ["fatal", "crash", "out of memory", "killed"]):
        severity = "🔴 Critical"
    elif any(k in e for k in ["warning", "deprecated"]):
        severity = "🟡 Low"
    else:
        severity = "🟠 Medium"

    if "syntax" in e:
        category = "Syntax Error"
    elif any(k in e for k in ["import", "module", "no module named"]):
        category = "Import Error"
    elif any(k in e for k in ["connection", "timeout", "network"]):
        category = "Network Error"
    elif any(k in e for k in ["key", "index", "out of range"]):
        category = "Index/Key Error"
    elif "type" in e:
        category = "Type Error"
    else:
        category = "Runtime Error"

    return {"language": lang, "severity": severity, "category": category}


# ─────────────────────────────────────────────
#   WEB SEARCH
# ─────────────────────────────────────────────

def web_search_error(error_message: str) -> str:
    try:
        lines = [l.strip() for l in error_message.split("\n") if l.strip()]
        query = lines[-1][:120] if lines else error_message[:100]
        url = "https://api.duckduckgo.com/"
        params = {"q": query + " fix solution", "format": "json", "no_redirect": 1, "no_html": 1}
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        results = []
        if data.get("Abstract"):
            results.append(data["Abstract"][:300])
        for topic in data.get("RelatedTopics", [])[:2]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"][:200])
        if results:
            return "\nWeb context:\n" + "\n".join(f"• {r}" for r in results)
        return ""
    except Exception:
        return ""


# ─────────────────────────────────────────────
#   GROQ API
# ─────────────────────────────────────────────

def call_groq(messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    for model in MODELS:
        try:
            payload = {"model": model, "messages": messages, "max_tokens": 1500, "temperature": 0.3}
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            print("STATUS:", resp.status_code)
            print("RESPONSE:", resp.text)

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue
    return "❌ All models failed. Please check your Groq API key."


# ─────────────────────────────────────────────
#   BUILD PROMPT
# ─────────────────────────────────────────────

def build_messages(error: str, info: dict, web_ctx: str) -> list:
    system = """You are an expert debugging assistant on Telegram.
Keep responses concise and mobile-friendly.
Use this format:

🔍 *What it means*
[1-2 sentences]

🎯 *Root cause*
[One sentence]

🛠️ *Fix*
1. [Step one]
2. [Step two]
3. [Step three if needed]

💻 *Code fix*
```
[fixed code snippet]
```

💡 *Pro tip*
[One short tip]

Use Telegram markdown formatting."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Language: {info['language']}\nCategory: {info['category']}\nSeverity: {info['severity']}\n{web_ctx}\n\nError:\n{error}"}
    ]


# ─────────────────────────────────────────────
#   LOAD / SAVE HISTORY
# ─────────────────────────────────────────────

def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history: dict):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ─────────────────────────────────────────────
#   TELEGRAM HANDLERS
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Debugging Agent Online!*\n\n"
        "Just paste any error message and I'll fix it instantly!\n\n"
        "Commands:\n"
        "• Just paste any error → get fix\n"
        "• /history → see past errors\n"
        "• /stats → error statistics\n"
        "• /help → show this menu",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *How to use:*\n\n"
        "1. Just paste your error message\n"
        "2. I analyze it automatically\n"
        "3. You get the fix in seconds!\n\n"
        "Commands:\n"
        "• /history — last 5 errors\n"
        "• /stats — your error patterns\n"
        "• /clear — clear history\n"
        "• /help — this menu",
        parse_mode="Markdown"
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    history = load_history()
    user_history = history.get(chat_id, [])

    if not user_history:
        await update.message.reply_text("No history yet! Paste your first error 😄")
        return

    msg = "📜 *Last errors:*\n\n"
    for i, h in enumerate(user_history[-5:], 1):
        msg += f"{i}. [{h['timestamp']}]\n"
        msg += f"   {h['category']} — {h['language']}\n"
        msg += f"   `{h['error'][:60]}...`\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    history = load_history()
    user_history = history.get(chat_id, [])

    if not user_history:
        await update.message.reply_text("No stats yet! Paste your first error 😄")
        return

    langs, cats = {}, {}
    for h in user_history:
        langs[h["language"]] = langs.get(h["language"], 0) + 1
        cats[h["category"]]  = cats.get(h["category"],  0) + 1

    msg = f"📊 *Stats — {len(user_history)} errors fixed*\n\n"
    msg += "*Languages:*\n"
    for k, v in sorted(langs.items(), key=lambda x: -x[1]):
        msg += f"  • {k}: {v}\n"
    msg += "\n*Error types:*\n"
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        msg += f"  • {k}: {v}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    history = load_history()
    history[chat_id] = []
    save_history(history)
    await update.message.reply_text("✅ History cleared!")

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id   = str(update.effective_chat.id)
    error_msg = update.message.text.strip()

    if not error_msg:
        return

    # Thinking message
    thinking = await update.message.reply_text("⏳ Analyzing your error...")

    info    = detect_error_info(error_msg)
    web_ctx = web_search_error(error_msg)

    # Analysis summary
    analysis = (
        f"🔎 *Analysis*\n"
        f"💻 Language: {info['language']}\n"
        f"📂 Category: {info['category']}\n"
        f"🚨 Severity: {info['severity']}\n"
    )
    await thinking.edit_text(analysis, parse_mode="Markdown")

    # Get fix
    messages = build_messages(error_msg, info, web_ctx)
    fix = call_groq(messages)

    # Send fix
    await update.message.reply_text(fix, parse_mode="Markdown")

    # Save to history
    history = load_history()
    if chat_id not in history:
        history[chat_id] = []
    history[chat_id].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "error":     error_msg,
        "fix":       fix,
        "language":  info["language"],
        "category":  info["category"],
    })
    save_history(history)

    logger.info(f"Fixed error for chat {chat_id}: {info['category']} in {info['language']}")


# ─────────────────────────────────────────────
#   MAIN
# ─────────────────────────────────────────────

def main():
    if GROQ_API_KEY == "your_groq_api_key_here":
        logger.error("Please set GROQ_API_KEY environment variable!")
        return

    logger.info("🤖 Debugging Agent Bot starting...")
    print("TOKEN:", repr(TELEGRAM_TOKEN))
    if TELEGRAM_TOKEN:
        print("LENGTH:", len(TELEGRAM_TOKEN))
    else:
        print("TOKEN NOT FOUND")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats",   stats_command))
    app.add_handler(CommandHandler("clear",   clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_error))

    logger.info("✅ Bot is running! Send a message on Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
