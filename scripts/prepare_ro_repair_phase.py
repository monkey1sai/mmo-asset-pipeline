"""Create a new explicitly authorized local repair phase, preserving old history."""
import hashlib
import json
from pathlib import Path
import workbench

ROOT = Path(__file__).resolve().parents[1]
ID = 'ro-swordsman-combo-r002'
qa = ROOT / 'runs/qa' / ID
qa.mkdir(parents=True, exist_ok=True)
request_path = ROOT / 'requests' / (ID + '.json')
if request_path.exists():
    raise RuntimeError('New phase already exists; never reset a phase or its clock')
request = workbench.read_json(ROOT / 'requests/ro-swordsman-combo.json')
request['id'] = ID
request['title'] = 'RO 劍士：來源角色局部重建與連段驗收第二階段'
request['brief'] = '用需求與固定品質標準 → Hyper3D API 生成候選 → 保存原始版本與建立基準 → Blender 技能修改與優化 → 固定視角與功能檢查 → 逐項品質比較的創作流程，完成後再做一次壓力測試；保留 commit、push 等使用者驗證成果。'
request['production'] = {'route': 'modify', 'reason': 'Reuse completed authorized Hyper3D candidate at assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb. Preserve the exhausted invalid prior experiment; this new user-authorized phase establishes a complete source baseline before local semantic reconstruction. No new paid submission.', 'max_revisions': 3, 'reuse_candidates': ['ro-swordsman-rodin-v001']}
request['spec']['size_m'] = [1.2, 1.74, 1.2]
request['spec']['size_scope'] = 'GLB [X,Y,Z]: character nominal standing height1.74m (+Y up); X/Z are planning envelope only. Weapon and animated envelope measured separately; no claim exact XYZ size.'
request['spec']['texture_px'] = 2048
request['assumptions'][2] = 'Use existing Hyper3D embedded2048px PBR textures for retained source surfaces; new repaired surfaces use portable PBR materials. No new paid generation.'
request['provenance']['reference'] += '; phase2 latest explicit user instruction: local creation and second stress test, hold commit/push until user verification'
request['phase_history'] = {'previous_request': 'requests/ro-swordsman-combo.json', 'previous_ledger': 'runs/qa/ro-swordsman-combo/quality-ledger-blocked.json', 'old_revisions_used': 3, 'old_revisions_limit': 3, 'old_result': 'invalid experiment and failed deformation, preserved without reset', 'new_scope': 'three bounded local reconstruction revisions after a reviewed new source baseline', 'new_paid_authority': False, 'git_mutation': 'held_for_user_verification'}
errors = workbench.validate_request(request)
if errors:
    raise ValueError(errors)
request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
start = {'schema_version': 1, 'phase_id': ID, 'phase_started_utc': '2026-10-02T13:38:25+00:00', 'baseline_started_utc': '2026-10-02T13:38:25+00:00', 'source_sha256': hashlib.sha256((ROOT/'assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb').read_bytes()).hexdigest(), 'request_sha256': workbench.request_sha256(request), 'protocol_sha256': workbench.quality_sha256(request), 'quality_targets_preserved': True, 'old_phase_not_reset': True, 'time_accounting': 'UTC wall-clock start before new baseline preparation through independent review; no retroactive invented durations', 'revision_budget': 3, 'trial_seconds': 7200, 'total_seconds': 21600, 'git_actions': 'no staging, commit, push', 'api_actions': 'reuse downloaded asset; no new credits authorized'}
(qa/'phase-start.json').write_text(json.dumps(start, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(qa/'plan.json').write_text(json.dumps(workbench.production_plan(request), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(start, ensure_ascii=False))
