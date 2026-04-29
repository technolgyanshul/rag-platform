# Demo Script

## 1. Start services

```bash
# terminal 1
cd backend
source .venv/bin/activate
uvicorn main:app --reload

# terminal 2
cd frontend
npm run dev
```

## 2. Upload a document

Open `http://localhost:3000/upload` and upload a sample PDF, image, or text file.

Expected outcome:

- upload succeeds
- document appears in list
- chunk count is shown

## 3. Run a query

Open `http://localhost:3000/chat`, ask a question relevant to the uploaded file, and submit.

Expected outcome:

- answer appears
- source citations appear
- agent trace shows Researcher -> Critic -> Synthesizer -> Judge
- scorecard appears

## 4. Verify history

Open `http://localhost:3000/history`.

Expected outcome:

- recent query appears
- answer preview and scores appear

## 5. Verify dashboard

Open `http://localhost:3000/dashboard`.

Expected outcome:

- total queries, average latency, and average score cards are populated
- 7-day bar chart is populated

## 6. Show tests and evaluation

```bash
cd backend
pytest

cd ../frontend
npm test
npm run build

cd ..
python backend/tests/evaluation/run_eval.py
```

Open `backend/tests/evaluation/results.md` to show benchmark scaffold output.
