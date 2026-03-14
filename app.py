"""
J-RV-S — Just a Rather Very Intelligent System
Built by Nazib Siddique
Flask Backend v1.0
"""

import os
import re
import uuid
import threading
import time
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from orchestrator import orchestrate, detect_intent, format_tool_result, build_system_prompt
from tools.ai_brain import chat, analyze_image
from tools.web_tools import get_weather, get_news, web_search, wikipedia_search, convert_currency, get_stock
from tools.memory import (
    save_message, get_history, save_memory, get_memories, purge_memories,
    save_note, get_notes, save_task, get_tasks
)
from tools.file_tools import process_uploaded_file

app = Flask(__name__)
CORS(app)

# ─── KEEP ALIVE ───────────────────────────────────────────────────────────────
def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
    while True:
        try:
            requests.get(f"{url}/ping", timeout=10)
        except:
            pass
        time.sleep(840)

threading.Thread(target=keep_alive, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return jsonify({"status": "alive", "system": "J-RV-S"})

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

        memories = get_memories(user_id)
        orchestration = orchestrate(user_message, user_name, memories)
        intent = orchestration["intent"]
        system_prompt = orchestration["system_prompt"]
        tool_result = None

        if intent == "weather":
            words = user_message.lower().split()
            city = "Delhi"
            for i, w in enumerate(words):
                if w in ["in", "at", "for"] and i + 1 < len(words):
                    city = words[i + 1].title()
                    break
            tool_result = get_weather(city)
        elif intent == "news":
            query = user_message.lower().replace("news", "").replace("khabar", "").strip() or "India"
            tool_result = get_news(query)
        elif intent == "search":
            tool_result = web_search(user_message)
        elif intent == "wikipedia":
            query = user_message.lower().replace("wikipedia","").replace("wiki","").replace("what is","").replace("who is","").strip()
            tool_result = wikipedia_search(query)
        elif intent == "currency":
            match = re.search(r"(\d+\.?\d*)\s*([a-zA-Z]{3})\s*(?:to|in)\s*([a-zA-Z]{3})", user_message, re.IGNORECASE)
            if match:
                tool_result = convert_currency(float(match.group(1)), match.group(2), match.group(3))
        elif intent == "stock":
            match = re.search(r'\b([A-Z]{1,5})\b', user_message.upper())
            tool_result = get_stock(match.group(1) if match else "AAPL")

        tool_context = format_tool_result(intent, tool_result) if tool_result else ""
        history = get_history(session_id, limit=15)
        history.append({"role": "user", "content": user_message})
        ai_response = chat(system_prompt, history, tool_context)
        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", ai_response)

        return jsonify({"response": ai_response, "intent": intent, "session_id": session_id, "tool_used": intent if tool_result else None})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files.get("file")
        user_message = request.form.get("message", "Analyze this file.")
        session_id = request.form.get("session_id", str(uuid.uuid4()))
        user_name = request.form.get("user_name", "Boss")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        file_data = process_uploaded_file(file.read(), file.filename, file.content_type)

        if file_data["type"] == "image":
            system_prompt = build_system_prompt("image", user_name)
            ai_response = analyze_image(file_data["content"], file_data["mime_type"], user_message, system_prompt)
        else:
            system_prompt = build_system_prompt("pdf", user_name)
            history = [{"role": "user", "content": f"File: {file.filename}\n\n{file_data['content']}\n\n{user_message}"}]
            ai_response = chat(system_prompt, history)

        return jsonify({"response": ai_response, "file_type": file_data["type"], "filename": file.filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/memory/save", methods=["POST"])
def save_mem():
    data = request.get_json()
    return jsonify({"success": save_memory(data.get("user_id","default"), data.get("memory",""))})

@app.route("/memory/get", methods=["GET"])
def get_mem():
    return jsonify({"memories": get_memories(request.args.get("user_id","default"))})

@app.route("/memory/purge", methods=["POST"])
def purge_mem():
    data = request.get_json()
    return jsonify({"success": purge_memories(data.get("user_id","default"))})

@app.route("/notes/save", methods=["POST"])
def save_note_ep():
    data = request.get_json()
    return jsonify({"success": save_note(data.get("user_id","default"), data.get("content",""), data.get("title",""))})

@app.route("/notes/get", methods=["GET"])
def get_notes_ep():
    return jsonify({"notes": get_notes(request.args.get("user_id","default"))})

@app.route("/tasks/save", methods=["POST"])
def save_task_ep():
    data = request.get_json()
    return jsonify({"success": save_task(data.get("user_id","default"), data.get("task",""), data.get("priority","normal"))})

@app.route("/tasks/get", methods=["GET"])
def get_tasks_ep():
    return jsonify({"tasks": get_tasks(request.args.get("user_id","default"))})

@app.route("/tools/weather", methods=["GET"])
def weather_ep():
    return jsonify(get_weather(request.args.get("city","Delhi")))

@app.route("/tools/news", methods=["GET"])
def news_ep():
    return jsonify(get_news(request.args.get("q","India")))

@app.route("/tools/search", methods=["GET"])
def search_ep():
    return jsonify(web_search(request.args.get("q","")))

@app.route("/tools/currency", methods=["GET"])
def currency_ep():
    return jsonify(convert_currency(float(request.args.get("amount",1)), request.args.get("from","USD"), request.args.get("to","INR")))

@app.route("/tools/stock", methods=["GET"])
def stock_ep():
    return jsonify(get_stock(request.args.get("symbol","AAPL")))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
