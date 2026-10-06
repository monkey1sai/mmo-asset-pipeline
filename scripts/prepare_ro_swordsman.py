"""Copy the authorized, immutable reference set and freeze the production contract."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:\.llmcode\ro_swordsman_animation')
DEST = ROOT / 'assets/raw/ro-swordsman-combo/references-v001'
DEST.mkdir(parents=True, exist_ok=True)
names = ['01_provoke.jpg', '02_bash.jpg', '03_magnum_break.jpg', '04_endure.jpg',
         '05_victory.jpg', 'ro_swordsman_action_sheet.jpg', 'ro_swordsman_combo_60fps.mp4']
names += [f'transparent_frames/sprite_{i:02d}.png' for i in range(1,13)]
manifest = []
for name in names:
    src, dst = SOURCE / name, DEST / name
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
        raise RuntimeError('reference collision: '+name)
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists(): shutil.copyfile(src,dst)
    manifest.append({'source':str(src),'path':dst.relative_to(ROOT).as_posix(),
                     'size_bytes':dst.stat().st_size,'sha256':sha})
(DEST/'manifest.json').write_text(json.dumps({'source_policy':'user-supplied; original read-only; commercial rights unverified','files':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
quality=json.loads((ROOT/'templates/quality-contract.json').read_text(encoding='utf-8-sig'))
quality.update(status='frozen',reference_artifacts=[{'path':x['path'],'sha256':x['sha256']} for x in manifest if not x['path'].endswith('.mp4')])
quality['protocol']={
    'views':['front','side','back','three-quarter','detail'],
    'lighting':'Fixed Eevee studio: Key (3,-4,5)700W 4m; Fill(-3,-2,3)350W 3m; Rim(0,3,4)800W 3m; world(.16,.16,.16). No VFX on evaluation views.',
    'background':'AgX exposure0; neutral grey floor(.18,.19,.21); 1280x1280 PNG.',
    'framing':'Frame1; ortho scale2.25; target(0,0,.9); front(0,-4,1.35),side(4,0,1.35),back(0,4,1.35),3Q(2.8,-4,2). Detail(1.2,-4,1.75)target(0,0,1.53)scale.62.',
    'tool_version':'Blender4.5.5 LTS build836beaaf597a; BLENDER_EEVEE_NEXT; local reproducible construction.',
    'inspection_context':'Standalone stylized humanoid matching supplied art. Compare five views and face; inspect neutral animation entire300frames and transition midpoints; shoulders/elbows/hips/knees, grip, sword arc, foot contact, garment collision; clean GLB reimport. No target game specified.'}
quality['budget']={'trial_seconds':7200,'total_seconds':21600}
quality.pop('note',None)
quality['dimensions'][0]['criterion']='棕色尖髮男性劍士、銀色分片甲、藍衣擺／白前襟、皮裝、直劍皆符合照片；臉部動漫語言相符。'
quality['dimensions'][4]['criterion']='固定視角與連段中肩肘髖膝變形、甲衣接合、劍手握持皆無關鍵瑕疵；特效不掩蓋缺陷。'
quality['dimensions'][5]['criterion']='挑釁→狂擊→怒爆→霸體→勝利及12參考姿勢／連續銜接清楚，重心、支撐脚和劍尖弧線可信；必要效果為分離可關閉內容。'
request={
 'schema_version':1,'id':'ro-swordsman-combo','title':'RO 劍士造型、骨架與連續技能：真實品質實驗',
 'brief':'以 C:\\ .llmcode\\ro_swordsman_animation 的 RO 劍士連續技能照片製作角色模型＋骨架＋照片中的連續技能動畫；作為 autoresearch 壓力測試，完成且無誤後 commit push main。',
 'purpose':'獨立可編輯角色與可搬移GLB，驗證固定基準、有界修訂、真實美術／骨架／連段及匯出驗收。',
 'task_type':'rigged_character','status':'specified','project':None,
 'style':{'description':'照片中的年輕棕髮男性動漫劍士，銀灰裝甲、深藍衣襬、白色前襟及棕色皮裝；依二維參考重建三維。',
          'references':[str(SOURCE),'runs/evidence/ro-swordsman-reference-analysis.md'],
          'must_have':['棕色尖髮與動漫男性臉','分片銀色胸肩臂甲','深藍分叉衣擺與白前襟','皮手套／腰帶／長靴','獨立直劍／武器掛點','可編輯骨架及真正連續技能動作','可關閉的斬擊、怒爆火焰、霸體金色光效'],
          'must_not_have':['把場景文字或火光融合進角色幾何','靜態圖片輪播代替骨骼動畫','以特效遮住握持或關節缺陷','自行新增遊戲傷害／碰撞規則']},
 'spec':{'size_m':[1.2,1.2,1.74],'size_scope':'角色約1.74m高；XY為含動作與武器的規劃包絡，實測另記。','units':'m','up_axis':'+Y','forward_axis':'+Z',
         'target_triangles':60000,'triangle_budget_scope':'完整角色與劍合計上限；展示stage/VFX另記。','texture_px':None,'requires_rig':True,
         'animations':['AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory'],
         'animation_contract':{'fps':60,'frames':300,'sampling_interval_seconds':[0,4.9833333333],'playback_duration_seconds':5,'reference_order':['provoke','bash','magnum_break','endure','victory'],'root_motion':'原地表演；跳躍由骨盆位移，不改遊戲位移；動作銜接推定。'},
         'parts':[{'id':'character','pivot':'地面中心；Blender+Z上/-Y前→GLB+Y上/+Z前'}, {'id':'sword','pivot':'握柄中心；掛hand.R武器骨'}, {'id':'coat-tails','pivot':'骨盆左右分叉衣擺獨立活動'}, {'id':'effects','pivot':'分離展示層，角色動作可不含效果檢查'}]},
 'production':{'route':'generate','reason':'素材庫沒有相符角色；使用已核實本機Blender新建真實baseline，依固定評估修訂；本次不授權付費。','max_revisions':3,'reuse_candidates':[]},
 'delivery':{'scope':'standalone','formats':['blend','glb'],'target_environment':None},
 'provenance':{'kind':'user_brief','reference':str(SOURCE)+'; user explicit source and rig/animation scope'},
 'additional_checks':[{'id':'export-roundtrip','area':'technical','description':'乾淨場景GLB重匯入，實際skin/joints/channels/材質/採樣與變形保留；以交付hash綁定。'}, {'id':'skill-effects','area':'art','description':'斬擊／怒爆／霸體效果對應參考且可關閉；無效果全段另外檢查。'}],
 'assumptions':['standalone，不宣稱指定遊戲可用。','背面及中間動作依照片設計推定；不是原作測量還原。','無角色外部貼圖；材質以GLB可攜PBR節點配色，UV不作貼圖效率宣稱。','來源容器5秒60fps；精確節奏及不可見姿態為重建。','不包含臉部台詞或自動重定向；骨架命名映射與使用說明交付。','參考權利由使用者提供，商業使用權仍未驗證。'],
 'open_questions':[],'quality':quality}
(ROOT/'requests/ro-swordsman-combo.json').write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared',len(manifest),'unchanged reference files and frozen request.')
