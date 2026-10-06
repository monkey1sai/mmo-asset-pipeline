"""Wire helper-bone rules into the measurement, export and runtime tools.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-helper-tools-used.py
- cv1_joint_range.py and cv1_export_candidate.py: helpers are set after the pose and before the morph rules.
- cv1_export_candidate.py: the blend sample recomputes helpers from the blended sources, as the runtime does.
- cv1-runtime.js: the evaluator sets helper bones after the mixer; the loader reports which bones a clip keys.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NL = chr(10)


def patch(path, pairs):
    text = (ROOT / path).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, (path, old[:60])
        text = text.replace(old, new)
    (ROOT / path).write_text(text, encoding="utf-8", newline=NL)


patch("scripts/cv1_joint_range.py", [
    ('''AXES = {name: Vector(value) for name, value in contract["axes"].items()}''',
     '''AXES = {name: Vector(value) for name, value in contract["axes"].items()}
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}'''),
    ('''            pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
        state = {''', '''            pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
        # Helper bones (pauldrons, coat panels) follow their sources before the morph rules read the pose.
        for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
            pose[name] = quaternion
        bpy.context.view_layer.update()
        state = {'''),
])
patch("scripts/cv1_export_candidate.py", [
    ('''poser = ContractPoser(arm, contract, poses)''', '''poser = ContractPoser(arm, contract, poses)
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in arm.data.bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in arm.data.bones}
HELPERS = [h["bone"] for h in rules.get("helpers", [])]


def apply_helpers():
    """Helper bones follow their sources; the pose is read after every other bone is set."""
    bpy.context.view_layer.update()
    for name, quaternion in rules_math.helper_rotations(rules, pose_rel(arm), REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = quaternion
    bpy.context.view_layer.update()'''),
    ('''        state = poser.apply(row["motion"], contract["levels"][row["level"]])
        row["state"] = {k: float(state.get(k, 0.0)) for k in state_keys}''', '''        state = poser.apply(row["motion"], contract["levels"][row["level"]])
        row["state"] = {k: float(state.get(k, 0.0)) for k in state_keys}
    apply_helpers()'''),
    ('''for pb in arm.pose.bones:
    pb.rotation_quaternion = pb.rotation_quaternion.slerp(target_rotations[pb.name], 0.5)
bpy.context.view_layer.update()''', '''for pb in arm.pose.bones:
    if pb.name not in HELPERS:
        pb.rotation_quaternion = pb.rotation_quaternion.slerp(target_rotations[pb.name], 0.5)
apply_helpers()'''),
    ('''    "frames": frames, "blocks": blocks,''', '''    "frames": frames, "blocks": blocks, "helper_bones": HELPERS,
    "helper_channels": "keyed in both GLBs at export; strip them from the runtime-owner GLB with scripts/cv1_strip_bone_channels.py so the evaluator is their only writer",'''),
])
patch("tools/runtime-qa/three/src/cv1-runtime.js", [
    ('''import { evaluate, driverValues } from './cv1-pose-rules.js';''', '''import { evaluate, driverValues, helperRotations } from './cv1-pose-rules.js';'''),
    ('''  const animatedMorphChannels = [];''', '''  const parents = {};
  for (const [name, bone] of Object.entries(bones)) parents[name] = bone.parent?.isBone ? (bone.parent.userData.name ?? bone.parent.name) : null;
  const restLocalWxyz = Object.fromEntries(Object.entries(restLocal).map(([name, q]) => [name, [q.w, q.x, q.y, q.z]]));
  const animatedBones = [...new Set(clip.tracks.filter((t) => /\\.quaternion$/.test(t.name)).map((t) => {
    const node = root.getObjectByName(t.name.replace(/\\.quaternion$/, ''));
    return node ? (node.userData.name ?? node.name) : t.name;
  }))];
  const animatedMorphChannels = [];'''),
    ('''    file: describe(file), root, meshes, bones, skeleton, restLocal, restDisagreementDeg: restDisagreement, mixer, clip, fps, animatedMorphChannels,''',
     '''    file: describe(file), root, meshes, bones, skeleton, restLocal, restLocalWxyz, parents, restDisagreementDeg: restDisagreement, mixer, clip, fps, animatedMorphChannels, animatedBones,'''),
    ('''// Evaluator step: runs after the mixer and reads the final pose.
export function applyCorrectives(model, rules, state, poseOverride) {
  const pose = poseOverride ?? model.poseRel();''', '''// Helper bones follow their sources; runs after the mixer, before the morph rules.
export function applyHelpers(model, rules) {
  const rotations = helperRotations(rules, model.poseRel(), model.restLocalWxyz, model.parents);
  for (const [name, [w, x, y, z]] of Object.entries(rotations)) model.bones[name].quaternion.copy(model.restLocal[name]).multiply(new THREE.Quaternion(x, y, z, w));
  return rotations;
}

// Evaluator step: runs after the mixer and reads the final pose. A pose override (negative control) skips the helpers.
export function applyCorrectives(model, rules, state, poseOverride) {
  if (!poseOverride) applyHelpers(model, rules);
  const pose = poseOverride ?? model.poseRel();'''),
])
patch("tools/runtime-qa/three/src/candidate.js", [
    ('''import { evaluate, ownershipConflicts } from './cv1-pose-rules.js';''', '''import { evaluate, ownershipConflicts, helperConflicts } from './cv1-pose-rules.js';'''),
    ('''  const ownership = ownershipConflicts(rules, runtime.animatedMorphChannels);''', '''  const ownership = ownershipConflicts(rules, runtime.animatedMorphChannels);
  const helperOwnership = helperConflicts(rules, runtime.animatedBones);'''),
    ('''    runtime_owner_clip_has_no_owned_morph_channel: ownership.length === 0,''', '''    runtime_owner_clip_has_no_owned_morph_channel: ownership.length === 0,
    runtime_owner_clip_has_no_helper_bone_channel: helperOwnership.length === 0,'''),
    ('''    NC3_baked_clip_in_runtime_owner_mode: { detected: nc3.length > 0, conflicting_channels: nc3.length },''',
     '''    NC3_baked_clip_in_runtime_owner_mode: { detected: nc3.length > 0 || helperConflicts(rules, baked.animatedBones).length > 0, conflicting_channels: nc3.length,
      conflicting_helper_bones: helperConflicts(rules, baked.animatedBones).length },'''),
])
print("patched")
