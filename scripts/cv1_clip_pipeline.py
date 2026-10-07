"""Closed-loop preparation for one character V1 clip attempt (runs Blender and the GLB tools in order).

Usage: python -B scripts/cv1_clip_pipeline.py export <clip> <attempt> [--every 6] [--half 0,30] [--label b18]
       python -B scripts/cv1_clip_pipeline.py readback <clip> <attempt> [--label b18]
export: scripts/cv1_export_clip.py (runtime- and baked-owner GLBs plus the Blender reference), strip the helper bone
channels from the runtime-owner GLB, restore the exact source weights in both, and write runtime-manifest.json for
tools/runtime-qa/three/candidate.html. readback: fresh-Blender readback of the exact-weight baked GLB at the frozen
5 um tolerance, baked integer-frame samples only. Folders follow the clip layout:
  assets/processed/ro-swordsman-character-v1/v001/clips/<clip>/<attempt>/export
  runs/qa/ro-swordsman-character-v1/v001/clips/<clip>/<attempt>-closed-loop
(--label adds a suffix to both folders, e.g. to re-verify an attempt on a newer foundation.) Existing outputs are refused by the underlying tools.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
FOUNDATION = "assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/ro_character_v001_b20-coatlie3.blend"
RULES = "assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/corrective-rules.json"
SNAPSHOT = "runs/qa/ro-swordsman-character-v1/v001/b20-coatlie3/weights-snapshot.json"
REGISTRY = "runs/qa/ro-swordsman-character-v1/v001/clips/interaction-registry.json"
GATE_MANIFEST = "runs/qa/ro-swordsman-character-v1/v001/b05-twist/closed-loop/runtime-manifest.json"
HELPERS = "wrist_transition.R_twist,wrist_transition.L_twist"


def info(path):
    path = ROOT / path
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def run(command, log=None):
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if log:
        (ROOT / log).write_text(done.stdout + done.stderr, encoding="utf-8", newline="\n")
    lines = [line for line in (done.stdout + done.stderr).splitlines() if line.startswith("CV1_") or "Error" in line or "REFUSE" in line]
    if done.returncode != 0:
        raise SystemExit(f"FAILED {command[0]} {done.returncode}: {lines[-3:]}")
    return lines


def main():
    command, clip, attempt = sys.argv[1], sys.argv[2], sys.argv[3]
    options = dict(zip(sys.argv[4::2], sys.argv[5::2]))
    assets = f"assets/processed/ro-swordsman-character-v1/v001/clips/{clip}"
    label = options.get("--label", "")
    suffix = f"-{label}" if label else ""
    qa = f"runs/qa/ro-swordsman-character-v1/v001/clips/{clip}/{attempt}-closed-loop{suffix}"
    export = f"{assets}/{attempt}/export{suffix}"
    tag = f"{clip.lower()}_{attempt}{suffix.replace('-', '_')}"
    if command == "export":
        lines = run([BLENDER, "-b", "--factory-startup", "--disable-autoexec", FOUNDATION, "--python", "scripts/cv1_export_clip.py", "--",
                     "--clip-blend", f"{assets}/{attempt}/{clip}.blend", "--interaction", f"{assets}/interaction.json", "--registry", REGISTRY,
                     "--rules", RULES, "--tag", tag, "--asset-dir", export, "--qa-dir", qa,
                     "--every", options.get("--every", "6"), "--half", options.get("--half", "")], log=f"{qa}-export.log")
        print(*lines, sep="\n")
        # A clip with sword sockets also loses its sword channel: the runtime places the sword from the socket events.
        socketed = "sword_socket" in json.loads((ROOT / assets / "interaction.json").read_text(encoding="utf-8"))
        print(*run([sys.executable, "-B", "scripts/cv1_strip_bone_channels.py", f"{export}/{tag}_runtime_owner.glb", f"{export}/{tag}_runtime_owner_stripped.glb",
                    HELPERS + (",sword" if socketed else ""), f"{qa}/strip-runtime_owner.json"]), sep="\n")
        for kind in ("runtime_owner_stripped", "baked_owner"):
            run([sys.executable, "-B", "scripts/cv1_restore_glb_weights.py", f"{export}/{tag}_{kind}.glb", SNAPSHOT, f"{export}/{tag}_{kind}_exact_weights.glb",
                 f"{qa}/restore-{kind}.json"])
        manifest = json.loads((ROOT / GATE_MANIFEST).read_text(encoding="utf-8"))
        reference = json.loads((ROOT / qa / "blender-reference.json").read_text(encoding="utf-8"))
        sampled = sorted(b["frame"] for b in reference["blocks"] if b["label"].startswith("all/frame-") and b.get("baked_sample", True))
        manifest.update({"reference": info(f"{qa}/blender-reference.json"), "reference_binary": info(f"{qa}/blender-reference.f64.bin"), "rules": info(RULES),
                         "glb": {"runtime_owner": info(f"{export}/{tag}_runtime_owner_stripped_exact_weights.glb"), "baked_owner": info(f"{export}/{tag}_baked_owner_exact_weights.glb")},
                         "capture": [[sampled[0], "whole"], [sampled[0], "hands"], [sampled[len(sampled) // 2], "whole"]],
                         "sword_socket": reference.get("sword_socket"),
                         "note": f"Clip closed loop for {clip} {attempt} (scripts/cv1_clip_pipeline.py). Exact-weight GLBs; helper channels"
                                 + (" and the sword channel" if socketed else "") + " stripped from the runtime-owner GLB."})
        (ROOT / qa / "runtime-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"MANIFEST {qa}/runtime-manifest.json")
    elif command == "readback":
        print(*run([BLENDER, "-b", "--factory-startup", "--disable-autoexec", "--python", "scripts/cv1_verify_glb_roundtrip.py", "--",
                    "--glb", f"{export}/{tag}_baked_owner_exact_weights.glb", "--reference", f"{qa}/blender-reference.json", "--prefix", "all",
                    "--baked-samples-only", "--time-rule", "frame_over_fps", "--tolerance", "5e-6", "--out", f"{qa}/roundtrip-{tag}_baked_owner_exact_weights.json"],
                   log=f"{qa}/roundtrip.log")[-1:], sep="\n")
    else:
        raise SystemExit("usage: export|readback <clip> <attempt>")


if __name__ == "__main__":
    main()
