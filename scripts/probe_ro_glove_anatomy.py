"""Read actual source sections and original wrist fixture before source fitting."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r006"
dest = QA / "hand-source/anatomy-probe.json"
assert not dest.exists()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets/processed/ro-swordsman-combo-r006/hand-source/right_glove_source.blend"), load_ui=False, use_scripts=False)
ob = bpy.data.objects["SM_RO_RightGlove_Source"]
sections = []
for z in [.005,.012,.02,.035,.055,.07,.085,.095,.105,.115,.125,.135,.145,.155,.165,.175,.185]:
    points = []
    for e in ob.data.edges:
        a,b = (ob.data.vertices[i].co for i in e.vertices)
        if (a.z-z)*(b.z-z)>0 or abs(a.z-b.z)<1e-9:
            continue
        points.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
    points.sort(key=lambda p:p.x)
    groups = []
    for p in points:
        if not groups or p.x - groups[-1][-1].x > .0035:
            groups.append([p])
        else:
            groups[-1].append(p)
    sections.append({"z":z,"groups":[{"count":len(g),"min":[min(p[i] for p in g) for i in range(3)],
        "max":[max(p[i] for p in g) for i in range(3)],"center":[(min(p[i] for p in g)+max(p[i] for p in g))/2 for i in range(3)]} for g in groups]})
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets/processed/ro-swordsman-combo-r006/baseline/ro_hand_baseline.blend"), load_ui=False, use_scripts=False)
state = json.loads(bpy.data.objects["ARM_RO_Swordsman"]["state_json"])
report = {"sections":sections,"baseline":{k:state[k] for k in ["hand_frames","grips","measurements"]},
          "baseline_right_rest":{n:seg for n,seg in state["rest"].items() if ".R" in n and n.startswith(("hand","lower_arm","finger","thumb"))}}
dest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report))
