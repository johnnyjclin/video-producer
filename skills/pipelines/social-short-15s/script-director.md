# Script Director — social-short-15s

## When To Use

`brief` is approved. Time to write the 5-section script that hits the
fixed `Hook (3s) + Mid_1 (3s) + Mid_2 (3s) + Mid_3 (3s) + CTA (3s)`
structure.

## Output

A `script` artifact:

```yaml
brief_ref: <brief_id>
subject_prefix: <copied verbatim from brief>
sections:
  - id: hook
    seconds: 3
    narration: "I cancelled three productivity apps last month."
    on_screen_text: "I cancelled 3 apps."
    notes: "Land first 4 words by 1.5s"
  - id: mid_1
    seconds: 3
    narration: "..."
    ...
  - id: mid_2
    seconds: 3
    ...
  - id: mid_3
    seconds: 3
    ...
  - id: cta
    seconds: 3
    narration: "Follow for the experiment results."
    on_screen_text: "Follow for results"
total_seconds: 15
```

## Process

### 1. Length budget per section

Each section is exactly 3 seconds. That's:

- **English**: 8-12 words spoken, OR 3-5 words on-screen text
- **Mandarin**: 15-22 syllables spoken, OR 6-10 characters on-screen text

If the user's draft narration runs over, cut. Don't compress to mumble.

### 2. Section-by-section job

| Section | Job | Common mistake |
|---|---|---|
| `hook` | Earn 3 more seconds. State the promise/claim/question. | Setup with no payoff in the first 1.5s |
| `mid_1` | Show the WHY or set the stakes | Restating the hook |
| `mid_2` | Show the HOW or the central proof | Listing multiple ideas |
| `mid_3` | Show the LAND — payoff, lesson, surprising twist | Petering out |
| `cta` | Tell viewer exactly what to do | Vague "let me know what you think" |

If the user's brief is product-led (selling something), the structure
shifts slightly:

| Section | Product-led version |
|---|---|
| `hook` | The pain or the desire |
| `mid_1` | Show the product solving it |
| `mid_2` | One specific feature or proof point |
| `mid_3` | Outcome / before-after |
| `cta` | Where to buy / try / learn more |

### 3. On-screen text vs narration

These are NOT the same. Narration is spoken (TTS or VO). On-screen text
is what burns into the video.

Rules:

- On-screen text is shorter than narration
- On-screen text uses present tense, no punctuation, kinetic phrasing
- Hook on-screen text MUST land by 1.5s — it's the scroll-stop
- CTA on-screen text MUST be visible for the full 3 seconds

If TTS isn't configured (check `tools_available` from preflight), the
short runs silent — on-screen text is the only thing the viewer reads.
In that case, on-screen text becomes the spoken-line equivalent and
needs to carry more meaning.

### 4. Carry the subject prefix forward

Copy `brief.subject_prefix` into `script.subject_prefix` verbatim. This
gets passed to `scene-director` and ultimately to every prompt. Do not
mutate it here.

## Review

`human_approval_default: true`. Present:

```
HOOK (3s):    "I cancelled three productivity apps last month."
              → on-screen: "I cancelled 3 apps."
MID_1 (3s):   "Notion, Todoist, and Sunsama. All paid."
              → on-screen: "$240/year gone"
MID_2 (3s):   "Replaced everything with one plain text file."
              → on-screen: "→ one .txt file"
MID_3 (3s):   "Three weeks later, I'm shipping more."
              → on-screen: "more shipped, less tabs"
CTA (3s):     "Follow for the 30-day result."
              → on-screen: "follow → 30-day result"

Total: 15s. Approve? [yes / revise <section>]
```

## Section count flexibility

Default is 5 sections (3s each). The pipeline accepts **4-6 sections**
totaling 15s, picked to fit the narrative pattern from `brief.narrative_mode`:

| narrative_mode | Recommended section count | Why |
|---|---|---|
| `object_led` ("day in life", transformation) | 4 sections × ~3.75s | Slower beats let the object's journey breathe |
| `environment_led` (time-in-place) | 5 sections × 3s | Default — establishing/people/detail/time-shift/return |
| `pov` (first-person reveal) | 5 sections × 3s | Default — see/reach/interact/reveal/resolve |
| `stylized` (animation) | 5-6 sections | Faster cuts read more "animated" |
| `character_led` (single protagonist) | 5 sections × 3s | Default; 1 face shot + 4 face-avoiding |

If you choose non-default count, every section ID must still include
exactly one `hook` and one `cta`. Middle sections are `mid_1`, `mid_2`, etc.

## Anti-patterns

- Don't write filler — every section advances ONE idea
- Don't write "as I was saying earlier" or any phrase that assumes prior
  context. The hook stands alone or it dies.
- Don't write more than 6 sections — past 6 the pacing fragments
- Don't write less than 4 — total runtime can't carry meaningful narrative
- Don't pick visuals here — leave that to `scene-director`. Just write
  the words.
