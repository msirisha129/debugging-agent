# 🤖 Debugging Agent — AI Error Fixer + Telegram Bot

> Paste any error. Get the fix. Instantly. From anywhere in the world. 📱

Every error you paste gets **analyzed, fixed, logged and tracked automatically** — the agent keeps a full record of every bug it has ever fixed, building a personal error database that grows smarter over time.

---

## ✨ What It Does

- 🤖 **AI Fix** — Detects language, severity and category. Gives step-by-step fix with corrected code
- 📁 **Auto Logs Every Fix** — Creates a new timestamped file in `fix_logs/` for every single error fixed
- 🗂️ **Tracks All History** — Every error and fix stored in `error_history.json` — your personal bug database
- 📊 **Error Statistics** — See which errors and languages you hit the most
- 🌐 **Web Search** — Searches the web for extra context on every error automatically
- 🔧 **Auto Fix Files** — Give it your `.py` file path and it patches the bug directly
- 📧 **Email Alerts** — Sends the full fix report to your Gmail
- 📱 **Telegram Bot** — Control everything from your phone, anywhere in the world

---

## 📁 Project Structure

```
debugging-agent/
├── agent.py           # Full terminal version
├── bot.py             # Telegram bot — control from phone
├── requirements.txt   # Dependencies
├── fix_logs/          # Auto-created — one fix file per error 📂
├── error_history.json # Auto-created — full error database 🗄️
└── README.md
```

---

## ⚙️ Local Setup

```bash
git clone https://github.com/msirisha129/debugging-agent.git
cd debugging-agent
pip install -r requirements.txt
```

Get your free API key → [console.groq.com](https://console.groq.com)

```bash
set GROQ_API_KEY=your_groq_key_here
python agent.py
```

---

## 📱 Telegram Bot Commands

| Command | What it does |
|---------|-------------|
| Paste any error | Instant AI fix |
| `/history` | Last 5 errors fixed |
| `/stats` | Your personal error statistics |
| `/clear` | Clear history |
| `/help` | Help menu |

---

## 🚀 Deployment

Deployed on **Railway** — running 24/7 in the cloud. 🚂

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Groq + LLaMA 3 | AI model — free & ultra fast |
| python-telegram-bot | Telegram integration |
| DuckDuckGo API | Web search — no key needed |
| Railway | Cloud hosting — free tier |

---

## 👨‍💻 Built by
**sirisha**
