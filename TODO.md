# Atlas — Next Steps

## Session Status (2026-02-20)

### What's Working
- FastAPI backend on port 8888 with all routes (health, spoke proxy, chat, settings, search, people, pipeline)
- Spoke proxy to civic_media (follow_redirects fix applied, tested with meetings + transcript)
- React frontend (Vite dev on 5173, production build serves from 8888)
- Dashboard with spoke status cards
- Meetings page loads from civic_media proxy, links open correct review page
- SQLite database at `database/atlas.db` with WAL mode
- All models defined (LLMProvider, Conversation, ConversationMessage, UnifiedPerson, PersonMapping)
- Settings page UI for managing external LLM providers (add/edit/delete/test/toggle)
- Chat UI with SSE streaming, tool call indicators, conversation history

### What Needs Doing

#### 1. Get a Local LLM Running (BLOCKED)
WSL2 networking is broken — ICMP works but TCP connections to the internet hang. Two options:

**Option A: Fix WSL2 networking**
- Outbound TCP from WSL2 doesn't work (ping 8.8.8.8 works, curl hangs)
- Could be Windows Firewall, VPN, or WSL2 mirrored networking issue
- Once fixed: `source ~/vllm-env/bin/activate && pip install vllm` then run scripts/vllm-start.sh
- A venv already exists at `~/vllm-env` in WSL2 Ubuntu

**Option B: Use Ollama instead (RECOMMENDED)**
- Install Ollama from https://ollama.com (Windows native, uses GPU directly)
- `ollama pull qwen2.5:7b` — downloads the 7B model
- Auto-serves OpenAI-compatible API at http://localhost:11434/v1
- Update `app/config.py` LLM_PROFILES to point to Ollama:
  ```python
  "fast": LLMProfile(
      name="atlas-fast",
      base_url="http://localhost:11434/v1",
      model="qwen2.5:7b",
  ),
  ```
- No WSL2 needed, no networking issues

**Option C: External API (quickest)**
- Open http://localhost:5173/settings
- Add a Claude/OpenAI/DeepSeek API key
- Chat works immediately

#### 2. Test Chat End-to-End
Once an LLM is running:
- Send a message like "What meetings have been processed?"
- Verify: query classifier routes to civic_media tools
- Verify: LLM calls search_meetings tool
- Verify: tool executor hits civic_media API
- Verify: response streams back via SSE

#### 3. Test Other Spoke Pages
- Articles page — needs article-tracker running on port 5000
- Files page — needs Shasta-DB running on port 8844
- Messages page — needs Facebook-Offline running on port 8147
- Each spoke page fetches through the Atlas proxy

#### 4. Start Other Spokes
For full testing, start the other spoke apps:
- `cd E:\0-Automated-Apps\article-tracker` — check how to start (Flask, port 5000)
- `cd E:\0-Automated-Apps\Shasta-DB` — FastAPI, port 8844
- `cd E:\0-Automated-Apps\Facebook-Offline` — FastAPI, port 8147

#### 5. Frontend Polish
- Search page needs the `/api/search` backend tested with live spokes
- People page — empty until unified person records are created
- Chat model selector dropdown (pick local profile or external provider per conversation)
- Inline media players in chat responses (video/audio from civic_media proxy)

#### 6. Cross-App Features (Phase 4)
- Test unified search across multiple spokes
- Test media pipeline (Shasta-DB file → civic_media transcription)
- Test person discovery and cross-app identity linking

### How to Start Atlas
```bash
# Terminal 1 — Backend
cd E:\0-Automated-Apps\Atlas
python start.py

# Terminal 2 — Frontend (hot reload)
cd E:\0-Automated-Apps\Atlas\frontend
npm run dev

# Terminal 3 — civic_media (or other spokes)
cd E:\0-Automated-Apps\civic_media
uvicorn app.main:app --port 8000
```

### Known Issues
- Multiple `python start.py` invocations create zombie processes on port 8888 that are hard to kill. Use `python start.py` WITHOUT `--reload` to avoid orphaned reloader children. Kill with: `powershell -Command "Get-Process python* | Stop-Process -Force"`
- WSL2 Ubuntu has no outbound TCP (only ICMP). Needs investigation or just use Ollama.
- Shasta-DB port in config is 8844 — verify this matches the actual Shasta-DB startup port
