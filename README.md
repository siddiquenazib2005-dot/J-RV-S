# J-RV-S — Just a Rather Very Intelligent System
**Built by Nazib Siddique**

## Architecture
```
User → Frontend → Orchestrator → AI Brain → Tools → Memory → APIs
```

## Features
- 🧠 Orchestrator with Intent Detection & Tool Routing
- 💬 Natural AI Chat (Groq LLaMA)
- 🌐 Web Search, News, Weather, Wikipedia, Stock, Currency
- 📄 PDF & File Analyzer
- 👁️ Image Vision (LLaMA Vision)
- 🧠 Persistent Memory (Supabase)
- 📝 Notes & Tasks System
- 🎤 Voice Input/Output
- ⚡ Keep-Alive (Render free tier)

## Setup

### 1. Clone & Install
```bash
git clone https://github.com/siddiquenazib2005-dot/J-RV-S
cd J-RV-S
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
- `GROQ_API_KEY` — from console.groq.com
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` — from supabase.com
- `WEATHER_API_KEY` — from openweathermap.org (free)
- `NEWS_API_KEY` — from newsapi.org (free)
- `SERPER_API_KEY` — from serper.dev (free)

### 3. Supabase Tables
Run in Supabase SQL editor:
```sql
create table chat_history (
  id uuid default gen_random_uuid() primary key,
  session_id text, role text, content text, created_at timestamptz
);
create table user_memory (
  id uuid default gen_random_uuid() primary key,
  user_id text, memory text, created_at timestamptz
);
create table notes (
  id uuid default gen_random_uuid() primary key,
  user_id text, title text, content text, created_at timestamptz
);
create table tasks (
  id uuid default gen_random_uuid() primary key,
  user_id text, task text, priority text, done boolean default false, created_at timestamptz
);
```

### 4. Run Locally
```bash
python app.py
```

### 5. Deploy to Render
- Connect GitHub repo
- Add environment variables in Render dashboard
- Deploy!

## License
MIT — Built by Nazib Siddique
# J-RV-S
