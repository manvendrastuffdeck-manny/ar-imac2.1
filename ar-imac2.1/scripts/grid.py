"""Contact sheet for one tryon.py run: top row = every reference that was sent (the temple view
included, so a reviewer can check it against the output), then one row per model, poses left/front/right.

python3 ar-imac2.1/scripts/grid.py ar-imac2.1/out/<customer>_<pid>
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 340, 400


def _font(size, bold=False):
    for path in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, size, index=1 if bold and path.endswith(".ttc") else 0)
        except OSError:
            continue
    return ImageFont.load_default()


def make(run):
    run = pathlib.Path(run)
    m = json.loads((run / "manifest.json").read_text())
    bold, font = _font(19, True), _font(16)
    refs = list(m["inputs"].items())
    models = list(dict.fromkeys(r["model"] for r in m["results"]))
    poses = [p for p in ("left", "front", "right") if any(r["pose"] == p for r in m["results"])]
    by = {(r["model"], r["pose"]): r for r in m["results"] if "file" in r}
    cols = max(len(refs), len(poses))
    s = Image.new("RGB", (cols * W, (1 + len(models)) * H), "white")
    d = ImageDraw.Draw(s)

    def tile(f, x, y, a, b, colour):
        im = Image.open(f).convert("RGB")
        im.thumbnail((W - 8, H - 64))
        s.paste(im, (x + (W - im.width) // 2, y + 58))
        d.text((x + 5, y + 6), a, fill=colour, font=bold)
        d.text((x + 5, y + 32), b, fill="black", font=font)

    for i, (role, f) in enumerate(refs):
        tile(f, i * W, 0, "SENT " + role.replace("_", " "), f"PID {m['pid']}" if role.startswith("product") else m["cid"], "red")
    for row, model in enumerate(models, start=1):
        for c, pose in enumerate(poses):
            r = by.get((model, pose))
            if r:
                q = r.get("qc") or {}
                tile(run / r["file"], c * W, row * H, model, f"{pose} · id {q.get('id_arc')} / sf {q.get('id_sf')}", "#0b57d0")
    s.save(run / "grid.jpg", quality=86)
    return run / "grid.jpg"


if __name__ == "__main__":
    for run in sys.argv[1:]:
        print(make(run))
