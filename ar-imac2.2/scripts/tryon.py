"""AR-iMac 2.2 try-on: AR-iMac 2.1 with switchable prompt packs.

The run is the 2.1 run: the same reference packs, upload order, temple gate (build_call /
TempleNotSent) and scoring, imported from ar-imac2.1/scripts. Only two things come from the pack:
the style paragraphs of the prompt and the output size.

python3 ar-imac2.2/scripts/tryon.py --pid 208956 --front f.jpg --left l.jpg --right r.jpg               # PP2 (default)
python3 ar-imac2.2/scripts/tryon.py --pid 208956 --front f.jpg --left l.jpg --right r.jpg --pack PP1     # revert: = 2.1
python3 ar-imac2.2/scripts/tryon.py --pid 208956 --front f.jpg --left l.jpg --right r.jpg --pack PP1,PP2 # A/B + compare.jpg
    --models, --poses, --sheet, --facial-hair, --customer, --dry-run work as in 2.1
Output: ar-imac2.2/out/<customer>_<pid>_<PACK>/ (manifest.json, grid.jpg), plus
        ar-imac2.2/out/<customer>_<pid>_compare.jpg when more than one pack is run.
"""
import argparse
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import packs  # noqa: E402  (also puts ar-imac2.1/scripts on the path)

T21 = packs.T21
pid_refs = T21.pid_refs
HERE = pathlib.Path(__file__).resolve().parents[1]
RATIOS = {"1:1": 1.0, "4:5": 0.8, "3:4": 0.75, "2:3": 2 / 3, "9:16": 9 / 16}


def sized(model_key, args, size):
    """Apply the pack's output size in each model's own parameter."""
    w, h = size
    if model_key == "nano_banana_pro":
        args["aspect_ratio"] = min(RATIOS, key=lambda k: abs(RATIOS[k] - w / h))
    else:
        args["image_size"] = {"width": w, "height": h}
    return args


def est_cost(model_key, size):
    """2.1's per-image estimate, scaled by pixels against 1024x1024 (Nano Banana Pro is priced per image)."""
    base = T21.MODELS[model_key][4]
    return round(base if model_key == "nano_banana_pro" else base * size[0] * size[1] / 1024 ** 2, 3)


def build_call(pack, refs, pose, files, facial_hair, model_key, sheet=False):
    ep, args, roles = T21.build_call(refs, pose, files, facial_hair, model_key, sheet)  # temple gate
    args["prompt"] = packs.tryon_prompt(pack, refs, pose, roles, facial_hair, T21.MODELS[model_key][2])
    return ep, sized(model_key, args, pack["tryon"]["size"]), roles


def run(a, pack):
    import falx
    refs = pid_refs.load(a.pid)
    cid = a.customer or pathlib.Path(a.front).stem
    out = HERE / "out" / f"{cid}_{a.pid}_{pack['code']}"
    out.mkdir(parents=True, exist_ok=True)
    pack_dir = pid_refs.PIDS / a.pid

    local = {"customer_front": T21.head(a.front, out / "in_front.jpg")}
    for pose, p in {"left": a.left, "right": a.right}.items():
        if p:
            local[f"customer_pose_{pose}"] = T21.head(p, out / f"in_{pose}.jpg")
    if a.sheet:
        local["product_sheet"] = pack_dir / "sheet.png"
    else:
        for view in ("front", "three_quarter", "temple"):
            if view in refs["views"]:
                local[f"product_{view}"] = pack_dir / refs["views"][view]["file"]

    up = (lambda p: f"local://{p}") if a.dry_run else falx.upload
    urls = {k: up(v) for k, v in local.items()}
    jobs = []
    for pose in a.poses:
        files = {k: v for k, v in urls.items() if not k.startswith("customer_pose_")}
        if urls.get(f"customer_pose_{pose}"):
            files["customer_pose"] = urls[f"customer_pose_{pose}"]
        for mk in a.models:
            jobs.append((pose, mk, *build_call(pack, refs, pose, files, a.facial_hair, mk, a.sheet)))

    def go(job):
        pose, mk, ep, args, roles = job
        name = f"{pose}_{mk}_{pack['code']}"
        rec = dict(variant=name, model=f"{T21.MODELS[mk][0]} · {pack['code']}", pose=pose, endpoint=ep, roles=roles,
                   pack=pack["label"], size=pack["tryon"]["size"], prompt=args["prompt"],
                   est_cost=0 if a.dry_run else est_cost(mk, pack["tryon"]["size"]))
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
    m = dict(version="ar-imac2.2", pack=pack["label"], pack_status=pack["status"], cid=cid, pid=a.pid,
             product=refs["name"], mode="sheet" if a.sheet else "multi",
             inputs={k: str(v) for k, v in local.items()}, refs=refs, results=results,
             total_est_cost=round(sum(r["est_cost"] for r in results), 3))
    (out / "manifest.json").write_text(json.dumps(m, indent=2))
    if not a.dry_run:
        T21.score(out)
        import grid
        grid.make(out)
    return out


def compare(runs, dest):
    """Stack each pack's grid.jpg, labelled with its code word, into one sheet."""
    from PIL import Image, ImageDraw
    import grid
    font = grid._font(26, True)
    grids = [(json.loads((r / "manifest.json").read_text())["pack"], Image.open(r / "grid.jpg")) for r in runs
             if (r / "grid.jpg").is_file()]
    if len(grids) < 2:
        return None
    w, bar = max(g.width for _, g in grids), 56
    sheet = Image.new("RGB", (w, sum(g.height + bar for _, g in grids)), "white")
    d, y = ImageDraw.Draw(sheet), 0
    for label, g in grids:
        d.rectangle((0, y, w, y + bar), fill="#111")
        d.text((16, y + 14), f"Prompt pack {label}", fill="white", font=font)
        sheet.paste(g, (0, y + bar))
        y += g.height + bar
    sheet.save(dest, quality=86)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", required=True)
    ap.add_argument("--front", required=True, help="customer photo facing the camera (identity)")
    ap.add_argument("--left")
    ap.add_argument("--right")
    ap.add_argument("--customer")
    ap.add_argument("--pack", default="PP2", help="prompt pack code word(s): PP1, PP2 or PP1,PP2 (default PP2)")
    ap.add_argument("--models", default="gpt_2_5_flare")
    ap.add_argument("--poses", default="front,left,right")
    ap.add_argument("--facial-hair", default="facial hair")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    a.models, a.poses = a.models.split(","), a.poses.split(",")
    for p in a.poses:
        if p not in T21.POSES:
            ap.error(f"unknown pose {p}; use {', '.join(T21.POSES)}")
    runs = []
    for code in a.pack.split(","):
        pack = packs.load(code)
        out = run(a, pack)
        runs.append(out)
        m = json.loads((out / "manifest.json").read_text())
        print(f"{m['cid']} x {m['pid']}  pack {m['pack']}  ({m['mode']})  est ${m['total_est_cost']}  -> {out}")
        for r in m["results"]:
            print(f"  {r['variant']:30} {r['size'][0]}x{r['size'][1]}  {r.get('seconds', '')}s {r.get('qc') or r.get('error') or ''}")
    if len(runs) > 1 and not a.dry_run:
        print("compare:", compare(runs, HERE / "out" / f"{runs[0].name.rsplit('_', 1)[0]}_compare.jpg"))


if __name__ == "__main__":
    main()
