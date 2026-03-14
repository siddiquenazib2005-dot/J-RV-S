"""
J-RV-S — Just a Rather Very Intelligent System
Built by Nazib Siddique
ONE FILE — NO GROQ LIBRARY — PURE REQUESTS — BULLETPROOF
"""

import os, re, uuid, threading, time, base64, io
import requests
from flask import Flask, request, jsonify, render_template
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

CHAT_MODEL   = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ════════════════════════════════════════════════════════════
# KEEP ALIVE
# ════════════════════════════════════════════════════════════
def keep_alive():
    while True:
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass
        time.sleep(840)

threading.Thread(target=keep_alive, daemon=True).start()

# ════════════════════════════════════════════════════════════
# AI BRAIN — Pure requests, no groq library
# ════════════════════════════════════════════════════════════
def ai_chat(system_prompt, messages, tool_context=""):
    try:
        msgs = [m.copy() for m in messages]
        if tool_context and msgs:
            msgs[-1]["content"] = f"{tool_context}\n\nUser: {msgs[-1]['content']}"
        payload = {
            "model": CHAT_MODEL,
            "messages": [{"role": "system", "content": system_prompt}] + msgs,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        r = requests.post(GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

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
            "temperature": 0.7,
            "max_tokens": 2048
        }
        r = requests.post(GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Vision Error: {str(e)}"

# ════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ════════════════════════════════════════════════════════════
INTENT_MAP = {
    "weather":   ["weather","temperature","rain","forecast","humidity","mausam","barish","garmi","sardi"],
    "news":      ["news","headline","breaking","latest news","khabar","samachar"],
    "search":    ["search","find","look up","google","khojo","dhundo"],
    "wikipedia": ["wikipedia","wiki","define","meaning","history of","kaun hai","kya hai"],
    "currency":  ["currency","convert","usd","inr","dollar","rupee","euro","pound","exchange rate"],
    "stock":     ["stock","share price","market","sensex","nifty","crypto","bitcoin","ethereum"],
    "code":      ["code","program","function","debug","error","script","python","javascript","html","css","fix this","bug"],
    "translate": ["translate","translation","in hindi","in english","anuvad"],
    "summarize": ["summarize","summary","tldr","brief","saaransh"],
    "image":     ["image","photo","picture","analyze image","screenshot"],
    "pdf":       ["pdf","document","analyze this","summarize this file"],
}

def detect_intent(msg):
    m = msg.lower()
    for intent, keywords in INTENT_MAP.items():
        for kw in keywords:
            if kw in m:
                return intent
    return "chat"

def build_system_prompt(intent, user_name="Boss", memories=[]):
    base = f"""You are J-RV-S (Just a Rather Very Intelligent System), an advanced AI assistant built by Nazib Siddique.
You are talking to {user_name}. Be intelligent, helpful, direct, and slightly witty like JARVIS from Iron Man.
Always reply in the same language the user uses (Hindi, English, or Hinglish)."""
    if memories:
        base += "\n\nThings I remember about the user:\n" + "\n".join([f"- {m}" for m in memories[:10]])
    prompts = {
        "weather":   base + "\nPresent weather data clearly with emojis.",
        "news":      base + "\nPresent news as a numbered list of headlines.",
        "search":    base + "\nSummarize search findings clearly.",
        "wikipedia": base + "\nGive a clear educational summary.",
        "currency":  base + "\nShow the converted amount clearly.",
        "stock":     base + "\nPresent price and change clearly.",
        "code":      base + "\nWrite clean, commented, working code. Explain briefly.",
        "translate": base + "\nGive accurate translation with context.",
        "summarize": base + "\nBe concise and capture only key points.",
        "image":     base + "\nDescribe and analyze the image in detail.",
        "pdf":       base + "\nAnalyze and summarize the file content clearly.",
        "chat":      base + "\nEngage in natural, intelligent conversation.",
    }
    return prompts.get(intent, prompts["chat"])

def format_tool_result(intent, result):
    if not result or result.get("error"):
        return ""
    if intent == "weather":
        return f"Weather: {result.get('city')} | {result.get('temp')}°C | {result.get('description')} | Humidity: {result.get('humidity')}%"
    elif intent == "search":
        items = result.get("results", [])
        return "Search Results:\n" + "\n".join([f"- {r.get('title','')}: {r.get('snippet','')}" for r in items[:3]])
    elif intent == "wikipedia":
        return f"Wikipedia:\n{result.get('summary','')}"
    elif intent == "news":
        arts = result.get("articles", [])
        return "News:\n" + "\n".join([f"{i+1}. {a.get('title','')}" for i, a in enumerate(arts[:5])])
    elif intent == "currency":
        return f"Currency: {result.get('amount')} {result.get('from')} = {result.get('converted')} {result.get('to')}"
    elif intent == "stock":
        return f"Stock: {result.get('symbol')} | ${result.get('price')} | Change: {result.get('change')}"
    return str(result)

# ════════════════════════════════════════════════════════════
# SUPABASE — Direct REST, no library
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

def save_message(sid, role, content):
    supa("POST", "chat_history", {"session_id": sid, "role": role, "content": content})

def get_history(sid, limit=15):
    r = supa("GET", "chat_history", params=f"?session_id=eq.{sid}&order=created_at&limit={limit}&select=role,content")
    return [{"role": x.get("role"), "content": x.get("content")} for x in r if x.get("role")]

def save_memory(uid, memory):
    supa("POST", "user_memory", {"user_id": uid, "memory": memory})

def get_memories(uid, limit=15):
    r = supa("GET", "user_memory", params=f"?user_id=eq.{uid}&order=created_at.desc&limit={limit}&select=memory")
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

# ════════════════════════════════════════════════════════════
# WEB TOOLS
# ════════════════════════════════════════════════════════════
def get_weather(city="Delhi"):
    try:
        r = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric", timeout=5)
        d = r.json()
        if r.status_code == 200:
            return {"city": d["name"], "temp": d["main"]["temp"], "description": d["weather"][0]["description"].title(), "humidity": d["main"]["humidity"], "wind": d["wind"]["speed"]}
        return {"error": d.get("message","Not found")}
    except Exception as e:
        return {"error": str(e)}

def get_news(query="India"):
    try:
        # Try top-headlines first (India, English)
        r = requests.get(
            f"https://newsapi.org/v2/top-headlines?country=in&pageSize=5&apiKey={NEWS_KEY}",
            timeout=5)
        arts = r.json().get("articles", [])
        # If query is specific (not generic), use everything endpoint
        if query.lower() not in ["india","latest","news"] and len(arts) == 0:
            r = requests.get(
                f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_KEY}",
                timeout=5)
            arts = r.json().get("articles", [])
        return {"articles": [{"title": a.get("title",""), "source": a.get("source",{}).get("name","")} for a in arts[:5] if a.get("title") and "[Removed]" not in a.get("title","")]}
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
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ','_')}", timeout=5)
        d = r.json()
        return {"title": d.get("title",""), "summary": d.get("extract","")[:1000]}
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
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d",
            headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        meta = r.json().get("chart",{}).get("result",[{}])[0].get("meta",{})
        price = meta.get("regularMarketPrice", 0)
        prev  = meta.get("previousClose", price)
        return {"symbol": symbol.upper(), "price": price, "change": round(price-prev, 2)}
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

@app.route("/static/sw.js")
def service_worker():
    return app.send_static_file("sw.js"), 200, {"Content-Type": "application/javascript", "Service-Worker-Allowed": "/"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return jsonify({"status":"alive","system":"J-RV-S"})

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
            for i, w in enumerate(words):
                if w in ["in","at","for","of"] and i+1 < len(words):
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

        tool_context  = format_tool_result(intent, tool_result) if tool_result else ""
        history       = get_history(session_id)
        history.append({"role":"user","content":user_msg})
        ai_response   = ai_chat(system_prompt, history, tool_context)
        save_message(session_id,"user",user_msg)
        save_message(session_id,"assistant",ai_response)

        return jsonify({"response":ai_response,"intent":intent,"session_id":session_id,"tool_used":intent if tool_result else None})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file      = request.files.get("file")
        user_msg  = request.form.get("message","Analyze this file.")
        user_name = request.form.get("user_name","Boss")
        if not file:
            return jsonify({"error":"No file"}), 400
        file_data = process_file(file.read(), file.filename, file.content_type)
        if file_data["type"] == "image":
            ai_response = ai_vision(file_data["content"],file_data["mime_type"],user_msg,build_system_prompt("image",user_name))
        else:
            history = [{"role":"user","content":f"File: {file.filename}\n\n{file_data['content']}\n\nRequest: {user_msg}"}]
            ai_response = ai_chat(build_system_prompt("pdf",user_name), history)
        return jsonify({"response":ai_response,"file_type":file_data["type"],"filename":file.filename})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/memory/save",  methods=["POST"])
def mem_save():
    d = request.get_json(); save_memory(d.get("user_id","default"),d.get("memory","")); return jsonify({"success":True})

@app.route("/memory/get",   methods=["GET"])
def mem_get():
    return jsonify({"memories":get_memories(request.args.get("user_id","default"))})

@app.route("/memory/purge", methods=["POST"])
def mem_purge():
    purge_memories(request.get_json().get("user_id","default")); return jsonify({"success":True})

@app.route("/notes/save",   methods=["POST"])
def notes_save():
    d = request.get_json(); save_note(d.get("user_id","default"),d.get("content",""),d.get("title","")); return jsonify({"success":True})

@app.route("/notes/get",    methods=["GET"])
def notes_get():
    return jsonify({"notes":get_notes(request.args.get("user_id","default"))})

@app.route("/tasks/save",   methods=["POST"])
def tasks_save():
    d = request.get_json(); save_task(d.get("user_id","default"),d.get("task",""),d.get("priority","normal")); return jsonify({"success":True})

@app.route("/tasks/get",    methods=["GET"])
def tasks_get():
    return jsonify({"tasks":get_tasks(request.args.get("user_id","default"))})

@app.route("/tools/weather",  methods=["GET"])
def tool_weather():
    return jsonify(get_weather(request.args.get("city","Delhi")))

@app.route("/tools/news",     methods=["GET"])
def tool_news():
    return jsonify(get_news(request.args.get("q","India")))

@app.route("/tools/search",   methods=["GET"])
def tool_search():
    return jsonify(web_search(request.args.get("q","")))

@app.route("/tools/currency", methods=["GET"])
def tool_currency():
    return jsonify(convert_currency(float(request.args.get("amount",1)),request.args.get("from","USD"),request.args.get("to","INR")))

@app.route("/tools/stock",    methods=["GET"])
def tool_stock():
    return jsonify(get_stock(request.args.get("symbol","AAPL")))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
