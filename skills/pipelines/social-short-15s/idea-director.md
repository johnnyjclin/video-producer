# Idea Director — social-short-15s

## When To Use

The user wants a 15-second social short on a specific topic, platform, or
angle. Typical inputs from the host 小編 agent:

- "Make a 15s Reel about our new oat-milk latte"
- "Cut a TikTok hook about Q3 retention numbers"
- "Shorts version of the pricing page argument"

Skip this stage entirely **only** when the host agent already supplies a
pre-built brief artifact.

## Output

A `brief` artifact with these required fields:

| Field | Notes |
|---|---|
| `platform` | `instagram_reels` \| `tiktok` \| `youtube_shorts` — drives aspect ratio + caption style |
| `aspect_ratio` | `9:16` default; `1:1` only if explicitly requested |
| `duration_seconds` | Always `15` for this pipeline |
| `topic` | One sentence — what is this short about? |
| `hook_angle` | A concrete promise, question, or contrarian claim. NOT "talk about X". |
| `cta` | One verb + one object. "Follow for daily tips" / "Tap link in bio" / "Save this for later" |
| `narrative_mode` | One of `object_led` \| `environment_led` \| `pov` \| `stylized` \| `character_led` \| `dialogue`. **See viability table below — this decides whether the brief stays local or needs cloud.** |
| `subject_prefix` | The locked subject description carried into every shot prompt — the consistency anchor. See `.agents/skills/comfyui/SKILL.md` Option 1. |
| `tone` | 2-3 adjectives (`warm + intimate`, `kinetic + bold`, `quiet + earnest`) |
| `target_audience` | Who scrolls past unless this is good? Be specific. |

## Narrative Mode — viability on 8GB local (HARD RULE)

The single most important brief decision. Be honest with the user
*before* approval — don't ship a doomed brief into production.

| Mode | What it is | Local 8GB? | When to recommend |
|---|---|---|---|
| `object_led` | Story told via objects, no faces (alarm clock → coffee → laptop → ...) | ✅ **Excellent** | Default for product, café, daily-life, lifestyle brands |
| `environment_led` | One locked location, time-of-day or arrival/departure changes | ✅ **Excellent** | Spaces, restaurants, studios, atmosphere brands |
| `pov` | First-person POV, hands and objects, never the protagonist's face | ✅ **Excellent** | Unboxing, ritual content, reveal moments, message-carrying |
| `stylized` | Animation/illustration/pixel/anime — style itself enforces consistency | ✅ **Good** | Brand-driven illustrative content, kid-friendly, gaming aesthetic. Requires AnimateDiff workflow (not yet shipped — flag as gap) |
| `character_led` | One protagonist across multiple shots, photoreal | ⚠️ **Risky without IPAdapter** | Tell user: "This works at ~50-70% consistency without IPAdapter (face will drift). Either accept the variance, or wait for IPAdapter template, or budget for 2-3× regen attempts per shot." |
| `dialogue` | Two+ people talking, lip-sync, conversation | ❌ **Recommend cloud** | "Local 8GB cannot do lip-sync or two-character continuity. This brief should run on HeyGen / Sync Labs / Veo 3 instead. Want me to switch to `avatar-spokesperson` pipeline?" |

### How to choose with the user

1. Ask: "What is this short *about* — a product/object, a place, a feeling, or a person?"
   - Object/product → `object_led`
   - Place/atmosphere → `environment_led`
   - Feeling/message/reveal → `pov`
   - A specific person/character → `character_led` or `dialogue`
2. If user says "person/character," **immediately surface the viability tradeoff above**. Don't approve a `character_led` brief without the user knowing the consistency risk.
3. If user says "two people talking" or "podcast clip" or "interview style," **stop and recommend a different pipeline**. Don't accept the brief.

### Subject prefix rules per mode

The `subject_prefix` looks different per mode:

- `object_led`: describe THE OBJECT being followed. *"a single steaming bowl of beef noodle soup, brushed-metal bowl, dark wooden table, warm tungsten light"*
- `environment_led`: describe THE PLACE. *"a small Taipei specialty coffee shop, exposed concrete walls, warm wood counter, pendant lamps"*
- `pov`: describe THE WORLD AS SEEN. *"first-person view, hands visible occasionally, plain white tee sleeves, modern apartment"*
- `stylized`: describe THE STYLE first, then subject. *"flat 2D vector illustration, pastel palette, soft outlines, a curious cat"*
- `character_led`: describe THE PERSON in maximum detail (locks consistency). *"a 30-year-old Taiwanese woman, shoulder-length black hair, round wire-frame glasses, white linen shirt, calm expression"*
- `dialogue`: not applicable — pipeline rejects this mode.

The more specific the prefix, the higher the consistency hit rate. Resist the urge to write generic prefixes like "a young person" — they fail consistency every time.

## Process

### 1. Classify the brief

Three modes the user typically lands in:

- **Concrete brief** — they tell you platform, hook, CTA, tone. Just
  validate and assemble the artifact.
- **Half brief** — they have a topic but no angle. You owe them 2-3
  hook angles before locking the brief. Don't pick for them.
- **Vague request** — "make a Reel about productivity". You owe them a
  topic-narrowing question first. Don't generate filler.

### 2. Lock the hook angle (the most important field)

A weak hook makes everything downstream weak. Apply this filter:

- **Specific**: "I cancelled three productivity apps last month" beats
  "Productivity apps are overrated"
- **Time-bound or quantified**: a number, a date, a duration
- **Self-contained**: the viewer should understand the claim from the
  hook alone, without context

Reject weak hooks back to the user before approval. Don't smuggle them
through to script stage and discover the problem there.

### 3. Choose the platform

Default to `instagram_reels` if unspecified. Map:

| Platform | Aspect | Caption baked in? | Notes |
|---|---|---|---|
| `instagram_reels` | 9:16 | yes (auto-burned by compose) | 1080×1920 output |
| `tiktok` | 9:16 | yes | 1080×1920 output |
| `youtube_shorts` | 9:16 | yes | 1080×1920 output |
| `instagram_post` | 1:1 | optional | 1080×1080 — only use this for non-Reels formats |

### 4. Lock narrative_mode + subject prefix together

These two fields are linked. Pick `narrative_mode` first (using the
viability table above), then write `subject_prefix` in the format that
mode demands (see "Subject prefix rules per mode" above).

If the user pushes back on a downgrade ("but I wanted a person in it"),
the conversation is:

> "On a 4060 8GB the protagonist will visibly shift across 5 shots
> ~30-50% of the time. Three options: (a) shift to `object_led` or `pov`
> and the person becomes implied rather than seen — usually stronger
> creatively anyway; (b) accept the consistency risk and budget for
> regen; (c) escalate to cloud (Runway/Veo) for ~$0.20-0.50 per short.
> Which?"

Don't smuggle a doomed `character_led` brief into production by being
polite about it.

### 5. Match tone to a playbook

Pull `compatible_playbooks` from the manifest:

| Tone | Playbook |
|---|---|
| Energetic, bold, social-native | `flat-motion-graphics` |
| Calm, professional, brand-safe | `clean-professional` |
| Custom requirements | `custom_allowed: true` — define inline |

## Review

This stage's `human_approval_default: true`. Present the brief as a
compact summary AND the viability flag, then **wait** before script stage:

```
Platform:        instagram_reels (9:16, 1080×1920)
Narrative mode:  pov ✅ excellent local viability
Hook:            "I cancelled three productivity apps last month"
CTA:             "Follow for the experiment results"
Subject prefix:  "first-person view, hands visible occasionally, plain white tee, sun-lit minimal desk"
Tone:            minimal + earnest
Playbook:        clean-professional

Approve? [yes / change <field>]
```

If `narrative_mode` is `character_led` or `dialogue`, the summary MUST
include the warning verbatim — never let the user discover the
consistency problem at asset stage.

## Anti-patterns

- Don't research the topic — that's not this pipeline's job. If the user
  needs deep research before scripting, that's a different deliverable
  and a different plugin. Tell them so honestly; don't try to do it here.
- Don't generate the hook line itself yet — that's `script-director`.
- Don't pick visuals — that's `scene-director`.
- Don't accept "everyone" or "general audience" as `target_audience` —
  push back for a specific cohort.
