"""Signed extremes additional views before combined-motion permission."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
result=read(QA/'v001-vectors/result.json');folder=QA/'v001-signed-views'
assert result['numeric_self_gate']
assert not folder.exists();folder.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic']
ob.data.materials.clear();ob.data.materials.append(material('r008SignedGray',(.55,.55,.55)))
for label,params in isolated_parameters():
    if any(abs(r['angle']) in [.30,.15] for r in params) and ('--' in label or 'opposition' in label):
        pose(rig,params);render(folder,label)
save(folder/'report.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))],'combined_started':False})
