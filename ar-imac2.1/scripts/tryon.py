"""AR-iMac 2.1 try-on: the customer's three camera shots (left, front, right) in, three studio
portraits wearing the exact PID out. Mirrors the app flow; the product side now always carries
the temple view.

What changed from v2.0 (poc/scripts/studio.py):
  * Product references come from pid_refs.py by catalog label: front + three-quarter + TEMPLE.
    v2.0 sent one gallery image (front/three-quarter), so temples were invented.
  * Hard gate: build_call() raises if the temple view is not in the payload. No call goes out
    without it, whichever model or mode is used.
  * The prompt gives each image one named role and has a separate Temples paragraph that names
    the temple colour, material and length from the catalog specs.
  * Each output pose uses the matching customer shot as the pose reference, and the front shot
    as the identity reference.
  * --sheet mode for callers that can attach only one product image: sends sheet.png
    (front / three-quarter / temple stacked) instead of three files.

python3 ar-imac2.1/scripts/tryon.py --pid 208956 --front me_front.jpg --left me_left.jpg --right me_right.jpg
python3 ar-imac2.1/scripts/tryon.py --pid 208956 --front me_front.jpg            # poses described in text
    --models gpt_2_5_flare,nano_banana_pro   (default: gpt_2_5_flare)
    --poses front,left,right                 (default: all three)
    --sheet                                  one product image instead of three
    --facial-hair "beard and moustache"
    --dry-run                                write the exact payloads, call nothing (free)
    --score                                  re-score a finished run (no API calls)
Output: ar-imac2.1/out/<customer>_<pid>/ with manifest.json (payload roles, prompt, cost, scores)
and grid.jpg (references sent + outputs).
"""
import argparse
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pid_refs  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
SQ = {"width": 1024, "height": 1024}

# Pose words are from the camera's point of view, like the app's capture screens.
POSES = {
    "front": dict(text="facing the camera straight on, head level, eyes looking into the lens",
                  near_temple="both temple arms are seen end-on beside the head"),
    "left": dict(text="head and shoulders turned about 30 degrees to the camera's left",
                 near_temple="the temple arm on the side of the face nearest the camera is clearly visible "
                             "from the hinge back to the ear"),
    "right": dict(text="head and shoulders turned about 30 degrees to the camera's right",
                  near_temple="the temple arm on the side of the face nearest the camera is clearly visible "
                              "from the hinge back to the ear"),
}

MODELS = {
    "gpt_2_5_flare": ("GPT Image 2.5 Flare", "openai/gpt-image-2.5/flare/edit", "Image",
                      lambda p, u: dict(prompt=p, image_urls=u, image_size=SQ, quality="high", output_format="png"), 0.20),
    "nano_banana_pro": ("Nano Banana Pro", "fal-ai/nano-banana-pro/edit", "Image",
                        lambda p, u: dict(prompt=p, image_urls=u, aspect_ratio="1:1", resolution="2K", output_format="png"), 0.15),
    "seedream_5_pro": ("Seedream 5 Pro", "bytedance/seedream/v5/pro/edit", "Figure",
                       lambda p, u: dict(prompt=p, image_urls=u, image_size=SQ, output_format="png"), 0.072),
    "qwen": ("Qwen Image Edit 2511 (open)", "fal-ai/qwen-image-edit-2511", "Image",
             lambda p, u: dict(prompt=p, image_urls=u, image_size=SQ, output_format="png"), 0.03),
}


class TempleNotSent(RuntimeError):
    """Raised when a generation payload would go out without the temple reference."""


def roles_for(pose, have_pose_shot, sheet):
    """Ordered image roles for one call. Customer images first (identity in slot 1)."""
    roles = []
    if have_pose_shot and pose != "front":
        roles += ["customer_pose", "customer_front"]
    else:
        roles += ["customer_front"]
    roles += ["product_sheet"] if sheet else ["product_front", "product_three_quarter", "product_temple"]
    return roles


def prompt(refs, pose, roles, facial_hair, n="Image"):
    d, s = refs["description"], refs["specs"]
    idx = {r: i + 1 for i, r in enumerate(roles)}
    lines = []
    if "customer_pose" in idx:
        lines.append(f"{n} {idx['customer_pose']} is the customer photographed at the pose to reproduce. "
                     f"{n} {idx['customer_front']} is the same customer facing the camera: use it for the face.")
    else:
        lines.append(f"{n} {idx['customer_front']} is the identity source: a photo of a real customer.")
    if "product_sheet" in idx:
        k = idx["product_sheet"]
        lines.append(f"{n} {k} shows the product, {d['eyewear']}, in three views stacked top to bottom: "
                     "front, three-quarter, and a side view of the temple arm.")
        front_ref, temple_ref = f"the front view in {n} {k}", f"the side view at the bottom of {n} {k}"
    else:
        f, q, t = idx["product_front"], idx.get("product_three_quarter"), idx["product_temple"]
        three = f" {n} {q} is the same product at a three-quarter angle." if q else ""
        lines.append(f"{n} {f} is the product from the front: {d['eyewear']}.{three} "
                     f"{n} {t} is the same product from the side, showing the temple arm.")
        front_ref, temple_ref = f"{n} {f}", f"{n} {t}"

    who = f"{n} {idx.get('customer_front')}"
    temple_spec = d["temple"] + (f", about {s['temple_mm']} mm long" if s.get("temple_mm") else "")
    width = f" The frame is about {s['frame_width_mm']} mm wide." if s.get("frame_width_mm") else ""
    pose_line = (f"Reproduce the head angle of {n} {idx['customer_pose']}: {POSES[pose]['text']}."
                 if "customer_pose" in idx else f"Pose: {POSES[pose]['text']}.")

    return "\n\n".join([
        " ".join(lines),
        "Create a studio catalog portrait of this customer wearing exactly this eyewear.",
        f"Person: keep the facial features exactly the same as {who}: face shape, eyes, eyebrows, nose, lips, "
        f"skin tone, {facial_hair}, hairline and hairstyle. Someone who knows this person must recognise them "
        "immediately. Ignore the customer photos' background, clothing, lighting and any glasses worn there.",
        f"Frame front: the same shape, proportions, colour and finish, rim thickness and bridge as {front_ref}, "
        f"with {d['lens']}.{width}",
        f"Temples: copy the temple arms from {temple_ref} exactly: {temple_spec}. Keep the same thickness and "
        "profile, the same hinge and end-piece, the same tip shape, and every logo, emblem, print, groove or "
        "texture in the same place along the arm. Do not draw plain or generic temple arms. "
        f"In this shot {POSES[pose]['near_temple']}.",
        f"Shot: close-up head-and-shoulders portrait. {pose_line} Relaxed neutral expression, eyes looking into "
        "the lens, plain dark grey crew-neck T-shirt. Seamless pure white studio background. Soft, even, diffused "
        "front lighting. 85 mm lens at eye level, sharp focus on the eyes, the frame and the temple arm.",
        "Render it as an unretouched photograph of a real person, with natural skin texture.",
    ])


def build_call(refs, pose, files, facial_hair, model_key, sheet=False):
    """Return (endpoint, arguments, roles) for one generation. `files` maps role -> uploaded URL.
    This is the integration point for the app: it fails closed when the temple is missing."""
    label, ep, n, args, _ = MODELS[model_key]
    roles = roles_for(pose, "customer_pose" in files, sheet)
    if not sheet and "product_temple" not in files:
        raise TempleNotSent(f"PID {refs['pid']}: temple reference missing from the upload set")
    if sheet and "temple" not in refs.get("sheet_order", []):
        raise TempleNotSent(f"PID {refs['pid']}: product sheet was built without the temple view")
    roles = [r for r in roles if r in files]
    if not any(r in roles for r in ("product_temple", "product_sheet")):
        raise TempleNotSent(f"PID {refs['pid']}: no temple reference in the payload for pose {pose}")
    return ep, args(prompt(refs, pose, roles, facial_hair, n), [files[r] for r in roles]), roles


def head(path, out):
    """Head crop + upscale (prep.py). Strongly turned faces can defeat the detector: then use the photo."""
    try:
        import prep
        prep.head_crop(path, out)
        return out
    except Exception:
        return pathlib.Path(path)


def run(a):
    import falx
    refs = pid_refs.load(a.pid)
    cid = a.customer or pathlib.Path(a.front).stem
    out = HERE / "out" / f"{cid}_{a.pid}"
    out.mkdir(parents=True, exist_ok=True)
    pack = pid_refs.PIDS / a.pid

    local = {"customer_front": head(a.front, out / "in_front.jpg")}
    shots = {"left": a.left, "right": a.right}
    for pose, p in shots.items():
        if p:
            local[f"customer_pose_{pose}"] = head(p, out / f"in_{pose}.jpg")
    if a.sheet:
        local["product_sheet"] = pack / "sheet.png"
    else:
        for view in ("front", "three_quarter", "temple"):
            if view in refs["views"]:
                local[f"product_{view}"] = pack / refs["views"][view]["file"]

    up = (lambda p: f"local://{p}") if a.dry_run else falx.upload
    urls = {k: up(v) for k, v in local.items()}
    jobs = []
    for pose in a.poses:
        files = {k: v for k, v in urls.items() if not k.startswith("customer_pose_")}
        if urls.get(f"customer_pose_{pose}"):
            files["customer_pose"] = urls[f"customer_pose_{pose}"]
        for mk in a.models:
            ep, args, roles = build_call(refs, pose, files, a.facial_hair, mk, a.sheet)
            jobs.append((pose, mk, ep, args, roles))

    def go(job):
        pose, mk, ep, args, roles = job
        name = f"{pose}_{mk}"
        rec = dict(variant=name, model=MODELS[mk][0], pose=pose, endpoint=ep, roles=roles,
                   prompt=args["prompt"], est_cost=0 if a.dry_run else MODELS[mk][4])
        if a.dry_run:
            return rec
        t0 = time.time()
        try:
            res = falx.run(ep, args)
            falx.download(res["images"][0]["url"], out / f"{name}.png")
            rec.update(file=f"{name}.png", seconds=round(time.time() - t0, 1))
        except Exception as e:
            rec.update(error=str(e)[:300], est_cost=0)
        return rec

    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(go, jobs))
    m = dict(version="ar-imac2.1", cid=cid, pid=a.pid, product=refs["name"], mode="sheet" if a.sheet else "multi",
             inputs={k: str(v) for k, v in local.items()}, refs=refs, results=results,
             total_est_cost=round(sum(r["est_cost"] for r in results), 3))
    (out / "manifest.json").write_text(json.dumps(m, indent=2))
    if not a.dry_run:
        score(out)
        import grid
        grid.make(out)
    return out


def score(out):
    """Identity (ArcFace + SFace vs the customer's front shot). Needs get_models.sh."""
    try:
        import qc
    except Exception as e:
        print("scoring skipped (run ar-imac2.1/get_models.sh):", e)
        return
    m = json.loads((out / "manifest.json").read_text())
    cust = qc.feats(m["inputs"]["customer_front"])
    for r in m["results"]:
        if "file" in r and cust is not None:
            o = qc.feats(out / r["file"])
            r["qc"] = None if o is None else dict(id_arc=round(float(o["arc"] @ cust["arc"]), 3),
                                                  id_sf=round(float(o["sf"] @ cust["sf"]), 3))
    (out / "manifest.json").write_text(json.dumps(m, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid")
    ap.add_argument("--front", help="customer photo facing the camera (identity)")
    ap.add_argument("--left", help="customer photo turned to the camera's left (optional)")
    ap.add_argument("--right", help="customer photo turned to the camera's right (optional)")
    ap.add_argument("--customer", help="id for the output folder (default: front photo's file name)")
    ap.add_argument("--models", default="gpt_2_5_flare")
    ap.add_argument("--poses", default="front,left,right")
    ap.add_argument("--facial-hair", default="facial hair")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--score", metavar="RUN_DIR")
    a = ap.parse_args()
    if a.score:
        score(pathlib.Path(a.score))
        import grid
        print(grid.make(pathlib.Path(a.score)))
        return
    if not (a.pid and a.front):
        ap.error("--pid and --front are required")
    a.models, a.poses = a.models.split(","), a.poses.split(",")
    for p in a.poses:
        if p not in POSES:
            ap.error(f"unknown pose {p}; use {', '.join(POSES)}")
    out = run(a)
    m = json.loads((out / "manifest.json").read_text())
    print(f"{m['cid']} x {m['pid']} ({m['mode']})  est ${m['total_est_cost']}  -> {out}")
    for r in m["results"]:
        print(f"  {r['variant']:24} roles={','.join(r['roles'])}  {r.get('seconds', '')}s {r.get('qc') or r.get('error') or ''}")


if __name__ == "__main__":
    main()
