"""
J-RV-S Web Tools — External API Integrations
"""

import os
import requests

# API Keys from env
WEATHER_KEY = os.environ.get("WEATHER_API_KEY", "")
NEWS_KEY = os.environ.get("NEWS_API_KEY", "")
SERPER_KEY = os.environ.get("SERPER_API_KEY", "")

# ─── WEATHER ──────────────────────────────────────────────────────────────────
def get_weather(city: str = "Delhi") -> dict:
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric"
        r = requests.get(url, timeout=5)
        data = r.json()
        if r.status_code == 200:
            return {
                "city": data["name"],
                "temp": data["main"]["temp"],
                "description": data["weather"][0]["description"].title(),
                "humidity": data["main"]["humidity"],
                "wind": data["wind"]["speed"],
                "feels_like": data["main"]["feels_like"]
            }
        return {"error": data.get("message", "City not found")}
    except Exception as e:
        return {"error": str(e)}

# ─── NEWS ─────────────────────────────────────────────────────────────────────
def get_news(query: str = "India") -> dict:
    try:
        url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize=5&apiKey={NEWS_KEY}"
        r = requests.get(url, timeout=5)
        data = r.json()
        articles = data.get("articles", [])
        return {
            "articles": [
                {
                    "title": a.get("title", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "url": a.get("url", "")
                }
                for a in articles[:5]
            ]
        }
    except Exception as e:
        return {"error": str(e)}

# ─── WEB SEARCH ───────────────────────────────────────────────────────────────
def web_search(query: str) -> dict:
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": 5}
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        data = r.json()
        results = data.get("organic", [])
        return {
            "results": [
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", "")
                }
                for item in results[:5]
            ]
        }
    except Exception as e:
        return {"error": str(e)}

# ─── WIKIPEDIA ────────────────────────────────────────────────────────────────
def wikipedia_search(query: str) -> dict:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return {
            "title": data.get("title", ""),
            "summary": data.get("extract", "No info found.")[:1000],
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
        }
    except Exception as e:
        return {"error": str(e)}

# ─── CURRENCY ─────────────────────────────────────────────────────────────────
def convert_currency(amount: float, from_curr: str, to_curr: str) -> dict:
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr.upper()}"
        r = requests.get(url, timeout=5)
        data = r.json()
        rate = data.get("rates", {}).get(to_curr.upper(), None)
        if rate:
            converted = round(amount * rate, 2)
            return {
                "from": from_curr.upper(),
                "to": to_curr.upper(),
                "amount": amount,
                "rate": rate,
                "converted": converted
            }
        return {"error": "Currency not found"}
    except Exception as e:
        return {"error": str(e)}

# ─── STOCK ────────────────────────────────────────────────────────────────────
def get_stock(symbol: str) -> dict:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice", "N/A")
        prev = meta.get("previousClose", price)
        change = round(price - prev, 2) if isinstance(price, float) else "N/A"
        return {
            "symbol": symbol.upper(),
            "price": price,
            "change": change,
            "currency": meta.get("currency", "USD")
        }
    except Exception as e:
        return {"error": str(e)}
