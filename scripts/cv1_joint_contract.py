"""Build the character V1 joint-range contract from a request's support envelope.

Usage: python -B scripts/cv1_joint_contract.py requests/<id>.json <new contract.json> [baseline joint-range-result.json]
Angles come from request.support_envelope.joint_ranges_deg; the output is what gets frozen by SHA-256.
Motions are anatomical (swing a bone toward a body direction, or turn it about an axis) so they do not
depend on bone rolls. Shoulder, elbow, hip and knee turn about the body's own axes: a swing toward a direction
carries the limb across the midline once it passes 90 degrees, which is not what flexion or abduction mean. Without a baseline result the contract has no ceilings and can only calibrate.
With one, the no-worse-than-baseline ceilings are recorded per motion and level. Existing output files
are not overwritten.
"""
import json
import sys


def swing(bone, toward, degrees):
    return {"bone": bone, "kind": "swing", "toward": toward, "degrees": degrees}


def twist_axis(bone, about, degrees):
    return {"bone": bone, "kind": "twist", "about": about, "degrees": degrees}


def twist_bone(bone, about_bone, degrees):
    return {"bone": bone, "kind": "twist", "about_bone": about_bone, "degrees": degrees}


def build(request):
    ranges = request["support_envelope"]["joint_ranges_deg"]
    motions = []

    def add(motion_id, region, steps, focus, view, scale, side=None, expect=None, hand_extreme=True, **extra):
        # hand_extreme: the hand-region intersection rule also applies at the extreme level. It is off only where
        # the motion itself folds the hand (wrist, finger and thumb sweeps, full fist); those extremes go to art review.
        motion = {"id": motion_id, "region": region, "steps": steps, "focus_bones": focus, "view": view, "ortho_scale": scale,
                  "gate_extreme_hand_region": hand_extreme, **extra}
        if side:
            motion["side"] = side
        if expect:
            motion["expect"] = expect
        motions.append(motion)

    spine = ranges["spine_total"]
    for name, toward in (("flexion", "forward"), ("extension", "back"), ("lateral", "left")):
        half = spine[name] / 2
        view = {"forward": 1} if name == "lateral" else {"left": 1, "forward": 0.35}
        # Leaning sideways while the arms stay at rest carries a hand into the coat; that extreme is reported, not gated.
        add(f"spine-{name}", "torso", [swing("spine_01", toward, half), swing("spine_02", toward, half)], ["spine_01", "spine_02"], view, 1.3,
            expect={"bone": "spine_02", "toward": toward}, hand_extreme=name != "lateral")
    add("spine-twist", "torso", [twist_axis("spine_01", "up", spine["twist"] / 2), twist_axis("spine_02", "up", spine["twist"] / 2)],
        ["spine_01", "spine_02"], {"forward": 1, "left": 0.3}, 1.3)
    neck = ranges["neck_head"]
    add("neck-yaw", "head", [twist_axis("neck", "up", neck["yaw"] / 2), twist_axis("head", "up", neck["yaw"] / 2)], ["neck", "head"], {"forward": 1}, 0.7)
    add("neck-pitch", "head", [swing("neck", "forward", neck["pitch"] / 2), swing("head", "forward", neck["pitch"] / 2)], ["neck", "head"],
        {"left": 1, "forward": 0.3}, 0.7, expect={"bone": "head", "toward": "forward"})
    add("neck-roll", "head", [swing("neck", "left", neck["roll"] / 2), swing("head", "left", neck["roll"] / 2)], ["neck", "head"], {"forward": 1}, 0.7,
        expect={"bone": "head", "toward": "left"})

    for side in "LR":
        def limb(name):
            return f"{name}.{side}"

        def finger(i, j):
            return f"finger{i}.{side}_0{j}"

        def thumb(j):
            return f"thumb.{side}_0{j}"

        arm, hand, leg = f"arm.{side}", f"hand.{side}", f"leg.{side}"
        shoulder = ranges["shoulder"]
        # Flexion and extension turn about the left-right axis, abduction about the front-back axis.
        abduct = "back" if side == "R" else "forward"
        for name, about, toward, view in (("flexion", "right", "forward", {"out": 1, "forward": 0.4}), ("extension", "left", "back", {"out": 1, "forward": 0.4}),
                                          ("abduction", abduct, "out", {"forward": 1})):
            add(f"shoulder-{name}.{side}", arm, [twist_axis(limb("upper_arm"), about, shoulder[name])], [limb("upper_arm")], view, 1.1, side,
                {"bone": limb("upper_arm"), "toward": toward})
        for sign, name in ((1, "axial-plus"), (-1, "axial-minus")):
            add(f"shoulder-{name}.{side}", arm, [twist_bone(limb("upper_arm"), limb("upper_arm"), sign * shoulder["axial_rotation"])], [limb("upper_arm")],
                {"forward": 1, "out": 0.5}, 1.1, side)
        add(f"elbow-flexion.{side}", arm, [twist_axis(limb("lower_arm"), "right", ranges["elbow"]["flexion"])], [limb("lower_arm")], {"out": 1, "forward": 0.3}, 0.8, side,
            {"bone": limb("lower_arm"), "toward": "forward"})
        for sign, name in ((1, "pronation"), (-1, "supination")):
            add(f"forearm-{name}.{side}", arm, [twist_bone(limb("hand"), limb("lower_arm"), sign * ranges["forearm"]["twist"])], [limb("hand")],
                {"forward": 1, "out": 0.5}, 0.45, side, hand_extreme=False)
        wrist = ranges["wrist"]
        wrist_moves = (("flexion", "palmar", {"radial": 1}), ("extension", "dorsal", {"radial": 1}), ("radial", "radial", {"dorsal": 1}), ("ulnar", "ulnar", {"dorsal": 1}))
        for name, toward, view in wrist_moves:
            add(f"wrist-{name}.{side}", hand, [swing(limb("hand"), toward, wrist[name])], [limb("hand")], view, 0.4, side, {"bone": limb("hand"), "toward": toward},
                hand_extreme=False)
        mcp = [swing(finger(i, 1), "palmar", ranges["finger_mcp"]["flexion"]) for i in (1, 2, 3, 4)]
        pip = [swing(finger(i, 2), "palmar", ranges["finger_pip"]["flexion"]) for i in (1, 2, 3, 4)]
        dip = [swing(finger(i, 3), "palmar", ranges["finger_dip"]["flexion"]) for i in (1, 2, 3, 4)]
        finger_view, finger_focus = {"radial": 1, "palmar": 0.25}, [finger(2, 1), finger(3, 1)]
        add(f"fingers-mcp-flexion.{side}", hand, mcp, finger_focus, finger_view, 0.32, side, {"bone": finger(2, 1), "toward": "palmar"}, hand_extreme=False)
        add(f"fingers-pip-flexion.{side}", hand, pip, finger_focus, finger_view, 0.32, side, {"bone": finger(2, 2), "toward": "palmar"}, hand_extreme=False)
        add(f"fingers-dip-flexion.{side}", hand, dip, finger_focus, finger_view, 0.32, side, {"bone": finger(2, 3), "toward": "palmar"}, hand_extreme=False)
        spread = ranges["finger_mcp"]["spread"]
        add(f"fingers-spread.{side}", hand, [swing(finger(4, 1), "radial", spread), swing(finger(1, 1), "ulnar", spread)], finger_focus, {"dorsal": 1}, 0.32, side)
        thumb_range = ranges["thumb"]
        thumb_steps = [swing(thumb(1), "palmar", thumb_range["cmc_opposition"]), swing(thumb(2), "ulnar", thumb_range["mcp_flexion"]), swing(thumb(3), "ulnar", thumb_range["ip_flexion"])]
        thumb_view = {"palmar": 1, "radial": 0.4}
        add(f"thumb-cmc-opposition.{side}", hand, thumb_steps[:1], [thumb(1)], thumb_view, 0.32, side, {"bone": thumb(1), "toward": "palmar"}, hand_extreme=False)
        add(f"thumb-mcp-flexion.{side}", hand, thumb_steps[1:2], [thumb(1)], thumb_view, 0.32, side, {"bone": thumb(2), "toward": "ulnar"}, hand_extreme=False)
        add(f"thumb-ip-flexion.{side}", hand, thumb_steps[2:], [thumb(1)], thumb_view, 0.32, side, {"bone": thumb(3), "toward": "ulnar"}, hand_extreme=False)
        add(f"combo-empty-fist.{side}", "combo", mcp + pip + dip + thumb_steps, finger_focus, {"radial": 1, "palmar": 0.5}, 0.32, side, hand_extreme=False)
        hip = ranges["hip"]
        for name, about, toward, view in (("flexion", "right", "forward", {"out": 1, "forward": 0.3}), ("extension", "left", "back", {"out": 1, "forward": 0.3}),
                                          ("abduction", abduct, "out", {"forward": 1})):
            add(f"hip-{name}.{side}", leg, [twist_axis(limb("upper_leg"), about, hip[name])], [limb("upper_leg")], view, 1.3, side, {"bone": limb("upper_leg"), "toward": toward})
        for sign, name in ((1, "axial-plus"), (-1, "axial-minus")):
            add(f"hip-{name}.{side}", leg, [twist_bone(limb("upper_leg"), limb("upper_leg"), sign * hip["axial_rotation"])], [limb("upper_leg")], {"forward": 1}, 1.3, side)
        side_view = {"out": 1, "forward": 0.3}
        add(f"knee-flexion.{side}", leg, [twist_axis(limb("lower_leg"), "left", ranges["knee"]["flexion"])], [limb("lower_leg")], side_view, 1.1, side,
            {"bone": limb("lower_leg"), "toward": "back"})
        ankle = ranges["ankle"]
        add(f"ankle-dorsiflexion.{side}", leg, [swing(limb("foot"), "up", ankle["dorsiflexion"])], [limb("foot")], side_view, 0.6, side, {"bone": limb("foot"), "toward": "up"})
        add(f"ankle-plantarflexion.{side}", leg, [swing(limb("foot"), "down", ankle["plantarflexion"])], [limb("foot")], side_view, 0.6, side, {"bone": limb("foot"), "toward": "down"})
        add(f"toe-extension.{side}", leg, [swing(limb("toe"), "up", ranges["toe"]["extension"])], [limb("toe")], side_view, 0.6, side, {"bone": limb("toe"), "toward": "up"})

    def both(make):
        return [dict(step, side=side) for side in "LR" for step in make(side)]

    add("combo-arms-overhead", "combo", both(lambda s: [twist_axis(f"upper_arm.{s}", "right", 150), twist_axis(f"lower_arm.{s}", "right", 20)]), ["spine_02"], {"forward": 1, "left": 0.6}, 2.3)
    # Two hands on one hilt cannot be written as joint angles without the hands landing on each other: the candidate supplies the authored pose.
    add("combo-two-hand-chop", "combo", [swing("spine_01", "forward", 15), swing("spine_02", "forward", 15)], ["spine_02"], {"forward": 1, "left": 0.6}, 2.3,
        requires_pose="two_hand_chop", state={"grasp.R": 1.0, "grasp.L": 1.0})
    add("combo-deep-squat", "combo", [swing("spine_01", "forward", 10), swing("spine_02", "forward", 10)]
        + both(lambda s: [twist_axis(f"upper_leg.{s}", "right", 100), twist_axis(f"lower_leg.{s}", "left", 120), swing(f"foot.{s}", "up", 25)]), ["pelvis"], {"left": 1, "forward": 0.6}, 2.3)
    cast = [twist_axis("upper_arm.L", "right", 90), twist_axis("lower_arm.L", "right", 30), swing("hand.L", "dorsal", 30), swing("finger4.L_01", "radial", 15), swing("finger1.L_01", "ulnar", 15)]
    add("combo-cast-open-palm.L", "combo", [dict(step, side="L") for step in cast], ["hand.L"], {"forward": 1, "out": 0.6}, 1.2, "L")
    # Sword grasp with wrist motion: needs the candidate's authored FK grasp pose; a character without one fails as missing.
    for name, toward, view in (("flexion", "palmar", {"radial": 1}), ("extension", "dorsal", {"radial": 1}), ("radial", "radial", {"dorsal": 1}), ("ulnar", "ulnar", {"dorsal": 1})):
        add(f"combo-grasp-wrist-{name}.R", "combo", [swing("hand.R", toward, ranges["wrist"][name])], ["hand.R"], view, 0.4, "R", {"bone": "hand.R", "toward": toward},
            hand_extreme=False, requires_pose="grasp.R", state={"grasp.R": 1.0})

    return {
        "schema_version": 4, "id": f"{request['id']}-joint-range", "source": "request.support_envelope.joint_ranges_deg",
        "axes": {"forward": [0, -1, 0], "up": [0, 0, 1], "left": [1, 0, 0]},
        "hand_landmarks": {"hand": "hand.{side}", "finger_base": "finger{i}.{side}_01", "thumb_base": "thumb.{side}_01"},
        "levels": {"typical": 0.5, "extreme": 1.0},
        "limits": {
            "collapse_area_ratio": 0.05, "min_rest_triangle_area_m2": 1e-10,
            "hand_bone_prefixes": ["hand.", "finger", "thumb.", "wrist_transition."],
            "hand_edge_ratio": [0.25, 3.0], "deform_min_weight": 0.1, "deform_min_displacement_m": 1e-4,
            "excluded_meshes": ["SM_RO_sword"],
            **({"armor_meshes": request["support_envelope"]["armor_contact"]["meshes"], "armor_bones": request["support_envelope"]["armor_contact"]["bones"],
                "armor_depth_slack_m": request["support_envelope"]["armor_contact"]["slack_mm"] / 1000} if "armor_contact" in request["support_envelope"] else {}),
        },
        "render": {"tile_px": 384, "engine": "BLENDER_WORKBENCH", "shading": "studio, single gray 0.62, cavity on"},
        "deferred_combinations": ["仰臥睡姿：需要床面與睡眠clip，於 clip-set 評估"],
        "motions": motions,
    }


if __name__ == "__main__":
    source, target = sys.argv[1], sys.argv[2]
    with open(source, encoding="utf-8") as handle:
        contract = build(json.load(handle))
    if len(sys.argv) > 3:
        with open(sys.argv[3], encoding="utf-8") as handle:
            baseline = json.load(handle)
        contract["limits"]["ceilings"] = {
            row["id"]: {level: {"other_new_pairs": row["levels"][level]["other_new_pairs"], "max_other_edge_ratio": row["levels"][level]["other_edge_ratio"][1]} for level in ("typical", "extreme")}
            for row in baseline["results"] if row["status"] == "measured" and row["gate"]["deforms"]}
        contract["limits"]["rest_other_pairs_ceiling"] = baseline["rest_pairs"]["other"]
        contract["limits"]["ceiling_source"] = {
            "path": sys.argv[3].replace(chr(92), "/"), "subject_sha256": baseline["subject"]["sha256"],
            "rule": "Not an acceptance of the baseline's intersections or stretch: a ratchet so candidates cannot be worse than the baseline away from the hands. "
                    "Motions the baseline could not pose, or posed without deforming any skin, have no entry and get the general bound: zero new pairs and the hand guard's stretch limit."}
    with open(target, "x", encoding="utf-8", newline="\n") as handle:
        json.dump(contract, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print(len(contract["motions"]), "motions", "with ceilings" if "ceilings" in contract["limits"] else "calibration only")
