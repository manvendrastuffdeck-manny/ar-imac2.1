# AR-iMac 2.2: switchable prompt packs

2.2 is AR-iMac 2.1 plus **prompt packs**. A pack changes how the pictures look (the photo style, the framing and the output size) without changing the wiring. 2.1 is unchanged and still works on its own.

## Code words

| Code word | What it is |
|---|---|
| **AR-iMac 2.0** | `poc/`: the original POC, one product photo per call. Temples come out invented. |
| **AR-iMac 2.1** | `ar-imac2.1/`: temple lock. Front, three-quarter and temple views, chosen by catalog label, plus the temple gate. |
| **AR-iMac 2.2** | `ar-imac2.2/`: 2.1 plus prompt packs. The default pack is PP2. |
| **PP1-STUDIO** (`PP1`) | Prompt pack 1, the current wording. Try On is the 2.1 studio prompt word for word (`packs.py check` proves it). Style is the LK2.0 app's wording as of 18 Nov. **Switch back to PP1 to revert.** |
| **PP2-PHONE** (`PP2`) | Prompt pack 2: a computational smartphone photo, vertical 9:16 (1152×2048), deep focus, mobile HDR. Shot from 1.5 to 2 m away, not a selfie. Style shots are framed from the waist up. Experimental. |

A result is named by both codes, for example **"AR-iMac 2.2 · PP2"**. Every output file, folder and manifest carries the pack code (`front_gpt_2_5_flare_PP2.png`, `out/<customer>_<pid>_PP2/`), so results from different packs never mix.

## What a pack can and cannot change

| Changed by the pack | Locked (always from AR-iMac 2.1 code) |
|---|---|
| The task line ("Create a … photo of this customer …") | The image-role lines (which image is which) |
| The Shot paragraph: framing, background, camera, light | Person: the identity paragraph |
| The render paragraph: photo style | Frame front |
| The Style theme strings: scene, pose, outfit, light | Temples: the 2.1 fix |
| Output size | Upload order, the temple gate (`TempleNotSent`), scoring |

`packs.py check` fails if PP1 stops matching 2.1 word for word, if any pack touches a locked paragraph, or if a theme has an unfilled placeholder.

## What PP2 changes, and why

- **The look:** the smartphone-rendering paragraph, word for word, as the last paragraph of every prompt.
- **Face size:** a phone's main camera is wide-angle. From arm's length (a selfie) it enlarges the nose and face. PP2 says the photo is taken by another person from 1.5 to 2 m away, which keeps the phone look with natural proportions.
  - Style shots are framed from the waist up, with the face about a fifth of the width. PP1 said "the face large and in the upper third".
  - Try On stays chest-up so the temple logos stay readable.
- **Shape and resolution:** 9:16 at 1152×2048. The app's card is about 0.54 wide-to-tall and 9:16 is 0.5625, so the card crops about 4% of the width instead of 19%.
  - 1152 px wide is about 1:1 on a 1132 px card, so it is no longer enlarged in the card.
- **Deep focus:** "softly out of focus" and "bokeh" are removed from the theme strings. "Shallow depth of field" and the 50 mm lens are removed from the Shot paragraph.
  - Otherwise the prompt would contradict the phone paragraph's "avoid shallow depth of field".
- **Light:** the cinematic light wording ("warm", "golden-hour", "soft shadows") is toned down, and night scenes say "as a phone's night mode records it".
- **Step B (the glasses pass in the app):** the last paragraph asks the model to keep Image 1's sharpness, noise and tone mapping, and not to add grain. This may reduce the second-pass grain; it is untested.

## Run

Uses the 2.1 setup (`bash install.sh 2.1`) and the 2.1 reference packs in `ar-imac2.1/pids/`.

```bash
python3 ar-imac2.2/scripts/packs.py list                 # packs and their sizes
python3 ar-imac2.2/scripts/packs.py check                # PP1 == 2.1; locked paragraphs intact
python3 ar-imac2.2/scripts/packs.py show PP2 --pid 208956 --pose left    # the full prompt
python3 ar-imac2.2/scripts/packs.py show PP2 --theme work                # the Style strings for one theme
python3 ar-imac2.2/scripts/packs.py export PP2           # writes packs/PP2-PHONE.app.md for the app developer

# generate; flags as in 2.1, plus --pack
python3 ar-imac2.2/scripts/tryon.py --pid 208956 --front f.jpg --left l.jpg --right r.jpg --pack PP1,PP2 --dry-run
python3 ar-imac2.2/scripts/tryon.py --pid 208956 --front f.jpg --left l.jpg --right r.jpg --pack PP1,PP2
```

With `--pack PP1,PP2`, each pack gets its own run folder and grid, and `out/<customer>_<pid>_compare.jpg` stacks the two grids with their code words.

**Estimated cost per image (GPT Image 2.5 Flare):** PP1 at 1024×1024 is about $0.20. PP2 at 1152×2048 is about $0.45. This assumes the price scales with pixels; it has not been confirmed on a bill.

## The LK2.0 app

The app has its own Swift copy of the prompts. To try PP2 there, send `packs/PP2-PHONE.app.md` to the app developer. It lists every string and size to swap, with the PP1 text beside each one, so reverting means pasting PP1 back. No call order, merge or layout changes.

## Not verified yet

- 1152×2048 has not been sent to GPT Image 2.5 Flare on fal. The app already uses custom sizes (1024×1536, 1024×1280), so it is expected to work. If it is refused, use 1024×1824.
- PP2 has only been dry-run (payloads checked, nothing generated). Judge it on a paid A/B against PP1.
