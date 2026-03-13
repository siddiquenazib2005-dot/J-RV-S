"""
J-RV-S AI Brain — Groq LLaMA Integration
"""

import os
import base64
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
CHAT_MODEL = "llama-3.3-70b-versatile"

def chat(system_prompt: str, messages: list, tool_context: str = "") -> str:
    """Send chat request to Groq."""
    try:
        # Inject tool context into last user message if available
        if tool_context and messages:
            messages = messages.copy()
            last = messages[-1]
            messages[-1] = {
                "role": "user",
                "content": f"{tool_context}\n\nUser: {last['content']}"
            }

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

def analyze_image(image_data: str, mime_type: str, user_prompt: str, system_prompt: str) -> str:
    """Analyze image using LLaMA Vision."""
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt or "Analyze this image in detail."
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Vision Error: {str(e)}"
