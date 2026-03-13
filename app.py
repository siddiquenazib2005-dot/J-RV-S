"""
J-RV-S — Just a Rather Very Intelligent System
Built by Nazib Siddique
Flask Backend v1.0
"""

import os
import uuid
import threading
import time
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# Internal modules
from orchestrator import orchestrate, detect_intent
from tools.ai_brain import chat, analyze_image
from tools.web_tools import get_weather, get_news, web_search, wikipedia_search, convert_currency, get_stock
from tools.memory import (
    save_message, get_history, save_memory, get_memories, purge_memories,
    save_note, get_notes, save_task, get_tasks
)
from tools.file_tools import process_uploaded_file

app = Flask(__name__)
CORS(app)

# ─── KEEP ALIVE (Render free tier) ────────────────────────────────────────────
def keep_alive():
    """Ping self every 14 minutes to prevent Render sleep."""
    url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
    while True:
        try:
            requests.get(f"{url}/ping", timeout=10)
        except:
            pass
        time.sleep(840)  # 14 minutes

# Start keep-alive thread
threading.Thread(target=keep_alive, daemon=True).start()

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return jsonify({"status": "alive", "system": "J-RV-S"})

# ─── MAIN CHAT ────────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", str(uuid.uuid4()))
        user_id = data.get("user_id", "default_user")
        user_name = data.get("user_name", "Boss")

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        # Step 1: Get memories
        memories = get_memories(user_id)

        # Step 2: Detect intent via Orchestrator
        orchestration = orchestrate(user_message, user_name, memories)
        intent = orchestration["intent"]
        system_prompt = orchestration["system_prompt"]

        # Step 3: Run tools based on intent
        tool_result = None

        if intent == "weather":
            # Extract city from message
            words = user_message.lower().split()
            city = "Delhi"
            for i, w in enumerate(words):
                if w in ["in", "at", "for"] and i + 1 < len(words):
                    city = words[i + 1].title()
                    break
            tool_result = get_weather(city)

        elif intent == "news":
            query = user_message.replace("news", "").replace("khabar", "").strip() or "India"
            tool_result = get_news(query)

        elif intent == "search":
            tool_result = web_search(user_message)

        elif intent == "wikipedia":
            query = user_message.lower().replace("wikipedia", "").replace("wiki", "").replace("what is", "").replace("who is", "").strip()
            tool_result = wikipedia_search(query)

        elif intent == "currency":
            # Simple parse: "100 usd to inr"
            import re
            match = re.search(r"(\d+\.?\d*)\s*([a-zA-Z]{3})\s*(?:to|in)\s*([a-zA-Z]{3})", user_message, re.IGNORECASE)
            if match:
                amount, from_c, to_c = float(match.group(1)), match.group(2), match.group(3)
                tool_result = convert_currency(amount, from_c, to_c)

        elif intent == "stock":
            import re
            match = re.search(r'\b([A-Z]{1,5})\b', user_message.upper())
            symbol = match.group(1) if match else "AAPL"
            tool_result = get_stock(symbol)

        # Step 4: Build tool context
        tool_context = orchestration.get("tool_context", "")
        if tool_result:
            from orchestrator import format_tool_result
            tool_context = format_tool_result(intent, tool_result)

        # Step 5: Get chat history
        history = get_history(session_id, limit=15)
        history.append({"role": "user", "content": user_message})

        # Step 6: Call AI Brain
        ai_response = chat(system_prompt, history, tool_context)

        # Step 7: Save to memory
        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", ai_response)

        return jsonify({
            "response": ai_response,
            "intent": intent,
            "session_id": session_id,
            "tool_used": intent if tool_result else None
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── FILE UPLOAD ──────────────────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files.get("file")
        user_message = request.form.get("message", "Analyze this file.")
        session_id = request.form.get("session_id", str(uuid.uuid4()))
        user_name = request.form.get("user_name", "Boss")

        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        file_bytes = file.read()
        filename = file.filename
        mime_type = file.content_type

        # Process file
        file_data = process_uploaded_file(file_bytes, filename, mime_type)

        # If image → use Vision
        if file_data["type"] == "image":
            from orchestrator import build_system_prompt
            system_prompt = build_system_prompt("image", user_name)
            ai_response = analyze_image(
                image_data=file_data["content"],
                mime_type=file_data["mime_type"],
                user_prompt=user_message,
                system_prompt=system_prompt
            )
        else:
            # Inject file content as context
            from orchestrator import build_system_prompt
            system_prompt = build_system_prompt("pdf", user_name)
            file_context = f"File: {filename}\n\nContent:\n{file_data['content']}"
            history = [{"role": "user", "content": f"{file_context}\n\n{user_message}"}]
            ai_response = chat(system_prompt, history)

        return jsonify({
            "response": ai_response,
            "file_type": file_data["type"],
            "filename": filename
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── MEMORY ENDPOINTS ─────────────────────────────────────────────────────────
@app.route("/memory/save", methods=["POST"])
def save_mem():
    data = request.get_json()
    success = save_memory(data.get("user_id", "default"), data.get("memory", ""))
    return jsonify({"success": success})

@app.route("/memory/get", methods=["GET"])
def get_mem():
    user_id = request.args.get("user_id", "default")
    memories = get_memories(user_id)
    return jsonify({"memories": memories})

@app.route("/memory/purge", methods=["POST"])
def purge_mem():
    data = request.get_json()
    success = purge_memories(data.get("user_id", "default"))
    return jsonify({"success": success})

# ─── NOTES ────────────────────────────────────────────────────────────────────
@app.route("/notes/save", methods=["POST"])
def save_note_ep():
    data = request.get_json()
    success = save_note(data.get("user_id", "default"), data.get("content", ""), data.get("title", ""))
    return jsonify({"success": success})

@app.route("/notes/get", methods=["GET"])
def get_notes_ep():
    user_id = request.args.get("user_id", "default")
    notes = get_notes(user_id)
    return jsonify({"notes": notes})

# ─── TASKS ────────────────────────────────────────────────────────────────────
@app.route("/tasks/save", methods=["POST"])
def save_task_ep():
    data = request.get_json()
    success = save_task(data.get("user_id", "default"), data.get("task", ""), data.get("priority", "normal"))
    return jsonify({"success": success})

@app.route("/tasks/get", methods=["GET"])
def get_tasks_ep():
    user_id = request.args.get("user_id", "default")
    tasks = get_tasks(user_id)
    return jsonify({"tasks": tasks})

# ─── DIRECT TOOL ENDPOINTS ────────────────────────────────────────────────────
@app.route("/tools/weather", methods=["GET"])
def weather_ep():
    city = request.args.get("city", "Delhi")
    return jsonify(get_weather(city))

@app.route("/tools/news", methods=["GET"])
def news_ep():
    query = request.args.get("q", "India")
    return jsonify(get_news(query))

@app.route("/tools/search", methods=["GET"])
def search_ep():
    query = request.args.get("q", "")
    return jsonify(web_search(query))

@app.route("/tools/currency", methods=["GET"])
def currency_ep():
    amount = float(request.args.get("amount", 1))
    from_c = request.args.get("from", "USD")
    to_c = request.args.get("to", "INR")
    return jsonify(convert_currency(amount, from_c, to_c))

@app.route("/tools/stock", methods=["GET"])
def stock_ep():
    symbol = request.args.get("symbol", "AAPL")
    return jsonify(get_stock(symbol))

# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
