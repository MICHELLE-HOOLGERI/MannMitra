# MannMitra — Youth Mental Wellness (Prototype)

> A confidential, empathetic **Streamlit** app for Indian youth mental wellness.  
> Built for **H2S Gen AI Exchange Hackathon** using **Google Gemini** + privacy-first local storage.

## ✨ Features
- Anonymous **chat** (English / हिन्दी / Hinglish), stigma-free tone  
- **WHO-5** daily check-in → **Mood graph** (last 14 days) + **Happiness %** (this week)  
- **Quick exercises**: 4-7-8 breathing, 5-4-3-2-1 grounding, Box breathing, Body scan, STOP skill  
- **Contextual suggestions**: recommends exercises/games from chat cues  
- **Mind-ease games**: Color–Word **Stroop**, **Brain Teasers** (5 random riddles + hints)  
- **Crisis guardrails**: Indian helplines shown only on high-risk cues  
- **Quick Hide** screen, **session recap** download

## 📁 Structure

~~~
MannMitra/
├─ app.py
├─ content/
│  ├─ who5.json
│  ├─ exercises.json
│  └─ helplines_in.json
├─ data/           # local logs (ignored)
│  └─ mood_log.csv (created at runtime)
├─ .env            # not committed
├─ .gitignore
└─ requirements.txt
~~~



