# Content Generation Agent 🎨

AI-powered social media content generator using GPT-5, DALL-E 3, and Sora-2.

This repo now separates content generation from compliance. The Content agent generates media and captions; Design and Policy are dedicated agents you can call via CLI commands.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your OpenAI API key to .env
OPENAI_API_KEY=sk-your-key-here

# 3. Run
python main.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│                    (CLI Interface)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              content_generator_agent.py                     │
│         (LangChain Agent with GPT-5)                        │
│   Tools: generate_image, generate_video, generate_caption   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌────────────────────────┐   ┌────────────────────────┐
│   agents/design_agent  │   │   agents/policy_agent  │
│  (Design Compliance)   │   │  (Policy Compliance)   │
│  Tool: check_design_*  │   │  Tool: check_policy_*  │
└────────────────────────┘   └────────────────────────┘
```

## Tools

| Tool                      | Description                               | Model    | Used by                      |
| ------------------------- | ----------------------------------------- | -------- | ---------------------------- |
| `generate_image`          | Creates images, saves locally + URL       | DALL-E 3 | Content agent                |
| `generate_video`          | Creates videos with aspect ratio mapping  | Sora-2   | Content agent                |
| `generate_caption`        | Platform-optimized captions + hashtags    | GPT-5    | Content agent                |
| `check_policy_compliance` | Reviews content against policy guidelines | GPT-5    | Policy agent (dedicated)     |
| `check_design_compliance` | Reviews visuals against design guidelines | GPT-5    | Design agent (dedicated)     |

## Aspect Ratio Options

| Ratio | Resolution | Best For                   |
| ----- | ---------- | -------------------------- |
| 16:9  | 1920x1080  | YouTube, LinkedIn, Twitter |
| 9:16  | 1080x1920  | TikTok, Reels, Shorts      |
| 1:1   | 1080x1080  | Instagram Feed, Facebook   |
| 4:5   | 1080x1350  | Instagram Feed (optimal)   |
| 21:9  | 2560x1080  | Cinematic content          |

## Configuration

The CLI prompts for these settings on startup:

- Video Duration: 5-60 seconds
- Aspect Ratio: 16:9 / 9:16 / 1:1 / 4:5 / 21:9 (with resolution)
- Captions: Enable/disable auto-caption generation
- Caption Style: professional / casual / creative
- Image Size: 1024x1024 / 1792x1024 / 1024x1792
- Image Quality: standard / hd
- Auto Compliance: if enabled, the CLI will PROMPT you to run design/policy checks after content generation

## CLI Commands

| Command     | Description                       |
| ----------- | --------------------------------- |
| `/config`   | Reconfigure settings              |
| `/settings` | View current settings             |
| `/clear`    | Clear conversation history        |
| `/design`   | Run design compliance review      |
| `/policy`   | Run policy compliance review      |
| `/help`     | Show help                         |
| `/exit`     | Exit application                  |

## Compliance Checking

Compliance is now handled by dedicated agents:

- Design Compliance: via `agents/design_agent.py` (CLI `/design`)
- Policy Compliance: via `agents/policy_agent.py` (CLI `/policy`)

Behavior when Auto Compliance is enabled:
- After generating content, the CLI asks if you want to run policy/design checks now.
- If you choose yes, it will collect the minimal inputs and run both agents.

Guidelines used:
- Policy: `guidelines/policy_guidelines.md`
- Design: `guidelines/design_guidelines.md`

## Output

Generated content is saved to:

```
generated_content/
├── images/     # DALL-E 3 generated images
└── videos/     # Sora-2 generated videos
```

## File Structure

```
content-generation-agent - Copy/
├── main.py                      # CLI entry point
├── content_generator_agent.py   # Content agent (image/video/caption)
├── agents/
│   ├── __init__.py
│   ├── design_agent.py          # Dedicated design compliance agent
│   └── policy_agent.py          # Dedicated policy compliance agent
├── config.py                    # Configuration management
├── tools/
│   ├── __init__.py
│   ├── image_generator.py       # DALL-E 3 + local save
│   ├── video_generator.py       # Sora-2 + aspect ratios
│   ├── caption_generator.py     # Captions + hashtags
│   ├── policy_checker.py        # Policy compliance tool
│   └── design_checker.py        # Design compliance tool
├── guidelines/
│   ├── policy_guidelines.md     # Policy rules
│   └── design_guidelines.md     # Design rules
├── generated_content/           # Output folder (auto-created)
├── .env                         # API keys
├── requirements.txt
└── README.md
```

## Zero Data Retention Note

If you encounter a "zero data retention" error with Sora API, you need to contact OpenAI sales team to request ZDR approval for your organization. This is not a code workaround - it's a policy setting that must be enabled by OpenAI for your account.

## Integration Notes

- `ContentGeneratorAgent` class can be imported and used directly for media generation and captions.
- `agents.design_agent.DesignComplianceAgent` and `agents.policy_agent.PolicyComplianceAgent` can be used standalone for reviews.
- `config.py` allows programmatic configuration.
- Tools can be imported individually from `tools/` module.
