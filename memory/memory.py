"""
J-RV-S Memory System — Supabase Integration
"""

import os
import json
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "") or os.environ.get("SUPABASE_KEY", "")

def get_client():
    if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None

# ─── CHAT HISTORY ─────────────────────────────────────────────────────────────
def save_message(session_id: str, role: str, content: str):
    try:
        client = get_client()
        if not client:
            return False
        client.table("chat_history").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        print(f"Memory save error: {e}")
        return False

def get_history(session_id: str, limit: int = 20) -> list:
    try:
        client = get_client()
        if not client:
            return []
        result = client.table("chat_history")\
            .select("role, content")\
            .eq("session_id", session_id)\
            .order("created_at")\
            .limit(limit)\
            .execute()
        return [{"role": r["role"], "content": r["content"]} for r in result.data]
    except Exception as e:
        print(f"Memory load error: {e}")
        return []

# ─── USER MEMORY (Long-term facts) ────────────────────────────────────────────
def save_memory(user_id: str, memory: str):
    try:
        client = get_client()
        if not client:
            return False
        client.table("user_memory").insert({
            "user_id": user_id,
            "memory": memory,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        print(f"Memory save error: {e}")
        return False

def get_memories(user_id: str, limit: int = 15) -> list:
    try:
        client = get_client()
        if not client:
            return []
        result = client.table("user_memory")\
            .select("memory")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return [r["memory"] for r in result.data]
    except Exception as e:
        print(f"Memory get error: {e}")
        return []

def purge_memories(user_id: str):
    try:
        client = get_client()
        if not client:
            return False
        client.table("user_memory").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        return False

# ─── NOTES ────────────────────────────────────────────────────────────────────
def save_note(user_id: str, note: str, title: str = ""):
    try:
        client = get_client()
        if not client:
            return False
        client.table("notes").insert({
            "user_id": user_id,
            "title": title,
            "content": note,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        return False

def get_notes(user_id: str) -> list:
    try:
        client = get_client()
        if not client:
            return []
        result = client.table("notes")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return result.data
    except Exception as e:
        return []

# ─── TASKS ────────────────────────────────────────────────────────────────────
def save_task(user_id: str, task: str, priority: str = "normal"):
    try:
        client = get_client()
        if not client:
            return False
        client.table("tasks").insert({
            "user_id": user_id,
            "task": task,
            "priority": priority,
            "done": False,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        return False

def get_tasks(user_id: str) -> list:
    try:
        client = get_client()
        if not client:
            return []
        result = client.table("tasks")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("done", False)\
            .order("created_at", desc=True)\
            .execute()
        return result.data
    except Exception as e:
        return []
