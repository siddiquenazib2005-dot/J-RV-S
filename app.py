"""
J-RV-S — Just a Rather Very Intelligent System
Built by Nazib Siddique
FINAL VERSION — ONE FILE — BULLETPROOF — FAST
"""

import os, re, uuid, threading, time, base64, io, json
import requests
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ════════════════════════════════════════════════════════════
# ENV
# ════════════════════════════════════════════════════════════
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
WEATHER_KEY  = os.environ.get("WEATHER_API_KEY", "")
NEWS_KEY     = os.environ.get("NEWS_API_KEY", "")
SERPER_KEY   = os.environ.get("SERPER_API_KEY", "")
RENDER_URL   = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")

GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
FAST_MODEL   = "llama-3.1-8b-instant"      # Speed priority
SMART_MODEL  = "llama-3.3-70b-versatile"   # Quality priority
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ════════════════════════════════════════════════════════════
# KEEP ALIVE — Anti cold start ping
# ════════════════════════════════════════════════════════════
def keep_alive():
    while True:
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass
        time.sleep(600)  # Every 10 min

threading.Thread(target=keep_alive, daemon=True).start()

# ════════════════════════════════════════════════════════════
# AI BRAIN — Pure requests, no library
# ════════════════════════════════════════════════════════════
def ai_chat(system_prompt, messages, tool_context="", fast=True):
    try:
        msgs = [m.copy() for m in messages]
        if tool_context and msgs:
            msgs[-1]["content"] = f"{tool_context}\n\nUser: {msgs[-1]['content']}"
        payload = {
            "model": FAST_MODEL if fast else SMART_MODEL,
            "messages": [{"role": "system", "content": system_prompt}] + msgs,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=25)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def ai_chat_stream(system_prompt, messages, tool_context=""):
    """Streaming response generator"""
    try:
        msgs = [m.copy() for m in messages]
        if tool_context and msgs:
            msgs[-1]["content"] = f"{tool_context}\n\nUser: {msgs[-1]['content']}"
        payload = {
            "model": FAST_MODEL,
            "messages": [{"role": "system", "content": system_prompt}] + msgs,
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": True
        }
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=25, stream=True)

        full_response = ""
        for line in r.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield f"data: [DONE]\n\n"
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            full_response += delta
                            yield f"data: {json.dumps({'text': delta})}\n\n"
                    except:
                        continue
        return full_response
    except Exception as e:
        yield f"data: {json.dumps({'text': f'⚠️ Error: {str(e)}', 'error': True})}\n\n"

def ai_vision(image_b64, mime_type, prompt, system_prompt):
    try:
        payload = {
            "model": VISION_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                    {"type": "text", "text": prompt or "Analyze this image in detail."}
                ]}
            ],
            "temperature": 0.7, "max_tokens": 1024
        }
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=25)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Vision Error: {str(e)}"

# ════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ════════════════════════════════════════════════════════════
INTENT_MAP = {
    "weather":   ["weather","temperature","rain","forecast","humidity","mausam","barish","garmi","sardi","aaj ka mausam"],
    "news":      ["news","headline","breaking","latest news","khabar","samachar","aaj ki news"],
    "search":    ["search","find","look up","google","khojo","dhundo","bata","tell me about"],
    "wikipedia": ["wikipedia","wiki","define","meaning","history of","kaun hai","kya hota hai"],
    "currency":  ["currency","convert","usd","inr","dollar","rupee","euro","pound","exchange rate","kitne mein"],
    "stock":     ["stock","share price","market","sensex","nifty","crypto","bitcoin","ethereum"],
    "code":      ["code","program","function","debug","error","script","python","javascript","html","css","fix this","bug","write a"],
    "translate": ["translate","translation","in hindi","in english","anuvad","urdu mein"],
    "summarize": ["summarize","summary","tldr","brief","short mein","saaransh"],
    "image":     ["image","photo","picture","analyze image","screenshot","yeh kya hai","is mein kya"],
    "pdf":       ["pdf","document","analyze this","summarize this file","file mein"],
}

def detect_intent(msg):
    m = msg.lower()
    for intent, keywords in INTENT_MAP.items():
        for kw in keywords:
            if kw in m:
                return intent
    return "chat"

def build_system_prompt(intent, user_name="Boss", memories=[]):
    base = f"""You are J-RV-S (Just a Rather Very Intelligent System), a highly advanced AI assistant built by Nazib Siddique.
You are speaking with {user_name}.
Personality: Intelligent, witty, direct — like JARVIS from Iron Man. Loyal to your creator Nazib Siddique.
CRITICAL RULES:
- Always reply in the SAME language the user uses (Hindi/English/Hinglish)
- ALWAYS maintain context — if user says "his", "that", "it", "uska", "woh" — refer to previous conversation
- Be concise but thorough. No unnecessary filler words.
- Never say you can't do something without trying first."""

    if memories:
        base += "\n\n[USER MEMORY — Facts about this user]:\n" + "\n".join([f"• {m}" for m in memories[:10]])

    prompts = {
        "weather":   base + "\n\nTask: Present weather data clearly with relevant emojis. Give feel-like advice too.",
        "news":      base + "\n\nTask: Present news as clean numbered list. Add brief context to each headline.",
        "search":    base + "\n\nTask: Summarize search results clearly. Extract the most useful information.",
        "wikipedia": base + "\n\nTask: Give a clear, engaging educational summary. Make it interesting.",
        "currency":  base + "\n\nTask: Show conversion result clearly. Mention if rate is good/bad historically.",
        "stock":     base + "\n\nTask: Present stock data clearly with trend context.",
        "code":      base + "\n\nTask: Write clean, commented, working code. Explain what it does briefly.",
        "translate": base + "\n\nTask: Provide accurate translation. Note any cultural context if relevant.",
        "summarize": base + "\n\nTask: Give a crisp summary. Bullet points for key takeaways.",
        "image":     base + "\n\nTask: Describe and analyze the image in detail. Note all important elements.",
        "pdf":       base + "\n\nTask: Analyze the file content. Give structured summary with key points.",
        "chat":      base + "\n\nTask: Engage naturally and intelligently. Be helpful, witty, and insightful.",
    }
    return prompts.get(intent, prompts["chat"])

def format_tool_result(intent, result):
    if not result or result.get("error"):
        return ""
    if intent == "weather":
        return f"[WEATHER DATA]\nCity: {result.get('city')} | Temp: {result.get('temp')}°C | Feels like: {result.get('feels_like','N/A')}°C\nCondition: {result.get('description')} | Humidity: {result.get('humidity')}% | Wind: {result.get('wind')} km/h"
    elif intent == "search":
        items = result.get("results", [])
        lines = "\n".join([f"- {r.get('title','')}: {r.get('snippet','')}" for r in items[:4]])
        return f"[SEARCH RESULTS]\n{lines}"
    elif intent == "wikipedia":
        return f"[WIKIPEDIA]\nTitle: {result.get('title','')}\n{result.get('summary','')}"
    elif intent == "news":
        arts = result.get("articles", [])
        lines = "\n".join([f"{i+1}. {a.get('title','')} — {a.get('source','')}" for i, a in enumerate(arts[:5])])
        return f"[LATEST NEWS]\n{lines}"
    elif intent == "currency":
        return f"[CURRENCY]\n{result.get('amount')} {result.get('from')} = {result.get('converted')} {result.get('to')} (Rate: {result.get('rate')})"
    elif intent == "stock":
        return f"[STOCK]\n{result.get('symbol')} | Price: ${result.get('price')} | Change: {result.get('change')}"
    return str(result)

# ════════════════════════════════════════════════════════════
# SUPABASE — Direct REST API
# ════════════════════════════════════════════════════════════
def supa(method, table, data=None, params=""):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/{table}{params}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=data, timeout=5)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=5)
        else:
            return []
        result = r.json() if r.content else []
        return result if isinstance(result, list) else []
    except:
        return []

def save_message(sid, role, content, session_name=""):
    supa("POST", "chat_history", {
        "session_id": sid, "role": role,
        "content": content, "session_name": session_name
    })

def get_history(sid, limit=20):
    r = supa("GET", "chat_history",
        params=f"?session_id=eq.{sid}&order=created_at&limit={limit}&select=role,content")
    return [{"role": x.get("role"), "content": x.get("content")} for x in r if x.get("role")]

def get_sessions(uid):
    r = supa("GET", "chat_history",
        params=f"?user_id=eq.{uid}&order=created_at.desc&select=session_id,session_name,content,created_at")
    # Get unique sessions
    seen = {}
    for x in r:
        sid = x.get("session_id","")
        if sid and sid not in seen:
            seen[sid] = {"session_id": sid, "session_name": x.get("session_name","New Chat"), "preview": x.get("content","")[:50]}
    return list(seen.values())[:20]

def save_memory(uid, memory):
    supa("POST", "user_memory", {"user_id": uid, "memory": memory})

def get_memories(uid, limit=15):
    r = supa("GET", "user_memory",
        params=f"?user_id=eq.{uid}&order=created_at.desc&limit={limit}&select=memory")
    return [x.get("memory","") for x in r if x.get("memory")]

def purge_memories(uid):
    supa("DELETE", "user_memory", params=f"?user_id=eq.{uid}")

def save_note(uid, content, title=""):
    supa("POST", "notes", {"user_id": uid, "title": title, "content": content})

def get_notes(uid):
    return supa("GET", "notes", params=f"?user_id=eq.{uid}&order=created_at.desc")

def save_task(uid, task, priority="normal"):
    supa("POST", "tasks", {"user_id": uid, "task": task, "priority": priority, "done": False})

def get_tasks(uid):
    return supa("GET", "tasks", params=f"?user_id=eq.{uid}&done=eq.false&order=created_at.desc")

def complete_task(task_id):
    supa("POST", "tasks", params=f"?id=eq.{task_id}")

# ════════════════════════════════════════════════════════════
# WEB TOOLS
# ════════════════════════════════════════════════════════════
def get_weather(city="Delhi"):
    try:
        r = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric",
            timeout=5)
        d = r.json()
        if r.status_code == 200:
            return {
                "city": d["name"], "temp": d["main"]["temp"],
                "feels_like": d["main"]["feels_like"],
                "description": d["weather"][0]["description"].title(),
                "humidity": d["main"]["humidity"], "wind": d["wind"]["speed"]
            }
        return {"error": d.get("message","Not found")}
    except Exception as e:
        return {"error": str(e)}

def get_news(query="India"):
    try:
        r = requests.get(
            f"https://newsapi.org/v2/top-headlines?country=in&pageSize=5&apiKey={NEWS_KEY}",
            timeout=5)
        arts = r.json().get("articles", [])
        if not arts and query.lower() not in ["india","latest","news"]:
            r = requests.get(
                f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_KEY}",
                timeout=5)
            arts = r.json().get("articles", [])
        return {"articles": [
            {"title": a.get("title",""), "source": a.get("source",{}).get("name","")}
            for a in arts[:5] if a.get("title") and "[Removed]" not in a.get("title","")
        ]}
    except Exception as e:
        return {"error": str(e)}

def web_search(query):
    try:
        r = requests.post("https://google.serper.dev/search",
            json={"q": query, "num": 5},
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            timeout=5)
        items = r.json().get("organic", [])
        return {"results": [{"title": x.get("title",""), "snippet": x.get("snippet",""), "link": x.get("link","")} for x in items[:5]]}
    except Exception as e:
        return {"error": str(e)}

def wikipedia_search(query):
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ','_')}",
            timeout=5)
        d = r.json()
        return {"title": d.get("title",""), "summary": d.get("extract","")[:1200]}
    except Exception as e:
        return {"error": str(e)}

def convert_currency(amount, from_c, to_c):
    try:
        r = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_c.upper()}", timeout=5)
        rate = r.json().get("rates",{}).get(to_c.upper())
        if rate:
            return {"from": from_c.upper(), "to": to_c.upper(), "amount": amount, "rate": rate, "converted": round(amount*rate,2)}
        return {"error": "Currency not found"}
    except Exception as e:
        return {"error": str(e)}

def get_stock(symbol):
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d",
            headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        meta = r.json().get("chart",{}).get("result",[{}])[0].get("meta",{})
        price = meta.get("regularMarketPrice", 0)
        prev  = meta.get("previousClose", price)
        return {"symbol": symbol.upper(), "price": price, "change": round(price-prev,2)}
    except Exception as e:
        return {"error": str(e)}

# ════════════════════════════════════════════════════════════
# FILE PROCESSOR
# ════════════════════════════════════════════════════════════
def process_file(file_bytes, filename, mime_type):
    fname = filename.lower()
    if mime_type == "application/pdf" or fname.endswith(".pdf"):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "".join([p.extract_text() or "" for p in reader.pages])
            return {"type":"pdf","content":text[:8000],"filename":filename}
        except Exception as e:
            return {"type":"pdf","content":f"PDF error: {e}","filename":filename}
    elif any(fname.endswith(x) for x in [".txt",".md",".csv",".json",".py",".js",".html",".css"]):
        return {"type":"text","content":file_bytes.decode("utf-8",errors="ignore")[:8000],"filename":filename}
    elif mime_type.startswith("image/"):
        return {"type":"image","content":base64.b64encode(file_bytes).decode(),"mime_type":mime_type,"filename":filename}
    return {"type":"unknown","content":"Unsupported file.","filename":filename}

# ════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return jsonify({"status":"alive","system":"J-RV-S","version":"2.0"})

@app.route("/static/sw.js")
def service_worker():
    return app.send_static_file("sw.js"), 200, {
        "Content-Type": "application/javascript",
        "Service-Worker-Allowed": "/"
    }

# ── STREAMING CHAT ────────────────────────────────────────
@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    try:
        data       = request.get_json()
        user_msg   = data.get("message","").strip()
        session_id = data.get("session_id", str(uuid.uuid4()))
        user_id    = data.get("user_id","default_user")
        user_name  = data.get("user_name","Boss")
        if not user_msg:
            return jsonify({"error":"Empty"}), 400

        memories      = get_memories(user_id)
        intent        = detect_intent(user_msg)
        system_prompt = build_system_prompt(intent, user_name, memories)
        tool_result   = None

        if intent == "weather":
            words = user_msg.lower().split()
            city = "Delhi"
            for i,w in enumerate(words):
                if w in ["in","at","for","of","mein"] and i+1 < len(words):
                    city = words[i+1].title(); break
            tool_result = get_weather(city)
        elif intent == "news":
            q = re.sub(r"news|khabar|samachar|latest","",user_msg,flags=re.IGNORECASE).strip() or "India"
            tool_result = get_news(q)
        elif intent == "search":
            tool_result = web_search(user_msg)
        elif intent == "wikipedia":
            q = re.sub(r"wikipedia|wiki|what is|who is|kya hai|kaun hai","",user_msg,flags=re.IGNORECASE).strip()
            tool_result = wikipedia_search(q)
        elif intent == "currency":
            m = re.search(r"(\d+\.?\d*)\s*([a-zA-Z]{3})\s*(?:to|in|se)\s*([a-zA-Z]{3})",user_msg,re.IGNORECASE)
            if m: tool_result = convert_currency(float(m.group(1)),m.group(2),m.group(3))
        elif intent == "stock":
            m = re.search(r'\b([A-Z]{2,5})\b',user_msg.upper())
            tool_result = get_stock(m.group(1) if m else "AAPL")

        tool_context = format_tool_result(intent, tool_result) if tool_result else ""
        history      = get_history(session_id)
        history.append({"role":"user","content":user_msg})

        full_response = []

        def generate():
            # Send intent first
            yield f"data: {json.dumps({'intent': intent, 'tool_used': intent if tool_result else None})}\n\n"

            msgs = [m.copy() for m in history]
            if tool_context and msgs:
                msgs[-1]["content"] = f"{tool_context}\n\nUser: {msgs[-1]['content']}"

            payload = {
                "model": FAST_MODEL,
                "messages": [{"role":"system","content":system_prompt}] + msgs,
                "temperature": 0.7,
                "max_tokens": 1024,
                "stream": True
            }
            try:
                r = requests.post(GROQ_URL,
                    headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                    json=payload, timeout=25, stream=True)

                for line in r.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            chunk_data = line_str[6:]
                            if chunk_data == "[DONE]":
                                yield f"data: [DONE]\n\n"
                                break
                            try:
                                chunk = json.loads(chunk_data)
                                delta = chunk["choices"][0]["delta"].get("content","")
                                if delta:
                                    full_response.append(delta)
                                    yield f"data: {json.dumps({'text': delta})}\n\n"
                            except:
                                continue
            except Exception as e:
                yield f"data: {json.dumps({'text': f'⚠️ {str(e)}', 'error': True})}\n\n"
                yield f"data: [DONE]\n\n"

            # Save after stream
            ai_resp = "".join(full_response)
            if ai_resp:
                save_message(session_id,"user",user_msg)
                save_message(session_id,"assistant",ai_resp)

        return Response(stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── REGULAR CHAT (fallback) ───────────────────────────────
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    try:
        data       = request.get_json()
        user_msg   = data.get("message","").strip()
        session_id = data.get("session_id", str(uuid.uuid4()))
        user_id    = data.get("user_id","default_user")
        user_name  = data.get("user_name","Boss")
        if not user_msg:
            return jsonify({"error":"Empty message"}), 400

        memories      = get_memories(user_id)
        intent        = detect_intent(user_msg)
        system_prompt = build_system_prompt(intent, user_name, memories)
        tool_result   = None

        if intent == "weather":
            words = user_msg.lower().split()
            city = "Delhi"
            for i,w in enumerate(words):
                if w in ["in","at","for","of","mein"] and i+1 < len(words):
                    city = words[i+1].title(); break
            tool_result = get_weather(city)
        elif intent == "news":
            q = re.sub(r"news|khabar|samachar|latest","",user_msg,flags=re.IGNORECASE).strip() or "India"
            tool_result = get_news(q)
        elif intent == "search":
            tool_result = web_search(user_msg)
        elif intent == "wikipedia":
            q = re.sub(r"wikipedia|wiki|what is|who is|kya hai|kaun hai","",user_msg,flags=re.IGNORECASE).strip()
            tool_result = wikipedia_search(q)
        elif intent == "currency":
            m = re.search(r"(\d+\.?\d*)\s*([a-zA-Z]{3})\s*(?:to|in|se)\s*([a-zA-Z]{3})",user_msg,re.IGNORECASE)
            if m: tool_result = convert_currency(float(m.group(1)),m.group(2),m.group(3))
        elif intent == "stock":
            m = re.search(r'\b([A-Z]{2,5})\b',user_msg.upper())
            tool_result = get_stock(m.group(1) if m else "AAPL")

        tool_context = format_tool_result(intent, tool_result) if tool_result else ""
        history      = get_history(session_id)
        history.append({"role":"user","content":user_msg})
        ai_response  = ai_chat(system_prompt, history, tool_context)
        save_message(session_id,"user",user_msg)
        save_message(session_id,"assistant",ai_response)

        return jsonify({"response":ai_response,"intent":intent,"session_id":session_id,"tool_used":intent if tool_result else None})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── FILE UPLOAD ───────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file      = request.files.get("file")
        user_msg  = request.form.get("message","Analyze this file.")
        user_name = request.form.get("user_name","Boss")
        session_id = request.form.get("session_id", str(uuid.uuid4()))
        if not file: return jsonify({"error":"No file"}), 400
        file_data = process_file(file.read(), file.filename, file.content_type)
        if file_data["type"] == "image":
            ai_response = ai_vision(file_data["content"],file_data["mime_type"],user_msg,build_system_prompt("image",user_name))
        else:
            history = [{"role":"user","content":f"File: {file.filename}\n\n{file_data['content']}\n\nRequest: {user_msg}"}]
            ai_response = ai_chat(build_system_prompt("pdf",user_name), history)
        save_message(session_id,"user",f"[FILE: {file.filename}] {user_msg}")
        save_message(session_id,"assistant",ai_response)
        return jsonify({"response":ai_response,"file_type":file_data["type"],"filename":file.filename})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── SESSIONS ──────────────────────────────────────────────
@app.route("/sessions", methods=["GET"])
def get_sessions_ep():
    uid = request.args.get("user_id","default")
    return jsonify({"sessions": get_sessions(uid)})

# ── MEMORY ────────────────────────────────────────────────
@app.route("/memory/save",  methods=["POST"])
def mem_save():
    d = request.get_json(); save_memory(d.get("user_id","default"),d.get("memory","")); return jsonify({"success":True})

@app.route("/memory/get",   methods=["GET"])
def mem_get():
    return jsonify({"memories":get_memories(request.args.get("user_id","default"))})

@app.route("/memory/purge", methods=["POST"])
def mem_purge():
    purge_memories(request.get_json().get("user_id","default")); return jsonify({"success":True})

# ── NOTES ─────────────────────────────────────────────────
@app.route("/notes/save", methods=["POST"])
def notes_save():
    d = request.get_json(); save_note(d.get("user_id","default"),d.get("content",""),d.get("title","")); return jsonify({"success":True})

@app.route("/notes/get",  methods=["GET"])
def notes_get():
    return jsonify({"notes":get_notes(request.args.get("user_id","default"))})

# ── TASKS ─────────────────────────────────────────────────
@app.route("/tasks/save", methods=["POST"])
def tasks_save():
    d = request.get_json(); save_task(d.get("user_id","default"),d.get("task",""),d.get("priority","normal")); return jsonify({"success":True})

@app.route("/tasks/get",  methods=["GET"])
def tasks_get():
    return jsonify({"tasks":get_tasks(request.args.get("user_id","default"))})

# ── DIRECT TOOLS ──────────────────────────────────────────
@app.route("/tools/weather",  methods=["GET"])
def tool_weather(): return jsonify(get_weather(request.args.get("city","Delhi")))

@app.route("/tools/news",     methods=["GET"])
def tool_news(): return jsonify(get_news(request.args.get("q","India")))

@app.route("/tools/search",   methods=["GET"])
def tool_search(): return jsonify(web_search(request.args.get("q","")))

@app.route("/tools/currency", methods=["GET"])
def tool_currency():
    return jsonify(convert_currency(float(request.args.get("amount",1)),request.args.get("from","USD"),request.args.get("to","INR")))

@app.route("/tools/stock",    methods=["GET"])
def tool_stock(): return jsonify(get_stock(request.args.get("symbol","AAPL")))

# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
