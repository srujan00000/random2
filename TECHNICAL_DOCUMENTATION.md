# Technical Documentation: Content Generation Agent

## Overview

This is a LangChain-based AI agent system for social media content workflows. It now separates concerns into:
- Content Generation agent: images, videos, and captions
- Design Compliance agent: reviews visuals against design guidelines
- Policy Compliance agent: reviews content against policy guidelines

A CLI orchestrates configuration and interaction, and optionally prompts to run compliance after content generation.

---

## Architecture (Updated)

```
User Input (CLI)
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                     main.py (Entry Point)                    │
│  - Loads environment variables (.env)                        │
│  - Prompts user for configuration via config.py              │
│  - Initializes ContentGeneratorAgent                         │
│  - Commands: /design, /policy for dedicated agents           │
│  - Optional post-gen prompt to run compliance                │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│           content_generator_agent.py (Content Agent)         │
│  - Uses langchain.agents.create_agent()                      │
│  - Model: "openai:gpt-5"                                     │
│  - Injects system prompt with current config                 │
│  - Registers 3 tools: image, video, caption                  │
│  - Maintains conversation history                            │
└──────────────────────────────────────────────────────────────┘
       │                                  ┌────────────────────┐
       │                                  │  /design, /policy  │
       │                                  ▼                    │
       │                  ┌────────────────────────────────────┴───────────────┐
       │                  │                    agents/                         │
       │                  ├────────────────────────────────────────────────────┤
       │                  │  design_agent.py  → check_design_compliance tool   │
       │                  │  policy_agent.py  → check_policy_compliance tool   │
       │                  └────────────────────────────────────────────────────┘
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Tool Execution Layer                      │
├──────────────────────────────────────────────────────────────┤
│  generate_image    │ DALL-E 3 API → downloads → local file  │
│  generate_video    │ Sora-2 API → downloads → local file    │
│  generate_caption  │ GPT-5 chat completion → formatted text │
│  check_policy      │ GPT-5 + guidelines → policy report     │
│  check_design      │ GPT-5 + guidelines → design report     │
└──────────────────────────────────────────────────────────────┘
```

---

## Module Breakdown

### 1) `main.py` - CLI Entry Point

Purpose:
- Interactive terminal interface and high-level orchestration

Key responsibilities:
- Load `.env`, validate `OPENAI_API_KEY`
- Collect user configuration via `config.get_config_from_user()`
- Instantiate `ContentGeneratorAgent`
- Parse commands:
  - `/design`: interactive prompts → `DesignComplianceAgent`
  - `/policy`: interactive prompts → `PolicyComplianceAgent`
  - `/config`, `/settings`, `/clear`, `/help`, `/exit`, `/quit`
- After each normal content interaction, if `auto_compliance_check=True`, the CLI prompts:
  - “Run policy/design compliance checks now? (yes/no)”
  - If yes, it runs a combined `run_compliance_flow()` asking for minimal inputs and calling the two dedicated agents.

Notes:
- Compliance is no longer auto-invoked by the content agent itself; it’s a CLI-driven prompt for clarity and reliability.

---

### 2) `config.py` - Configuration Management

Purpose:
- Dataclass-based configuration with interactive prompts and validation.

Key elements:
```python
ASPECT_RATIO_OPTIONS = {
    "16:9": {"size": "1920x1080", "desc": "Landscape - YouTube, LinkedIn, Twitter"},
    "9:16": {"size": "1080x1920", "desc": "Portrait - TikTok, Reels, Shorts"},
    "1:1": {"size": "1080x1080", "desc": "Square - Instagram Feed, Facebook"},
    "4:5": {"size": "1080x1350", "desc": "Portrait - Instagram Feed optimal"},
    "21:9": {"size": "2560x1080", "desc": "Ultra-wide - Cinematic content"}
}

@dataclass
class GenerationConfig:
    video_duration: int = 10
    video_aspect_ratio: str = "16:9"
    enable_captions: bool = True
    caption_style: str = "professional"
    image_size: str = "1024x1024"
    image_quality: str = "hd"
    auto_compliance_check: bool = False  # Now used by CLI to prompt post-gen checks

    @property
    def video_resolution(self) -> str:
        return ASPECT_RATIO_OPTIONS.get(self.video_aspect_ratio, ASPECT_RATIO_OPTIONS["16:9"])["size"]
```

Global state:
- `current_config` singleton with `get_current_config()` / `set_current_config()`

---

### 3) `content_generator_agent.py` - Content Agent

Purpose:
- Orchestrate content generation and captions via tools. No compliance tools.

Agent creation:
```python
from langchain.agents import create_agent
from tools.image_generator import generate_image
from tools.video_generator import generate_video
from tools.caption_generator import generate_caption

agent = create_agent(
    model="openai:gpt-5",
    tools=[generate_image, generate_video, generate_caption],
    system_prompt=get_system_prompt(),
    debug=False
)
```

System prompt highlights:
- Describes primary capabilities (image/video/caption)
- Injects current config (durations, aspect ratios/resolution, caption style, etc.)
- Instructs the model to suggest using dedicated agents (/design, /policy) for compliance
- If `auto_compliance_check=True`, the prompt recommends compliance, but the actual call path is via CLI prompt

Conversation memory:
- Simple list of dict messages, with agent invocation using `invoke({"messages": chat_history})`

---

### 4) `agents/design_agent.py` - Design Compliance Agent

Purpose:
- Dedicated agent exposing only `check_design_compliance` tool

Design:
```python
from tools.design_checker import check_design_compliance

agent = create_agent(
    model="openai:gpt-5",
    tools=[check_design_compliance],
    system_prompt=get_system_prompt(),
    debug=False
)
```

Prompt:
- Role: design reviewer
- Produces a structured design report
- Requests clarifications when inputs are missing (content_type, resolution, etc.)

---

### 5) `agents/policy_agent.py` - Policy Compliance Agent

Purpose:
- Dedicated agent exposing only `check_policy_compliance` tool

Design:
```python
from tools.policy_checker import check_policy_compliance

agent = create_agent(
    model="openai:gpt-5",
    tools=[check_policy_compliance],
    system_prompt=get_system_prompt(),
    debug=False
)
```

Prompt:
- Role: policy reviewer
- Produces a structured policy report
- Requests clarifications when inputs are missing (platform, caption, etc.)

---

### 6) `tools/` - Tool Implementations

- `image_generator.py`:
  - DALL·E 3 image generation, downloads to `generated_content/images/`
- `video_generator.py`:
  - Sora-2 video generation, aspect ratio → resolution mapping, attempts to download to `generated_content/videos/`
- `caption_generator.py`:
  - GPT-5 chat-based captioning with platform guidelines and optional hashtags/emojis
- `policy_checker.py`:
  - GPT-5-based policy compliance with structured report, loads `guidelines/policy_guidelines.md`
- `design_checker.py`:
  - GPT-5-based design compliance with structured report, loads `guidelines/design_guidelines.md`

---

## Data Flow

### Content Generation Flow
```
1. User interacts with main CLI (free text)
2. Content agent decides on tool usage:
   - generate_image(prompt, size, quality)
   - generate_video(prompt, aspect_ratio→size, seconds)
   - generate_caption(content_description, platform, style, flags)
3. Media downloaded to generated_content/{images|videos}
4. CLI prints agent response
5. If auto_compliance_check=True → CLI prompts to run compliance agents
```

### Compliance Flow (Dedicated Agents)
```
1. User invokes /design or /policy command (or accepts post-gen prompt)
2. CLI collects required inputs
3. Dedicated agent called with a prompt to run the specific compliance tool
4. Structured report is printed to the console
```

---

## Environment Variables

```
OPENAI_API_KEY=sk-...  # Required
```

Loaded via `python-dotenv` where appropriate.

---

## Dependencies

| Package            | Purpose                               |
| ------------------ | ------------------------------------- |
| `openai>=1.40.0`   | DALL-E 3, Sora-2, GPT-5 API client    |
| `langchain>=0.3.0` | Agent framework with `create_agent()` |
| `langchain-openai` | OpenAI integration for LangChain      |
| `langchain-core`   | Core abstractions, `@tool` decorator  |
| `python-dotenv`    | Load `.env` file                      |
| `requests`         | Download images from URLs             |

Note: Some API endpoints (e.g., Sora video/download) may be placeholders depending on OpenAI’s current Python SDK surface. Adjust accordingly.

---

## Error Handling and Robustness

- Lazy initialization of OpenAI clients within tool functions
- Parameter validation with fallbacks
- Exceptions are returned as user-readable error strings rather than raised
- CLI continues even if compliance flow fails (non-fatal handling)

---

## Extension Points

1. Add new media or analysis tools:
   - Create a `@tool` function in `tools/`
   - Export via `tools/__init__.py`
   - Register in the relevant agent

2. Enforce programmatic post-processing:
   - If you need guaranteed compliance after generation, the CLI can be extended to make compliance mandatory (no prompt).

3. Persistence:
   - Persist configuration to disk and/or accept non-interactive CLI flags for automation pipelines.

---

## File Output Layout

```
generated_content/
├── images/
│   └── image_YYYYMMDD_HHMMSS.png
└── videos/
    └── video_YYYYMMDD_HHMMSS.mp4
```

---

## Quick Usage

```
pip install -r requirements.txt
echo OPENAI_API_KEY=sk-... > .env
python main.py

# In the CLI:
- Ask for content ideas or request image/video/caption directly
- Use /design or /policy to run dedicated compliance agents
- Enable Auto Compliance during setup to be prompted after generation
