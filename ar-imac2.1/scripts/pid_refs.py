"""PID reference pack: pick the product shots by their catalog label, never by gallery position.

v2.0 sent one product photo (gallery image 0) to the image model. That image is a front or
three-quarter view, so the model never saw the temple arm and invented a plain one: logos,
grooves, hinge blocks and tip shapes were lost. v2.1 builds a pack of labelled views and
refuses to generate without the side (temple) view.

The Lenskart product API labels every gallery image in `imageUrlsDetail`:
    Image_Front     straight-on front view               -> required
    Image_Temple    side profile, shows the temple arm   -> required (the fix)
    Image_Left      three-quarter view                   -> used when present
    model_*, ''     worn-by-model / lifestyle shots      -> never used as product reference

Output in ar-imac2.1/pids/<pid>/:
    front.png  temple.png  three_quarter.png   tight-cropped, square, 1024 px
    sheet.png        the three views stacked in one image, for callers that can send only
                     one product image (front on top, three-quarter, temple at the bottom)
    refs.json        source URLs, labels, specs (temple colour/material/length) and the
                     auto-built eyewear description

python3 ar-imac2.1/scripts/pid_refs.py 208956 244418
python3 ar-imac2.1/scripts/pid_refs.py 208956 --json      # print refs.json
"""
import io
import json
import pathlib
import sys
import urllib.error
import urllib.request

import truststore

truststore.inject_into_ssl()

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
PIDS = HERE / "pids"
API = "https://api-gateway.juno.lenskart.com/v2/products/product/{}"
SIZE = 1024

# view -> catalog labels that count as that view, in order of preference
VIEWS = {
    "front": ("image_front",),
    "three_quarter": ("image_left",),
    "temple": ("image_temple",),
}
REQUIRED = ("front", "temple")


class MissingReference(RuntimeError):
    """A required product view (front or temple) is not in the PID's catalog gallery."""


def get(url):
    req = urllib.request.Request(url, headers={"x-api-client": "desktop", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def pick_views(detail):
    """Map each view to the first gallery image whose label matches. Labels look like
    'Image_Left', 'Image_Left New', 'model_bento'; compare on the leading word pair."""
    found = {}
    for item in detail or []:
        label = (item.get("label") or "").strip().lower()
        for view, wanted in VIEWS.items():
            if view not in found and any(label.startswith(w) for w in wanted):
                found[view] = dict(url=item["url"], label=item.get("label"))
    return found


def specs(data):
    items = {it.get("name_en") or it.get("name"): (it.get("value_en") or it.get("value") or "").strip()
             for group in data.get("specifications", []) for it in group.get("items", [])}
    dims = items.get("Frame Dimensions", "")
    parts = [p for p in dims.replace(" ", "").split("-") if p.isdigit()]
    return dict(
        product_type=items.get("Product Type") or data.get("type", ""),
        brand=data.get("brandName_en") or data.get("brandName", ""),
        model=items.get("Model No.", ""),
        frame_colour=items.get("Frame colour", ""),
        frame_type=items.get("Frame Type", ""),
        frame_shape=items.get("Frame Shape", ""),
        frame_material=items.get("Frame Material") or items.get("Material", ""),
        frame_width_mm=items.get("Frame Width", "").replace("mm", "").strip(),
        lens_mm=parts[0] if len(parts) == 3 else "",
        bridge_mm=parts[1] if len(parts) == 3 else "",
        temple_mm=parts[2] if len(parts) == 3 else "",
        temple_colour=items.get("Temple Colour", ""),
        temple_material=items.get("Temple Material", ""),
        lens_colour=items.get("Glass Color", ""),
        lens_tech=items.get("Lens Technology", ""),
    )


def describe(s, name):
    sun = "sunglass" in (s["product_type"] or name).lower()
    bits = [s["frame_colour"], s["frame_type"].lower(), s["frame_shape"].lower(), s["brand"],
            "sunglasses" if sun else "eyeglasses"]
    eyewear = " ".join(b for b in bits if b) or name
    temple = " ".join(b for b in (s["temple_colour"], s["temple_material"]) if b)
    return dict(
        eyewear=eyewear,
        temple=f"{temple} temple arms" if temple else "temple arms",
        sunglasses=sun,
        lens=(f"{s['lens_colour'].lower()} tinted lenses" if sun and s["lens_colour"] else
              "tinted lenses" if sun else "clear lenses"),
    )


def tight_crop(raw, pad=0.06):
    """Crop to the product (pixels that differ from the corner background) with a small pad.
    Makes the frame fill the reference so small temple logos survive the model's downscale."""
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    h, w = a.shape[:2]
    k = max(4, min(h, w) // 40)
    corners = np.concatenate([a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3),
                              a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3)])
    bg = tuple(int(c) for c in np.median(corners, axis=0))
    ys, xs = np.nonzero(np.abs(a - np.array(bg)).max(axis=2) > 14)
    if len(xs) > 50:
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        p = int(pad * max(x1 - x0, y1 - y0))
        im = im.crop((max(0, x0 - p), max(0, y0 - p), min(w, x1 + p), min(h, y1 + p)))
    return im, bg


def fit(im, bg, w, h):
    im = im.copy()
    s = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    c = Image.new("RGB", (w, h), bg)
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def tight_square(raw, size=SIZE):
    return fit(*tight_crop(raw), size, size)


def build(pid, force=False):
    """Fetch the PID, pick labelled views, write the pack. Raises MissingReference when the
    front or temple view is absent (pass force=True only to inspect a broken PID)."""
    out = PIDS / str(pid)
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(get(API.format(pid)))["result"]
    views = pick_views(data.get("imageUrlsDetail"))
    missing = [v for v in REQUIRED if v not in views]
    if missing and not force:
        raise MissingReference(
            f"PID {pid}: no {', '.join(missing)} view in the catalog gallery "
            f"(labels seen: {[i.get('label') for i in data.get('imageUrlsDetail') or []]}). "
            "Generation is blocked: without the temple view the model invents the temple arms.")

    raws = {v: get(meta["url"]) for v, meta in views.items()}
    for v, raw in raws.items():
        tight_square(raw).save(out / f"{v}.png")
        views[v]["file"] = f"{v}.png"

    order = [v for v in ("front", "three_quarter", "temple") if v in raws]
    sheet = Image.new("RGB", (SIZE, SIZE), "white")
    for i, v in enumerate(order):
        sheet.paste(fit(*tight_crop(raws[v]), SIZE, SIZE // len(order)), (0, i * SIZE // len(order)))
    sheet.save(out / "sheet.png")

    s = specs(data)
    name = data.get("fullName_en") or data.get("fullName", "")
    refs = dict(pid=str(pid), name=name, views=views, sheet="sheet.png", sheet_order=order,
                missing=missing, specs=s, description=describe(s, name))
    (out / "refs.json").write_text(json.dumps(refs, indent=2))
    return refs


def load(pid):
    """Read a built pack; build it if absent."""
    f = PIDS / str(pid) / "refs.json"
    return json.loads(f.read_text()) if f.exists() else build(pid)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    bad = 0
    for pid in args:
        try:
            r = build(pid, force="--force" in sys.argv)
        except (MissingReference, urllib.error.URLError) as e:
            print("BLOCKED", pid, e)
            bad += 1
            continue
        if "--json" in sys.argv:
            print(json.dumps(r, indent=2))
        else:
            print(pid, "views:", {v: m["label"] for v, m in r["views"].items()},
                  "| temple:", r["description"]["temple"], f"{r['specs']['temple_mm']} mm")
    sys.exit(1 if bad else 0)
