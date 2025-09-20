import os, json, time, random, re
import pandas as pd
import streamlit as st
from pathlib import Path
import datetime as dt

# ---------- env & config ----------
st.set_page_config(page_title="MannMitra (Prototype)", page_icon="💚", layout="wide")
APP_DIR = Path(__file__).parent
os.makedirs(APP_DIR / "data", exist_ok=True)

# ---------- aesthetic CSS ----------
st.markdown("""
<style>
:root{ --bg1:#0ea5e9; --bg2:#a78bfa; --card:#111827; --text:#e5e7eb; --muted:#cbd5e1; --accent:#22c55e; }
.block-container{padding-top:2rem;}
[data-testid="stAppViewContainer"]{ background:linear-gradient(135deg,rgba(14,165,233,.10),rgba(167,139,250,.10)); }
.stContainer > div{ border-radius:16px !important; border:1px solid rgba(226,232,240,.12) !important; background:var(--card) !important; box-shadow:0 8px 24px rgba(2,6,23,.35) !important; }
body,[data-testid="stAppViewContainer"] .stMarkdown,[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] li,[data-testid="stAppViewContainer"] label,[data-testid="stSidebar"] *{ color:var(--text) !important; line-height:1.6;}
h1,h2,h3,h4{ margin-top:.6rem !important; line-height:1.25; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto; }
.stButton>button{ background:linear-gradient(135deg,var(--bg1),var(--bg2)); color:#fff; border:none; border-radius:12px; padding:.5rem 1rem; font-weight:700; }
.stButton>button:hover{ filter:brightness(.96); }
[data-testid="stMetricValue"]{font-weight:800;}
.stChatMessage{ background:#0b1220 !important; border-radius:16px; }
.stChatMessage, .stChatMessage * { color:#f8fafc !important; }
.chat-scroll{ max-height:60vh; overflow-y:auto; padding-right:8px; }
</style>
""", unsafe_allow_html=True)

# ---------- helpers ----------
def load_json_safe(rel_path: str, default: dict):
    p = APP_DIR / rel_path
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def pick_new(state_key: str, choices: list[str]) -> str:
    last = st.session_state.get(state_key)
    pool = [c for c in choices if c != last] or choices
    choice = random.choice(pool)
    st.session_state[state_key] = choice
    return choice

CHEER_LOW  = ["Tough days happen. You still showed up — that matters.","Be gentle with yourself today. Tiny steps count."]
CHEER_OK   = ["Steady is good. Normal days build strength.","Nice balance today — keep the kind pace."]
CHEER_HIGH = ["Great vibe — share a kind word today!","Lovely energy — note what helped and repeat it."]
QUOTE_LOW  = ["“Small steps are still steps.”","“No rain, no flowers.”"]
QUOTE_OK   = ["“Ordinary days build extraordinary strength.”","“Consistency beats intensity.”"]
QUOTE_HIGH = ["“Joy shared is joy doubled.”","“Gratitude turns enough into plenty.”"]

GAME_GOOD   = ["Great focus — your attention is sharp! 👏","Awesome run — you were dialed in! ⚡"]
GAME_AVG    = ["Nice effort — try once more, slow and steady.","Solid! One more round can boost it further."]
GAME_LOW    = ["Mind might be busy — a 30-sec breath can help.","It’s okay — reset with a breath and try again."]
GAME_QUOTES = ["“Focus grows where attention goes.”","“Progress > perfection.”","“Storms pass; you stay.”"]

# ---------- content files (safe defaults) ----------
WHO5 = load_json_safe("content/who5.json", {
    "items":[
        "I have felt cheerful and in good spirits",
        "I have felt calm and relaxed",
        "I have felt active and vigorous",
        "I woke up feeling fresh and rested",
        "My daily life has been filled with things that interest me"
    ]
})
EXERCISES = load_json_safe("content/exercises.json", {
    "breathing_478":{"title":"4-7-8 Breathing","steps":["Inhale 4s","Hold 7s","Exhale 8s"],"cycles":3},
    "grounding_54321":{"title":"5-4-3-2-1 Grounding","steps":["5 see","4 touch","3 hear","2 smell","1 taste"],"cycles":1}
})
HELPLINES = load_json_safe("content/helplines_in.json", {
    "tele_manas":{"name":"Tele-MANAS","phone":"14416","alt":"1-800-891-4416"},
    "kiran":{"name":"KIRAN","phone":"1800-599-0019"}
})

# ---------- extra exercises ----------
MORE_EXERCISES = {
    "box_breath":{"title":"Box Breathing","when":"Feeling anxious or heart racing; need a quick reset.",
                  "what":"Inhale–Hold–Exhale–Hold for equal counts.","steps":["Inhale 4s","Hold 4s","Exhale 4s","Hold 4s"],"cycles":4},
    "body_scan":{"title":"60-sec Body Scan","when":"Tense or restless; want to relax before sleep or study.",
                 "what":"Move attention head to toe, relaxing each area.",
                 "steps":["Head & face relax","Neck & shoulders soften","Chest & arms loosen","Stomach unclench","Legs feel heavy","Notice easy breathing"],"cycles":1},
    "stop_skill":{"title":"STOP Skill","when":"Strong emotions or urge to react; need a pause.",
                  "what":"DBT micro-skill: pause, breathe, observe, proceed.",
                  "steps":["S—Stop","T—Take a slow breath","O—Observe body/thoughts","P—Proceed with one small helpful action"],"cycles":1}
}

# ---------- Gemini (optional) ----------
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
client = None
if api_key:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except Exception:
        client = None

SYSTEM = ("You are MannMitra, an empathetic, non-judgmental wellness companion for Indian youth. "
          "Be supportive, reduce stigma. Offer gentle self-care (breathing, grounding, journaling). "
          "Do not diagnose or prescribe. If crisis/self-harm hints appear, encourage immediate help and show helplines.")

def gemini_reply(msg: str, lang: str = "English") -> str:
    if not client:
        if lang == "हिन्दी": return "मैं आपकी बात सुन रहा/रही हूँ। आप अकेले नहीं हैं।"
        if lang == "Hinglish": return "Main sun raha/rahi hoon. Aap akelay nahi ho."
        return "Thanks for sharing. I’m here to listen."
    try:
        lang_instr = {
            "English":"Reply in natural, supportive English.",
            "हिन्दी":"Reply in Hindi (Devanagari). Keep it warm and simple.",
            "Hinglish":"Reply in Hindi written in Latin script (Hinglish). Example: 'main theek hoon'. Keep tone warm."
        }[lang]
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[{"role":"user","parts":[{"text": f"{SYSTEM}\n{lang_instr}\nUser: {msg}"}]}]
        )
        return (resp.text or "").strip() or ("Main theek hoon." if lang!="English" else "I’m here for you.")
    except Exception as e:
        return f"(Temporary issue: {e}) I’m still here to support you."

# ---------- risk classification ----------
def classify_risk(text: str) -> int:
    tl = text.lower()
    urgent = any(x in tl for x in ["suicide","kill myself","end my life","jump off","hang myself","आत्महत्या","hurt myself badly"])
    high   = any(x in tl for x in ["self harm","cut myself","can't go on","no reason to live","severe pain"])
    if urgent: return 3
    if high:   return 2
    if client:
        try:
            r = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[{"role":"user","parts":[{"text": "Classify self-harm risk: return only JSON {\"risk\":0|1|2|3}. Message: "+text}]}]
            )
            import json as _json
            return int(_json.loads((r.text or "{}").strip()).get("risk",0))
        except Exception:
            pass
    if any(x in tl for x in ["very sad","depressed","lonely","crying","hopeless","numb","empty"]): return 1
    return 0

# ---------- suggestion rules ----------
SUGGESTION_RULES = [
    {"id":"breathing_478","type":"exercise","title":"Try 4-7-8 breathing",
     "match_any":[r"\banxious\b", r"\banxiety\b", r"\bstressed?\b", r"\boverwhelm", r"घबराहट", r"tension"]},
    {"id":"grounding_54321","type":"exercise","title":"Try 5-4-3-2-1 grounding",
     "match_any":[r"\boverthink", r"\bspiral", r"\bloop", r"\bracing thoughts\b"]},
    {"id":"stroop","type":"game","title":"Play a 1-minute Focus game",
     "match_any":[r"\bbored\b", r"\bdistract", r"\bcan.?t focus\b", r"\bprocrastinat"]},
]
def _regex_any(patterns, text): return any(re.search(p, text.lower()) for p in patterns)
def choose_suggestion(user_text: str):
    for r in SUGGESTION_RULES:
        if _regex_any(r["match_any"], user_text): return {"source":"rules", **r}
    if len(user_text.split()) >= 25:
        return {"source":"rules","id":"breathing_478","type":"exercise","title":"Try 4-7-8 breathing"}
    return None

# ---------- sidebar state ----------
st.session_state.setdefault("quick_hide", False)
st.session_state.setdefault("history", [])
st.session_state.setdefault("lang", "English")

with st.sidebar:
    st.markdown("### Privacy & Tools")
    cA, cB = st.columns(2)
    if cA.button("🔒 Quick Hide"): st.session_state.quick_hide = True
    if cB.button("🔓 Unhide"):     st.session_state.quick_hide = False
    st.session_state.lang = st.radio("Reply language / भाषा", ["English","हिन्दी","Hinglish"], index=0)
    st.caption("**AI status:** " + ("✅ Gemini enabled" if client else "⚠️ Fallback mode (no API key)"))

    # recap
    def build_recap(history, lang):
        last_user = [t for r,t in history if r=="user"][-3:]
        points = "\n".join(f"- {x}" for x in last_user) if last_user else "- (no details)"
        base = f"Session recap ({lang}):\n{points}\n\nTiny plan for today:\n• 3 cycles 4-7-8\n• One kind line to yourself\n• 10-min walk"
        if client and last_user:
            try:
                pr = f"{SYSTEM}\nSummarize in {lang} ≤60 words, then 3-bullet plan. Return plain text.\n" + "\n".join(last_user)
                r = client.models.generate_content(model="gemini-2.5-flash-lite", contents=[{"role":"user","parts":[{"text":pr}]}])
                return (r.text or "").strip() or base
            except: return base
        return base
    if st.button("📝 Generate recap"):
        txt = build_recap(st.session_state.history, st.session_state.lang)
        st.text_area("Recap preview", txt, height=160)
        st.download_button("Download recap (.txt)", txt, file_name="recap.txt", mime="text/plain")

if st.session_state.quick_hide:
    st.markdown("### ✨ Screen hidden. This is your space — take a slow breath. When ready, unhide from the sidebar.")
    st.stop()

# ---------- UI ----------
left, right = st.columns([3,2])

with left:
    st.markdown("## 💚 MannMitra — Youth Wellness (Prototype)")
    st.caption("Anonymous demo • Not medical advice • Data stays local")

    # Chat
    with st.container(border=True):
        st.subheader("Chat")
        st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
        for role, text in st.session_state.history:
            st.chat_message(role).markdown(text)
        st.markdown('</div>', unsafe_allow_html=True)

        user_msg = st.chat_input("Share what's on your mind… (EN/Hinglish/Hindi)")
        if user_msg:
            plain = user_msg.strip().lower().rstrip("?.! ")
            if plain in {"aap kaise ho","kaise ho","tum kaise ho"}:
                if st.session_state.lang=="हिन्दी":
                    st.session_state.history.append(("assistant","मैं ठीक हूँ — आपका शुक्रिया! आप कैसे हैं?"))
                elif st.session_state.lang=="Hinglish":
                    st.session_state.history.append(("assistant","Main theek hoon — shukriya! Aap kaise ho?"))
                else:
                    st.session_state.history.append(("assistant","I’m doing well — thanks for asking! How are you?"))
                st.rerun()

            st.session_state.history.append(("user", user_msg))
            risk = classify_risk(user_msg)
            if risk >= 2:
                st.error(
                    "You deserve support. If you’re in danger, please reach out now.\n\n"
                    f"📞 {HELPLINES['tele_manas']['name']}: {HELPLINES['tele_manas']['phone']} / {HELPLINES['tele_manas'].get('alt','')}\n"
                    f"📞 {HELPLINES['kiran']['name']}: {HELPLINES['kiran']['phone']}"
                )
                st.session_state.pop("suggestion", None)
            elif risk == 1:
                st.info("Thanks for sharing how heavy this feels. Would you like to tell me what made today hard?")
                st.session_state["suggestion"] = choose_suggestion(user_msg)
            else:
                st.session_state["suggestion"] = choose_suggestion(user_msg)

            bot = gemini_reply(user_msg, st.session_state.lang)
            st.session_state.history.append(("assistant", bot))
            st.rerun()

    # Suggestion card
    if st.session_state.get("suggestion"):
        sug = st.session_state["suggestion"]
        with st.container(border=True):
            st.markdown("#### Suggested for you")
            if sug["type"] == "exercise":
                ex = EXERCISES.get(sug["id"], {})
                st.write(f"**{sug['title']}** · quick relief")
                st.caption("A short, guided step you can try now.")
                if st.button("Start now", key="sug_start_ex"):
                    steps = ex.get("steps", [])
                    st.info("Take your time:\n- " + "\n- ".join(steps) if steps else "Let's take a gentle minute together.")
                    st.success(pick_new("cheer_ex", [
                        "Nice choice — tiny steps change the vibe.",
                        "Good call — gentle actions shift the day."
                    ]) + "\n\n" + pick_new("quote_ex", ["“Slow is smooth, and smooth is fast.”","“One breath at a time.”"]))
                    st.session_state.pop("suggestion", None)
                if st.button("Not now", key="sug_skip_ex"):
                    st.session_state.pop("suggestion", None)

            elif sug["type"] == "game" and sug["id"] == "stroop":
                st.write("**Play a 1-minute Focus game (Stroop)**")
                st.caption("Tap the INK color (ignore the word). It helps reset attention.")
                if st.button("Play now", key="sug_play_stroop"):
                    st.session_state["show_stroop"] = True
                    st.session_state.pop("suggestion", None)
                    st.rerun()
                if st.button("Not now", key="sug_skip_game"):
                    st.session_state.pop("suggestion", None)

    # Quick Exercises
    with st.container(border=True):
        st.subheader("Quick Exercises")
        merged = {
            "breathing_478": {
                "title": EXERCISES.get("breathing_478", {}).get("title","4-7-8 Breathing"),
                "when": "Anxious or restless; calm down in <2 min.",
                "what": "Paced breathing that nudges the body toward calm.",
                "steps": EXERCISES.get("breathing_478", {}).get("steps", ["Inhale 4s","Hold 7s","Exhale 8s"]),
                "cycles": EXERCISES.get("breathing_478", {}).get("cycles", 3)
            },
            "grounding_54321": {
                "title": EXERCISES.get("grounding_54321", {}).get("title","5-4-3-2-1 Grounding"),
                "when": "Overthinking; come back to the present.",
                "what": "Use your senses to anchor attention safely.",
                "steps": EXERCISES.get("grounding_54321", {}).get("steps", ["5 see","4 touch","3 hear","2 smell","1 taste"]),
                "cycles": 1
            }
        }
        merged.update(MORE_EXERCISES)
        for eid, meta in merged.items():
            with st.expander(f"🧩 {meta['title']}"):
                st.caption(f"**When to use:** {meta['when']}")
                st.caption(f"**What it is:** {meta['what']}")
                if st.button("Start", key=f"ex_{eid}"):
                    st.info("Take your time:\n- " + "\n- ".join(meta["steps"]))
                    st.success(pick_new("cheer_ex2", [
                        "You showed up for yourself today.",
                        "Nice — caring for yourself is strength."
                    ]) + "\n\n" + pick_new("quote_ex2", ["“One breath at a time.”","“Small acts, big change.”"]))

with right:
    # WHO-5 Check-in
    with st.container(border=True):
        st.subheader("How was your day? (WHO-5)")
        who5_scores = []
        with st.form("who5_form", clear_on_submit=True):
            for i, q in enumerate(WHO5["items"]):
                who5_scores.append(st.radio(q, options=[0,1,2,3,4,5], horizontal=True, key=f"q{i}"))
            note = st.text_input("One line about today (optional)")
            submitted = st.form_submit_button("Save check-in")
        if submitted:
            total = sum(who5_scores) * 4   # 0–100
            row = pd.DataFrame([{"ts": int(time.time()), "score": total, "note": note}])
            path = APP_DIR / "data/mood_log.csv"
            if path.exists():
                prev = pd.read_csv(path); row = pd.concat([prev, row], ignore_index=True)
            row.to_csv(path, index=False)
            st.success(f"Saved! Today’s WHO-5 score: {total}/100")
            if total < 40:
                st.warning(pick_new("cheer_low", CHEER_LOW) + "\n\n" + pick_new("q_low", QUOTE_LOW))
            elif total < 70:
                st.info(pick_new("cheer_ok", CHEER_OK) + "\n\n" + pick_new("q_ok", QUOTE_OK))
            else:
                st.success(pick_new("cheer_high", CHEER_HIGH) + "\n\n" + pick_new("q_high", QUOTE_HIGH))

    # Mood & Happiness — bar if 1 point, line if 2+
    with st.container(border=True):
        st.subheader("Mood & Happiness")
        path = APP_DIR / "data/mood_log.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["ts"], unit="s").dt.date
            daily = df.groupby("date")["score"].mean().tail(14)
            daily.index.name = "Date"
            if len(daily) == 1:
                st.caption("One entry so far — showing a bar. Add another day to see a line.")
                st.bar_chart(daily, height=220)
            else:
                st.line_chart(daily, height=220)
            today = dt.date.today()
            past7 = {today - dt.timedelta(days=i) for i in range(7)}
            wdf = daily[daily.index.isin(past7)]
            happy_days = int((wdf >= 60).sum())
            st.metric("Happy days this week", f"{happy_days}/7")
        else:
            st.info("No check-ins yet. Submit WHO-5 above to see your graphs.")

# ---------- Games ----------
st.divider()
st.subheader("🎮 Mind-Ease Games")

now_ts = time.time()
if "reaction_result_until" in st.session_state and now_ts < st.session_state.reaction_result_until:
    kind = st.session_state.reaction_result_payload.get("type","info")
    text = st.session_state.reaction_result_payload.get("text","")
    (st.success if kind=="success" else st.warning if kind=="warning" else st.info)(text)
elif "reaction_result_until" in st.session_state and now_ts >= st.session_state.reaction_result_until:
    st.session_state.pop("reaction_result_until", None)
    st.session_state.pop("reaction_result_payload", None)

st.session_state.setdefault("show_stroop", False)
st.session_state.setdefault("show_quiz", False)

# --- Game 1: Stroop ---
with st.container(border=True):
    st.markdown("**Color–Word Stroop (≈1 min):** Helps attention control and reduces rumination by refocusing on a simple rule.")
    if not st.session_state.show_stroop:
        if st.button("Play Stroop"):
            st.session_state.show_stroop = True
            st.rerun()
    else:
        COLORS = ["RED","BLUE","GREEN","YELLOW","PURPLE","ORANGE"]
        for k,v in {"stroop_trial":0,"stroop_score":0,"stroop_start":None,"stroop_item":None}.items():
            st.session_state.setdefault(k,v)
        def new_item():
            return random.choice(COLORS), random.choice(COLORS)
        if st.session_state.stroop_item is None: st.session_state.stroop_item = new_item()
        TRIALS = 5
        trial = st.session_state.stroop_trial
        word, ink = st.session_state.stroop_item
        if trial==0 and st.session_state.stroop_start is None: st.session_state.stroop_start = time.time()
        st.caption("Tap the **INK COLOR** (ignore the word). 5 rounds.")
        st.markdown(f"<h1 style='color:{ink.lower()};margin-top:0'>{word}</h1>", unsafe_allow_html=True)
        cols = st.columns(len(COLORS))
        for i,c in enumerate(COLORS):
            if cols[i].button(c):
                st.session_state.stroop_trial += 1
                if c==ink: st.session_state.stroop_score += 1
                if st.session_state.stroop_trial >= TRIALS:
                    dur = time.time()-st.session_state.stroop_start
                    score = st.session_state.stroop_score
                    if score >= 4:
                        text = f"{pick_new('game_good', GAME_GOOD)} {score}/{TRIALS} in {dur:.1f}s\n\n{pick_new('gq', GAME_QUOTES)}"
                        st.success(text); st.session_state.reaction_result_payload={"type":"success","text":text}
                    elif score == 3:
                        text = f"{pick_new('game_avg', GAME_AVG)} {score}/{TRIALS}\n\n{pick_new('gq', GAME_QUOTES)}"
                        st.info(text); st.session_state.reaction_result_payload={"type":"info","text":text}
                    else:
                        text = f"{pick_new('game_low', GAME_LOW)} {score}/{TRIALS}\n\n{pick_new('gq', GAME_QUOTES)}"
                        st.warning(text); st.session_state.reaction_result_payload={"type":"warning","text":text}
                    st.session_state.reaction_result_until = time.time() + 20
                    st.session_state.update({"stroop_trial":0,"stroop_score":0,"stroop_start":None,"stroop_item":None,"show_stroop":False})
                else:
                    st.session_state.stroop_item = new_item()
                st.rerun()

# --- Game 2: Brain Teaser Quiz (same as before) ---
RIDDLES = [
    {"q":"What is that which can run but has no legs?","answers":["clock"],"hint":"It has hands and a face but cannot walk."},
    {"q":"What runs but never walks, has a mouth but never talks?","answers":["river"],"hint":"It flows to the sea."},
    {"q":"What has to be broken before you can use it?","answers":["egg"],"hint":"Found at breakfast."},
    {"q":"What has hands but can’t clap?","answers":["clock","a clock"],"hint":"It tells time."},
    {"q":"I speak without a mouth and hear without ears. What am I?","answers":["echo"],"hint":"You hear it in valleys."},
    {"q":"The more of this there is, the less you see. What is it?","answers":["darkness","the dark"],"hint":"Turn on a light to beat it."},
    {"q":"What gets wetter the more it dries?","answers":["towel"],"hint":"Found after a shower."},
    {"q":"What has many keys but can’t open a lock?","answers":["piano","keyboard"],"hint":"Makes music."},
    {"q":"What belongs to you but is used more by others?","answers":["your name","name"],"hint":"People call you by it."},
    {"q":"What has a head and a tail but no body?","answers":["coin","a coin"],"hint":"Flip it to decide."},
    {"q":"What goes up but never comes down?","answers":["age"],"hint":"Birthday related."},
    {"q":"What can you catch but not throw?","answers":["cold"],"hint":"Happens in winter."},
    {"q":"What has a neck but no head?","answers":["bottle"],"hint":"Holds water."},
    {"q":"What can travel around the world while staying in a corner?","answers":["stamp","a stamp"],"hint":"On an envelope."},
    {"q":"I’m tall when I’m young and short when I’m old. What am I?","answers":["candle"],"hint":"Melted by a flame."},
    {"q":"What gets bigger the more you take away?","answers":["hole"],"hint":"Digging makes it larger."},
    {"q":"What has one eye but cannot see?","answers":["needle"],"hint":"Useful for stitching."},
    {"q":"What has words but never speaks?","answers":["book"],"hint":"You read it."},
    {"q":"What building has the most stories?","answers":["library"],"hint":"Quiet place."},
    {"q":"Forward I am heavy, backward I am not. What am I?","answers":["ton"],"hint":"It’s a weight; read me in reverse."}
]
def _norm(s:str)->str: return re.sub(r"[^a-z0-9 ]+","",s.strip().lower())

with st.container(border=True):
    st.markdown("**Brain Teaser Quiz (≈2–3 min):** 5 quick riddles to spark curiosity. You can use a **Hint** if stuck.")
    st.session_state.setdefault("show_quiz", False)
    if not st.session_state.show_quiz:
        if st.button("Play Riddle Quiz"):
            st.session_state.show_quiz=True
            st.session_state.quiz_pool=random.sample(RIDDLES,5)
            st.session_state.quiz_idx=0
            st.session_state.quiz_score=0
            st.session_state.quiz_show_hint=False
            st.session_state.quiz_feedback=""
            st.rerun()
    else:
        i = st.session_state.quiz_idx
        q = st.session_state.quiz_pool[i]
        st.caption(f"Riddle {i+1} of 5"); st.write(f"**{q['q']}**")
        if st.session_state.quiz_show_hint: st.info(f"Hint: {q['hint']}")
        ans = st.text_input("Your answer", key=f"quiz_ans_{i}")
        c1,c2,c3 = st.columns(3)
        if c1.button("Submit", key=f"quiz_submit_{i}"):
            if ans.strip():
                ok = any(_norm(ans)==_norm(a) for a in q["answers"])
                if ok: st.session_state.quiz_score += 1; st.session_state.quiz_feedback="✅ Correct!"
                else:  st.session_state.quiz_feedback=f"❌ Not quite. Answer: **{q['answers'][0]}**"
                if i==4:
                    score = st.session_state.quiz_score
                    if score>=4:
                        text=f"{pick_new('quiz_good', GAME_GOOD)} {score}/5 🎉\n\n{pick_new('quiz_q', GAME_QUOTES)}"; st.success(text); st.session_state.reaction_result_payload={"type":"success","text":text}
                    elif score==3:
                        text=f"{pick_new('quiz_avg', GAME_AVG)} {score}/5 🙂\n\n{pick_new('quiz_q', GAME_QUOTES)}"; st.info(text); st.session_state.reaction_result_payload={"type":"info","text":text}
                    else:
                        text=f"{pick_new('quiz_low', GAME_LOW)} {score}/5 💪\n\n{pick_new('quiz_q', GAME_QUOTES)}"; st.warning(text); st.session_state.reaction_result_payload={"type":"warning","text":text}
                    st.session_state.reaction_result_until=time.time()+20
                    st.session_state.show_quiz=False; st.rerun()
                else:
                    st.session_state.quiz_idx += 1; st.session_state.quiz_show_hint=False; st.rerun()
            else:
                st.info("Type your best guess or tap **Hint**.")
        if c2.button("Hint", key=f"quiz_hint_{i}"):
            st.session_state.quiz_show_hint=True; st.rerun()
        if c3.button("Skip", key=f"quiz_skip_{i}"):
            st.info(f"Skipped. Answer: **{q['answers'][0]}**")
            if i==4:
                score = st.session_state.quiz_score
                if score>=4:
                    text=f"{pick_new('quiz_good', GAME_GOOD)} {score}/5 🎉\n\n{pick_new('quiz_q', GAME_QUOTES)}"; st.success(text); st.session_state.reaction_result_payload={"type":"success","text":text}
                elif score==3:
                    text=f"{pick_new('quiz_avg', GAME_AVG)} {score}/5 🙂\n\n{pick_new('quiz_q', GAME_QUOTES)}"; st.info(text); st.session_state.reaction_result_payload={"type":"info","text":text}
                else:
                    text=f"{pick_new('quiz_low', GAME_LOW)} {score}/5 💪\n\n{pick_new('quiz_q', GAME_QUOTES)}"; st.warning(text); st.session_state.reaction_result_payload={"type":"warning","text":text}
                st.session_state.reaction_result_until=time.time()+20
                st.session_state.show_quiz=False; st.rerun()
            else:
                st.session_state.quiz_idx += 1; st.session_state.quiz_show_hint=False; st.rerun()
        if st.session_state.quiz_feedback: st.caption(st.session_state.quiz_feedback)

# --- Gratitude Blitz (non-blocking; inputs visible) ---
st.markdown("---")
st.markdown("**Gratitude Blitz (60s):** Write 3 small good things. This lifts mood and balances negativity bias.")
st.session_state.setdefault("grat_start_ts", None)
c1,c2 = st.columns(2)
if c1.button("Start 60-sec timer"): st.session_state.grat_start_ts = time.time()
if c2.button("Reset"): st.session_state.grat_start_ts = None

remain_ph = st.empty()
def _remaining():
    if st.session_state.grat_start_ts is None: return None
    return int(max(0, 60 - (time.time() - st.session_state.grat_start_ts)))

remain = _remaining()
if remain is not None and remain > 0:
    remain_ph.info(f"Time left: {remain}s")
elif remain == 0:
    remain_ph.success("Time’s up! Save your 3 notes below. 🌟"); st.session_state.grat_start_ts = None
else:
    remain_ph.info("Ready when you are — press Start to begin a 60-sec blitz.")

with st.form("gratitude", clear_on_submit=True):
    g1 = st.text_input("1) A tiny win")
    g2 = st.text_input("2) Something you appreciate")
    g3 = st.text_input("3) One kind thing you can do")
    if st.form_submit_button("Save"):
        st.success(pick_new("grat_msg", ["Nice! Noted for today 🌟","Beautiful — gratitude shifts the spotlight to the good."])
                   + "\n\n" + pick_new("grat_quote", ["“Where attention goes, emotion flows.”","“What we appreciate, appreciates.”"]))

if _remaining() not in (None, 0):
    time.sleep(1); st.rerun()

