# import json, sys, tempfile, traceback
# from pathlib import Path
# from praser.doc_builder import build_document

import json, sys, tempfile, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
from cad import CADShape, Exporter
from praser.builder import build
from praser.doc_builder import build_document

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Part
from cad import CADShape, Exporter
from praser.builder import build

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

if len(sys.argv) > 1:
    target = sys.argv[1]
    # Check if they passed the full path, or just the filename
    if Path(target).is_file():
        files_to_run = [Path(target)]
    else:
        files_to_run = [Path(__file__).parent / "cases" / target]
        if not files_to_run[0].is_file():
            print(f"Error: Could not find file '{target}'")
            sys.exit(1)
else:
    # Default: grab all JSON files in the cases folder
    files_to_run = sorted((Path(__file__).parent / "cases").glob("*.json"))
    
ok = bad = 0
for f in files_to_run:
    t = json.loads(f.read_text(encoding="utf-8"))
    
    # if t["expect"] != "valid":
    #     continue
    
    doc = App.newDocument(f.stem)
    tmp = Path(tempfile.gettempdir()) / f"{f.stem}_ops.json"
    tmp.write_text(json.dumps(t["document"]), encoding="utf-8")
    
    try:
        shapes = build(str(tmp))
        solids = {k: v for k, v in shapes.items() if isinstance(v, CADShape)}
        if solids:
            last = list(solids)[-1]                      
            Exporter(solids[last]).exportStep(OUT / f"{f.stem}.step")
            Exporter(solids[last]).exportStl(OUT / f"{f.stem}.stl")
            
            # used = set()                                 
            # for op in t["document"]["operations"]:
            #     for k, v in op.items():
            #         if k in ("type", "name"):
            #             continue
            #         if isinstance(v, str):
            #             used.add(v)
            #         elif isinstance(v, list):
            #             used.update(x for x in v if isinstance(x, str))

            # for name, s in solids.items():                     
            #         Part.show(s._shape, name)
            build_document(doc, t["document"]["operations"], shapes)
            doc.saveAs(str(OUT / f"{f.stem}.FCStd"))
            doc.recompute()
            doc.saveAs(str(OUT / f"{f.stem}.FCStd"))
            
        print(f"BUILD OK   {f.name} -> {list(solids)}")
        ok += 1
            
    except Exception as e:
        print(f"BUILD FAIL {f.name}")
        traceback.print_exc(file=sys.stderr) # Forces the error to standard error stream
        bad += 1
        
        # KEY ADDITION: If we are testing a single LLM file, exit immediately so the chat script catches it
        if len(sys.argv) > 1:
            App.closeDocument(doc.Name)
            sys.exit(1) 
                
    # This must be INSIDE the for loop to close the doc after every file
    App.closeDocument(doc.Name)

print(f"{ok} built, {bad} failed. Files are in {OUT}")