# video-producer

An AI-orchestrated video production system for **Claude Code**. Describe what you want in plain language — the agent handles research, scripting, asset generation, editing, and final composition.

> Based on [OpenMontage](https://github.com/calesthio/OpenMontage) by calesthio (AGPLv3). See [NOTICE](NOTICE) for details.

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPLv3-blue.svg" alt="License"></a>
</p>

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **FFmpeg** — `brew install ffmpeg` / `sudo apt install ffmpeg`
- **Node.js 18+**
- **Claude Code**

### Install

```bash
git clone https://github.com/johnnyjclin/video-producer.git
cd video-producer
make setup
```

Open the project in Claude Code and tell it what you want:

```
Make a 60-second animated explainer about how neural networks learn
```

> **No `make`?** Run manually: `pip install -r requirements.txt && cd remotion-composer && npm install && cd .. && pip install piper-tts && cp .env.example .env`

### Add API Keys (optional — more keys = more tools)

Copy `.env.example` to `.env` and fill in what you have. Every key is optional.

```bash
# Image + video gateway
FAL_KEY=your-key               # FLUX images + Veo, Kling, MiniMax video

# Free stock media
PEXELS_API_KEY=your-key
PIXABAY_API_KEY=your-key
UNSPLASH_ACCESS_KEY=your-key

# Voice & music
ELEVENLABS_API_KEY=your-key
SUNO_API_KEY=your-key

# Other providers
OPENAI_API_KEY=your-key
GOOGLE_API_KEY=your-key
RUNWAY_API_KEY=your-key
HEYGEN_API_KEY=your-key
XAI_API_KEY=your-key
```

---

## What You Get With Zero API Keys

| Capability | Free Tool |
|-----------|-----------|
| Narration | Piper TTS (offline) |
| Stock footage | Archive.org, NASA, Wikimedia Commons |
| Extra stock | Pexels, Unsplash, Pixabay (free dev keys) |
| Composition | Remotion (React-based) + HyperFrames (HTML/GSAP) |
| Post-production | FFmpeg |
| Subtitles | Built-in word-level timing |

---

## Pipelines

| Pipeline | Best For |
|----------|----------|
| `animated-explainer` | Topic → fully generated explainer |
| `animation` | Motion graphics, kinetic typography |
| `avatar-spokesperson` | Avatar-driven presenter videos |
| `cinematic` | Trailers, teasers, mood-led edits |
| `clip-factory` | Many clips from one long source |
| `hybrid` | Source footage + AI-generated support visuals |
| `localization-dub` | Subtitle, dub, translated variants |
| `podcast-repurpose` | Podcast highlights to video |
| `screen-demo` | Screen recordings and walkthroughs |
| `talking-head` | Footage-led speaker videos |

Every pipeline follows the same structured flow:

```
research → proposal → script → scene_plan → assets → edit → compose
```

---

## Architecture

```
video-producer/
├── tools/              # Python tools (video, audio, image, analysis, avatar, subtitle)
├── pipeline_defs/      # YAML pipeline manifests
├── skills/             # Markdown stage director skills
├── schemas/            # JSON schemas for artifact validation
├── styles/             # Visual style playbooks (YAML)
├── remotion-composer/  # React/Remotion composition engine
├── lib/                # Core infrastructure (checkpoints, pipeline loader, config)
└── tests/              # Contract tests and QA harness
```

### Three-Layer Knowledge Architecture

```
Layer 1: tools/ + pipeline_defs/   "What exists" — capabilities + orchestration
Layer 2: skills/                   "How to use it" — stage director skills, quality bars
Layer 3: .agents/skills/           "How it works" — provider-specific knowledge packs
```

---

## How It Works

The AI agent IS the orchestrator. No Python orchestration logic — all creative decisions, review criteria, and quality standards live in readable YAML manifests and Markdown skills.

```
Read pipeline manifest (YAML)
  → Read stage director skill (MD)
    → Call Python tools
      → Self-review via reviewer skill
        → Checkpoint state (JSON)
          → Present to human for approval
            → Render (Remotion / HyperFrames / FFmpeg)
              → Post-render validation
                → Final video output
```

---

## Testing

```bash
# Contract tests (no API keys needed)
make test-contracts

# All tests
make test
```

---

## License

[GNU AGPLv3](LICENSE)

---

## Acknowledgements

This project is a fork of [OpenMontage](https://github.com/calesthio/OpenMontage) by calesthio, licensed under the GNU AGPLv3. The core pipeline architecture, tool registry, stage director skill system, and composition engine are based on upstream OpenMontage. This fork removes non-Claude Code agent integrations and NoirsBoxes-specific commercial content, and is maintained independently.
