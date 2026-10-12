import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from validator.schema import validate

failed = 0
for f in sorted((Path(__file__).parent / "cases").glob("*.json")):
    t = json.loads(f.read_text(encoding="utf-8"))
    errors, warnings = validate(t["document"])
    ok = (not errors) if t["expect"] == "valid" else any(t["expect"] in e for e in errors)
    print("PASS" if ok else "FAIL", f.name)
    if not ok:
        print("   expected:", t["expect"])
        print("   got     :", errors)
    failed += not ok

print(f"{failed} failed")
sys.exit(1 if failed else 0)