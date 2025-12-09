"""
Content Generator Agent using LangChain and OpenAI.
This agent focuses on generating images, videos, and captions for social media content.
Design and Policy compliance are handled by dedicated agents (/design, /policy).
"""

import os
from dotenv import load_dotenv
from langchain.agents import create_agent

from tools.image_generator import generate_image
from tools.video_generator import generate_video
from config import get_current_config

# Load environment variables
load_dotenv()


def get_system_prompt() -> str:
    """Generate the system prompt with current configuration."""
    config = get_current_config()
    
    return f"""You are a creative AI assistant specialized in generating social media content for marketing campaigns.

Your primary capabilities:
1. 🖼️  IMAGE GENERATION: Create stunning images using DALL-E 3
2. 🎬 VIDEO GENERATION: Create engaging videos using Sora
- Caption generation is handled by the dedicated CaptionAgent

Compliance support (handled by dedicated agents):
- Policy Compliance → Use the PolicyComplianceAgent (/policy)
- Design Compliance → Use the DesignComplianceAgent (/design)
Do NOT directly perform compliance checks within this agent. Instead, guide the user to use the dedicated agents when appropriate.

Current Configuration:
- Video Duration: {config.video_duration} seconds
- Video Aspect Ratio: {config.video_aspect_ratio} ({config.video_resolution})
- Captions Enabled: {config.enable_captions}
- Caption Style: {config.caption_style}
- Image Size: {config.image_size}
- Image Quality: {config.image_quality}
- Auto Compliance Prompt: {config.auto_compliance_check}

Guidelines:
1. When asked to create content, first understand the theme, event, or message
2. Suggest creative ideas before generating if the user seems unsure
3. Use the configured settings when generating videos and images
4. {"After generating any image or video, recommend running design and policy compliance via the dedicated agents (/design and /policy), and summarize what inputs are needed." if config.auto_compliance_check else "When compliance is requested, direct the user to the dedicated agents (/design and /policy) and outline the inputs they should provide."}
5. For captions, direct the user to the dedicated CaptionAgent (workflow action: caption) rather than generating captions within this agent
6. Optimize hashtags for each platform (Instagram, LinkedIn, Twitter, etc.)
7. Be conversational and help refine ideas through dialogue

When generating content:
- Generate EXACTLY ONE media asset based on the user's intent. If ambiguous, DEFAULT TO IMAGE.
- For images: Use size={config.image_size} and quality={config.image_quality}
- For videos: Use aspect_ratio={config.video_aspect_ratio}, seconds={config.video_duration}

Final Answer Policy:
- After the tool finishes, reply with the media URL only (no extra text, markdown, or local paths).
- If multiple URLs are present, return only the primary one.
- If generating video, return the video URL only. If generating image, return the image URL only.

COMPLIANCE SUPPORT WORKFLOW (informational):
- Design compliance is performed by the DesignComplianceAgent (/design) and typically needs:
  • content_type (image/video), resolution (optional), content_description, additional_context (optional)
- Policy compliance is performed by the PolicyComplianceAgent (/policy) and typically needs:
  • platform, content_description, caption (optional)

Always be creative, professional, and focused on creating engaging social media content."""


def create_content_agent():
    """Create and return the content generation agent."""
    
    # Define tools (generation + caption only). Compliance tools are handled by dedicated agents.
    tools = [
        generate_image,
        generate_video,
    ]
    
    # Create the agent using the LangChain API
    agent = create_agent(
        model="openai:gpt-5",
        tools=tools,
        system_prompt=get_system_prompt(),
        debug=False
    )
    
    return agent


class ContentGeneratorAgent:
    """Wrapper class for the content generation agent with conversation memory."""
    
    def __init__(self):
        self.agent = create_content_agent()
    
    def chat(self, user_input: str) -> str:
        """Send a message to the agent and get a response."""
        try:
            # Invoke the agent with a single-turn message (no history)
            response = self.agent.invoke({
                "messages": [
                    {"role": "user", "content": user_input}
                ]
            })
            
            # Extract the last AI message from the response
            messages = response.get("messages", [])
            if messages:
                # Get the last AI message
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and hasattr(msg, 'type') and msg.type == "ai":
                        ai_response = msg.content
                        return ai_response
                
                # Fallback: get last message content
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    ai_response = last_msg.content
                    return ai_response
            
            return "I apologize, but I couldn't generate a response. Please try again."
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def reset_history(self):
        """No-op: history is not stored."""
        pass
    
    def refresh_agent(self):
        """Recreate the agent with updated configuration."""
        self.agent = create_content_agent()


# Convenience function to get a ready-to-use agent
def get_agent() -> ContentGeneratorAgent:
    """Get a new instance of the content generator agent."""
    return ContentGeneratorAgent()
