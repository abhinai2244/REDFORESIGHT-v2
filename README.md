# RedForesight v2 — Predictive Threat Intelligence with Real Telemetry

> **Predictive Threat Intelligence with Real Attack Telemetry and a Standalone Analyst Dashboard**

RedForesight is an autonomous threat forecasting engine that captures live Windows/Sysmon telemetry from isolated Atomic Red Team attack executions, correlates events using MITRE ATT&CK semantic knowledge and ChromaDB episodic memory, expands potential adversary moves via a kill-chain game tree, and streams predictive threat briefs live to a dedicated React dashboard.

---

## What Changed in v2

RedForesight v2 is a rebuild featuring two major architectural upgrades:

1. **Real attack telemetry, zero simulated JSON fixtures.** Attacks genuinely execute inside an isolated disposable victim VM using Atomic Red Team. Splunk's Universal Forwarder streams authentic Sysmon and Windows Event logs to Splunk Enterprise (`index=redforesight_range`).
2. **Standalone React + FastAPI dashboard.** Fully decoupled from Splunk's SimpleXML dashboarding. RedForesight's own web application provides real-time WebSocket updates, kill-chain visualization, and interactive analyst feedback controls.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  ISOLATED ATTACK RANGE (VirtualBox internal network — no internet)│
│                                                                 │
│   ┌────────────────┐         ┌─────────────────────────────┐   │
│   │  Victim VM      │         │  Attacker/Runner VM          │   │
│   │  Windows 10/11  │◄────────┤  Executes Atomic Red Team    │   │
│   │  Sysmon + UF     │         │  test chains (real commands) │   │
│   └───────┬────────┘         └─────────────────────────────┘   │
│           │ forwards real telemetry                             │
└───────────┼─────────────────────────────────────────────────────┘
            │
            ▼
   ┌─────────────────────┐
   │  Splunk Enterprise    │   index=redforesight_range
   │  (dev host machine)   │   real Sysmon/WinEventLog data
   └──────────┬────────────┘
              │  MCP Server (JSON-RPC 2.0)
              ▼
   ┌─────────────────────────────────────────────────────────┐
   │              RedForesight Agent Core (Python)           │
   │  LangGraph 6-node pipeline: ingest → context → classify → │
   │  game-tree → LLM score → brief                            │
   │       │                              │                  │
   │       ▼                              ▼                  │
   │  ChromaDB (semantic +          Gemini/Ollama/Anthropic   │
   │  episodic memory)              (adversarial scoring)     │
   └──────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Backend     │
                    │  REST + WebSocket   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  React Dashboard    │
                    │  (standalone SPA)   │
                    └─────────────────────┘
```

---

## Tech Stack Overview

| Layer | Technology |
|---|---|
| **Attack Victim VM** | Windows 10/11 Enterprise evaluation ISO + Sysmon + Splunk Universal Forwarder |
| **Attack Execution** | Atomic Red Team (`Invoke-AtomicTest`) |
| **SIEM & MCP Bridge** | Splunk Enterprise (`index=redforesight_range`) + Splunk MCP Server (App ID 7931) |
| **Vector Database** | ChromaDB (`sentence-transformers/all-MiniLM-L6-v2`) |
| **Agent Orchestration** | LangGraph 6-node `StateGraph` state machine |
| **LLM Providers** | Gemini 1.5/2.0 Flash (default), Ollama (offline fallback), Anthropic |
| **Backend API** | FastAPI + Uvicorn + WebSockets |
| **Dashboard Frontend** | React 18 + Vite + TypeScript + Tailwind CSS |

---

## Quick Start & Setup

### 1. Install Dependencies

```bash
# Python backend dependencies
pip install -r backend/requirements.txt pydantic chromadb tenacity httpx langgraph sentence-transformers pytest pytest-asyncio uvicorn fastapi

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Configure Environment

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export SPLUNK_MCP_URL="https://127.0.0.1:8089/services/mcp"
export SPLUNK_MCP_TOKEN="your-mcp-bearer-token"
```

### 3. Start Backend & Frontend

**Backend (FastAPI REST & WebSocket on port 8810):**
```bash
PYTHONPATH=. python3 -m uvicorn backend.main:app --port 8810 --host 127.0.0.1
```

**Frontend (React Dashboard on port 5180):**
```bash
cd frontend
npm run dev
```
Open [http://127.0.0.1:5180](http://127.0.0.1:5180) in your browser.

---

## Verification & Testing

### 1. Run Unit Tests
```bash
PYTHONPATH=. python3 -m pytest backend/tests/test_redforesight.py -v
```

### 2. Run Attack-Chain Evaluation Harness
```bash
PYTHONPATH=. python3 scripts/evaluate.py
```
Outputs Precision@1, Precision@3, and Mean Reciprocal Rank (MRR) metrics calculated against ground-truth attack execution logs.

### 3. Trigger a Test Signal
```bash
curl -X POST http://127.0.0.1:8810/api/v1/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "signal_id": "test_sig_001",
    "sourcetype": "WinEventLog:Sysmon",
    "host": "VICTIM-01",
    "process_name": "T1003.001",
    "command_line": "powershell.exe -c Invoke-LSASSDump"
  }'
```
Check `http://127.0.0.1:5180` to see the live WebSocket stream update the threat brief and kill-chain visualizer.

---

## License

[MIT](LICENSE)
