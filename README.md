## FairwAI – Golf Score from Photo

This is a beginner-friendly FastAPI app that takes a picture of a golf scorecard, uses **Gemini** (Google AI) to read it, and returns **all players' scores** and totals.

### Tech stack

- Python
- FastAPI
- Pillow (for image handling)
- google-generativeai (Gemini API)

Everything important lives in `app/main.py`.

### Setup

1. Install Python 3.10+.
2. Get a **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey).
3. Install Python dependencies (for example, in a virtualenv):

```bash
pip install fastapi uvicorn pillow google-generativeai python-dotenv
```

4. Set your API key (required to run the app):

```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY="your_key_here"

# Windows (cmd)
set GEMINI_API_KEY=your_key_here

# Linux / macOS
export GEMINI_API_KEY=your_key_here
```

Or create a `.env` file in the project root (same folder as `app/`) with `GEMINI_API_KEY=your_key_here`; the app will load it automatically if `python-dotenv` is installed.

### Run the app

From the project root (the folder that contains `app/`), run:

```bash
uvicorn app.main:app --reload
```

Then open this URL in your browser **on the same PC**:

```text
http://127.0.0.1:8000/upload
```

> `127.0.0.1` (or `localhost`) always means “this device itself”. It works from the PC that is running Uvicorn, but **not** from your phone.

To test on your phone on the same Wi‑Fi:

- Find your computer’s local IP address with something like `ipconfig` (for example `192.168.1.10`).
- Start Uvicorn bound to all interfaces (this is what lets other devices reach it):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Here `0.0.0.0` is only the **bind address for the server**, not something you type into the browser.

- On your phone’s browser (same Wi‑Fi), open:

```text
http://192.168.1.10:8000/upload
```

### How it works

1. You select or capture a **scorecard photo** and choose 9 or 18 holes.
2. The browser sends the image to `POST /upload/score-guess`.
3. The backend reads the image in memory, fixes orientation (EXIF), and sends it to **Gemini** with a structured prompt.
4. Gemini returns a JSON object with every player’s per-hole scores and total.
5. The API responds with JSON:
   - `filename`
   - `holes_requested`
   - `players`: array of `{ "name", "scores_by_hole": [ { "hole", "score" }, ... ], "total" }`
   - Optional `debug` with the raw model response when requested.

Images are not saved to disk; they are processed in memory only.

You can open `app/main.py` to follow the whole flow end-to-end and tweak it as you learn.
