# app/routes.py
"""API route handlers."""
from __future__ import annotations

import asyncio
import io
import json
import os
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
from PIL import Image

from app import config
from app import gemini_client
from app import scorecard

router = APIRouter()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@router.get("/")
def root():
    return {
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "time": _now_iso(),
        "endpoints": ["/health", "/upload", "POST /upload/ocr", "POST /upload/score-guess"],
    }


@router.get("/health")
def health():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return {
        "status": "ok",
        "time": _now_iso(),
        "gemini_configured": bool(key),
    }


@router.get("/upload", response_class=HTMLResponse)
def upload_form():
    return """
    <html>
      <head>
        <title>FairwAI Golf Score Helper</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <!-- ===== STYLE SECTION (you can edit this) ===== -->
        <style>
          /* === COLORS YOU CAN CHANGE === */
          :root {
            --bg-page: #ffffff;      /* page background */
            --bg-card: #166534;      /* white card in center */
            --text-main: #0f172a;    /* main text color */
            --accent: #064E3B;       /* button + highlight color */
            --accent-hover: #022C22; /* button hover color */
            --result-bg: #064E3B;    /* result box background */
          }

          /* === PAGE LAYOUT === */
          body {
            font-family: Arial, sans-serif;
            background-color: var(--bg-page);
            margin: 0;
            padding: 30px;
            display: flex;
            justify-content: center;
          }

          .card {
            background-color: var(--bg-card);
            max-width: 700px;
            width: 100%;
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
          }

          /* === MOBILE TWEAKS === */
          @media (max-width: 600px) {
            body {
              padding: 16px;
            }

            .card {
              padding: 20px;
            }
          }

          h2 {
            margin-top: 0;
            color: var(--text-main);
          }

          /* === FORM + INPUT AREA === */
          .field-label {
            font-weight: bold;
            margin-bottom: 8px;
            display: block;
          }

          .file-box {
            padding: 16px;
            border: 2px dashed #cbd5f5;
            border-radius: 8px;
            margin-bottom: 20px;
          }

          /* === BUTTON STYLES === */
          .primary-button {
            background-color: var(--accent);
            color: white;
            border: none;
            border-radius: 999px;   /* big pill shape */
            padding: 14px 28px;
            font-size: 18px;
            cursor: pointer;
            min-height: 48px;       /* nicer for touch */
          }

          .primary-button:hover {
            background-color: var(--accent-hover);
          }

          /* === RESULT BOX === */
          #result {
            background: var(--result-bg);
            padding: 16px;
            border-radius: 8px;
            white-space: pre-wrap;
          }
        </style>



      </head>
      <body>
        <div class="card">
          <!-- ===== PAGE TITLE ===== -->
          <h2>Upload a Scorecard Photo</h2>

          <!-- ===== UPLOAD FORM ===== -->
          <form id="score-form" enctype="multipart/form-data">
            <!-- File input field -->
            <div class="file-box">
              <label>
                <span class="field-label">Scorecard Image:</span>
                <input
                  name="file"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  required
                />
              </label>
            </div>

            <!-- Submit button -->
            <button type="submit" class="primary-button">Get Scores</button>
          </form>

          <!-- ===== RESULT AREA ===== -->
          <h3 style="margin-top: 30px;">Results</h3>
          <pre id="result">No results yet.</pre>
        </div>

        <!-- ===== PAGE SCRIPT  ===== -->
        <script>
          const form = document.getElementById("score-form");
          const resultEl = document.getElementById("result");

          function formatResult(data) {
            if (data.players && data.players.length > 0) {
              let s = "";
              for (const p of data.players) {
                s += "Player " + p.name + " — Total: " + p.total + "\\n";
                const scores = (p.scores_by_hole || []).map(function(h) { return h.score; });
                s += "  Holes: " + scores.join(", ") + "\\n\\n";
              }
              return s.trim();
            }
            return JSON.stringify(data, null, 2);
          }

          form.addEventListener("submit", async (event) => {
            event.preventDefault();
            resultEl.textContent = "Loading...";

            const formData = new FormData(form);
            const url = "/upload/score-guess";

            try {
              const response = await fetch(url, {
                method: "POST",
                body: formData,
              });

              const data = await response.json();

              if (!response.ok) {
                resultEl.textContent =
                  (typeof data.detail === "string"
                    ? data.detail
                    : JSON.stringify(data.detail)) || "Something went wrong.";
                return;
              }

              resultEl.textContent = formatResult(data);
            } catch (error) {
              resultEl.textContent = "Request failed: " + error;
            }
          });
        </script>
      </body>
    </html>
    """

@router.post("/upload/ocr")
async def upload_ocr(file: UploadFile = File(...)):
    """Upload an image → read in memory → Gemini extracts text → return."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (content-type image/*).")
    try:
        raw = await file.read()
        img = Image.open(io.BytesIO(raw))
        img = gemini_client.fix_image_orientation(img)
        img = gemini_client.resize_for_vision(img)
        text = await asyncio.to_thread(
            gemini_client.gemini_vision,
            img,
            "Extract all text from this image. Output only the raw text, preserving layout and line order. No commentary.",
        )
        return JSONResponse(
            content={
                "filename": file.filename,
                "content_type": file.content_type,
                "extracted_text": text,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="OCR failed: " + str(e))


@router.post("/upload/score-guess")
async def upload_score_guess(
    file: UploadFile = File(...),
    debug: bool = Query(False, description="Include raw model response in debug"),
):
    """Upload scorecard image → Gemini returns all players' scores → parse and return."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (content-type image/*).")
    try:
        raw = await file.read()
        img = Image.open(io.BytesIO(raw))
        img = gemini_client.fix_image_orientation(img)
        img = gemini_client.resize_for_vision(img)
        raw_response = await asyncio.to_thread(
            gemini_client.gemini_vision, img, scorecard.SCORECARD_PROMPT
        )
        parsed = scorecard.parse_scorecard_json(raw_response)
        players = scorecard.normalize_players_response(parsed)
        out = {
            "filename": file.filename,
            "players": players,
        }
        if debug:
            out["debug"] = {
                "model": gemini_client.get_resolved_model(),
                "raw_response": raw_response[:2000] + ("..." if len(raw_response) > 2000 else ""),
            }
        return JSONResponse(content=out)
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Gemini did not return valid JSON. Try again or use debug=true to see the raw response.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Score guess failed: " + str(e))
