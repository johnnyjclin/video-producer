# Scene Director — social-short-15s

## When To Use

`script` is approved. Now translate each of the 5 sections into a visual
spec that an asset director can hand to `comfyui_image` and
`comfyui_video`.

**Read `.agents/skills/comfyui/SKILL.md` before this stage.** Every
decision below references it.

## Output

A `scene_plan` artifact. **4-6 shots totaling 15s.** Default is 5 shots,
but the narrative pattern can flex to 4 (slower, more contemplative) or
6 (faster, more cuts).

```yaml
brief_ref: <brief_id>
script_ref: <script_id>
subject_prefix: <copied verbatim>
narrative_mode: <copied from brief>
shots:
  - shot_id: 1
    section_id: hook
    target_seconds: 3.0          # display duration in final video
    motion_seconds: 2.0          # actual SVD motion (always 2.0s on 8GB)
    static_pad_intro_s: 0.3      # keyframe held before motion starts
    static_pad_outro_s: 0.7      # last motion frame held after motion ends
    composition: "tight close-up, eye contact"
    setting: "sun-lit minimalist desk, blurred plain wall behind"
    image_prompt: "<full prompt — see prompt assembly below>"
    image_workflow: flux_schnell_gguf
    image_size: {width: 768, height: 1344}    # high-res keyframe for static pads
    svd_input_size: {width: 432, height: 768} # downsized copy fed into SVD
    video_workflow: svd_image_to_video
    video_motion: subtle           # → motion_bucket_id 80-100
    notes: "Subject looks up at camera mid-action. NO smile."
  - shot_id: 2
    ...
total_target_seconds: 15.0
```

### Shot duration budget (the "motion sandwich" pattern)

SVD on 8GB outputs **exactly 14 frames at 7fps = 2.0 seconds of motion.
This is fixed.** Don't ask for 3.0s of motion — you'll either OOM (more
frames) or get visible jitter (lower fps). Instead, **frame each shot as
a sandwich**: keyframe held briefly → 2s of SVD motion → final frame
held briefly. Viewers read this as deliberate pacing, not as freezing.

Allocate `static_pad_intro_s` + `motion_seconds` (always 2.0) +
`static_pad_outro_s` to hit each shot's `target_seconds`:

| Shot intent | target_seconds | intro_s | motion_s | outro_s | Why |
|---|---|---|---|---|---|
| Hook (high impact) | 2.5 | 0.2 | 2.0 | 0.3 | Tight, fast-paced |
| Mid (default) | 3.0 | 0.3 | 2.0 | 0.7 | Room to read overlay |
| Mid (contemplative) | 3.5 | 0.5 | 2.0 | 1.0 | Atmosphere shots |
| CTA (text-heavy) | 3.0 | 0.5 | 2.0 | 0.5 | Time to read CTA |
| Static-only shot | 2.0 | varies | 0.0 | varies | When motion adds nothing — set `video_workflow: null` |

**Common 15-second layouts**:
- `5 × 3.0s` — default balanced narrative (14 motion frames per shot)
- `2.5 + 3.0 + 3.0 + 3.0 + 3.5` — fast hook + contemplative landing
- `4 × 3.75s` — slower, transformation-style stories (object_led "day in life")
- `2.0 + 2.5 + 2.5 + 2.5 + 2.5 + 3.0` — 6 shots, fast cuts (high-energy brands)

Pick the layout that fits the narrative pattern and brief tone, not the
default 5×3.0.

## Process

### 1. Pick the narrative pattern from `brief.narrative_mode`

The pattern dictates EVERYTHING downstream — shot count, framing
language, motion intent, and which shots dare show a face. **Use the
template from "Narrative Pattern Templates" below that matches
`brief.narrative_mode`.** Don't invent your own structure.

### 2. One shot per section, in order

Mapping is rigid:

| Section | Shot | Visual job |
|---|---|---|
| hook | 1 | Stop the scroll. High-impact framing, sharp focus, eye contact if person-led. |
| mid_1 | 2 | Establish stakes. Wider context shot or detail revealing the WHY. |
| mid_2 | 3 | The proof point. The specific thing happening. |
| mid_3 | 4 | The land. Outcome shot — before/after, result, expression. |
| cta | 5 | Branded sign-off. Logo / product / hand gesture. Clean composition. |

### 2. Pick the image workflow per shot

Per the comfyui skill's heuristic:

- Hook (shot 1) → `flux_schnell_gguf` (best first impression)
- CTA (shot 5) → `flux_schnell_gguf` (brand frame, often has text)
- Middle (shots 2-4) → `sdxl_lightning` (volume, faster iteration)

**Override rules:**
- All 5 shots use `flux_schnell_gguf` if FLUX models are loaded but SDXL
  isn't — never split workflows just for the sake of variety.
- All 5 use `sdxl_lightning` if FLUX isn't available (check tool status
  via preflight).
- If the brief explicitly requires text inside the image (e.g.
  "show the price '$9' on screen") → that shot MUST use FLUX. SDXL
  mangles in-image text.

### 3. Pick the video workflow + motion intensity

Default `video_workflow: svd_image_to_video` for all 5 shots.

Set `video_motion` per shot intent (this becomes `motion_bucket_id` at
asset stage):

| Intent | `video_motion` | bucket_id range |
|---|---|---|
| Portrait, food, product hero | `subtle` | 60-100 |
| Default conversational shot | `balanced` | 110-140 |
| Action, environment, reveal | `dramatic` | 150-200 |

Don't go above 200 — warping artifacts dominate. If a shot needs more
motion than that, it's the wrong shot type for SVD; consider a static
keyframe with Ken Burns instead (set `video_workflow: null` and let
compose stage handle motion via Remotion).

### 4. Assemble the image prompt

For every shot:

```
<subject_prefix>, <shot-specific action>, <composition>, <setting>, <lighting>, <style/medium>
```

Example for the productivity-apps short, shot 1 (hook):

```
a 30-year-old freelancer at a sun-lit desk, plain white tee, clean
wooden surface, looking up from his laptop with a quiet exhale,
tight close-up, eye contact, sun-lit minimalist desk, blurred plain
wall behind, soft window light from left, photographic, 35mm,
shallow depth of field, cinematic
```

If the workflow is `flux_schnell_gguf`: write in natural sentences (as
above).

If the workflow is `sdxl_lightning`: rewrite the same shot in tag style:

```
30yo freelancer, sun-lit desk, white tee, looking up from laptop,
quiet exhale, tight close-up, eye contact, blurred wall, soft window
light, 35mm, shallow depth of field, cinematic, photorealistic, sharp
focus
```

The prompt FORMAT must match the workflow. Don't send tag-style to FLUX
or sentence-style to SDXL.

### 5. Pick image size by aspect ratio

From `brief.aspect_ratio`, pick TWO sizes per shot:

- `image_size`: the higher-resolution keyframe kept for static intro/outro pads
- `svd_input_size`: the downsized copy fed into SVD for the 2-second motion clip

They do NOT match on 8GB hardware; the mismatch is intentional:

| Aspect | FLUX keyframe | SDXL Lightning keyframe | SVD input size |
|---|---|---|---|
| 9:16 (Reels/TikTok/Shorts) | 768×1344 | 768×1280 | 432×768 — yes, smaller; 8GB SVD ceiling |
| 1:1 (square) | 1024×1024 | 1024×1024 | 576×576 |

The keyframe size > SVD size discrepancy is **intentional**. asset-director
will resize the keyframe down to `svd_input_size` for SVD input, but the
higher-res keyframe also gets used as the static intro/outro frames at the
keyframe's native resolution. Compose-director scales up the SVD motion
frames to match the final output.

Don't go above the comfyui skill's per-workflow ceiling on a 4060 8GB.

### 6. Visual variety check

Across 5 shots, you must vary:

- **Composition**: don't run 3 close-ups in a row. Mix close / medium / wide.
- **Camera angle**: eye-level / high / low — vary at least once
- **Action vs static**: alternate active and contemplative beats

If the script only supports one composition type (rare), explicitly note
it and accept the tradeoff — but flag it in the `notes` field.

## Review

`human_approval_default: true`. Present a compact 5-row table:

```
SHOT | sec | workflow      | motion    | composition         | summary
1    | 3   | flux_schnell  | subtle    | tight close-up      | freelancer looks up from laptop
2    | 3   | sdxl_lightning| balanced  | medium wide         | three branded apps on phone screen
3    | 3   | sdxl_lightning| balanced  | overhead detail     | hand typing in plain text editor
4    | 3   | sdxl_lightning| dramatic  | over-shoulder wide  | ship-it celebration moment
5    | 3   | flux_schnell  | subtle    | branded centered    | logo with "follow → 30-day result"

Approve scene plan? [yes / revise shot N]
```

## Narrative Pattern Templates

Pick the template that matches `brief.narrative_mode`. Each is tuned for
realistic 8GB local output — no shot type that SVD/FLUX/SDXL silently
fails on. Adjust shot details to fit the brief, but **keep the framing
discipline of the pattern.**

### Pattern A — `object_led`: "The Object's Day"

Story carried by an object that moves, transforms, or is acted upon.
**No faces.** No human protagonist visible.

| Shot | Job | Composition example | Motion intent |
|---|---|---|---|
| 1 (hook) | Reveal the object in stillness | Tight macro, dramatic lighting | `subtle` (steam rising, light shift) |
| 2 (mid_1) | First interaction / change | Hand enters frame, brief touch | `balanced` (object moves) |
| 3 (mid_2) | Transformation / use | The object doing its thing | `balanced` |
| 4 (mid_3) | Aftermath / consequence | The object after, surroundings changed | `subtle` |
| 5 (cta) | Branded resolution | Object + logo + clean composition | `subtle` |

**Image workflow**: FLUX schnell GGUF for hook + CTA, SDXL Lightning for middle.

**Why this works on 8GB**: SVD handles inanimate subjects beautifully —
no face deformation, no hand artifacts, no two-character problem.

---

### Pattern B — `environment_led`: "Time in a Place"

Locked location, the story is what changes — light, who's there, what's
on the table. **People appear as silhouettes, backs, hands — never centered faces.**

| Shot | Job | Composition example | Motion intent |
|---|---|---|---|
| 1 (hook) | Establishing wide of empty space, charged with anticipation | Wide angle, golden hour or pre-dawn | `subtle` (light shift, dust in air) |
| 2 (mid_1) | Someone enters (back/silhouette only) | Over-shoulder or back-to-camera | `balanced` (slow walk-in) |
| 3 (mid_2) | Moment in the space — detail | Close-up of hands or object on table | `balanced` |
| 4 (mid_3) | Time passes — same shot, later | Same composition as shot 1 but transformed | `subtle` (changed light) |
| 5 (cta) | Empty space again + brand mark | Same wide as shot 1 + overlay | `subtle` |

**Image workflow**: FLUX schnell for shots 1, 4, 5 (the establishing
beats); SDXL Lightning for 2, 3.

**Why this works on 8GB**: environment continuity is enforced by the
locked composition. If the chair moves slightly between shots, viewers
read it as time passing, not as inconsistency.

---

### Pattern C — `pov`: "First-Person Reveal"

Camera is the protagonist's eyes. Hands and objects are the actors.
**Never the protagonist's face.** This is the most flexible pattern.

| Shot | Job | Composition example | Motion intent |
|---|---|---|---|
| 1 (hook) | What the protagonist sees first | First-person POV, foreground focal point | `subtle` |
| 2 (mid_1) | Reach toward / approach | Hands enter frame from below | `balanced` |
| 3 (mid_2) | Interaction / discovery | Hands manipulate the object | `balanced` |
| 4 (mid_3) | Reveal / payoff | Object opens / changes / shows information | `balanced` |
| 5 (cta) | Final beat + on-screen text | Object placed back, brand overlay | `subtle` |

**Image workflow**: FLUX schnell throughout (POV needs natural-language
prompts; SDXL gets confused by "first-person" framing).

**Why this works on 8GB**: hands at low-medium motion intensity (bucket
70-110) are the ONE area where SVD is genuinely good. POV bypasses every
SVD failure mode.

---

### Pattern D — `stylized`: "Animated Motif"

Strong illustrative style, animation-first. The style itself enforces
visual consistency.

| Shot | Job | Composition example | Motion intent |
|---|---|---|---|
| 1-5 | Free — story can be character or environment-led, the style carries it | Match the chosen art style strictly | `balanced` to `dramatic` |

**Image workflow**: SDXL Lightning + style LoRA (e.g., flat-vector,
pixel, anime, watercolor).

**Video workflow**: ⚠️ AnimateDiff template not yet shipped. If this
mode is selected, `asset-director` will need to fall back to per-shot
SVD on the still frame — output may look more like motion-stills than
animation. Flag this in scene_plan.notes.

---

### Pattern E — `character_led`: "Single Protagonist" (with explicit risk)

The protagonist must be present and recognizable in multiple shots.
**Required**: `subject_prefix` is maximally detailed. **Recommended**:
the user has approved IPAdapter usage at idea stage — otherwise expect
30-50% face drift.

Without IPAdapter, structure to MINIMIZE face shots:

| Shot | Job | Composition trick to reduce drift |
|---|---|---|
| 1 (hook) | Establish protagonist | Tight close-up — best chance at consistency |
| 2 (mid_1) | Action | Over-shoulder or back-to-camera (no face) |
| 3 (mid_2) | Detail | Hands or object in protagonist's possession (no face) |
| 4 (mid_3) | Outcome | Wide shot, protagonist small in frame (face less critical) |
| 5 (cta) | Resolution | Protagonist's silhouette OR back-to-camera + text overlay |

This "1 face shot + 4 face-avoiding shots" structure is the realistic
8GB compromise. Don't write 5 face close-ups; the result will look like
5 different people.

---

### Pattern F — `dialogue`

Pipeline rejects this mode at idea stage. Should not reach scene-director.
If somehow it does, raise an error and refer back to idea-director.


