# Multi-Agent Multi-Model RAG Platform — Full Execution Plan

## Context

Multi-agent research platform: Researcher → Critic → Synthesizer → Judge pipeline using
Groq (LLM agents) + Sarvam (multilingual + judge) + Pinecone (vectors) + LlamaIndex (RAG)
+ LangGraph (orchestration) + Next.js (frontend) + FastAPI (backend) + Supabase (auth/db)
+ Docker + Cloudflare Tunnels. Starting from zero in `/home/anshulgarg/Documents/RAG-platform`.

---

## Final Directory Structure

```
RAG-platform/
├── frontend/                          # Next.js 14 app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Landing / redirect
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   └── (app)/
│   │       ├── layout.tsx             # Sidebar + auth guard
│   │       ├── dashboard/page.tsx     # Analytics overview
│   │       ├── chat/
│   │       │   ├── page.tsx           # Chat list
│   │       │   └── [sessionId]/page.tsx  # Active chat
│   │       ├── teams/
│   │       │   ├── page.tsx           # Team list
│   │       │   ├── new/page.tsx       # Create team
│   │       │   └── [teamId]/page.tsx  # Edit team
│   │       ├── knowledge/
│   │       │   └── [teamId]/page.tsx  # Upload + manage docs
│   │       └── history/
│   │           ├── page.tsx           # All past queries
│   │           └── [queryId]/page.tsx # Full trace view
│   ├── components/
│   │   ├── ui/                        # shadcn/ui primitives
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── QueryInput.tsx
│   │   │   ├── AgentTrace.tsx         # Live debate trace
│   │   │   ├── SourcePanel.tsx        # Citations + images
│   │   │   └── ScoreCard.tsx          # Quality scores
│   │   ├── teams/
│   │   │   ├── TeamForm.tsx
│   │   │   └── AgentCard.tsx
│   │   └── layout/
│   │       ├── Sidebar.tsx
│   │       └── Header.tsx
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts              # Browser client
│   │   │   └── server.ts              # Server client
│   │   ├── api.ts                     # FastAPI client
│   │   └── types.ts                   # Shared TypeScript types
│   ├── middleware.ts                   # Auth route protection
│   ├── .env.local                     # Secrets (gitignored)
│   ├── .env.example
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
│
├── backend/                           # FastAPI + LangGraph
│   ├── main.py                        # FastAPI app entry
│   ├── routers/
│   │   ├── query.py                   # POST /query (debate trigger)
│   │   ├── ingest.py                  # POST /ingest (doc upload)
│   │   └── health.py                  # GET /health
│   ├── orchestration/
│   │   ├── state.py                   # AgentState TypedDict
│   │   ├── graph.py                   # LangGraph debate graph
│   │   ├── researcher.py              # Groq Llama 3.1 8B
│   │   ├── critic.py                  # Groq Mixtral 8x7B
│   │   ├── synthesizer.py             # Groq Llama 3.1 70B
│   │   └── judge.py                   # Sarvam (multilingual scorer)
│   ├── rag/
│   │   ├── pipeline.py                # Ingest + chunk + embed
│   │   ├── retriever.py               # Pinecone hybrid search
│   │   └── vision.py                  # Image → description (vision API)
│   ├── llms/
│   │   ├── groq_client.py             # Groq SDK wrapper
│   │   └── sarvam_client.py           # Sarvam HTTP wrapper
│   ├── db/
│   │   └── supabase.py                # Supabase Python client
│   ├── utils/
│   │   ├── language.py                # Language detection + translation
│   │   └── retry.py                   # Exponential backoff
│   ├── .env                           # Secrets (gitignored)
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
│
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql     # Full DB schema
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .gitignore
└── README.md
```

---

## Phase 1: Foundation (Days 1–5)

### Goal
All services running locally, APIs tested, Supabase schema deployed, Pinecone index created.

---

### Task 1.1 — Project Scaffolding (Day 1) [Independent]

**Commands:**
```bash
cd /home/anshulgarg/Documents/RAG-platform

# Frontend
npx create-next-app@latest frontend \
  --typescript --tailwind --eslint --app --src-dir=false

# Backend
mkdir backend && cd backend
python3 -m venv venv
source venv/bin/activate

# Shadcn UI setup (in frontend/)
cd ../frontend
npx shadcn@latest init
# Choose: Default style, Slate color, yes CSS variables
```

**Create `.gitignore` (root):**
```
frontend/.env.local
backend/.env
**/__pycache__/
**/.DS_Store
**/node_modules/
**/.next/
**/venv/
```

**Verification:** `npm run dev` (port 3000) + `uvicorn main:app` (port 8000) both start cleanly.

---

### Task 1.2 — Supabase Schema (Day 1) [Independent, parallel with 1.1]

**File: `supabase/migrations/001_initial_schema.sql`**
```sql
-- Teams
CREATE TABLE teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  domain TEXT,
  collaboration_mode TEXT DEFAULT 'sequential',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Agents within a team
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  role TEXT NOT NULL,          -- 'researcher' | 'critic' | 'synthesizer'
  model TEXT NOT NULL,         -- 'groq/llama-3.1-8b' | 'groq/mixtral-8x7b' | etc.
  system_prompt TEXT,
  position INT DEFAULT 0
);

-- Knowledge base documents
CREATE TABLE knowledge_docs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  file_type TEXT,              -- 'pdf' | 'txt' | 'image'
  pinecone_namespace TEXT,     -- namespace in Pinecone index
  chunk_count INT DEFAULT 0,
  uploaded_at TIMESTAMPTZ DEFAULT now()
);

-- Chat sessions
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Query history + debate traces
CREATE TABLE queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  query_text TEXT NOT NULL,
  detected_language TEXT,
  final_answer TEXT,
  debate_trace JSONB,          -- full per-agent trace array
  quality_score FLOAT,
  citation_accuracy FLOAT,
  insight_depth FLOAT,
  response_time_ms INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS policies
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_docs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users own teams" ON teams FOR ALL USING (user_id = auth.uid());
CREATE POLICY "team agents visible to owner" ON agents FOR ALL
  USING (team_id IN (SELECT id FROM teams WHERE user_id = auth.uid()));
CREATE POLICY "team docs visible to owner" ON knowledge_docs FOR ALL
  USING (team_id IN (SELECT id FROM teams WHERE user_id = auth.uid()));
CREATE POLICY "user sessions" ON sessions FOR ALL USING (user_id = auth.uid());
CREATE POLICY "user queries" ON queries FOR ALL
  USING (session_id IN (SELECT id FROM sessions WHERE user_id = auth.uid()));
```

**Run:** `supabase db push` or paste into Supabase SQL editor.

**Verification:** Tables visible in Supabase dashboard, RLS enabled.

---

### Task 1.3 — Environment Variables (Day 1) [Independent]

**`backend/.env.example`:**
```
GROQ_API_KEY=
SARVAM_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=rag-platform
PINECONE_ENVIRONMENT=us-east-1
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
FRONTEND_URL=http://localhost:3000
```

**`frontend/.env.example`:**
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

**Verification:** Both `.env` and `.env.local` files filled, never committed.

---

### Task 1.4 — Groq + Sarvam Clients (Day 2) [Needs: 1.3]

**`backend/requirements.txt`:**
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
groq==0.11.0
llama-index==0.10.68
llama-index-vector-stores-pinecone==0.1.9
pinecone-client==4.1.2
supabase==2.7.4
httpx==0.27.2
python-multipart==0.0.9
python-dotenv==1.0.1
pydantic==2.8.2
langchain==0.2.16
langgraph==0.2.28
langchain-groq==0.1.9
pillow==10.4.0
pypdf==4.3.1
```

**`backend/llms/groq_client.py`:**
```python
from groq import Groq
import os

class GroqLLM:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def chat(self, messages: list, model: str, max_tokens: int = 2048) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

GROQ_MODELS = {
    "researcher": "llama-3.1-8b-instant",
    "critic": "mixtral-8x7b-32768",
    "synthesizer": "llama-3.1-70b-versatile",
}
```

**`backend/llms/sarvam_client.py`:**
```python
import httpx
import os

SARVAM_BASE = "https://api.sarvam.ai"

class SarvamLLM:
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

    def detect_language(self, text: str) -> str:
        # Returns BCP-47 language code: 'hi-IN', 'ta-IN', 'en-IN', etc.
        resp = httpx.post(
            f"{SARVAM_BASE}/text-analytics/identify",
            json={"input": text},
            headers=self.headers,
        )
        return resp.json().get("language_code", "en-IN")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        resp = httpx.post(
            f"{SARVAM_BASE}/translate",
            json={
                "input": text,
                "source_language_code": source_lang,
                "target_language_code": target_lang,
                "speaker_gender": "Male",
                "mode": "formal",
            },
            headers=self.headers,
        )
        return resp.json().get("translated_text", text)

    def judge(self, query: str, answer: str, sources: list[str]) -> dict:
        prompt = f"""You are a research quality judge. Evaluate this answer:

QUERY: {query}
ANSWER: {answer}
SOURCES USED: {', '.join(sources[:5])}

Rate on scale 1-10:
1. citation_accuracy: Are claims backed by sources?
2. insight_depth: Does it go beyond surface-level?
3. overall: Overall research quality?

Respond in JSON: {{"citation_accuracy": X, "insight_depth": X, "overall": X, "reasoning": "..."}}"""

        resp = httpx.post(
            f"{SARVAM_BASE}/chat/completions",
            json={
                "model": "sarvam-m",
                "messages": [{"role": "user", "content": prompt}],
            },
            headers=self.headers,
        )
        import json
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
```

**Verification:**
```bash
python -c "from llms.groq_client import GroqLLM; g=GroqLLM(); print(g.chat([{'role':'user','content':'Hello'}], 'llama-3.1-8b-instant'))"
python -c "from llms.sarvam_client import SarvamLLM; s=SarvamLLM(); print(s.detect_language('नमस्ते'))"
```

---

### Task 1.5 — Pinecone + LlamaIndex Setup (Day 2–3) [Needs: 1.3]

**`backend/rag/pipeline.py`:**
```python
from pinecone import Pinecone
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

def get_pinecone_index(namespace: str):
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    pinecone_index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace=namespace,
    )
    # Use sentence-transformers for embeddings (free, local)
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )
    return VectorStoreIndex.from_vector_store(vector_store)

def ingest_document(file_path: str, namespace: str, file_type: str) -> int:
    """Returns number of chunks created."""
    from llama_index.core import SimpleDirectoryReader
    from rag.vision import describe_image

    if file_type == "image":
        # Vision RAG: describe the image, treat as text document
        description = describe_image(file_path)
        docs = [Document(text=description, metadata={"source": file_path, "type": "image"})]
    else:
        reader = SimpleDirectoryReader(input_files=[file_path])
        docs = reader.load_data()

    index = get_pinecone_index(namespace)
    for doc in docs:
        index.insert(doc)
    return len(docs)
```

**`backend/rag/vision.py`:**
```python
import httpx
import base64
import os

def describe_image(image_path: str) -> str:
    """Use Groq LLaVA to describe an image and return text description."""
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = image_path.split(".")[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")

    response = client.chat.completions.create(
        model="llava-v1.5-7b-4096-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}},
                {"type": "text", "text": "Describe this image in detail for use in a research context. Include all text, data, charts, or visual information you see."}
            ]
        }],
        max_tokens=1024,
    )
    return response.choices[0].message.content
```

**`backend/rag/retriever.py`:**
```python
from rag.pipeline import get_pinecone_index

def retrieve(query: str, namespace: str, top_k: int = 5) -> list[dict]:
    index = get_pinecone_index(namespace)
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    return [
        {
            "text": node.text,
            "score": node.score,
            "source": node.metadata.get("source", "unknown"),
            "type": node.metadata.get("type", "text"),
        }
        for node in nodes
    ]
```

**Verification:** Upload a sample PDF, check chunks appear in Pinecone dashboard.

---

## Phase 2: Agent Orchestration (Days 6–11)

### Goal
Full 4-agent debate loop operational: R → C → S → Judge with traces.

---

### Task 2.1 — LangGraph State (Day 6) [Needs: Phase 1]

**`backend/orchestration/state.py`:**
```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    query: str
    detected_language: str          # BCP-47 code
    english_query: str              # Translated if needed
    namespace: str                  # Pinecone namespace
    retrieved_docs: list[dict]      # From RAG
    researcher_output: str
    critic_output: str
    synthesizer_output: str
    judge_scores: dict              # {citation_accuracy, insight_depth, overall, reasoning}
    debate_trace: list[dict]        # [{agent, model, input, output, sources, tokens, ms}]
    sources: list[str]              # Final cited sources
```

---

### Task 2.2 — Individual Agents (Day 6–7) [Needs: 2.1]

**`backend/orchestration/researcher.py`:**
```python
from orchestration.state import AgentState
from llms.groq_client import GroqLLM, GROQ_MODELS
from rag.retriever import retrieve
import time

groq = GroqLLM()

def researcher_node(state: AgentState) -> AgentState:
    start = time.time()
    query = state["english_query"]
    docs = retrieve(query, state["namespace"])

    context = "\n\n".join([f"[Source: {d['source']}]\n{d['text']}" for d in docs])
    messages = [
        {"role": "system", "content": "You are a research agent. Retrieve and synthesize relevant information from the provided context. Always cite sources."},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUERY: {query}\n\nProvide a detailed, well-cited initial research answer."}
    ]
    model = GROQ_MODELS["researcher"]
    output = groq.chat(messages, model)
    elapsed = int((time.time() - start) * 1000)

    state["researcher_output"] = output
    state["retrieved_docs"] = docs
    state["sources"] = [d["source"] for d in docs]
    state["debate_trace"] = state.get("debate_trace", []) + [{
        "agent": "Researcher",
        "model": model,
        "input": query,
        "output": output,
        "sources": [d["source"] for d in docs],
        "response_ms": elapsed,
    }]
    return state
```

**`backend/orchestration/critic.py`:**
```python
from orchestration.state import AgentState
from llms.groq_client import GroqLLM, GROQ_MODELS
import time

groq = GroqLLM()

def critic_node(state: AgentState) -> AgentState:
    start = time.time()
    model = GROQ_MODELS["critic"]
    messages = [
        {"role": "system", "content": "You are a critical research reviewer. Identify weaknesses, unsupported claims, missing context, and logical gaps in the research answer. Be rigorous but constructive."},
        {"role": "user", "content": f"ORIGINAL QUERY: {state['english_query']}\n\nRESEARCHER ANSWER:\n{state['researcher_output']}\n\nProvide specific critiques and what additional information is needed."}
    ]
    output = groq.chat(messages, model)
    elapsed = int((time.time() - start) * 1000)

    state["critic_output"] = output
    state["debate_trace"].append({
        "agent": "Critic",
        "model": model,
        "input": state["researcher_output"],
        "output": output,
        "sources": [],
        "response_ms": elapsed,
    })
    return state
```

**`backend/orchestration/synthesizer.py`:**
```python
from orchestration.state import AgentState
from llms.groq_client import GroqLLM, GROQ_MODELS
import time

groq = GroqLLM()

def synthesizer_node(state: AgentState) -> AgentState:
    start = time.time()
    model = GROQ_MODELS["synthesizer"]
    messages = [
        {"role": "system", "content": "You are a research synthesizer. Produce the final comprehensive answer incorporating the researcher's findings and critic's feedback. Cite all sources clearly."},
        {"role": "user", "content": f"ORIGINAL QUERY: {state['english_query']}\n\nRESEARCH:\n{state['researcher_output']}\n\nCRITIQUE:\n{state['critic_output']}\n\nWrite the final refined answer addressing all critique points."}
    ]
    output = groq.chat(messages, model)
    elapsed = int((time.time() - start) * 1000)

    state["synthesizer_output"] = output
    state["debate_trace"].append({
        "agent": "Synthesizer",
        "model": model,
        "input": f"Research + Critique",
        "output": output,
        "sources": state["sources"],
        "response_ms": elapsed,
    })
    return state
```

**`backend/orchestration/judge.py`:**
```python
from orchestration.state import AgentState
from llms.sarvam_client import SarvamLLM
import time

sarvam = SarvamLLM()

def judge_node(state: AgentState) -> AgentState:
    start = time.time()
    scores = sarvam.judge(
        query=state["english_query"],
        answer=state["synthesizer_output"],
        sources=state["sources"],
    )
    elapsed = int((time.time() - start) * 1000)

    state["judge_scores"] = scores
    state["debate_trace"].append({
        "agent": "Judge",
        "model": "sarvam-m",
        "input": state["synthesizer_output"],
        "output": scores.get("reasoning", ""),
        "sources": [],
        "response_ms": elapsed,
        "scores": scores,
    })
    return state
```

---

### Task 2.3 — LangGraph Debate Graph (Day 7–8) [Needs: 2.2]

**`backend/orchestration/graph.py`:**
```python
from langgraph.graph import StateGraph, END
from orchestration.state import AgentState
from orchestration.researcher import researcher_node
from orchestration.critic import critic_node
from orchestration.synthesizer import synthesizer_node
from orchestration.judge import judge_node
from llms.sarvam_client import SarvamLLM
from utils.retry import with_retry

sarvam = SarvamLLM()

def build_debate_graph():
    graph = StateGraph(AgentState)

    # Add nodes (with retry wrapper)
    graph.add_node("researcher", with_retry(researcher_node))
    graph.add_node("critic", with_retry(critic_node))
    graph.add_node("synthesizer", with_retry(synthesizer_node))
    graph.add_node("judge", with_retry(judge_node))

    # Sequential flow
    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "critic")
    graph.add_edge("critic", "synthesizer")
    graph.add_edge("synthesizer", "judge")
    graph.add_edge("judge", END)

    return graph.compile()

debate_graph = build_debate_graph()

def run_debate(query: str, namespace: str) -> dict:
    # Step 1: Detect language
    lang = sarvam.detect_language(query)
    english_query = query
    if not lang.startswith("en"):
        english_query = sarvam.translate(query, lang, "en-IN")

    initial_state: AgentState = {
        "query": query,
        "detected_language": lang,
        "english_query": english_query,
        "namespace": namespace,
        "retrieved_docs": [],
        "researcher_output": "",
        "critic_output": "",
        "synthesizer_output": "",
        "judge_scores": {},
        "debate_trace": [],
        "sources": [],
    }

    result = debate_graph.invoke(initial_state)

    # Step 2: Translate final answer back if needed
    final_answer = result["synthesizer_output"]
    if not lang.startswith("en"):
        final_answer = sarvam.translate(final_answer, "en-IN", lang)

    return {
        "final_answer": final_answer,
        "debate_trace": result["debate_trace"],
        "judge_scores": result["judge_scores"],
        "sources": result["sources"],
        "detected_language": lang,
    }
```

**`backend/utils/retry.py`:**
```python
import time
import functools

def with_retry(fn, max_retries: int = 3, base_delay: float = 1.0):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt))
    return wrapper
```

**Verification:**
```bash
cd backend && source venv/bin/activate
python -c "from orchestration.graph import run_debate; r=run_debate('What is quantum computing?', 'test-ns'); print(r['judge_scores'])"
```

---

### Task 2.4 — FastAPI Routes (Day 8–9) [Needs: 2.3]

**`backend/main.py`:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import query, ingest, health
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="RAG Platform Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(query.router, prefix="/query")
app.include_router(ingest.router, prefix="/ingest")
```

**`backend/routers/query.py`:**
```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from orchestration.graph import run_debate
import json

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    namespace: str           # Pinecone namespace (= team_id)
    session_id: str

@router.post("/")
async def run_query(req: QueryRequest):
    try:
        result = run_debate(req.query, req.namespace)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**`backend/routers/ingest.py`:**
```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from rag.pipeline import ingest_document
import tempfile, os

router = APIRouter()

@router.post("/")
async def ingest_file(
    file: UploadFile = File(...),
    namespace: str = Form(...),
):
    allowed = {"application/pdf", "text/plain", "image/jpeg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Unsupported file type")

    with tempfile.NamedTemporaryFile(
        suffix=f"_{file.filename}", delete=False
    ) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    file_type = "image" if file.content_type.startswith("image") else (
        "pdf" if file.content_type == "application/pdf" else "txt"
    )

    try:
        chunk_count = ingest_document(tmp_path, namespace, file_type)
        return {"filename": file.filename, "chunks": chunk_count}
    finally:
        os.unlink(tmp_path)
```

**`backend/routers/health.py`:**
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
```

**Verification:** `curl http://localhost:8000/health` → `{"status":"ok"}`

---

## Phase 3: Chat Interface (Days 12–16)

### Goal
Browser-based multi-agent chat with live debate trace.

---

### Task 3.1 — Supabase + Auth Setup (Day 12) [Needs: 1.2]

**`frontend/lib/supabase/client.ts`:**
```typescript
import { createBrowserClient } from "@supabase/ssr";

export const createClient = () =>
  createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
```

**`frontend/lib/supabase/server.ts`:**
```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export const createClient = () => {
  const cookieStore = cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => cookieStore.getAll(), setAll: (c) => c.forEach(({ name, value, options }) => cookieStore.set(name, value, options)) } }
  );
};
```

**`frontend/middleware.ts`:**
```typescript
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const response = NextResponse.next();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => request.cookies.getAll(), setAll: (c) => c.forEach(({ name, value, options }) => response.cookies.set(name, value, options)) } }
  );
  const { data: { user } } = await supabase.auth.getUser();
  if (!user && request.nextUrl.pathname.startsWith("/(app)")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return response;
}

export const config = { matcher: ["/((?!_next|favicon.ico|api).*)"] };
```

**Install:**
```bash
cd frontend && npm install @supabase/ssr @supabase/supabase-js
```

---

### Task 3.2 — Auth Pages (Day 12) [Needs: 3.1]

**`frontend/app/(auth)/login/page.tsx`:**
- Email/password form
- `supabase.auth.signInWithPassword()`
- Redirect to `/dashboard` on success

**`frontend/app/(auth)/register/page.tsx`:**
- Email/password form
- `supabase.auth.signUp()`
- Redirect to `/dashboard` after email verify

---

### Task 3.3 — Chat UI (Day 13–15) [Needs: 3.1, Phase 2]

**Install:**
```bash
npm install lucide-react recharts react-markdown
```

**`frontend/lib/api.ts`:**
```typescript
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL;

export async function runDebate(query: string, namespace: string, sessionId: string) {
  const res = await fetch(`${BACKEND}/query/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, namespace, session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Query failed");
  return res.json();
}

export async function uploadDocument(file: File, namespace: string) {
  const form = new FormData();
  form.append("file", file);
  form.append("namespace", namespace);
  const res = await fetch(`${BACKEND}/ingest/`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}
```

**`frontend/components/chat/AgentTrace.tsx`:**
```typescript
// Shows live debate trace:
// - Agent name badge (Researcher / Critic / Synthesizer / Judge)
// - Model badge (llama-3.1-8b / mixtral / llama-3.1-70b / sarvam-m)
// - Collapsible agent output
// - Response time
// - Sources used
```

**`frontend/components/chat/ScoreCard.tsx`:**
```typescript
// Displays Judge scores:
// - Overall: X/10 (large)
// - Citation Accuracy: X/10
// - Insight Depth: X/10
// - Reasoning text
```

**Key pages:**
- `chat/[sessionId]/page.tsx` — Full chat view with ChatWindow + AgentTrace + ScoreCard
- `knowledge/[teamId]/page.tsx` — File upload with drag-drop, file list, chunk count
- `teams/new/page.tsx` — Team name + domain + 3-agent config (role + model per agent)

---

## Phase 4: History & Analytics (Days 17–19)

### Goal
Research history with full traces, analytics dashboard.

---

### Task 4.1 — Save Queries to Supabase (Day 17) [Needs: 3.3]

After each debate, save to `queries` table:
```typescript
// In chat/[sessionId]/page.tsx, after runDebate() resolves:
await supabase.from("queries").insert({
  session_id: sessionId,
  query_text: query,
  detected_language: result.detected_language,
  final_answer: result.final_answer,
  debate_trace: result.debate_trace,
  quality_score: result.judge_scores.overall,
  citation_accuracy: result.judge_scores.citation_accuracy,
  insight_depth: result.judge_scores.insight_depth,
  response_time_ms: totalMs,
});
```

---

### Task 4.2 — History Pages (Day 17) [Needs: 4.1]

**`history/page.tsx`:**
- List queries from Supabase, ordered by `created_at DESC`
- Columns: date, query snippet, team, quality score badge
- Filter by team + date range
- Click row → `/history/[queryId]`

**`history/[queryId]/page.tsx`:**
- Full final answer
- Expandable per-agent trace (AgentTrace component)
- ScoreCard
- Export buttons: PDF / JSON

---

### Task 4.3 — Analytics Dashboard (Day 18–19) [Needs: 4.1]

**`dashboard/page.tsx`:**
```typescript
// Metrics from Supabase queries:
// - total_queries: COUNT(*)
// - avg_quality_score: AVG(quality_score)
// - avg_response_ms: AVG(response_time_ms)
// - queries_over_time: GROUP BY date (Recharts BarChart)
// - model_utilization: parse debate_trace JSONB (which models used most)
// - top scoring sessions: ORDER BY quality_score DESC LIMIT 5
```

**Install:** `npm install recharts`

---

## Phase 5: Docker & Deployment (Days 20–22)

### Goal
Full production-ready Docker setup, Cloudflare Tunnel demo.

---

### Task 5.1 — Dockerfiles (Day 20)

**`backend/Dockerfile`:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`frontend/Dockerfile`:**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
ENV PORT 3000
CMD ["node", "server.js"]
```

**`next.config.ts`:** Add `output: "standalone"` for Docker build.

---

### Task 5.2 — docker-compose.yml (Day 20)

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    networks:
      - app-network

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    env_file:
      - ./frontend/.env.local
    environment:
      - NEXT_PUBLIC_BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

**Verification:** `docker compose up --build` → both containers healthy.

---

### Task 5.3 — Cloudflare Tunnel (Day 21)

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Login and create tunnel
cloudflared tunnel login
cloudflared tunnel create rag-platform-demo

# Config file: ~/.cloudflared/config.yml
# tunnel: <tunnel-id>
# credentials-file: /home/anshulgarg/.cloudflared/<tunnel-id>.json
# ingress:
#   - hostname: rag-demo.yourdomain.com
#     service: http://localhost:3000
#   - service: http_status:404

cloudflared tunnel run rag-platform-demo
```

**Verification:** Public HTTPS URL accessible, shows frontend.

---

## Dependency Graph (Full)

```
1.1 Scaffold ────────┐
1.2 Schema ──────────┼──────────────────────────> 3.1 Auth Setup
1.3 Env Vars ────────┤                                    │
1.4 Groq+Sarvam ─────┤                                    │
1.5 Pinecone+LI ─────┘                                    │
         │                                                 │
         ▼                                                 │
2.1 AgentState                                            │
2.2 Agents (R,C,S,J) ──depends on 2.1 ──────────────────>│
2.3 LangGraph Graph  ──depends on 2.2                     │
2.4 FastAPI Routes   ──depends on 2.3                     │
         │                                                 │
         └──────────────────────> 3.3 Chat UI <───────────┘
                                       │
                                       ▼
                              4.1 Save to Supabase
                              4.2 History Pages
                              4.3 Analytics Dashboard
                                       │
                                       ▼
                              5.1 Dockerfiles
                              5.2 docker-compose
                              5.3 Cloudflare Tunnel
```

---

## Parallel Work Opportunities

| Can run simultaneously | Notes |
|------------------------|-------|
| 1.1 + 1.2 + 1.3 | No dependencies between them |
| 1.4 + 1.5 | Both need 1.3, otherwise independent |
| 3.1 (Auth) + Phase 2 | Auth setup and agent work are independent |
| 4.2 + 4.3 | Both read from Supabase, otherwise independent |
| 5.1 + 5.3 | Docker and Tunnel setup are independent |

---

## MVP Definition of Done

| Check | Verification |
|-------|-------------|
| Register + Login | Supabase user created, JWT cookie set |
| Create team with 3 agents | Team + agents rows in Supabase |
| Upload PDF + image | Chunks in Pinecone, doc in `knowledge_docs` |
| Ask query (English) | Full R→C→S→Judge trace, score 1-10 |
| Ask query (Hindi) | Auto-detected, translated, answer in Hindi |
| Image described in answer | Source panel shows image + description |
| History viewable | Query + trace + score visible in `/history` |
| Analytics working | Dashboard shows real metrics |
| Docker builds | `docker compose up` runs entire stack |
| Cloudflare Tunnel live | Public HTTPS URL works |

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Groq rate limits (free: 100 req/min) | Exponential backoff in `utils/retry.py`, queue parallel user requests |
| Sarvam API changes | Wrap in `sarvam_client.py`, easy to swap |
| Pinecone namespace collisions | Use team_id as namespace, guaranteed unique |
| Vision model (LLaVA) unavailable on Groq | Fallback: OCR with pytesseract, describe manually |
| Long debate exceeds context window | Summarize Researcher output before passing to Critic |
| Docker image size (ML deps) | Use `python:3.11-slim`, lazy-load embedding model |
