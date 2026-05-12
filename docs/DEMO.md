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

Open `http://localhost:3000/knowledge` and upload a sample PDF, image, or text file.

Expected outcome:

- upload succeeds
- document appears in list
- chunk count is shown

## 3. Run a query

Open `http://localhost:3000/chat`, ask a question relevant to the uploaded file, and submit.

Expected outcome:

- answer appears
- source citations appear

## 4. Verify history

Open `http://localhost:3000/history`.

Expected outcome:

- recent query appears
- answer preview appears

## 5. Verify dashboard

Open `http://localhost:3000/dashboard`.

Expected outcome:

- total queries and average latency cards are populated
- 7-day bar chart is populated

## 6. Show tests

```bash
cd backend
pytest

cd ../frontend
npm test
npm run build
```
