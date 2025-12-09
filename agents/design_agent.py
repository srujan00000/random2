"""
Design Compliance Agent using LangChain and OpenAI.
Provides a dedicated agent that uses only the design compliance tool.
"""

import os
from dotenv import load_dotenv
from langchain.agents import create_agent

from tools.design_checker import check_design_compliance
from config import get_current_config

# Ensure environment variables are loaded (in case invoked outside main.py)
load_dotenv()


def get_system_prompt() -> str:
    """System prompt specialized for design compliance review."""
    config = get_current_config()

    return f"""You are a design compliance reviewer agent for AI-generated visual content (images/videos).

Your purpose:
- Evaluate content descriptions against design guidelines.
- Produce a structured, actionable design compliance report.
- Ask clarifying questions if critical details are missing (e.g., content_type, resolution).

Context:
- Preferred video aspect ratio: {config.video_aspect_ratio} ({config.video_resolution})
- Preferred image size: {config.image_size}
- This agent focuses ONLY on design compliance. It does not generate media.

Tool usage:
- Use the check_design_compliance tool to perform the review.
- Pass along: content_description, content_type (image/video), resolution (if known), and any additional_context.
- Always return the full structured report to the user.
"""


def create_design_agent():
    """Create and return the design compliance agent."""
    tools = [check_design_compliance]

    agent = create_agent(
        model="openai:gpt-5",
        tools=tools,
        system_prompt=get_system_prompt(),
        debug=False
    )

    return agent


class DesignComplianceAgent:
    """Wrapper for the design compliance agent with conversation memory."""

    def __init__(self):
        self.agent = create_design_agent()
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
        self.agent = create_design_agent()


def get_agent() -> DesignComplianceAgent:
    """Convenience function to get a ready-to-use design compliance agent."""
    return DesignComplianceAgent()
