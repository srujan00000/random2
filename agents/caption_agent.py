"""
Caption Generation Agent using LangChain and OpenAI.
Provides a dedicated agent that uses only the caption generation tool.
"""

from dotenv import load_dotenv
from langchain.agents import create_agent

from tools.caption_generator import generate_caption
from config import get_current_config

# Ensure environment variables are loaded (in case invoked outside main.py)
load_dotenv()


def get_system_prompt() -> str:
    """System prompt specialized for social media caption generation."""
    cfg = get_current_config()

    return f"""You are a dedicated social media caption generation agent.

Your purpose:
- Create engaging, platform-optimized captions that match the requested tone/style.
- Include relevant, trending hashtags when appropriate.
- Optionally include emojis for platforms where they improve engagement.

Context (from current configuration):
- Default caption style: {cfg.caption_style}
- Captions enabled globally: {cfg.enable_captions}

Tool usage:
- Use the generate_caption tool to produce a caption for a given content description.
- Include platform-specific guidance when provided (instagram/linkedin/twitter/facebook).
- Keep responses concise and formatted per the tool's expected output (CAPTION + optional HASHTAGS section)."""


def create_caption_agent():
    """Create and return the caption generation agent."""
    tools = [generate_caption]

    agent = create_agent(
        model="openai:gpt-5",
        tools=tools,
        system_prompt=get_system_prompt(),
        debug=False
    )

    return agent


class CaptionAgent:
    """Wrapper for the caption generation agent with conversation memory."""

    def __init__(self):
        self.agent = create_caption_agent()
        self.chat_history = []

    def chat(self, user_input: str) -> str:
        """Send a message to the agent and get a response."""
        try:
            self.chat_history.append({"role": "user", "content": user_input})

            response = self.agent.invoke({
                "messages": self.chat_history
            })

            messages = response.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if hasattr(msg, "content") and hasattr(msg, "type") and msg.type == "ai":
                        ai_response = msg.content
                        self.chat_history.append({"role": "assistant", "content": ai_response})
                        return ai_response

                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    ai_response = last_msg.content
                    self.chat_history.append({"role": "assistant", "content": ai_response})
                    return ai_response

            return "I apologize, but I couldn't generate a response. Please try again."

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def reset_history(self):
        """Clear conversation history."""
        self.chat_history = []

    def refresh_agent(self):
        """Recreate the agent (e.g., after config change)."""
        self.agent = create_caption_agent()


def get_agent() -> CaptionAgent:
    """Convenience function to get a ready-to-use caption agent."""
    return CaptionAgent()
