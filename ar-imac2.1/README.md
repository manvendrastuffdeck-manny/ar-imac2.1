# AR-iMac 2.1: temple-locked try-on

Version 2.1 of the try-on image pipeline. It fixes wrong temple arms in the generated images. Version 2.0 is still in `poc/` and has not changed.

## What went wrong in 2.0

The app was tested on two customers. Their front views looked right, but the temples were wrong in every angled shot:

| Customer | Temple on the PID | Temple in the generated side shots |
|---|---|---|
| 1 (black square) | silver bat emblem, three grooved lines, ribbed tip | plain, smooth black arm |
| 2 (frosted ice-blue) | ∞ logo behind the hinge, see-through hinge block, notched arm | straight arm, smudged mark |

**Cause: the model never saw the temple.** The 2.0 recipe (`poc/scripts/studio.py`) sends two images to the model: the customer's head crop and one product photo. The product photo is the first gallery image, which is a front or three-quarter view, so the temple is edge-on or hidden. The prompt asked for "the same … temples as Image 2", but Image 2 had no temple to copy. The model drew a generic one.

There are two more problems:
- **Gallery order is not stable.** Image 0 is the front shot on some PIDs and the three-quarter shot on others (see `refs.json` for the six test PIDs). A wiring that says "take image 0" sends a different view per PID.
- **The prompt said nothing specific about the temple.** It gave no material, no colour and no instruction to keep logos. The catalog API already has this data (`Temple Colour`, `Temple Material`, and the temple length from `Frame Dimensions`).

## What 2.1 changes

1. **The product views are chosen by catalog label, not by position** (`scripts/pid_refs.py`). The Lenskart product API labels every gallery image in `imageUrlsDetail`. 2.1 takes:
   - `Image_Front`: required
   - `Image_Temple`: required (the side profile)
   - `Image_Left`: the three-quarter view, used when present

   Model and lifestyle shots are never used as product references. Every view is cropped tight and squared to 1024 px, so a small temple logo is still large enough to read.
2. **The temple is forced at two points.**
   - `pid_refs.build()` raises `MissingReference` if a PID has no labelled temple view, so no generation runs for that PID.
   - `tryon.build_call()` raises `TempleNotSent` if a payload is about to go out without the temple image, whichever model is used.
3. **Each image has one named role in the prompt.** The prompt has its own Temples paragraph: "copy the temple arms from Image N exactly: <colour> <material>, about <length> mm … every logo, emblem, print, groove or texture in the same place. Do not draw plain or generic temple arms."
4. **The three camera shots are used as in the app.** For the left and right outputs, the customer's own angled shot is the pose reference and the front shot is the identity reference.
5. **Sheet mode for single-image callers.** If the app can attach only one product image, send `sheet.png` (front, three-quarter and temple stacked) and use `--sheet`. That way the temple is in the one image the app sends.
6. **The contact sheet shows what was sent.** The top row of `grid.jpg` shows every reference sent, the temple view included, so a reviewer can compare the temple directly.

## Install and run

```bash
bash install.sh            # at the repo root; choose 2.1
source .venv/bin/activate
echo 'FAL_KEY=<your fal.ai key>' > .env

# 1. product reference pack (free; fails loudly if the PID has no temple view)
python3 ar-imac2.1/scripts/pid_refs.py 208956

# 2. check the exact payloads without spending anything
python3 ar-imac2.1/scripts/tryon.py --pid 208956 --front front.jpg --left left.jpg --right right.jpg --dry-run

# 3. generate (GPT Image 2.5 Flare by default, about $0.20 per image, so about $0.60 for three poses)
python3 ar-imac2.1/scripts/tryon.py --pid 208956 --front front.jpg --left left.jpg --right right.jpg \
    --facial-hair "beard and moustache" --models gpt_2_5_flare
```

Outputs go to `ar-imac2.1/out/<customer>_<pid>/`:
- `manifest.json`: the roles sent per call, the full prompt, the estimated cost and the identity scores
- `grid.jpg`: the contact sheet

`--poses front,left,right` and `--models gpt_2_5_flare,nano_banana_pro,seedream_5_pro,qwen` select what to run. `left` and `right` are from the camera's point of view.

## Wiring it into the app

The fix the app needs is in the upload step after a PID is selected. The app has to send **three product images per call, not one**. For each output pose, build `image_urls` in this order:

| Slot | Front output | Left / right output |
|---|---|---|
| 1 | customer front shot | customer shot at that angle |
| 2 | product `Image_Front` | customer front shot |
| 3 | product `Image_Left` (three-quarter) | product `Image_Front` |
| 4 | product `Image_Temple` | product `Image_Left` (three-quarter) |
| 5 | | product `Image_Temple` |

Use the prompt from `tryon.prompt()`. The quickest way to get it is to run `--dry-run` once and copy it from `manifest.json`. The image numbers in the prompt must match the slots above.

To pick the product images in the app, read `result.imageUrlsDetail` from `https://api-gateway.juno.lenskart.com/v2/products/product/<pid>` (header `x-api-client: desktop`). Choose by the `label` field: labels starting with `Image_Front`, `Image_Left` and `Image_Temple`. Do not choose by array index.

If the app's generation call accepts only one product image, upload `ar-imac2.1/pids/<pid>/sheet.png` and use the `--sheet` prompt.

**Server-side guard:** reject any generation request whose product images do not include the temple view. `build_call()` is the reference implementation.

## Limits

- Logos smaller than about 5 mm (the ∞ mark on customer 2's frame) may still come out soft. The model now has the reference, but a generative model redraws rather than copies. For exact logos, the next step is Route C from `docs/POC-PLAN.md`: paste the real product pixels back into the temple region with a mask.
- The temple shot shows one side of the frame. When a logo is printed on one temple only, the model can put it on the wrong side.
- 2.1 has been tested offline: reference packs for all six POC PIDs, payload dry-runs and the temple gate. A paid run on the two app customers is the next check.

## Layout

```
ar-imac2.1/
  scripts/
    pid_refs.py   labelled product views, temple gate, specs, sheet.png        (new)
    tryon.py      3-angle generation, multi-image prompt, TempleNotSent guard  (new)
    grid.py       contact sheet with the sent references                       (new)
    falx.py, prep.py, identity.py, qc.py   copied from v2.0 (falx also reads ar-imac2.1/.env)
  get_models.sh   face models; reuses poc/models when present
  requirements.txt
  pids/ out/ models/   generated locally, git-ignored
```
