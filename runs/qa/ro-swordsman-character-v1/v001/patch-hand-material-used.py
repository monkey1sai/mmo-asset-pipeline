"""Assembly: give both hands the textured leather material that belongs to the r007 hand source (same 904 vertices and UVs)."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_v001_assemble.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('parser.add_argument("--toe-blend-mm", type=float)', 'parser.add_argument("--toe-blend-mm", type=float)\nparser.add_argument("--hand-material", action="store_true")')
patch('''for leftover_object in (hand_arm, local_sword):''', '''materials_note = "Both hands still carry the r010 gray review material."
if args.hand_material:
    material_source = ROOT / "assets/processed/ro-swordsman-combo-r007/v004-root-weights/right_hand_root_weights.blend"
    with bpy.data.libraries.load(str(material_source), link=False) as (available_materials, wanted_materials):
        wanted_materials.materials = ["M_RO_Hand_SourcePBR_Explicit"]
    leather = wanted_materials.materials[0]
    leather.name = "M_RO_Hand_Leather"
    for obj in (hand, left):
        obj.data.materials.clear()
        obj.data.materials.append(leather)
    materials_note = ("Both hands use the r007 source PBR material (diffuse, metallic, roughness, normal, 2048 px, packed). The 16 faces of the thumb patch that "
                      "sample across UV islands are still unresolved, and the left hand shows the mirrored texture.")

for leftover_object in (hand_arm, local_sword):''')
patch('''    "materials_note": "Both hands still carry the r010 gray review material; textured material is a later step of this candidate.",''', '''    "materials_note": materials_note,''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
