"""
Bridge between the website and the text-to-CAD pipeline.

generate(prompt, answers) returns ONE of:

  {"status": "clarify", "questions": [{"id": "...", "text": "..."}]}

  {"status": "ok", "operations": [...], "download_url": "/media/cad/x.step",
   "message": "...", "preview_text": "...", "downloads": {"step": ..., "stl": ..., "fcstd": ...}}

It raises RuntimeError with a readable message when something fails.
"""

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI

from . import prompts

load_dotenv(override=True)

DEMO = False

FAST_MODEL = "z-ai/glm-5.3-flash"
CAD_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
MAX_RETRIES = 3

BASE = Path(settings.BASE_DIR)
FREECAD_PYTHON = getattr(
    settings,
    "FREECAD_PYTHON",
    os.getenv("FREECAD_PYTHON", r"C:\Users\Vikas Dubey\AppData\Local\Programs\FreeCAD 1.1\bin\python.exe"),
)
BUILD_SCRIPT = BASE / "tests" / "build_all.py"
BUILD_OUT = BASE / "tests" / "output"
JSON_DIR = BASE / "LLM_output"
MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", BASE / "media"))
MEDIA_URL = getattr(settings, "MEDIA_URL", "/media/")

JSON_DIR.mkdir(exist_ok=True)

_clients = {}


def _nv():
    if "nv" not in _clients:
        _clients["nv"] = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY"),
            timeout=180,
            max_retries=3,
        )
    return _clients["nv"]


def ask(client, model, messages, **kw):
    out = ""
    st = client.chat.completions.create(model=model, messages=messages, stream=True, **kw)
    for ch in st:
        if ch.choices and ch.choices[0].delta and ch.choices[0].delta.content:
            out += ch.choices[0].delta.content
    return out


def clean_json(txt):
    t = (txt or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    i = t.find("{")
    j = t.rfind("}")
    if i != -1 and j != -1 and j > i:
        t = t[i:j + 1]
    return t


def _slug(text, i):
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")[:40]
    return f"q{i + 1}_{s}" if s else f"q{i + 1}"


def _context(prompt, answers):
    ctx = f"Initial request: {prompt}"
    if answers:
        lines = []
        for k, v in answers.items():
            if str(v).strip():
                name = re.sub(r"^q\d+_", "", k).replace("_", " ")
                lines.append(f"- {name}: {v}")
        if lines:
            ctx += "\nClarifications from the user:\n" + "\n".join(lines)
            ctx += "\nDo not ask further questions; assume sensible defaults for anything still missing."
    return ctx


def generate(prompt: str, answers: dict | None = None) -> dict:
    if DEMO:
        return _demo(prompt, answers)

    ctx = _context(prompt, answers)

    try:
        txt = ask(
            _nv(),
            FAST_MODEL,
            [
                {"role": "system", "content": prompts.ANALYZER_PROMPT},
                {"role": "user", "content": ctx},
            ],
            temperature=0.0,
        )
        analysis = json.loads(clean_json(txt))
    except json.JSONDecodeError:
        analysis = {"status": "ready", "specification": ctx}
    except Exception as e:
        raise RuntimeError(f"Analyzer call failed: {e}") from e

    if analysis.get("status") == "needs_info" and not answers:
        qs = analysis.get("questions", [])
        return {
            "status": "clarify",
            "questions": [{"id": _slug(q, i), "text": q} for i, q in enumerate(qs)],
        }

    spec = analysis.get("specification") or ctx
    plan = analysis.get("plan") or ["Follow standard CAD procedures."]
    plan_text = "\n".join(str(p) for p in plan)

    messages = [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Generate the CAD operations JSON for this specification:\n\n"
                f"SPECIFICATION:\n{spec}\n\nEXECUTION PLAN TO FOLLOW:\n{plan_text}"
            ),
        },
    ]

    last_err = "unknown error"
    job = uuid.uuid4().hex[:8]

    for attempt in range(MAX_RETRIES):
        try:
            content = ask(_nv(), CAD_MODEL, messages, temperature=0.2, max_tokens=8192)
        except Exception as e:
            last_err = f"CAD model call failed: {e}"
            time.sleep(2)
            continue

        if not content:
            last_err = "CAD model returned an empty response"
            continue

        try:
            data = json.loads(clean_json(content))
        except json.JSONDecodeError:
            last_err = "CAD model returned invalid JSON"
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "Return only raw, valid JSON."})
            continue

        title = str(data.get("title") or "model")
        safe = "".join(c if c.isalnum() else "_" for c in title)[:60] or "model"
        stem = f"{safe}_{job}"
        json_path = JSON_DIR / f"{stem}.json"
        json_path.write_text(json.dumps(data, indent=4), encoding="utf-8")

        start = time.time()
        try:
            res = subprocess.run(
                [FREECAD_PYTHON, str(BUILD_SCRIPT), str(json_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            last_err = "FreeCAD build timed out"
            continue
        took = round(time.time() - start, 1)

        if res.returncode == 0:
            ops = data.get("document", {}).get("operations", [])
            urls = _publish(stem)
            return {
                "status": "ok",
                "operations": ops,
                "download_url": urls.get("step") or urls.get("fcstd") or urls.get("stl"),
                "downloads": urls,
                "message": f"Built in {took}s.",
                "preview_text": title,
            }

        err = (res.stderr.strip() or res.stdout.strip())[-1500:]
        last_err = f"FreeCAD build failed: {err}"
        messages.append({"role": "assistant", "content": content})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"FreeCAD execution failed with error:\n{err}\n\n"
                    "Fix the error. Ensure coincident constraints include pos_a and pos_b, "
                    "and sketch profiles form a single closed loop."
                ),
            }
        )
        time.sleep(1)

    raise RuntimeError(f"Could not build a valid model after {MAX_RETRIES} attempts. Last problem: {last_err}")


def _publish(stem):
    dest = MEDIA_ROOT / "cad"
    dest.mkdir(parents=True, exist_ok=True)
    urls = {}
    for key, ext in (("step", ".step"), ("stl", ".stl"), ("fcstd", ".FCStd")):
        src = BUILD_OUT / f"{stem}{ext}"
        if src.exists():
            shutil.copy2(src, dest / src.name)
            urls[key] = f"{MEDIA_URL}cad/{src.name}"
    jsrc = JSON_DIR / f"{stem}.json"
    if jsrc.exists():
        shutil.copy2(jsrc, dest / jsrc.name)
        urls["json"] = f"{MEDIA_URL}cad/{jsrc.name}"
    return urls


def _demo(prompt: str, answers: dict | None) -> dict:
    has_numbers = bool(re.search(r"\d", prompt))
    if not has_numbers and not answers:
        return {
            "status": "clarify",
            "questions": [{"id": "size", "text": "What are the main dimensions (e.g. 50 x 30 x 5 mm)?"}],
        }

    return {
        "status": "ok",
        "message": "Demo output. Set DEMO = False in pages/engine.py to use the real pipeline.",
        "preview_text": "Demo result (no real model built)",
        "operations": [
            {"op": "sketch", "plane": "XY", "shape": "rectangle", "note": "from: " + prompt[:60]},
            {"op": "extrude", "distance": "from prompt"},
        ],
        "download_url": None,
    }