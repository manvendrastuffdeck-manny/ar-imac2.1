"""Prompt packs for AR-iMac 2.2: swap the look of the pictures without touching the wiring.

A pack changes only the style paragraphs (the task line, the Shot paragraph, the render paragraph,
the Style theme strings) and the output size. These paragraphs are LOCKED and always come from the
AR-iMac 2.1 code unchanged, whichever pack is chosen: the image roles, Person (identity), Frame
front and Temples. A pack can therefore never undo the temple fix.

Code words:  PP1 = PP1-STUDIO (the current wording; revert to this)   PP2 = PP2-PHONE (smartphone look)

python3 ar-imac2.2/scripts/packs.py list
python3 ar-imac2.2/scripts/packs.py show PP2 --pid 208956 --pose left    # the full Try On prompt
python3 ar-imac2.2/scripts/packs.py export PP2      # writes packs/PP2-PHONE.app.md for the LK2.0 app
python3 ar-imac2.2/scripts/packs.py check           # PP1 == 2.1 word for word; every pack fills cleanly
"""
import argparse
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
ROOT = HERE.parent
V21 = ROOT / "ar-imac2.1" / "scripts"
PACKS = HERE / "packs"
LOCKED = "roles, Person, Frame front and Temples paragraphs (from AR-iMac 2.1, never changed by a pack)"


def _load_v21():
    sys.path.insert(0, str(V21))
    spec = importlib.util.spec_from_file_location("tryon21", V21 / "tryon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T21 = _load_v21()


def list_packs():
    return {json.loads(p.read_text())["code"]: p for p in sorted(PACKS.glob("PP*.json"))}


def load(code):
    """'PP2', 'pp2' and 'PP2-PHONE' all load the same pack."""
    key = code.strip().upper().split("-")[0]
    packs = list_packs()
    if key not in packs:
        raise SystemExit(f"unknown prompt pack {code!r}; have {', '.join(packs)}")
    pack = json.loads(packs[key].read_text())
    pack["label"] = f"{pack['code']}-{pack['name']}"
    return pack


def _fill(text, pack, **vals):
    return text.format(phone_look=pack.get("phone_look", ""), **vals)


def pose_line(pose, roles, n="Image"):
    idx = {r: i + 1 for i, r in enumerate(roles)}
    text = T21.POSES[pose]["text"]
    if "customer_pose" in idx:
        return f"Reproduce the head angle of {n} {idx['customer_pose']}: {text}."
    return f"Pose: {text}."


def tryon_prompt(pack, refs, pose, roles, facial_hair, n="Image"):
    """The 2.1 prompt with only the task, Shot and render paragraphs swapped for the pack's."""
    base = T21.prompt(refs, pose, roles, facial_hair, n).split("\n\n")
    if len(base) != 7:
        raise RuntimeError("AR-iMac 2.1 prompt layout changed; update packs.tryon_prompt")
    t, pl = pack["tryon"], pose_line(pose, roles, n)
    return "\n\n".join([base[0], _fill(t["task"], pack), base[2], base[3], base[4],
                        _fill(t["shot"], pack, pose_line=pl), _fill(t["render"], pack)])


def style_strings(pack, theme, custom=""):
    """The filled Style paragraphs for one theme, as the app would insert them."""
    s, th = pack["style"], pack["style"]["themes"][theme]
    return dict(
        task=_fill(s["scene"]["task"], pack, scene=th["scene"], custom=custom),
        pose=th["pose"], outfit=th["outfit"],
        shot=_fill(s["scene"]["shot"], pack, light=th["light"]),
        scene_render=_fill(s["scene"]["render"], pack),
        look_render=_fill(s["look"]["render"], pack),
    )


def check():
    """Fails loudly if PP1 is no longer 2.1 word for word, or if any pack has a broken placeholder."""
    p1, n_ok = load("PP1"), 0
    pid_dirs = [d for d in (ROOT / "ar-imac2.1" / "pids").glob("*") if (d / "refs.json").is_file()]
    if not pid_dirs:
        print("check: no reference packs in ar-imac2.1/pids/ (run ar-imac2.1/scripts/pid_refs.py <pid>); skipped the 2.1 comparison")
    for d in pid_dirs:
        refs = json.loads((d / "refs.json").read_text())
        for pose in T21.POSES:
            for have_shot in (True, False):
                for sheet in (False, True):
                    roles = T21.roles_for(pose, have_shot, sheet)
                    for n in ("Image", "Figure"):
                        want = T21.prompt(refs, pose, roles, "beard and moustache", n)
                        got = tryon_prompt(p1, refs, pose, roles, "beard and moustache", n)
                        assert got == want, f"PP1 differs from AR-iMac 2.1 for {d.name} {pose} shot={have_shot} sheet={sheet}"
                        for code in list_packs():
                            other = tryon_prompt(load(code), refs, pose, roles, "beard and moustache", n).split("\n\n")
                            assert other[0] == want.split("\n\n")[0] and other[2:5] == want.split("\n\n")[2:5], \
                                f"{code} changed a locked paragraph"
                        n_ok += 1
    for code in list_packs():
        pack = load(code)
        for theme in pack["style"]["themes"]:
            for v in style_strings(pack, theme, custom=" X.").values():
                assert "{" not in v and "}" not in v, f"{code} {theme}: unfilled placeholder in {v[:60]}"
        assert set(pack["style"]["themes"]) == set(p1["style"]["themes"]), f"{code}: theme list differs from PP1"
    print(f"check ok: PP1 matches AR-iMac 2.1 in {n_ok} prompt layouts; locked paragraphs unchanged in "
          f"{', '.join(list_packs())}; all Style themes fill cleanly")


def export(code):
    """Markdown hand-off for the LK2.0 app: which strings to swap, old next to new. No wiring change."""
    new, old = load(code), load("PP1")
    L = [f"# Prompt pack {new['label']} for the LK2.0 app", "",
         f"**What it is:** {new['summary']}", "",
         "**What to change:** strings and the output size only. Do not change the call order, the images sent, "
         "StyleBlend or the card layout. Every line to replace is listed below with the current (PP1) text next to "
         "the new text, so the change can be reverted by putting the PP1 text back.", "",
         f"**Leave as they are:** the {LOCKED}, the `Pose:` sentence that follows each theme's pose "
         "(\"The head is turned no more than 20 degrees…\"), the `Outfit:` line, and the Step B paragraphs about the "
         "frame front, temples and lighting the eyewear.", "",
         "**Tag every picture made with this pack** with the code word "
         f"`{new['label']}` (for example in the cache folder name or the `*.prompt.txt` file), so we can compare "
         "packs from screenshots.", "",
         "Line numbers come from the LK2.0 walkthrough of 18 Nov 2026.", ""]

    def row(title, where, a, b):
        L.extend([f"### {title}", f"*Where:* {where}", "", "**PP1 (now):**", "```", a, "```",
                  f"**{new['label']}:**", "```", b, "```", ""])

    L.append("## 1. Output size")
    row("Style picture size", "`StyleModels.swift:179`, `image_size`",
        "{}x{}".format(*old["style"]["size"]), "{}x{}".format(*new["style"]["size"]))
    row("Try On picture size", "`TryOn` request, `image_size` (the app uses 1024x1280 now; the 2.1 repo uses 1024x1024)",
        "1024x1280 (app) / 1024x1024 (repo)", "{}x{}".format(*new["tryon"]["size"]))
    L.append("## 2. Style, step A (`StylePrompt.scene`, `StyleModels.swift:184-200`)")
    for k, title in (("task", "Opening line"), ("shot", "Shot paragraph (`StyleModels.swift:197`)"), ("render", "Last paragraph")):
        row(title, "StylePrompt.scene", old["style"]["scene"][k], new["style"]["scene"][k])
    L.append("`{scene}`, `{custom}` and `{light}` are the same fields the app fills now.\n")
    if new.get("phone_look"):
        L.extend(["`{phone_look}` is this text, word for word:", "```", new["phone_look"], "```", ""])
    L.append("## 3. Style, step B (`StylePrompt.look`, `StyleModels.swift:204-220`)")
    row("Last paragraph", "StylePrompt.look", old["style"]["look"]["render"], new["style"]["look"]["render"])
    L.append("## 4. Theme strings (`StyleModels.swift:32-82`)\n")
    for theme, th in new["style"]["themes"].items():
        L.append(f"### {theme}")
        for f in ("scene", "pose", "outfit", "light"):
            was = old["style"]["themes"][theme][f]
            L.append(f"- **{f}:** {th[f]}" + ("" if th[f] == was else f"  \n  *(PP1: {was})*"))
        L.append("")
    L.append("## 5. Try On (`TryOnPrompt.swift`, the white-background photos)")
    for k, title in (("task", "Opening line (after the image-role lines)"), ("shot", "Shot paragraph"), ("render", "Last paragraph")):
        row(title, "TryOnPrompt.build", old["tryon"][k], new["tryon"][k])
    L.extend(["`{pose_line}` is the pose sentence the app builds now (\"Reproduce the head angle of Image N: …\" "
              "or \"Pose: …\").", "", "## 6. Revert", f"Put the PP1 text and sizes back. The file is `ar-imac2.2/packs/PP1-STUDIO.json`."])
    out = PACKS / f"{new['label']}.app.md"
    out.write_text("\n".join(L) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "show", "export", "check"])
    ap.add_argument("code", nargs="?", default="PP2")
    ap.add_argument("--pid", default="208956")
    ap.add_argument("--pose", default="front", choices=list(T21.POSES))
    ap.add_argument("--theme", help="show the Style strings for this theme instead of the Try On prompt")
    a = ap.parse_args()
    if a.cmd == "list":
        for code, path in list_packs().items():
            p = load(code)
            print(f"{p['label']:12} {p['status']:12} tryon {p['tryon']['size']}  style {p['style']['size']}  {path.name}")
    elif a.cmd == "check":
        check()
    elif a.cmd == "export":
        print(export(a.code))
    else:
        pack = load(a.code)
        if a.theme:
            print(json.dumps(style_strings(pack, a.theme), indent=2))
            return
        refs = json.loads((ROOT / "ar-imac2.1" / "pids" / a.pid / "refs.json").read_text())
        roles = T21.roles_for(a.pose, a.pose != "front", False)
        print(tryon_prompt(pack, refs, a.pose, roles, "beard and moustache"))


if __name__ == "__main__":
    main()
