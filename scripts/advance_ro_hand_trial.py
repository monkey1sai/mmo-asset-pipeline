"""Close observed failed v001 and start new evidence-driven v002 without clock reset."""
from datetime import datetime, timezone
import json
from pathlib import Path
from hyper3d_api import file_sha, write_json, read_json
import workbench

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r006"
request = read_json(ROOT / "requests/ro-swordsman-combo-r006.json")
ledger = read_json(QA / "quality-ledger.json")
start = read_json(QA / "v001-start.json")
clock = read_json(QA / "phase-start.json")
prototype = read_json(QA / "v001-generated-glove/prototype.json")
assert [t["id"] for t in ledger["trials"]] == ["baseline"]
assert prototype["grip_surface_gate"] is False
end = datetime.now(timezone.utc)
elapsed = (end-datetime.fromisoformat(start["started_utc"])).total_seconds()
phase = (end-datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds()
carried = phase-sum(t["elapsed_seconds"] for t in ledger["trials"])-elapsed
reports = [{"path":p.relative_to(ROOT).as_posix(),"sha256":file_sha(p)} for p in [
    QA/"v001-generated-glove/prototype.json",QA/"v001-generated-glove/fixture-events.json",
    QA/"v001-generated-glove/anatomy-and-masks.json"]]
review = {"verdict":"NO_SHIP","reviewer":"Coordinator actual open/small-curl/grip close-up inspection",
    "source_strength":"Separate five-digit source preserves coherent thenar shape and original UV",
    "failures":["Actual full grip9.8445mm deep penetration and359 triangle-pair transverse crossings",
        "Finger1 and thumb each0 fixed pad contacts within2mm",
        "Retained old wrist glove geometry pulled into angular flaps",
        "Whole60664 triangles; neither gear simplification nor full animation tested"],
    "candidate_complete":False,"scope":"right-only local prototype; full quality not claimed",
    "new_evidence_method":"Remove retained distal glove and digit weights from wrist; surface-aware separate-finger/thenar grip calibration"}
write_json(QA/"v001-review.json",review,exclusive=True)
ledger["trials"].append({"id":"v001","parent_id":"baseline","status":"failed",
    "started_utc":start["started_utc"],"ended_utc":end.isoformat(),"elapsed_seconds":elapsed+carried,
    "execution_seconds":elapsed,"carried_intertrial_seconds":carried,
    "protocol_sha256":workbench.quality_sha256(request),"reviewer":review["reviewer"],
    "hypothesis":start["hypothesis"],"change":"Independent generated glove own-branch52-bone right prototype",
    "failure_reason":"Actual contact/collision and retained old wrist failures; full quality remains incomplete",
    "supporting_reports":reports})
comparison = workbench.compare_quality(request,ledger)
assert not comparison["blockers"],comparison
write_json(QA/"quality-ledger-before-v001.json",read_json(QA/"quality-ledger.json"),exclusive=True)
write_json(QA/"quality-ledger.json",ledger)
write_json(QA/"comparison-v001.json",comparison,exclusive=True)
write_json(QA/"v002-start.json",{"id":"v002","started_utc":end.isoformat(),
    "phase_started_utc":clock["baseline_started_utc"],"request_sha256":clock["request_sha256"],
    "protocol_sha256":clock["protocol_sha256"],"local_gate_contract":start["local_gate_contract"],
    "hypothesis":"Actual retained sleeve/glove boundary cleanup plus surface-aware per-digit grip calibration",
    "new_evidence":reports,"source":prototype["artifact"],"maximum_search_events":40,
    "paid_operations":0,"budget":clock["budget"]},exclusive=True)
print(json.dumps({"closed":"v001 failed","started":"v002","candidate_trials_used":comparison["candidate_trials_used"],
    "next_action":comparison["next_action"],"phase_wall_seconds":phase}))
