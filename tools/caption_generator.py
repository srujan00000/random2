"""
Caption Generation Tool and Helper Functions.
Provides both a LangChain tool and a simple function for caption generation.
"""

import os
from langchain.tools import tool
from openai import OpenAI


# =============================================================================
# HELPER FUNCTION (Used by linkedin.py, instagram.py, facebook.py)
# =============================================================================

def create_caption(content_description: str, platform: str = "linkedin") -> str:
    """
    Generate a plain caption for social media posting.
    This is a simple function (not a tool) for use by posting modules.
    
    Args:
        content_description: What the content is about.
        platform: Target platform (linkedin, instagram, facebook).
    
    Returns:
        Plain text caption ready for posting.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Platform-specific prompts
        platform_prompts = {
            "linkedin": "Write a professional LinkedIn post. Keep it concise (2-3 sentences). Include 3-5 relevant hashtags at the end.",
            "instagram": "Write an engaging Instagram caption. Keep it short (2-3 lines). Include 5-10 relevant hashtags at the end. Emojis are encouraged.",
            "facebook": "Write a friendly, conversational Facebook post. Keep it brief (2-3 sentences). Include 2-3 hashtags at the end."
        }
        
        system_prompt = platform_prompts.get(platform.lower(), platform_prompts["linkedin"])
        
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for faster response
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a caption for: {content_description}"}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        # Return a simple fallback caption if generation fails
        return f"{content_description} #socialmedia #content"


# =============================================================================
# PLATFORM-SPECIFIC GUIDELINES
# =============================================================================

PLATFORM_GUIDELINES = {
    "instagram": {
        "max_length": 2200,
        "hashtag_count": "20-30",
        "notes": "Visual-first, storytelling works well, hashtags in comments or at end"
    },
    "linkedin": {
        "max_length": 3000,
        "hashtag_count": "3-5",
        "notes": "Professional tone, thought leadership, industry-specific hashtags"
    },
    "twitter": {
        "max_length": 280,
        "hashtag_count": "1-3",
        "notes": "Concise, punchy, trending hashtags work best"
    },
    "facebook": {
        "max_length": 63206,
        "hashtag_count": "1-3",
        "notes": "Conversational, questions engage well, minimal hashtags"
    }
}


# =============================================================================
# LANGCHAIN TOOL (Used by the agent)
# =============================================================================

@tool
def generate_caption(
    content_description: str,
    platform: str = "instagram",
    style: str = "professional",
    include_hashtags: bool = True,
    include_emojis: bool = True
) -> str:
    """
    Generate a social media caption with relevant hashtags.
    
    Args:
        content_description: Description of the content (image/video).
        platform: Target platform (instagram, linkedin, facebook, twitter).
        style: Caption style (professional, casual, creative).
        include_hashtags: Whether to include hashtags.
        include_emojis: Whether to include emojis.
    
    Returns:
        Generated caption with formatting details.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Get platform info
        platform = platform.lower()
        platform_info = PLATFORM_GUIDELINES.get(platform, PLATFORM_GUIDELINES["instagram"])
        
        # Build the prompt
        system_prompt = f"""You are an expert social media content creator for {platform}.

Create a caption that:
1. Uses a {style} tone
2. Stays under {platform_info['max_length']} characters
3. {"Includes " + platform_info['hashtag_count'] + " hashtags" if include_hashtags else "No hashtags"}
4. {"Uses appropriate emojis" if include_emojis else "No emojis"}
5. {platform_info['notes']}

Output ONLY the caption text, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a caption for: {content_description}"}
            ],
            max_tokens=500,
            temperature=0.8
        )
        
        caption = response.choices[0].message.content.strip()
        
        return f"""✅ Caption Generated for {platform.upper()}!

{caption}

📊 Settings: {style} style, hashtags={'yes' if include_hashtags else 'no'}, emojis={'yes' if include_emojis else 'no'}"""

    except Exception as e:
        return f"❌ Caption generation failed: {str(e)}"