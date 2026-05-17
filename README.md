# 🤖 Debugging Agent

A simple AI-powered agent that takes any error message and suggests a fix!

---

## ⚙️ Setup (One Time)

### Step 1 — Install Python
Make sure Python is installed. Check by running:
```
python --version
```

### Step 2 — Install the required library
```
pip install anthropic
```

### Step 3 — Get your API Key
- Go to https://console.anthropic.com
- Sign up / Login
- Create an API key

### Step 4 — Set your API Key

**On Windows:**
```
set ANTHROPIC_API_KEY=your_api_key_here
```

**On Mac/Linux:**
```
export ANTHROPIC_API_KEY=your_api_key_here
```

---

## ▶️ Run the Agent

```
python agent.py
```

---

## 💡 How to Use

1. Run the agent
2. Paste your error message
3. Press Enter twice
4. Get your fix suggestion!

### Example:
```
Enter your error: 
NameError: name 'pd' is not defined
[press Enter twice]

⏳ Analyzing your error...

✅ Here's what I found:
1. What this means: You're using 'pd' but haven't imported pandas...
2. Cause: Missing import statement
3. Fix: Add this at the top of your file: import pandas as pd
```

---

## 📁 Files

| File | What it does |
|------|-------------|
| agent.py | Main agent code |
| requirements.txt | Libraries needed |
| README.md | This guide |
