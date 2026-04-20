---
name: noirsboxes-shorts
description: |
  Produce a 30-second 9:16 vertical showcase short for NoirsBoxes Black Magic
  cable/charger testers (MD-905, MD-903, and future MD-xxx SKUs) in the brand's
  established AI-fast-cut style. Complete end-to-end pipeline: asset discovery
  from brand folder → Runway image-to-video + text-to-video generation →
  per-scene ElevenLabs TTS → Remotion composition with brand captions → final
  MP4 render. Trigger when the user says: "make me a NoirsBoxes short",
  "MD-905 TikTok/Reels/Shorts", "another video in the brand style",
  "vertical product promo for NoirsBoxes", or hands a new MD-xxx SKU and asks
  for a showcase video. Also triggers when the user says "do it like our
  1月2日 reference" or similar brand-reference cue.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# NoirsBoxes Shorts — 30s 9:16 Vertical Showcase Production

Proven end-to-end pipeline. The MD-905 v3 reference output
(`projects/md905-shorts-en/renders/md905-shorts-en-9x16-v3.mp4`) was produced
with this exact flow and validated by the brand owner. Reuse verbatim for new
SKUs — only the product photos, narration, and tagline change.

## When to use

- User asks for a NoirsBoxes / MD-xxx short (TikTok, Reels, Shorts, IG).
- User hands a new SKU (photo + features) and wants a showcase video.
- User says "make another one like [date].mp4" or "in the NoirsBoxes style".
- User says the MD-905 short but for a different language (see **Localization**).

## Locked brand DNA

| Field | Value |
|---|---|
| Aspect | 9:16, **1080×1920 exactly** |
| Duration | ~26.5 s (sweet spot — longer loses completion rate, shorter feels abrupt) |
| Frame rate | 30 fps |
| Codec | H.264 + AAC (Remotion default render) |
| Caption font | `Nunito`/`Montserrat` 900-weight italic with 2.5–3 px black stroke and multi-offset shadow stack (fakes a ~6–8 px outline) |
| Caption position | Top-center, `topPx ≈ 200` on 1920-tall canvas |
| Emphasis highlight | Colored background pill on the punch word: **pink `#FF3D8A`** = brand positive, **yellow `#FFD60A`** = neutral call-out, **red `#FF3B30`** = problem/warning, **green `#30D158`** = resolution/success |
| Highlight corner radius | 10–14 px |
| Narration style | First-person, present tense, punchy 3–7 word lines, male confident `voice_id: pNInz6obpgDQGcFmaJgB` (swap per language) |
| Narrative shape | Problem → Product reveal → Score reveal → Solution → CTA |
| Music | 30s ElevenLabs Music, prompt "Fast-paced modern tech short-form reveal, punchy electronic pulses, energetic build, confident sub bass, trendy TikTok/Reels vibe, no vocals" |
| Narration : Music mix | `volume=1.0` narration vs `volume=0.25` music (narration must dominate) |
| Closing CTA | Real `NoirsBoxes` logo top, product centered, `MD-XXX` giant italic, pink-highlighted tagline, `noirsboxes.com` URL footer |

The caption stack is the single strongest brand signal across all 4 reference
videos. Never swap it for a different font family or drop the italic + stroke.

## Brand assets (source of truth)

```
/Users/johnnylin/Documents/video-producer/assets/brand/norisboxes/
├── logo.png                                           # brand logo
└── product-image/
    ├── MD-905/
    │   ├── md905-blank.jpg                            # studio 3/4 angle (hero)
    │   ├── Product_MD-905-1.png                       # master PNG for Remotion scenes
    │   ├── MD-905-blank-holding.jpg                   # in-hand, blank screen
    │   ├── MD-905-product-holding.jpg                 # in-hand, alt angle
    │   ├── MD-905-cable-inferior.jpg                  # in-hand, inferior screen
    │   ├── MD-905-cable-inferior-89scores.jpg         # in-hand, "Inferior 89" ← score beat
    │   ├── MD-905-cable-original-100scores.jpg        # in-hand, "Original 100" ← score beat
    │   ├── MD-905-cable-result-original-100scores.jpg # alt angle of 100 score
    │   ├── MD-905-adapter-info-score-68.jpg           # adapter test screen
    │   └── MD-905-mode-selection.jpg                  # UI mode screen
    └── MD-903/                                        # same pattern for other SKUs
```

**Always work from `assets/brand/norisboxes/`.** Do NOT source product shots
from the reference-video keyframes in `~/Downloads/shorts video/` — those have
burned-in captions, vignette masks, and sometimes show the wrong SKU color.
The brand folder is the clean, canonical source.

For a new SKU, expect the user to drop matching filenames under
`product-image/MD-xxx/`. If any of the three score-beat photos
(`*-blank-holding`, `*-cable-inferior-*scores`, `*-cable-original-*scores`)
are missing, ask for them before proceeding — they're what makes the
reveal land.

## 9-scene structure (locked)

This is the exact cadence used by the reference MD-905 short. Scene durations
are audio-driven: `max(measured_TTS_duration + 0.25s pad, visual_minimum)`.
The totals below add to **26.5 s**.

| # | Time | Scene | Video source | Caption (pink/yellow/red/green highlight on the punch word) |
|---|---|---|---|---|
| 1 | 0.0–2.0 | Cable hook | Runway `gen4.5` t2v "cable close-up, spark at tip" | "This cable **looked real.**" (pink) |
| 2 | 2.0–4.0 | Problem | Runway `gen4.5` t2v "phone red warning glitch" | "But it was **killing my phone.**" (red) |
| 3 | 4.0–7.0 | Solution reveal | Runway `gen4_turbo` i2v from `*-blank-holding.jpg` | "Tested it with **NoirsBoxes.**" (yellow) |
| 4 | 7.0–11.0 | Inferior score | Runway `gen4_turbo` i2v from `*-cable-inferior-89scores.jpg` | "Inferior. **89.**" (red) |
| 5 | 11.0–13.0 | Swap cable | Runway `gen4.5` t2v "hand plugging new cable" | "Swap to **original.**" (green) |
| 6 | 13.0–17.0 | Original score | Runway `gen4_turbo` i2v from `*-cable-original-100scores.jpg` | "**100.** Perfect." (green) |
| 7 | 17.0–18.5 | Safe again | Runway `gen4.5` t2v "phone healthy green glow" | "**Safe** again." (green) |
| 8 | 18.5–22.5 | Features | Remotion — product PNG + 4 animated ticks | "C48 to C94 chips · Any charger, any cable · Offline. Portable. · Scored in seconds" |
| 9 | 22.5–26.5 | Hero CTA | Remotion — logo + product PNG + MD-XXX + tagline + URL | "Know before you sell." (pink) |

Scenes 1, 2, 5, 7 are pure text-to-video B-roll. Scenes 3, 4, 6 are the
product beats — **the real on-device score screens carry these**, which is
why we use the brand photos as Runway I2V sources instead of faking score
overlays in Remotion.

## End-to-end execution

### Step 0 — Preflight (API reality check)

The NoirsBoxes dev env has a recurring issue where `.env` gets saved with
inline comments that python-dotenv mis-parses as values. Before each run:

```bash
python -c "
from lib.env_loader import load_env; load_env()
import os
for k in ['RUNWAY_API_KEY', 'FAL_KEY', 'ELEVENLABS_API_KEY']:
    v = os.environ.get(k, '')
    print(f'{k}: len={len(v)} startswith_hash={v.startswith(\"#\")}')
"
```

- `RUNWAY_API_KEY` must be present, real (not `# ...`). **This is the only
  video gateway that currently works on this machine.**
- `FAL_KEY` is usually broken — **do NOT rely on `fal_client.upload_file`.**
  Use base64 data URLs as `promptImage` (see Step 2 below).
- `ELEVENLABS_API_KEY` must be real — TTS + music both live here.

### Step 1 — Create project workspace

```bash
SKU=MD-905  # or MD-903, etc.
PROJ=/Users/johnnylin/Documents/video-producer/projects/noirsboxes-${SKU}-shorts
mkdir -p $PROJ/{artifacts,assets/video,assets/audio,assets/music,renders}
```

### Step 2 — Generate 3 image-to-video clips via Runway gen4_turbo

Runway I2V uses `gen4_turbo` (fast, reliable, ~30–60s per clip). Because
`fal_client.upload_file` is broken, **pass the source image as a base64
data URL** to `promptImage`. Runway accepts this.

```python
"""Image-to-video generation — 3 brand-photo-sourced product beats."""
import sys, base64, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, "/Users/johnnylin/Documents/video-producer")
from lib.env_loader import load_env; load_env()
from tools.tool_registry import registry
registry.discover()

SKU    = "MD-905"
PROJ   = Path(f"/Users/johnnylin/Documents/video-producer/projects/noirsboxes-{SKU}-shorts")
BRAND  = Path(f"/Users/johnnylin/Documents/video-producer/assets/brand/norisboxes/product-image/{SKU}")

def data_url(path):
    return f"data:image/jpeg;base64,{base64.b64encode(open(path,'rb').read()).decode()}"

HOLDING_URL  = data_url(str(BRAND / f"{SKU}-blank-holding.jpg"))
INFERIOR_URL = data_url(str(BRAND / f"{SKU}-cable-inferior-89scores.jpg"))
ORIGINAL_URL = data_url(str(BRAND / f"{SKU}-cable-original-100scores.jpg"))

LOCK = (
    " CRITICAL: vertical 9:16 composition, product stays clearly visible and "
    "centered. Camera on a tripod, only subtle movement."
)

JOBS = [
    ("iv_device_reveal",  HOLDING_URL,  "A person's hand presenting a sleek black NoirsBoxes "+SKU+" cable-tester device in a warm home setting, the device screen flickers on with a subtle glow, the hand holds it steady while the camera gently tilts toward the screen, natural daylight, cinematic shallow depth of field." + LOCK),
    ("iv_inferior_push",  INFERIOR_URL, "Slow cinematic push-in onto the LCD screen showing detailed diagnostic data and an 'Inferior' score of 89, red tones intensify subtly, warm home lighting softly blurred." + LOCK),
    ("iv_original_push",  ORIGINAL_URL, "Slow cinematic push-in onto the LCD screen showing detailed diagnostic data and an 'Original' score of 100 with green certification tones, bright minimal home background softly blurred, triumphant palette." + LOCK),
]

def run(name, image_url, prompt):
    runway = registry._tools["runway_video"]
    t0 = time.time()
    print(f"[START] {name}", flush=True)
    r = runway.execute({
        "operation": "image_to_video",
        "image_url": image_url,
        "prompt": prompt,
        "model": "gen4_turbo",
        "duration": 5,
        "ratio": "9:16",
        "output_path": str(PROJ / f"assets/video/{name}.mp4"),
    })
    print(f"[{'OK   ' if r.success else 'FAIL '}] {name} in {time.time()-t0:.1f}s" +
          ("" if r.success else f": {r.error}"), flush=True)
    return (name, r.success)

with ThreadPoolExecutor(max_workers=3) as ex:
    list(as_completed([ex.submit(run, *j) for j in JOBS]))
```

### Step 3 — Generate 4 text-to-video clips via Runway gen4.5 (raw HTTP)

The `runway_video` tool's `model` enum does **not** include `gen4.5`, and
`gen4_turbo` returns 400 on the `/v1/text_to_video` endpoint (it's only
supported for I2V). Call the endpoint directly:

```python
"""Text-to-video generation — 4 non-product B-roll scenes."""
import sys, os, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, "/Users/johnnylin/Documents/video-producer")
from lib.env_loader import load_env; load_env()
from pathlib import Path

SKU  = "MD-905"
PROJ = Path(f"/Users/johnnylin/Documents/video-producer/projects/noirsboxes-{SKU}-shorts")
KEY  = os.environ["RUNWAY_API_KEY"]
H    = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "X-Runway-Version": "2024-11-06"}

JOBS = [
    ("tv_cable_bad",     "Extreme macro close-up of a cheap generic white Lightning USB cable connector lying on a dark wooden desk, subtle electrical blue spark flickering at the metal pins, warm moody studio lighting, shallow depth of field, cinematic product commercial aesthetic. Vertical 9:16."),
    ("tv_phone_dying",   "Close-up of a modern smartphone lying face up on a dark wooden desk, the screen glitches with a dominant red low-battery warning icon pulsing, eerie ambient red glow, moody night lighting, very shallow depth of field, cinematic tension. Vertical 9:16."),
    ("tv_cable_swap",    "Macro close-up of a clean brand-new white Lightning USB cable being gently inserted into a modern smartphone lying on a bright minimal desk, soft window daylight, warm wood tones, shallow depth of field, slow confident hand motion, cinematic product commercial. Vertical 9:16."),
    ("tv_phone_healthy", "A modern smartphone resting on a warm wooden desk, a white charging cable neatly attached, the screen glows calmly with a healthy green battery icon, soft cozy daylight from a window, shallow depth of field, peaceful confident cinematic vibe. Vertical 9:16."),
]

def submit_and_poll(name, prompt):
    t0 = time.time()
    print(f"[START] {name}", flush=True)
    r = requests.post("https://api.dev.runwayml.com/v1/text_to_video", headers=H,
        json={"model":"gen4.5","promptText":prompt,"duration":5,"ratio":"720:1280","watermark":False}, timeout=30)
    if r.status_code != 200:
        print(f"[FAIL ] {name} submit {r.status_code}: {r.text[:200]}")
        return (name, False)
    tid = r.json()["id"]
    # gen4.5 runs 3–7 min per clip — poll for up to 12 min
    for _ in range(150):
        time.sleep(5)
        p = requests.get(f"https://api.dev.runwayml.com/v1/tasks/{tid}", headers=H, timeout=15).json()
        if p.get("status") == "SUCCEEDED":
            vid = requests.get(p["output"][0], timeout=120).content
            out = PROJ / f"assets/video/{name}.mp4"
            out.write_bytes(vid)
            print(f"[OK   ] {name} in {time.time()-t0:.1f}s", flush=True)
            return (name, True)
        if p.get("status") == "FAILED":
            print(f"[FAIL ] {name}: {p.get('failure', 'unknown')}")
            return (name, False)
    print(f"[FAIL ] {name}: TIMED_OUT"); return (name, False)

with ThreadPoolExecutor(max_workers=4) as ex:
    list(as_completed([ex.submit(submit_and_poll, *j) for j in JOBS]))
```

Budget time: **8–15 minutes total** when the 4 clips run in parallel (one
or two routinely hit the 6-min timeout on the first attempt — just retry the
failed ones individually with `poll_max=150`).

### Step 4 — Generate per-scene TTS (ElevenLabs)

Nine separate TTS calls so each `<Sequence>` can play its own `<Audio>`.
**Don't call all nine in parallel** — ElevenLabs rate-limits at ~6 concurrent
requests with `eleven_turbo_v2_5` and the 7–9th hit 429. Run with
`max_workers=4` or retry the 429s sequentially with a 3-second pause.

```python
from tools.tool_registry import registry
registry.discover()
tts = registry._tools["elevenlabs_tts"]

NARRATION = [
    ("vo_01_hook",       "This cable looked real."),
    ("vo_02_problem",    "But it was killing my phone."),
    ("vo_03_solution",   "I tested it with NoirsBoxes."),
    ("vo_04_inferior",   "Inferior. Eighty-nine."),
    ("vo_05_swap",       "Swap to original."),
    ("vo_06_original",   "One hundred. Perfect."),
    ("vo_07_safe",       "Safe again."),
    ("vo_08_features",   "C forty-eight to C ninety-four. Any charger. In seconds."),
    ("vo_09_cta",        f"MD nine oh five. Know before you sell."),   # edit for other SKUs
]
for name, text in NARRATION:
    tts.execute({
        "text": text,
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "model_id": "eleven_turbo_v2_5",
        "output_path": str(PROJ / f"assets/audio/{name}.mp3"),
    })
```

Music bed (reuse across SKUs — no need to regenerate):

```python
registry._tools["music_gen"].execute({
    "prompt": "Fast-paced modern tech short-form reveal, punchy electronic pulses, energetic build, confident sub bass, trendy TikTok/Reels vibe, no vocals, 30 seconds.",
    "duration_seconds": 30,
    "output_path": str(PROJ / "assets/music/bed.mp3"),
})
```

### Step 5 — Measure TTS durations (for scene timing)

```bash
cd $PROJ/assets/audio && for f in vo_*.mp3; do
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  printf "%s: %.3f\n" "$f" "$dur"
done
```

On the reference MD-905 run, the measured durations gave these
`SCENE_SECONDS` values (in [MD905Shorts.tsx](../../remotion-composer/src/MD905Shorts.tsx)):

```ts
const SCENE_SECONDS = [2.0, 2.0, 3.0, 4.0, 2.0, 4.0, 1.5, 4.0, 4.0];  // total 26.5s
```

Those are rounded-up against visual minimums (kinetic card 1.8s, video scene
with audio 3s, score reveal 4s, features 4s, CTA 4s). For a new SKU, only
re-measure if the narration wording changes enough to shift scene 8 (features)
or scene 9 (CTA) past their current budgets.

### Step 6 — Stage assets into Remotion `public/`

```bash
DEST=/Users/johnnylin/Documents/video-producer/remotion-composer/public/noirsboxes-${SKU}
mkdir -p $DEST
cp $PROJ/assets/video/*.mp4        $DEST/
cp $PROJ/assets/audio/vo_*.mp3     $DEST/
cp $PROJ/assets/music/bed.mp3      $DEST/
cp /Users/johnnylin/Documents/video-producer/assets/brand/norisboxes/product-image/${SKU}/*blank*.jpg $DEST/
cp /Users/johnnylin/Documents/video-producer/assets/brand/norisboxes/logo.png $DEST/
```

### Step 7 — Register the composition in `Root.tsx`

The MD-905 composition is already registered. For a new SKU, either:

**Option A — reuse `MD905Shorts`** (if only the SKU string in scene 9 changes),
and override `defaultProps` with the new folder path.

**Option B — duplicate to `MD{SKU}Shorts.tsx`** and tweak:
- `SCENE_SECONDS` (only if narration length changed)
- Scene 4/6 captions (`"89."` / `"100."`) if this SKU uses different scoring
- Scene 9 CTA: swap `MD-905` literal to the new SKU
- Scene 8 feature bullets if the SKU has different spec claims

Register it in [Root.tsx](../../remotion-composer/src/Root.tsx) with
`width={1080} height={1920} fps={30}` and `defaultProps` pointing at the
`noirsboxes-{SKU}/` folder.

### Step 8 — Render

```bash
cd /Users/johnnylin/Documents/video-producer/remotion-composer
npx remotion render src/index.tsx MD905Shorts \
  /Users/johnnylin/Documents/video-producer/projects/noirsboxes-${SKU}-shorts/renders/noirsboxes-${SKU}-9x16.mp4
```

26.5s renders in ~60–90s on Apple Silicon.

## Cost per deliverable

| Line item | Unit cost | Per video |
|---|---|---|
| Runway `gen4_turbo` I2V × 3 | $0.25/clip (5s @ $0.05/s) | $0.75 |
| Runway `gen4.5` T2V × 4 | $0.25/clip (5s @ $0.05/s) | $1.00 |
| ElevenLabs TTS × 9 | ~$0.005/call | $0.05 |
| ElevenLabs Music × 1 | ~$0.20 | $0.20 |
| Remotion render | local | $0 |
| **Total** | | **~$2.00** |

Add ~$1–2 if you iterate on any Runway clip (each retake = $0.25).
Do NOT retake on caption/script tweaks — those only require a re-render.

## Localization

To produce the same short in another language:

1. Translate the 9 narration lines (professional translator or Claude).
2. Regenerate **only** the TTS clips with the target `voice_id`:
   - German confident male: `pqHfZKP75CvOlQylNhV4` (Bill)
   - Japanese: `Mu5jxyqZOLIGltFpfalg` (Asahi)
   - Spanish: `IoWAuKNnqRPuIktSJlCy` (Aria)
   - (Always confirm availability against the ElevenLabs voice library.)
3. Stage the new TTS files into a per-language public folder
   (e.g. `public/noirsboxes-MD-905-de/`), leaving the videos and music reused.
4. Duplicate the composition as `MD905ShortsDE` with the new `vo{N}` prop
   paths, or override `defaultProps` at render time via `--props`.
5. Captions in Remotion must be manually translated too — edit the
   `BrandCaption` children in each `<Sequence>`.

Cost per language: **~$0.05 TTS only** (everything else is reused).

## Variants & extensions

- **Longer cut (45–60s)**: insert 2–3 extra product-detail beats
  (firmware UI, adapter test, charger PD reading) after scene 6.
  Each extra beat = 1 new Runway I2V from the matching
  `MD-{SKU}-adapter-*.jpg` / `MD-{SKU}-mode-*.jpg` brand photo.
- **16:9 variant for YouTube**: rerun steps 2 + 3 with `ratio: "16:9"` /
  `"1280:720"`. Cannot crop the 9:16 render — captions and product will be
  in the wrong place.
- **UGC-style selfie variant**: see the separate `ugc-selfie` lane
  (requires HeyGen avatar or real footage). Not covered here — this skill
  is the AI fast-cut lane only.

## Verification checklist

Before delivering:

- [ ] Output is **1080×1920** (not 1920×1080 — check `ffprobe`).
- [ ] Duration is 26–31 s (`ffprobe ... format=duration`).
- [ ] Audio tracks are both present (`ffprobe ... stream=codec_name` shows `h264` + `aac`).
- [ ] Scene 4 and scene 6 show the **real on-device screens** with 89 and 100.
  If you see a fake giant animated number instead, you're looking at v2 —
  regenerate with `MD{SKU}Shorts.tsx` v3 (no `ScoreOverlay`).
- [ ] Captions are italic, bold, white-on-black-stroke with colored highlight.
- [ ] Narration volume dominates music (no ducking dip below intelligibility).
- [ ] CTA card shows: **logo top** → product → `MD-XXX` → pink tagline → URL.
- [ ] Total duration between 26 s and 31 s.
- [ ] No un-rendered placeholder text like `<product-name>` or `MD-XXX`.
- [ ] File plays cleanly on QuickTime **and** on headphones (music bed doesn't clip).

## Known pitfalls (every one of these bit us; read before running)

- **fal.ai upload returns 401** when `FAL_KEY` is a comment string (common in
  this repo's `.env`). Symptom: `fal_client.upload_file` → 401 Unauthorized.
  **Fix:** use base64 `data:image/jpeg;base64,...` URLs on `promptImage`
  instead of uploading. Runway accepts data URLs up to ~400 KB without issue.
- **Runway `gen4_turbo` on text_to_video returns 400.** That endpoint only
  accepts `gen3a_turbo`, `gen4.5`, `kling3.0_*`, `seedance2`, `veo3*`.
  **Fix:** use `gen4.5` (available on our account) via raw HTTP; the built-in
  `runway_video` tool's `model` enum doesn't include `gen4.5` yet.
- **Runway `gen3a_turbo`, `kling3.0_standard`, `veo3*`, and most other
  text_to_video variants return 403** on our account. Only `gen4.5` and
  `seedance2` are entitled. Don't waste a retry guessing.
- **gen4.5 is ~5× slower than gen4_turbo** (3–7 min per 5s clip vs ~30–60s).
  Plan parallelism accordingly; increase poll ceiling to 150 × 5s = 12.5 min.
- **ElevenLabs TTS 429 at >6 concurrent calls.** Keep `max_workers ≤ 4` and
  retry the 429s sequentially with a 2–3s sleep.
- **`seedance_video` tool has a latent bug**: `upload_image_to_fal` is
  referenced but not imported at
  [tools/video/seedance_video.py:219](../../tools/video/seedance_video.py:219).
  Don't use this tool for I2V — use `runway_video` with data URL instead.
- **Remotion `<Video>` / `<Audio>` need `staticFile()`** around their `src`.
  Plain strings render as 404s at compose time. `OffthreadVideo` preferred
  for 5s clips.
- **Don't trust the Runway text_to_video model to render a specific connector
  type.** If you prompt "Lightning cable" you may get USB-A or USB-C. Keep
  the narration generic ("this cable") so the visual mismatch is invisible.

## Reference artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Reference final render | `projects/md905-shorts-en/renders/md905-shorts-en-9x16-v3.mp4` | What the output should look like |
| Remotion composition | `remotion-composer/src/MD905Shorts.tsx` | Reusable 9-scene template — copy for new SKUs |
| Root composition registry | `remotion-composer/src/Root.tsx` | Register new `MD{SKU}Shorts` here |
| I2V asset runner | `projects/md905-shorts-en/run_assets_v3.py` | Template for Step 2 |
| T2V asset runner | `projects/md905-shorts-en/run_tv_v3.py` | Template for Step 3 — raw-HTTP gen4.5 invocation |
| TTS narration (reusable) | `projects/md905-shorts-en/assets/audio/vo_*.mp3` | Can reuse as-is if new SKU uses MD-905 script |
| Brand DNA reference videos | `/Users/johnnylin/Downloads/shorts video/1月2日.mp4`, `3月13日.mp4`, `3月20日.mp4`, `1月9日.mp4` | Visual DNA source — consult if brand direction questioned |

## Minimum new-SKU invocation

When asked for a new product short:

1. Ask for the **SKU** (e.g. MD-907) and confirm brand photos exist under
   `assets/brand/norisboxes/product-image/MD-XXX/`. If any of the three score
   photos are missing, stop and request them.
2. Ask for the **one-sentence value prop + 3–4 feature bullets + tagline**.
   If not provided, reuse MD-905's copy with the SKU number swapped.
3. Announce the plan: "going through 8 steps, ~$2 Runway+TTS cost,
   ~15 min wall time (gen4.5 is the slow one)."
4. Execute Steps 1–8 above without further confirmation — this pipeline
   is pre-approved by the brand owner based on the v3 reference output.
5. Deliver the MP4 path. Offer the 16:9 YouTube variant + other-language
   variants as follow-ups.

Iterate only on **caption text**, **scene timing**, or **music volume**
without spending new money — those all happen in Remotion source.
Regenerate Runway clips only if the user flags a specific framing or
content issue with a specific shot.
