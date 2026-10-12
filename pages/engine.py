"""
Bridge between the website and your text-to-CAD pipeline.

The Try page calls generate(prompt, answers) and expects ONE of these dicts back:

  Needs more detail  -> {"status": "clarify",
                         "questions": [{"id": "thickness", "text": "How thick should the plate be?"}]}

  Finished           -> {"status": "ok",
                         "operations": [...],            # the generated operations (shown as JSON)
                         "download_url": "/media/x.step" # optional, shows a Download button
                         "message": "optional note",
                         "preview_text": "optional label under the viewport"}

Replace the DEMO block below with calls into your pipeline, in this order:
  1. clarify step     (your models/app_clarify.py)   -> return "clarify" if it has questions
  2. generate step    (your models/generate_cad.py)  -> operations
  3. validate         (your validator/)              -> raise on failure
  4. build + export   (your praser/ + cad/exporter)  -> write a file, return its URL

`answers` is None on the first call, then {question_id: answer} after the user replies.
Keep slow work (model calls) in here; the browser shows progress while it waits.
"""

import re

DEMO = True  # set to False once you've wired the real pipeline


def generate(prompt: str, answers: dict | None = None) -> dict:
    if DEMO:
        return _demo(prompt, answers)

    # ---- Wire your pipeline here ----
    # from models.generate_cad import ...
    # from validator.schema import ...
    # from praser.builder import ...
    # from cad.exporter import ...
    raise NotImplementedError("Connect engine.generate() to the Friday pipeline.")


# ---------- Demo behaviour so the UI works end to end before the real pipeline is connected ----------
def _demo(prompt: str, answers: dict | None) -> dict:
    has_numbers = bool(re.search(r"\d", prompt))
    if not has_numbers and not answers:
        return {
            "status": "clarify",
            "questions": [{"id": "size", "text": "What are the main dimensions (e.g. 50 x 30 x 5 mm)?"}],
        }

    return {
        "status": "ok",
        "message": "Demo output. Connect pages/engine.py to your pipeline to get real models.",
        "preview_text": "Demo result (no real model built)",
        "operations": [
            {"op": "sketch", "plane": "XY", "shape": "rectangle", "note": "from: " + prompt[:60]},
            {"op": "extrude", "distance": "from prompt"},
        ],
        "download_url": None,
    }
