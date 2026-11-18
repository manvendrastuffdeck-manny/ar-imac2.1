# Prompt pack PP2-PHONE for the LK2.0 app

**What it is:** Makes every picture look like a real phone photo: vertical 9:16, deep focus, mobile HDR and tone mapping, no studio or cinematic look. Taken by another person from 1.5 to 2 m away, so the phone's wide lens does not enlarge the face. Style shots are framed from the waist up to fix the face-too-big problem. The face, frame-front and temple paragraphs are locked and identical to PP1.

**What to change:** strings and the output size only. Do not change the call order, the images sent, StyleBlend or the card layout. Every line to replace is listed below with the current (PP1) text next to the new text, so the change can be reverted by putting the PP1 text back.

**Leave as they are:** the roles, Person, Frame front and Temples paragraphs (from AR-iMac 2.1, never changed by a pack), the `Pose:` sentence that follows each theme's pose ("The head is turned no more than 20 degrees…"), the `Outfit:` line, and the Step B paragraphs about the frame front, temples and lighting the eyewear.

**Tag every picture made with this pack** with the code word `PP2-PHONE` (for example in the cache folder name or the `*.prompt.txt` file), so we can compare packs from screenshots.

Line numbers come from the LK2.0 walkthrough of 18 Nov 2026.

## 1. Output size
### Style picture size
*Where:* `StyleModels.swift:179`, `image_size`

**PP1 (now):**
```
1024x1536
```
**PP2-PHONE:**
```
1152x2048
```

### Try On picture size
*Where:* `TryOn` request, `image_size` (the app uses 1024x1280 now; the 2.1 repo uses 1024x1024)

**PP1 (now):**
```
1024x1280 (app) / 1024x1024 (repo)
```
**PP2-PHONE:**
```
1152x2048
```

## 2. Style, step A (`StylePrompt.scene`, `StyleModels.swift:184-200`)
### Opening line
*Where:* StylePrompt.scene

**PP1 (now):**
```
Create a candid lifestyle photograph of this customer {scene}.{custom}
```
**PP2-PHONE:**
```
Create an everyday smartphone photo of this customer {scene}.{custom}
```

### Shot paragraph (`StyleModels.swift:197`)
*Where:* StylePrompt.scene

**PP1 (now):**
```
Shot: vertical portrait from the chest up, the face large and in the upper third of the picture, with a calm, uncluttered area above the head. 50 mm lens, shallow depth of field, {light}.
```
**PP2-PHONE:**
```
Shot: vertical 9:16 photo framed from the waist up, with natural head-to-shoulder proportions, the face about a fifth of the picture's width, and a little open space above the head. Taken by a friend with a phone's main camera at chest height, about 2 m away: not a selfie, so the face is not stretched by the wide lens. The setting behind stays recognisable and mostly in focus. Light: {light}.
```

### Last paragraph
*Where:* StylePrompt.scene

**PP1 (now):**
```
Render it as an unretouched photograph of a real person, with natural skin texture.
```
**PP2-PHONE:**
```
{phone_look} Keep natural, unretouched skin texture.
```

`{scene}`, `{custom}` and `{light}` are the same fields the app fills now.

`{phone_look}` is this text, word for word:
```
Computational mobile-photo rendering, vertical 9:16 smartphone capture, small-sensor deep depth of field, short wide-angle optics, multi-frame mobile HDR, local tone mapping, edge-aware digital sharpening, mild denoising, compressed tonal rolloff, slight computational contrast, natural highlight rolloff, everyday candid phone realism. This should look like a real smartphone photo, not a DSLR image, not a studio shot, and not a polished stock image. Avoid shallow depth of field, avoid cinematic lighting, avoid perfect composition.
```

## 3. Style, step B (`StylePrompt.look`, `StyleModels.swift:204-220`)
### Last paragraph
*Where:* StylePrompt.look

**PP1 (now):**
```
Keep it an unretouched photograph of a real person, with natural skin texture.
```
**PP2-PHONE:**
```
Keep it the same smartphone photo as Image 1, with the same sharpness, noise, tone mapping and colour. Do not add grain, smoothing or extra sharpening, and leave everything away from the eyewear exactly as it is.
```

## 4. Theme strings (`StyleModels.swift:32-82`)

### work
- **scene:** at a desk in a bright, modern office in the morning, with a laptop, a notebook and a plant on the desk and the office visible behind  
  *(PP1: at a desk in a bright, modern office in the morning, with a laptop, a notebook and a plant softly out of focus behind)*
- **pose:** seated, turned slightly towards the camera with one forearm resting on the desk, a relaxed, confident half-smile, looking into the lens
- **outfit:** smart office wear: a crisp light-blue shirt with the collar open
- **light:** soft morning daylight from a large window at one side

### holiday
- **scene:** on the deck of a sailing boat on a sunny afternoon, with the sea and a hazy coastline behind  
  *(PP1: on the deck of a sailing boat on a sunny afternoon, with the sea and a hazy coastline softly out of focus behind)*
- **pose:** standing at the rail, turned slightly towards the camera, relaxed and at ease with a hint of a smile, looking into the lens
- **outfit:** a relaxed linen shirt in a light colour with the sleeves rolled
- **light:** bright afternoon sun  
  *(PP1: bright, warm afternoon sun with soft shadows)*

### party
- **scene:** on a rooftop terrace at night, with friends chatting in the background and the city lights behind  
  *(PP1: on a rooftop terrace at night, with friends chatting out of focus in the background and city lights as warm bokeh)*
- **pose:** standing, holding a glass at chest height, laughing as if mid-conversation, looking towards the lens
- **outfit:** a dark, well-fitted party outfit
- **light:** string lights overhead and the glow of the city at night, as a phone's night mode records it  
  *(PP1: warm string lights overhead and the glow of the city at night)*

### date_night
- **scene:** alone at a candle-lit table in a restaurant courtyard in the evening, with fairy lights strung behind and nobody else in the picture  
  *(PP1: alone at a candle-lit table in a restaurant courtyard in the evening, with fairy lights as warm bokeh behind and nobody else in the picture)*
- **pose:** seated, leaning in a little with one hand resting on the table, a warm, easy smile, looking into the lens
- **outfit:** an elegant dark evening outfit
- **light:** candlelight and the courtyard's fairy lights, as a phone's night mode records it  
  *(PP1: warm candlelight on the face and soft evening ambience)*

### ethnic_vibes
- **scene:** in the courtyard of a heritage haveli in the late afternoon, with carved stone arches behind  
  *(PP1: in the courtyard of a heritage haveli in the late afternoon, with carved stone arches softly out of focus behind)*
- **pose:** standing, turned slightly towards the camera, poised and at ease, looking into the lens
- **outfit:** elegant Indian ethnic wear
- **light:** late-afternoon sunlight  
  *(PP1: soft golden-hour light)*

### diwali
- **scene:** at a Diwali celebration at home in the evening, with rows of lit diyas and marigold garlands behind  
  *(PP1: at a Diwali celebration at home in the evening, with rows of lit diyas and marigold garlands softly out of focus behind)*
- **pose:** standing, relaxed, smiling warmly, looking into the lens
- **outfit:** festive Indian wear in a rich colour
- **light:** light from the diyas and the room lamps, as a phone's night mode records it  
  *(PP1: warm golden light from the lamps)*

### sportswear
- **scene:** on a running track beside a park in the early morning, with trees behind  
  *(PP1: on a running track beside a park in the early morning, with trees softly out of focus behind)*
- **pose:** standing, catching their breath after a run, energetic and relaxed, looking into the lens
- **outfit:** sportswear: a fitted performance top
- **light:** early-morning daylight  
  *(PP1: fresh early-morning light)*

## 5. Try On (`TryOnPrompt.swift`, the white-background photos)
### Opening line (after the image-role lines)
*Where:* TryOnPrompt.build

**PP1 (now):**
```
Create a studio catalog portrait of this customer wearing exactly this eyewear.
```
**PP2-PHONE:**
```
Create an everyday smartphone photo of this customer wearing exactly this eyewear.
```

### Shot paragraph
*Where:* TryOnPrompt.build

**PP1 (now):**
```
Shot: close-up head-and-shoulders portrait. {pose_line} Relaxed neutral expression, eyes looking into the lens, plain dark grey crew-neck T-shirt. Seamless pure white studio background. Soft, even, diffused front lighting. 85 mm lens at eye level, sharp focus on the eyes, the frame and the temple arm.
```
**PP2-PHONE:**
```
Shot: {pose_line} Relaxed neutral expression, eyes looking into the lens, plain dark grey crew-neck T-shirt. Vertical 9:16 photo framed from the chest up, with natural head-to-shoulder proportions. Plain white wall behind, lit by soft daylight from a window. Taken by another person with a phone's main camera at eye level, about 1.5 m away: not a selfie, so the face is not stretched by the wide lens. The eyes, the frame and the temple arm are sharp.
```

### Last paragraph
*Where:* TryOnPrompt.build

**PP1 (now):**
```
Render it as an unretouched photograph of a real person, with natural skin texture.
```
**PP2-PHONE:**
```
{phone_look} Keep natural, unretouched skin texture.
```

`{pose_line}` is the pose sentence the app builds now ("Reproduce the head angle of Image N: …" or "Pose: …").

## 6. Revert
Put the PP1 text and sizes back. The file is `ar-imac2.2/packs/PP1-STUDIO.json`.
