import os
from dotenv import load_dotenv

load_dotenv()
import re
import sys
import time
import json
import smtplib
import requests
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from colorama import init, Fore, Style

init(autoreset=True)

# ═══════════════════════════════════════════════════════
#   CONFIGURATION — fill in what you want to use
# ═══════════════════════════════════════════════════════

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "") # 👈 required
print("GROQ KEY:", repr(GROQ_API_KEY))
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

# Email alerts (optional — leave blank to skip)
EMAIL_SENDER   = "msirisha454@gmail.com" # your gmail e.g. you@gmail.com
EMAIL_PASSWORD = "zjttepuhrlgliqgh"          # gmail app-password (not normal password)
EMAIL_RECEIVER = "mothuri29@gmail.com"          # where to send the fix

# Features toggle
ENABLE_WEB_SEARCH  = True
ENABLE_AUTO_FIX    = True
ENABLE_VOICE       = False  # needs: pip install SpeechRecognition pyaudio
ENABLE_EMAIL_ALERT = True  # set True after filling email fields above

MAX_RETRIES   = 3
HISTORY_FILE  = "error_history.json"
LOGS_FOLDER   = "fix_logs"

MODELS = [
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


# ═══════════════════════════════════════════════════════
#   BANNER
# ═══════════════════════════════════════════════════════

def print_banner():
    print(Fore.CYAN + Style.BRIGHT + """
╔════════════════════════════════════════════════════════╗
║           🤖  DEBUGGING AGENT  v4.0                    ║
║   Groq AI · Web Search · Auto Fix · Voice · Email      ║
╚════════════════════════════════════════════════════════╝
""")


# ═══════════════════════════════════════════════════════
#   ERROR DETECTION
# ═══════════════════════════════════════════════════════

def detect_error_info(error: str) -> dict:
    e = error.lower()

    if any(k in e for k in ["traceback", "nameerror", "typeerror", "syntaxerror",
                              "indentationerror", "importerror", "attributeerror",
                              "keyerror", "indexerror", "valueerror", "zerodivisionerror"]):
        lang = "Python"
    elif any(k in e for k in ["referenceerror", "cannot read", "undefined is not",
                                "node_modules", "uncaughtexception", "typeerror: "]):
        lang = "JavaScript / Node.js"
    elif any(k in e for k in ["nullpointerexception", "classnotfound", "java.lang"]):
        lang = "Java"
    elif any(k in e for k in ["segmentation fault", "undefined reference", "gcc", "g++"]):
        lang = "C / C++"
    elif any(k in e for k in ["sqlexception", "syntax error near", "ora-", "mysql", "postgres"]):
        lang = "SQL / Database"
    else:
        lang = "General"

    if any(k in e for k in ["fatal", "crash", "segmentation", "out of memory", "killed"]):
        severity = "🔴 Critical"
    elif any(k in e for k in ["warning", "deprecated", "notice"]):
        severity = "🟡 Low"
    else:
        severity = "🟠 Medium"

    if "syntax" in e:
        category = "Syntax Error"
    elif any(k in e for k in ["import", "module", "package", "no module named"]):
        category = "Import / Module Error"
    elif any(k in e for k in ["connection", "timeout", "network", "refused"]):
        category = "Network / Connection Error"
    elif any(k in e for k in ["permission", "access denied", "forbidden"]):
        category = "Permission Error"
    elif any(k in e for k in ["memory", "heap", "stack overflow"]):
        category = "Memory Error"
    elif "type" in e:
        category = "Type Error"
    elif any(k in e for k in ["key", "index", "out of range"]):
        category = "Index / Key Error"
    else:
        category = "Runtime Error"

    return {"language": lang, "severity": severity, "category": category}


# ═══════════════════════════════════════════════════════
#   WEB SEARCH — DuckDuckGo (no API key needed!)
# ═══════════════════════════════════════════════════════

def web_search_error(error_message: str) -> str:
    if not ENABLE_WEB_SEARCH:
        return ""
    try:
        # Extract first meaningful line of error
        lines = [l.strip() for l in error_message.split("\n") if l.strip()]
        query = lines[-1] if lines else error_message[:100]
        query = query[:120]

        print(Fore.BLUE + f"  🌐 Searching web for: {query[:60]}...")

        url = "https://api.duckduckgo.com/"
        params = {"q": query + " fix solution", "format": "json", "no_redirect": 1, "no_html": 1}
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        results = []

        # Abstract (main blurb)
        if data.get("Abstract"):
            results.append(f"• {data['Abstract'][:300]}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"• {topic['Text'][:200]}")

        if results:
            return "\n🌐 Web context found:\n" + "\n".join(results)
        else:
            return "\n🌐 No direct web results — AI analysis only."

    except Exception as e:
        return f"\n🌐 Web search skipped ({e})"


# ═══════════════════════════════════════════════════════
#   GROQ API CALL WITH MODEL FALLBACK
# ═══════════════════════════════════════════════════════

def call_groq(messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    for model in MODELS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(Fore.YELLOW + f"  ⚡ {model} (attempt {attempt}/{MAX_RETRIES})...")
                payload = {"model": model, "messages": messages,
                           "max_tokens": 2000, "temperature": 0.3}
                resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except requests.exceptions.Timeout:
                print(Fore.RED + "  ⏱️  Timeout, retrying...")
                time.sleep(1)
            except requests.exceptions.HTTPError as ex:
                print(Fore.RED + f"  ❌ HTTP {ex.response.status_code} — trying next model...")
                break
            except Exception as ex:
                print(Fore.RED + f"  ❌ {ex}")
                if attempt == MAX_RETRIES:
                    break
                time.sleep(1)
    return "❌ All models failed. Check your API key and internet connection."


# ═══════════════════════════════════════════════════════
#   BUILD PROMPT
# ═══════════════════════════════════════════════════════

def build_messages(error: str, info: dict, history: list, web_ctx: str) -> list:
    system = """You are an expert software debugging assistant with 10+ years of experience.
Analyze the error and respond EXACTLY in this format:

## 🔍 What This Error Means
[Clear 2-3 sentence explanation for a beginner]

## 🎯 Root Cause
[Most likely reason this happened]

## 🛠️ Step-by-Step Fix
1. [Step one]
2. [Step two]
3. [Step three if needed]

## 💻 Corrected Code
```
[Fixed code snippet — always include this!]
```

## ⚡ Quick Checklist
- [ ] [Thing to verify 1]
- [ ] [Thing to verify 2]

## 💡 Pro Tip
[One expert tip to prevent this in future]

Be concise, practical, and beginner-friendly."""

    msgs = [{"role": "system", "content": system}]
    for h in history[-4:]:
        msgs.append({"role": "user",      "content": h["error"]})
        msgs.append({"role": "assistant", "content": h["fix"]})

    user_msg = f"""Language: {info['language']}
Category: {info['category']}
Severity: {info['severity']}
{web_ctx}

Error:
{error}"""
    msgs.append({"role": "user", "content": user_msg})
    return msgs


# ═══════════════════════════════════════════════════════
#   AUTO FIX — reads file, patches the bug
# ═══════════════════════════════════════════════════════

def auto_fix_file(fix_suggestion: str, error_message: str):
    if not ENABLE_AUTO_FIX:
        return

    # Try to extract filename from error traceback
    file_match = re.search(r'File ["\'](.+?\.py)["\']', error_message)
    if file_match:
        detected_file = file_match.group(1)
    else:
        detected_file = None

    print()
    if detected_file and os.path.exists(detected_file):
        print(Fore.CYAN + f"  📂 Detected file: {detected_file}")
        confirm = input(Fore.CYAN + f"  Auto-fix {detected_file}? (y/n): ").strip().lower()
        filepath = detected_file if confirm == "y" else None
    else:
        print(Fore.CYAN + "  🔧 Auto Fix — enter the path to your file to patch it:")
        print(Fore.LIGHTBLACK_EX + "     (press Enter to skip)")
        filepath = input(Fore.WHITE + "  File path: ").strip()

    if not filepath:
        print(Fore.YELLOW + "  ⏭️  Auto fix skipped.\n")
        return

    if not os.path.exists(filepath):
        print(Fore.RED + f"  ❌ File not found: {filepath}\n")
        return

    # Read the file
    with open(filepath, "r", encoding="utf-8") as f:
        original_code = f.read()

    print(Fore.YELLOW + "  ⚡ Asking AI to patch your file...")

    patch_messages = [
        {"role": "system", "content": """You are a code patching assistant.
You will receive the original code and a fix suggestion.
Return ONLY the complete fixed Python code with no explanation, no markdown, no backticks.
Just pure Python code that can be saved directly to a .py file."""},
        {"role": "user", "content": f"""Fix suggestion:
{fix_suggestion}

Original code:
{original_code}

Return the complete fixed code only."""}
    ]

    fixed_code = call_groq(patch_messages)

    # Clean any accidental markdown
    fixed_code = re.sub(r"^```[a-z]*\n?", "", fixed_code.strip())
    fixed_code = re.sub(r"\n?```$",       "", fixed_code.strip())

    # Backup original
    backup_path = filepath + ".backup"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(original_code)

    # Write fixed code
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(fixed_code)

    print(Fore.GREEN + f"  ✅ File patched: {filepath}")
    print(Fore.LIGHTBLACK_EX + f"  💾 Backup saved: {backup_path}\n")


# ═══════════════════════════════════════════════════════
#   VOICE INPUT — speak your error
# ═══════════════════════════════════════════════════════

def get_voice_input() -> str:
    if not ENABLE_VOICE:
        return ""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        print(Fore.MAGENTA + "  🎤 Speak your error now (listening for 10 seconds)...")
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=1)
            r.energy_threshold = 4000
            audio = r.listen(source, timeout=5, phrase_time_limit=6)
        text = r.recognize_google(audio)
        print(Fore.GREEN + f"  ✅ Heard: {text}\n")
        return text
    except ImportError:
        print(Fore.RED + "  ❌ Voice not installed. Run: pip install SpeechRecognition pyaudio")
        return ""
    except Exception as e:
        print(Fore.RED + f"  ❌ Voice error: {e}")
        return ""


# ═══════════════════════════════════════════════════════
#   EMAIL ALERT
# ═══════════════════════════════════════════════════════

def send_email_alert(error: str, fix: str, info: dict):
    if not ENABLE_EMAIL_ALERT or not EMAIL_SENDER or not EMAIL_RECEIVER:
        return
    try:
        print(Fore.BLUE + "  📧 Sending email alert...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🐛 Bug Fix Ready — {info['category']} in {info['language']}"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = EMAIL_RECEIVER

        body = f"""Debugging Agent Fix Report
{'='*50}
Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Language : {info['language']}
Category : {info['category']}
Severity : {info['severity']}
{'='*50}

ERROR:
{error}

FIX:
{fix}
"""
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(Fore.GREEN + f"  ✅ Fix emailed to {EMAIL_RECEIVER}\n")
    except Exception as e:
        print(Fore.RED + f"  ❌ Email failed: {e}\n")


# ═══════════════════════════════════════════════════════
#   SAVE LOG
# ═══════════════════════════════════════════════════════

def save_log(error: str, fix: str, info: dict) -> str:
    os.makedirs(LOGS_FOLDER, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOGS_FOLDER, f"fix_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Language  : {info['language']}\n")
        f.write(f"Category  : {info['category']}\n")
        f.write(f"Severity  : {info['severity']}\n")
        f.write("=" * 60 + "\n\nERROR:\n" + error + "\n\nFIX:\n" + fix + "\n")
    return path


# ═══════════════════════════════════════════════════════
#   HISTORY HELPERS
# ═══════════════════════════════════════════════════════

def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history: list):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def show_history(history: list):
    if not history:
        print(Fore.YELLOW + "\n  No history yet!\n"); return
    print(Fore.CYAN + f"\n  Last {min(len(history),5)} errors:\n")
    for i, h in enumerate(history[-5:], 1):
        print(Fore.WHITE       + f"  {i}. [{h['timestamp']}]  {h['category']} — {h['language']}")
        print(Fore.LIGHTBLACK_EX + f"     {h['error'][:90]}...")
        print()

def show_stats(history: list):
    if not history:
        print(Fore.YELLOW + "\n  No stats yet!\n"); return
    langs, cats = {}, {}
    for h in history:
        langs[h["language"]] = langs.get(h["language"], 0) + 1
        cats[h["category"]]  = cats.get(h["category"],  0) + 1
    print(Fore.CYAN + f"\n  📊 {len(history)} errors analyzed\n")
    print(Fore.WHITE + "  Languages:")
    for k, v in sorted(langs.items(), key=lambda x: -x[1]):
        print(Fore.LIGHTBLACK_EX + f"    {k}: {v}")
    print(Fore.WHITE + "\n  Error types:")
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        print(Fore.LIGHTBLACK_EX + f"    {k}: {v}")
    print()

def print_help():
    print(Fore.GREEN + "\n  Commands:")
    print(Fore.WHITE + "  • Paste error + Enter twice  →  get fix")
    print(Fore.WHITE + "  • 'voice'    →  speak your error")
    print(Fore.WHITE + "  • 'history'  →  past errors")
    print(Fore.WHITE + "  • 'stats'    →  error statistics")
    print(Fore.WHITE + "  • 'clear'    →  clear history")
    print(Fore.WHITE + "  • 'help'     →  show this menu")
    print(Fore.WHITE + "  • 'exit'     →  quit\n")


# ═══════════════════════════════════════════════════════
#   MAIN LOOP
# ═══════════════════════════════════════════════════════

def main():
    print_banner()

    if GROQ_API_KEY == "your_groq_api_key_here":
        print(Fore.RED + Style.BRIGHT + "  ⚠️  Paste your Groq API key in agent.py line 18!")
        print(Fore.YELLOW + "  Get it free: https://console.groq.com\n")
        return

    features = []
    if ENABLE_WEB_SEARCH:  features.append("🌐 Web search")
    if ENABLE_AUTO_FIX:    features.append("🔧 Auto fix")
    if ENABLE_VOICE:       features.append("🎤 Voice input")
    if ENABLE_EMAIL_ALERT: features.append("📧 Email alert")
    print(Fore.GREEN + "  Active features: " + "  ".join(features))

    history = load_history()
    print_help()

    while True:
        print(Fore.CYAN + Style.BRIGHT + "📋 Paste error (Enter twice when done):")

        lines = []
        while True:
            try:
                line = input()
            except KeyboardInterrupt:
                print(Fore.YELLOW + "\n\n  👋 Bye!")
                save_history(history)
                return

            cmd = line.strip().lower()

            if cmd == "exit":
                print(Fore.YELLOW + "\n  👋 Bye!")
                save_history(history)
                return
            if cmd == "history":
                show_history(history); lines = []; break
            if cmd == "stats":
                show_stats(history);   lines = []; break
            if cmd == "clear":
                history = []; save_history(history)
                print(Fore.GREEN + "\n  ✅ Cleared!\n"); lines = []; break
            if cmd == "help":
                print_help(); lines = []; break
            if cmd == "voice":
                spoken = get_voice_input()
                if spoken:
                    lines = [spoken]
                break
            if line == "" and lines:
                break
            lines.append(line)

        if not lines:
            continue

        error = "\n".join(lines).strip()
        if not error:
            continue

        info    = detect_error_info(error)
        web_ctx = web_search_error(error)

        print()
        print(Fore.LIGHTBLACK_EX + "  ┌─ Analysis ──────────────────────────────────────")
        print(Fore.WHITE         + f"  │  💻 Language : {info['language']}")
        print(Fore.WHITE         + f"  │  📂 Category : {info['category']}")
        print(Fore.WHITE         + f"  │  🚨 Severity : {info['severity']}")
        print(Fore.LIGHTBLACK_EX + "  └─────────────────────────────────────────────────")
        print()

        messages = build_messages(error, info, history, web_ctx)
        fix      = call_groq(messages)

        print()
        print(Fore.GREEN + Style.BRIGHT + "  ✅ Fix:\n")
        print(Fore.WHITE + fix)
        print()

        # Auto fix file
        auto_fix_file(fix, error)

        # Email alert
        send_email_alert(error, fix, info)

        # Save log
        log_path = save_log(error, fix, info)
        print(Fore.LIGHTBLACK_EX + f"  💾 Saved: {log_path}")
        print(Fore.LIGHTBLACK_EX + "  " + "─" * 50 + "\n")

        history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "error":     error,
            "fix":       fix,
            "language":  info["language"],
            "category":  info["category"],
        })
        save_history(history)


if __name__ == "__main__":
    main()
