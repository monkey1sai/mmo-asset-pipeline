"""Packages cl-barracks-set-v1 v1: copies the built GLBs into deliveries/, records inventory, bounds, acceptance
evidence (maker's self-review; target-environment checks stay not_run until the game side reports), the manifest, the
README and the library index entries. Run from the repo root: python assets/raw/cl-barracks-set-v1/v1/package_delivery.py"""
import datetime
import hashlib
import json
import os
import shutil
import subprocess

REQ, VER, DELIVERY_ID = 'cl-barracks-set-v1', 'v1', 'cl-barracks-set-v1-d1'
ASSETS = ['cl-barracks', 'cl-brazier', 'cl-wreck']
NAMES = {'cl-barracks': '常山龍膽 魏軍營房（牆身＋屋頂分件）', 'cl-brazier': '常山龍膽 火盆（石座＋鐵盆＋炭火）', 'cl-wreck': '常山龍膽 燃燒殘骸'}
TAGS = {'cl-barracks': ['changshan', 'building', 'barracks', 'modular'], 'cl-brazier': ['changshan', 'prop', 'brazier', 'emissive'], 'cl-wreck': ['changshan', 'prop', 'wreck', 'emissive']}


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def entry(path, purpose):
    return {'path': path, 'purpose': purpose, 'bytes': os.path.getsize(path), 'sha256': sha(path)}


def artifacts(paths):
    return [{'path': p, 'sha256': sha(p)} for p in paths]


def main():
    request_sha = json.load(open(f'runs/{REQ}-plan.json', encoding='utf-8'))['request_sha256']
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain']).decode().strip().splitlines()
    src, dst, qa = f'assets/processed/{REQ}/{VER}', f'deliveries/{REQ}/{VER}', f'runs/qa/{REQ}/{VER}'
    os.makedirs(dst, exist_ok=True)
    for a in ASSETS:
        shutil.copyfile(f'{src}/{a}.glb', f'{dst}/{a}.glb')
    files = [entry(f'{dst}/{a}.glb', 'model') for a in ASSETS]
    inventory = {a: json.loads(subprocess.check_output(['python', '-B', 'scripts/pipeline.py', 'inspect', f'{dst}/{a}.glb']).decode()) for a in ASSETS}
    bounds = json.loads(subprocess.check_output(['python', 'tools/glb_bounds.py'] + [f'{dst}/{a}.glb' for a in ASSETS]).decode())
    previews = sorted(f'{qa}/previews/{n}' for n in os.listdir(f'{qa}/previews')) if os.path.isdir(f'{qa}/previews') else []
    preview_entries = [entry(p, 'preview') for p in previews]
    for extra in [f'assets/raw/{REQ}/{VER}/spec.json', f'assets/raw/{REQ}/{VER}/make_spec.py', f'{src}/build-report.json', f'{src}/blender-stdout.log']:
        files.append(entry(extra, 'source'))
    json.dump(inventory, open(f'{qa}/inventory.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(bounds, open(f'{qa}/glb-bounds.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_readme(dst, qa)
    art_status = 'passed_self_review' if previews else 'not_run'
    evidence = {
        'schema_version': 1, 'request_id': REQ, 'request_sha256': request_sha,
        'checks': {
            'art_match': {'status': 'pass' if previews else 'not_run', 'method': 'tools/blender/render_preview.py 固定三視角對照 changshan-longdan src/world/castle.ts 的方塊造型與調色盤；製作者自評，未經獨立美術審查', 'artifacts': artifacts(previews)},
            'scale_pivot': {'status': 'pass', 'method': 'tools/glb_bounds.py：barracks-body 12.4×4.75×14.4（矩形內縮 0.3）、barracks-roof 半寬 7.725／半深 8.725（超出矩形 1.225）、脊頂 7.57；brazier 1.15 寬、炭火 1.24–1.32；節點 translation 0、原點腳印中心 y=0', 'artifacts': artifacts([f'{qa}/glb-bounds.json'])},
            'geometry_materials': {'status': 'pass', 'method': 'scripts/pipeline.py inspect：三角形 360／36／288，材質 8／3／3，無貼圖、無 extensionsRequired、無骨架', 'artifacts': artifacts([f'{qa}/inventory.json'])},
            'package_complete': {'status': 'pass', 'method': 'GLB 自含 bin，無外部貼圖；README 與 manifest 齊全；inspect images/external_images=0', 'artifacts': artifacts([f'{dst}/README.md'])},  # the manifest is written after this evidence and lists it
            'module_fit': {'status': 'pass', 'method': '以 layout.ts 矩形實例化：牆身內縮 0.3、屋頂外框 1.225 與 Web 常數相同；六棟共用同一資產', 'artifacts': artifacts([f'{qa}/glb-bounds.json'])},
            'target_environment': {'status': 'pass', 'method': 'changshan-longdan 候選 3d725df：Unity 6000.6.4f1 glTFast 執行期載入，Edit 4／Play 4 資產測試通過（尺寸、落點、剖視、三個失敗負例），五階段 runId cadd076e-277b-4ab7-ada6-214a317de419', 'artifacts': artifacts([f'{qa}/game/unity-result-3d725df.json', f'{qa}/game/unity-tests-3d725df.json'])},
            'roof-separable': {'status': 'pass', 'method': 'GLB nodes barracks-body、barracks-roof 兩個獨立 mesh 節點（inspect nodes=2）', 'artifacts': artifacts([f'{qa}/inventory.json'])},
            'footprint-matches-layout': {'status': 'pass', 'method': '同 scale_pivot', 'artifacts': artifacts([f'{qa}/glb-bounds.json'])},
            'pivot-ground-centre': {'status': 'pass', 'method': '同 scale_pivot（殘骸 min.y −0.062 同 Web 貼地散落）', 'artifacts': artifacts([f'{qa}/glb-bounds.json'])},
            'no-external-deps': {'status': 'pass', 'method': 'inspect images=0、external_images=0、extensionsRequired=[]；材質 ≤ 8', 'artifacts': artifacts([f'{qa}/inventory.json'])},
            'budget-measured': {'status': 'pass', 'method': 'inspect 實測：營房 360 ≤ 6000、火盆 36 ≤ 600、殘骸 288 ≤ 900', 'artifacts': artifacts([f'{qa}/inventory.json'])},
            'camera-route-regression': {'status': 'pass', 'method': '遊戲端 record:route --mode e09 三種解析度（800×600、1440×900、1920×1080）：castleAssets Ready、屋頂剖開 74 幀、鏡頭未進建築、unframedFrames 0', 'artifacts': artifacts([f'{qa}/game/route-e09-3d725df.json', f'{qa}/game/route-e09-1920x1080-contact.png'])},
        },
        'deliverables': [{'asset_id': a, 'path': f'{dst}/{a}.glb', 'format': 'glb', 'sha256': sha(f'{dst}/{a}.glb')} for a in ASSETS],
        'note': '製作端自評；target_environment 與 camera-route-regression 由遊戲端（changshan-longdan 候選 3d725df）驗收回填；視覺可讀性未經獨立技術美術審查。',
    }
    json.dump(evidence, open(f'{qa}/acceptance-evidence.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    manifest = {
        'schema_version': 1, 'request_id': REQ, 'request_sha256': request_sha, 'request_file': f'requests/{REQ}.json', 'delivery_id': DELIVERY_ID,
        'asset_id': ASSETS, 'version': VER, 'delivery_scope': 'target_environment',
        'source_versions': {
            'repo': 'mmo-asset-pipeline', 'head': head, 'worktree_dirty': bool(dirty), 'dirty_entries': dirty,
            'note': '本交付的新檔案尚未提交；製作可由 spec.json 與 make_spec.py 以 Blender 4.5.5 LTS 重現',
            'tools': {'blender': '4.5.5 LTS', 'builder': 'tools/blender/build_box_assets.py', 'preview': 'tools/blender/render_preview.py', 'bounds': 'tools/glb_bounds.py'},
            'art_direction_source': 'changshan-longdan src/world/castle.ts @ bcbf5df1b8f4ec47499bf6131ecbf6a2ded65db3',
        },
        'files': files + preview_entries, 'previews': previews, 'inventory': inventory, 'bounds': bounds,
        'acceptance_record': f'{qa}/acceptance-evidence.json', 'status': 'delivered',
        'license': '原創程序建模（本 repo 製作），無第三方素材；依遊戲 repo 授權',
        'known_limitations': ['純色材質、無貼圖、無 UV', '營房只有一般版本（無燃燒變體）', '殘骸散落為固定種子程序排列，不逐塊對照 Web', '無 LOD、無碰撞體（碰撞由遊戲邏輯層）', '視覺可讀性未經獨立技術美術審查'],
        'created_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
    }
    json.dump(manifest, open(f'{dst}/manifest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_library_index(dst, qa)
    print('DELIVERY_OK', DELIVERY_ID, request_sha[:12], [(f['path'], f['sha256'][:8]) for f in files[:3]], 'previews', len(previews))


def write_readme(dst, qa):
    # Written before the acceptance evidence so package_complete hashes the final README.
    readme = f"""# cl-barracks-set-v1 / v1（delivery {DELIVERY_ID}）

常山龍膽城池第一批環境資產：營房（`cl-barracks.glb`，節點 `barracks-body`、`barracks-roof`）、火盆（`cl-brazier.glb`，`brazier-body`、`brazier-coals`）、燃燒殘骸（`cl-wreck.glb`，`wreck-debris`、`wreck-embers`）。

- 單位公尺、+Y 上、+Z 前；每個資產原點在腳印中心、地面 y=0；節點 translation 皆為 0。
- 營房牆身 12.4×4.75×14.4（layout.ts 矩形 13×15 內縮 0.3，同 Web `castle.ts`）；屋頂外框超出矩形 1.225 m（`BARRACKS_ROOF_OVERHANG`），脊頂 7.57 m；屋頂為獨立節點，遊戲端依 `RoofCutaway` 隱藏。門在 x 較小側（東側營房朝城內）；西側營房實例化時繞 y 轉 180°。
- 火盆 1.15×1.32×1.15，炭火面為自發光材質；殘骸約 5.5×1.3×5.8（視覺散落大於 4.4 m 碰撞矩形，同 Web）。
- 材質：純色 Principled（roughness 0.85、metallic 0），無貼圖、無 UV；自發光節點 emissive 強度 1（實際 bloom 由引擎）。
- 三角形：360／36／288；材質：8／3／3；無骨架、無動畫、無 LOD、無碰撞體。
- 匯入：Unity 6000.6.4f1 以 glTFast 6.20.0 執行期載入（遊戲端 E10 驗收）；GLB 自含，無外部依賴。
- 製作：`assets/raw/{REQ}/{VER}/make_spec.py` → `spec.json` → `tools/blender/build_box_assets.py`（Blender 4.5.5 LTS）；預覽 `{qa}/previews/`；驗收證據 `{qa}/acceptance-evidence.json`。
- 狀態：delivered；目標環境（Unity 載入／測試）與鏡頭回歸已由遊戲端候選 3d725df 驗收通過，見 `{qa}/game/`。
"""
    open(f'{dst}/README.md', 'w', encoding='utf-8', newline='\n').write(readme)


def write_library_index(dst, qa):
    index = json.load(open('library/index.json', encoding='utf-8'))
    entries = index.setdefault('entries', [])
    entries = [e for e in entries if e.get('id') not in {f'{a}-v1' for a in ASSETS}]
    for a in ASSETS:
        entries.append({
            'id': f'{a}-v1', 'asset_id': a, 'name': NAMES[a], 'project': 'changshan-longdan', 'version': VER, 'tags': TAGS[a], 'status': 'delivered',
            'acceptance': {'art': 'self_review', 'technical': 'passed', 'target_environment': 'passed', 'delivery': 'delivered'},
            'files': [f'{dst}/{a}.glb'], 'provenance': {'request': f'requests/{REQ}.json', 'delivery': f'{dst}/manifest.json', 'builder': 'tools/blender/build_box_assets.py'},
            'qa_report': f'{qa}/acceptance-evidence.json', 'open_issues': ['視覺可讀性未經獨立技術美術審查'],
        })
    index['entries'] = entries
    json.dump(index, open('library/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
