import os, json, time, random, re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import datetime as dt

# ---------- env & config ----------
load_dotenv()
st.set_page_config(page_title="MannMitra (Prototype)", page_icon="💚", layout="wide")
os.makedirs("data", exist_ok=True)

# ---------- aesthetic CSS (readable + scrollable chat + no clipped headers) ----------
st.markdown("""
<style>
:root{
  --bg1:#0ea5e9; --bg2:#a78bfa; --card:#111827;  /* dark card for contrast */
  --text:#e5e7eb; --muted:#cbd5e1; --accent:#22c55e;
}
.block-container{padding-top:2rem;}  /* more space so headings aren't cut */
[data-testid="stAppViewContainer"]{
  background: linear-gradient(135deg, rgba(14,165,233,.10), rgba(167,139,250,.10));
}

/* card look */
.stContainer > div{
  border-radius:16px !important; border:1px solid rgba(226,232,240,.12) !important;
  background:var(--card) !important; box-shadow:0 8px 24px rgba(2,6,23,.35) !important;
}

/* global readable text on dark cards */
body, [data-testid="stAppViewContainer"] .stMarkdown, [data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li, [data-testid="stAppViewContainer"] label,
[data-testid="stSidebar"] * {
  color: var(--text) !important; line-height: 1.6;
}

/* headings */
h1,h2,h3,h4{ margin-top:.6rem !important; line-height:1.25; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto; }

/* gradient buttons */
.stButton>button{
  background: linear-gradient(135deg,var(--bg1),var(--bg2)); color:#fff; border:none;
  border-radius:12px; padding:.5rem 1rem; font-weight:700;
}
.stButton>button:hover{ filter:brightness(.96); }

/* metrics */
[data-testid="stMetricValue"]{font-weight:800;}

/* CHAT: black bubble with white text, only in chat */
.stChatMessage{
  background:#0b1220 !important; border-radius:16px; border:1px solid rgba(255,255,255,.08);
}
.stChatMessage, .stChatMessage * { color:#ffffff !important; }

/* scrollable chat area */
.chat-scroll{ max-height: 60vh; overflow-y: auto; padding-right: 8px; }
</style>
""", unsafe_allow_html=True)

# ---------- helpers ----------
def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_new(state_key: str, choices: list[str]) -> str:
    """Pick a message different from last time for variety."""
    last = st.session_state.get(state_key)
    pool = [c for c in choices if c != last] or choices
    choice = random.choice(pool)
    st.session_state[state_key] = choice
    return choice

CHEER_LOW = [
    "Tough days happen. You still showed up — that matters.",
    "Be gentle with yourself today. Tiny steps count."
]
CHEER_OK = [
    "Steady is good. Normal days build strength.",
    "Nice balance today — keep the kind pace."
]
CHEER_HIGH = [
    "Great vibe — share a kind word today!",
    "Lovely energy — note what helped and repeat it."
]
QUOTE_LOW = ["“Small steps are still steps.”", "“No rain, no flowers.”"]
QUOTE_OK = ["“Ordinary days build extraordinary strength.”", "“Consistency beats intensity.”"]
QUOTE_HIGH = ["“Joy shared is joy doubled.”", "“Gratitude turns enough into plenty.”"]

GAME_GOOD = ["Great focus — your attention is sharp! 👏", "Awesome run — you were dialed in! ⚡"]
GAME_AVG  = ["Nice effort — try once more, slow and steady.", "Solid! One more round can boost it further."]
GAME_LOW  = ["Mind might be busy — a 30-sec breath can help.", "It’s okay — reset with a breath and try again."]
GAME_QUOTES = ["“Focus grows where attention goes.”", "“Progress > perfection.”", "“Storms pass; you stay.”"]

# ---------- content files ----------
WHO5       = load_json("content/who5.json")
EXERCISES  = load_json("content/exercises.json")
HELPLINES  = load_json("content/helplines_in.json")

# ---------- extra exercises  ----------
MORE_EXERCISES = {
    "box_breath": {
        "title": "Box Breathing",
        "when": "Feeling anxious or heart racing; need a quick reset.",
        "what": "Inhale–Hold–Exhale–Hold for equal counts.",
        "steps": ["Inhale 4s","Hold 4s","Exhale 4s","Hold 4s"], "cycles": 4
    },
    "body_scan": {
        "title": "60-sec Body Scan",
        "when": "Tense or restless; want to relax before sleep or study.",
        "what": "Move attention from head to toe, relaxing each area.",
        "steps": ["Head & face relax","Neck & shoulders soften","Chest & arms loosen",
                  "Stomach unclench","Legs feel heavy","Notice easy breathing"], "cycles": 1
    },
    "stop_skill": {
        "title": "STOP Skill",
        "when": "Strong emotions or urge to react; need a pause.",
        "what": "DBT micro-skill: pause, breathe, observe, proceed.",
        "steps": ["S—Stop","T—Take a slow breath","O—Observe body/thoughts","P—Proceed with one small helpful action"], "cycles": 1
    }
}

# ---------- Gemini  ----------
api_key = os.getenv("GEMINI_API_KEY")
client = None
if api_key:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except Exception:
        client = None

SYSTEM = (
    "You are MannMitra, an empathetic, non-judgmental wellness companion for Indian youth. "
    "Be supportive, reduce stigma. Offer gentle self-care (breathing, grounding, journaling). "
    "Do not diagnose or prescribe. If crisis/self-harm hints appear, encourage immediate help and show helplines."
)

def gemini_reply(msg: str, lang: str = "English") -> str:
    if not client:
        if lang == "हिन्दी": return "मैं आपकी बात सुन रहा/रही हूँ। आप अकेले नहीं हैं।"
        if lang == "Hinglish": return "Main sun raha/rahi hoon. Aap akelay nahi ho."
        return "Thanks for sharing. I’m here to listen."
    try:
        lang_instr = {
            "English": "Reply in natural, supportive English.",
            "हिन्दी": "Reply in Hindi (Devanagari). Keep it warm and simple.",
            "Hinglish": "Reply in Hindi written in Latin script (Hinglish). Example: 'main theek hoon'. Keep tone warm."
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
                contents=[{"role":"user","parts":[{"text":
                    "Classify self-harm risk: return only JSON {\"risk\":0|1|2|3}. Message: "+text}]}]
            )
            import json as _json
            return int(_json.loads((r.text or "{}").strip()).get("risk",0))
        except Exception:
            pass
    if any(x in tl for x in ["very sad","depressed","lonely","crying","hopeless","numb","empty"]): return 1
    return 0

# ---------- suggestions ----------
SUGGESTION_RULES = [
    {"id":"breathing_478", "type":"exercise", "title":"Try 4-7-8 breathing",
     "match_any":[r"\banxious\b", r"\banxiety\b", r"\bstressed?\b", r"\boverwhelm", r"घबराहट", r"tension"]},
    {"id":"grounding_54321", "type":"exercise", "title":"Try 5-4-3-2-1 grounding",
        "match_any":[r"\boverthink", r"\bspiral", r"\bloop", r"\bracing thoughts\b"]},
    {"id":"stroop", "type":"game", "title":"Play a 1-minute Focus game",
     "match_any":[r"\bbored\b", r"\bdistract", r"\bcan.?t focus\b", r"\bprocrastinat"]},
]
def _regex_any(patterns, text): t=text.lower(); return any(re.search(p,t) for p in patterns)
def choose_suggestion(user_text: str):
    for r in SUGGESTION_RULES:
        if _regex_any(r["match_any"], user_text): return {"source":"rules", **r}
    if len(user_text.split())>=25: return {"source":"rules","id":"breathing_478","type":"exercise","title":"Try 4-7-8 breathing"}
    return None

# ---------- sidebar ----------
if "quick_hide" not in st.session_state: st.session_state.quick_hide = False
if "history" not in st.session_state: st.session_state.history = []
if "lang" not in st.session_state: st.session_state.lang = "English"

with st.sidebar:
    st.markdown("### Privacy & Tools")
    cA,cB = st.columns(2)
    if cA.button("🔒 Quick Hide"): st.session_state.quick_hide = True
    if cB.button("🔓 Unhide"):     st.session_state.quick_hide = False
    st.session_state.lang = st.radio("Reply language / भाषा", ["English","हिन्दी","Hinglish"], index=0)

    # recap
    def build_recap(history, lang):
        last_user = [t for r,t in history if r=="user"][-3:]
        points = "\n".join(f"- {x}" for x in last_user) if last_user else "- (no details)"
        base = f"Session recap ({lang}):\n{points}\n\nTiny plan for today:\n• 3 cycles 4-7-8\n• One kind line to yourself\n• 10-min walk"
        if client and last_user:
            try:
                pr = (f"{SYSTEM}\nSummarize in {lang} ≤60 words, then 3-bullet plan. Return plain text.\n"+"\n".join(last_user))
                r = client.models.generate_content(model="gemini-2.5-flash-lite", contents=[{"role":"user","parts":[{"text":pr}]}])
                t = (r.text or "").strip()
                return t if t else base
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

        # scrollable message area
        st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
        for role, text in st.session_state.history:
            st.chat_message(role).markdown(text)
        st.markdown('</div>', unsafe_allow_html=True)

        user_msg = st.chat_input("Share what's on your mind… (EN/Hinglish/Hindi)")
        if user_msg:
            plain = user_msg.strip().lower().rstrip("?.! ")
            if plain in {"aap kaise ho","kaise ho","tum kaise ho"}:
                if st.session_state.lang=="हिन्दी":   st.session_state.history.append(("assistant","मैं ठीक हूँ — आपका शुक्रिया! आप कैसे हैं?"))
                elif st.session_state.lang=="Hinglish": st.session_state.history.append(("assistant","Main theek hoon — shukriya! Aap kaise ho?"))
                else: st.session_state.history.append(("assistant","I’m doing well — thanks for asking! How are you?"))
                st.rerun()

            st.session_state.history.append(("user", user_msg))

            risk = classify_risk(user_msg)
            if risk >= 2:
                st.error("You deserve support. If you’re in danger, please reach out now.\n\n"
                         f"📞 {HELPLINES['kiran']['name']}: {HELPLINES['kiran']['phone']} • "
                         f"{HELPLINES['tele_manas']['name']}: {HELPLINES['tele_manas']['phone']}")
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
                    ]) + "\n\n" + pick_new("quote_ex", ["“Slow is smooth, and smooth is fast.”", "“One breath at a time.”"]))
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

    # Quick Exercises with “when/what”
    with st.container(border=True):
        st.subheader("Quick Exercises")
        merged = {
            "breathing_478": {
                "title": EXERCISES["breathing_478"]["title"], "when":"Anxious or restless; calm down in <2 min.",
                "what":"Paced breathing that nudges the body toward calm.", "steps":EXERCISES["breathing_478"]["steps"], "cycles":EXERCISES["breathing_478"].get("cycles",3)
            },
            "grounding_54321": {
                "title": EXERCISES["grounding_54321"]["title"], "when":"Overthinking; come back to the present.",
                "what":"Use your senses to anchor attention safely.", "steps":EXERCISES["grounding_54321"]["steps"], "cycles":1
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
                    ]) + "\n\n" + pick_new("quote_ex2", ["“One breath at a time.”", "“Small acts, big change.”"]))

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
            path = "data/mood_log.csv"
            if os.path.exists(path):
                prev = pd.read_csv(path); row = pd.concat([prev, row], ignore_index=True)
            row.to_csv(path, index=False)
            st.success(f"Saved! Today’s WHO-5 score: {total}/100")

            # rotating cheerful msg + quote
            if total < 40:
                st.warning(pick_new("cheer_low", CHEER_LOW) + "\n\n" + pick_new("q_low", QUOTE_LOW))
            elif total < 70:
                st.info(pick_new("cheer_ok", CHEER_OK) + "\n\n" + pick_new("q_ok", QUOTE_OK))
            else:
                st.success(pick_new("cheer_high", CHEER_HIGH) + "\n\n" + pick_new("q_high", QUOTE_HIGH))

    # Mood & Happiness — simple line graph (first style)
    with st.container(border=True):
        st.subheader("Mood & Happiness")
        path = "data/mood_log.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["ts"], unit="s").dt.date
            daily = df.groupby("date")["score"].mean().tail(14)
            daily.index.name = "Date"
            st.line_chart(daily, height=220)
            # weekly happiness
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

# Show persisted game result (for at least 20s)
now_ts = time.time()
if "reaction_result_until" in st.session_state and now_ts < st.session_state.reaction_result_until:
    kind = st.session_state.reaction_result_payload.get("type","info")
    text = st.session_state.reaction_result_payload.get("text","")
    if kind == "success": st.success(text)
    elif kind == "warning": st.warning(text)
    else: st.info(text)
elif "reaction_result_until" in st.session_state and now_ts >= st.session_state.reaction_result_until:
    st.session_state.pop("reaction_result_until", None)
    st.session_state.pop("reaction_result_payload", None)

# State flags to show games after "Play"
st.session_state.setdefault("show_stroop", False)
st.session_state.setdefault("show_riddles", False)   # NEW

# --- Game 1: Stroop (description first) ---
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
            word = random.choice(COLORS); ink = random.choice(COLORS); return word, ink
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
                        st.success(text)
                        st.session_state.reaction_result_payload = {"type":"success","text":text}
                    elif score == 3:
                        text = f"{pick_new('game_avg', GAME_AVG)} {score}/{TRIALS}\n\n{pick_new('gq', GAME_QUOTES)}"
                        st.info(text)
                        st.session_state.reaction_result_payload = {"type":"info","text":text}
                    else:
                        text = f"{pick_new('game_low', GAME_LOW)} {score}/{TRIALS}\n\n{pick_new('gq', GAME_QUOTES)}"
                        st.warning(text)
                        st.session_state.reaction_result_payload = {"type":"warning","text":text}
                    st.session_state.reaction_result_until = time.time() + 20  # persist 20s
                    st.session_state.update({"stroop_trial":0,"stroop_score":0,"stroop_start":None,"stroop_item":None,"show_stroop":False})
                else:
                    st.session_state.stroop_item = new_item()
                st.rerun()

# --- Game 2: Brain Teasers (Riddles) ---
RIDDLES = [
    {"q":"What runs but has no legs?", "a":["water","river"], "h":["It flows.","You can drink it or see it in taps."]},
    {"q":"What has keys but can’t open locks?", "a":["keyboard","piano"], "h":["You type or play on it.","Musical or computer."]},
    {"q":"What has hands but can’t clap?", "a":["clock"], "h":["It tells time.","It has a face."]},
    {"q":"I speak without a mouth and hear without ears. What am I?", "a":["echo"], "h":["You hear me in valleys.","I repeat what you say."]},
    {"q":"What gets wetter the more it dries?", "a":["towel"], "h":["Found in bathrooms.","You use it after a shower."]},
    {"q":"What has a neck but no head?", "a":["bottle"], "h":["In the fridge.","Holds liquids."]},
    {"q":"What has a face and two hands but no arms or legs?", "a":["clock","watch"], "h":["Time.","Worn or wall-mounted."]},
    {"q":"What has one eye but cannot see?", "a":["needle","hurricane","cyclone"], "h":["Tailor’s tool.","Also in a storm."]},
    {"q":"What belongs to you but others use it more than you?", "a":["name"], "h":["People call it out.","Identity."]},
    {"q":"What can be cracked, made, told, and played?", "a":["joke"], "h":["Laughter involved.","Comedians love it."]},
    {"q":"What has many teeth but cannot bite?", "a":["comb","zipper"], "h":["Hair tool.","Also on jackets."]},
    {"q":"What can you catch but not throw?", "a":["cold"], "h":["Health related.","Sneezes."]},
    {"q":"What has a head and a tail but no body?", "a":["coin"], "h":["Flip it.","Money."]},
    {"q":"What can travel around the world while staying in a corner?", "a":["stamp"], "h":["On letters.","Postal."]},
    {"q":"What room has no doors or windows?", "a":["mushroom"], "h":["It’s a pun.","Edible."]},
    {"q":"What gets broken without being held?", "a":["promise"], "h":["Trust issue.","Words."]},
    {"q":"What invention lets you look right through a wall?", "a":["window"], "h":["Transparent.","Glass."]},
    {"q":"What is full of holes but still holds water?", "a":["sponge"], "h":["Kitchen item.","Absorbs."]},
    {"q":"What goes up but never comes down?", "a":["age"], "h":["Birthday related.","Numbers."]},
    {"q":"What has words but never speaks?", "a":["book"], "h":["Library.","Pages."]},
]

with st.container(border=True):
    st.markdown("**Brain Teasers (≈2–3 min):** Answer 5 short riddles. Ask for a hint if stuck — it trains flexible thinking and lifts mood.")
    if not st.session_state.show_riddles:
        if st.button("Play Riddles"):
            st.session_state.show_riddles = True
            st.session_state.riddle_pool = random.sample(RIDDLES, 5)  # pick 5 each time
            st.session_state.riddle_round = 0
            st.session_state.riddle_score = 0
            st.session_state.riddle_hint_step = 0
            st.session_state.riddle_feedback = ""
            st.rerun()
    else:
        r = st.session_state.riddle_pool[st.session_state.riddle_round]
        st.caption(f"Riddle {st.session_state.riddle_round+1} / 5")
        st.write("**" + r["q"] + "**")

        # hint handling
        cols = st.columns([3,1,1])
        ans = cols[0].text_input("Your answer", key=f"ans_{st.session_state.riddle_round}")
        if cols[1].button("Hint"):
            st.session_state.riddle_hint_step = min(st.session_state.riddle_hint_step + 1, len(r["h"]))
        if st.session_state.riddle_hint_step > 0:
            shown = " • ".join(r["h"][:st.session_state.riddle_hint_step])
            st.info(f"Hints: {shown}")

        # normalize answer
        def norm(s): return re.sub(r"[^a-z0-9]+","", s.strip().lower())

        # submit / skip
        sub_col1, sub_col2 = st.columns([1,1])
        if sub_col1.button("Submit"):
            if ans.strip():
                if norm(ans) in {norm(x) for x in r["a"]}:
                    st.session_state.riddle_score += 1
                    st.session_state.riddle_feedback = "✅ Correct! Nice thinking."
                else:
                    st.session_state.riddle_feedback = f"❌ Not quite. Answer was **{r['a'][0].title()}**."
                # next round
                st.session_state.riddle_round += 1
                st.session_state.riddle_hint_step = 0
                if st.session_state.riddle_round >= 5:
                    # summary + persist for 20s
                    score = st.session_state.riddle_score
                    if score >= 4:
                        text = f"{pick_new('rt_good', GAME_GOOD)} You got **{score}/5**.\n\n{pick_new('rt_q', GAME_QUOTES)}"
                        st.success(text)
                        st.session_state.reaction_result_payload = {"type":"success","text":text}
                    elif score == 3:
                        text = f"{pick_new('rt_avg', GAME_AVG)} You got **{score}/5**.\n\n{pick_new('rt_q', GAME_QUOTES)}"
                        st.info(text)
                        st.session_state.reaction_result_payload = {"type":"info","text":text}
                    else:
                        text = f"{pick_new('rt_low', GAME_LOW)} You got **{score}/5**.\n\n{pick_new('rt_q', GAME_QUOTES)}"
                        st.warning(text)
                        st.session_state.reaction_result_payload = {"type":"warning","text":text}
                    st.session_state.reaction_result_until = time.time() + 20
                    st.session_state.show_riddles = False
                st.rerun()
        if sub_col2.button("Skip"):
            st.session_state.riddle_feedback = f"⏭️ Skipped. Answer was **{r['a'][0].title()}**."
            st.session_state.riddle_round += 1
            st.session_state.riddle_hint_step = 0
            if st.session_state.riddle_round >= 5:
                score = st.session_state.riddle_score
                if score >= 4:
                    text = f"{pick_new('rt_good', GAME_GOOD)} You got **{score}/5**.\n\n{pick_new('rt_q', GAME_QUOTES)}"
                    st.success(text)
                    st.session_state.reaction_result_payload = {"type":"success","text":text}
                elif score == 3:
                    text = f"{pick_new('rt_avg', GAME_AVG)} You got **{score}/5**.\n\n{pick_new('rt_q', GAME_QUOTES)}"
                    st.info(text)
                    st.session_state.reaction_result_payload = {"type":"info","text":text}
                else:
                    text = f"{pick_new('rt_low', GAME_LOW)} You got **{score}/5**.\n\n{pick_new('rt_q', GAME_QUOTES)}"
                    st.warning(text)
                    st.session_state.reaction_result_payload = {"type":"warning","text":text}
                st.session_state.reaction_result_until = time.time() + 20
                st.session_state.show_riddles = False
            st.rerun()

        if st.session_state.riddle_feedback:
            st.caption(st.session_state.riddle_feedback)

# --- Gratitude Blitz with real ticking countdown ---
st.markdown("---")
st.markdown("**Gratitude Blitz (60s):** Write 3 small good things. This lifts mood and balances negativity bias.")
st.session_state.setdefault("grat_start_ts", None)
c1,c2 = st.columns(2)
if c1.button("Start 60-sec timer"):
    st.session_state.grat_start_ts = time.time()
if c2.button("Reset"):
    st.session_state.grat_start_ts = None

ph = st.empty()
if st.session_state.grat_start_ts:
    remain = int(max(0, 60 - (time.time() - st.session_state.grat_start_ts)))
    if remain > 0:
        ph.info(f"Time left: {remain}s")
        time.sleep(1)
        st.rerun()
    else:
        ph.success("Time’s up! Save your 3 notes below. 🌟")
        st.session_state.grat_start_ts = None

with st.form("gratitude", clear_on_submit=True):
    g1 = st.text_input("1) A tiny win")
    g2 = st.text_input("2) Something you appreciate")
    g3 = st.text_input("3) One kind thing you can do")
    if st.form_submit_button("Save"):
        st.success(pick_new("grat_msg", [
            "Nice! Noted for today 🌟",
            "Beautiful — gratitude shifts the spotlight to the good."
        ]) + "\n\n" + pick_new("grat_quote", [
            "“Where attention goes, emotion flows.”",
            "“What we appreciate, appreciates.”"
        ]))
