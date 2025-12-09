"""
Video Generation Tool using OpenAI Sora.
Generates videos based on text prompts and saves locally.
"""

import os
from datetime import datetime
from pathlib import Path
from langchain.tools import tool
from openai import OpenAI
from config import get_current_config
from .design_checker import load_design_guidelines
from .policy_checker import load_policy_guidelines


def get_client():
    """Get OpenAI client with lazy initialization."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_output_dir() -> Path:
    """Get or create the output directory for generated content."""
    output_dir = Path("generated_content/videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# Aspect ratio to resolution mapping for popular social media platforms
# Using resolutions that conform to Sora API and social media standards
ASPECT_RATIO_MAP = {
    "16:9": {
        "size": "1920x1080",
        "description": "Landscape - YouTube, LinkedIn, Twitter",
        "platforms": ["YouTube", "LinkedIn", "Twitter", "Facebook"]
    },
    "9:16": {
        "size": "1080x1920",
        "description": "Portrait - TikTok, Instagram Reels, YouTube Shorts",
        "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts", "Snapchat"]
    },
    "1:1": {
        "size": "1080x1080",
        "description": "Square - Instagram Feed, Facebook",
        "platforms": ["Instagram Feed", "Facebook", "LinkedIn"]
    },
    "4:5": {
        "size": "1080x1350",
        "description": "Portrait (4:5) - Instagram Feed optimal",
        "platforms": ["Instagram Feed", "Facebook"]
    },
    "21:9": {
        "size": "2560x1080",
        "description": "Ultra-wide - Cinematic content",
        "platforms": ["YouTube", "Cinematic"]
    }
}


def get_aspect_ratio_options() -> str:
    """Return formatted string of available aspect ratio options."""
    options = []
    for ratio, info in ASPECT_RATIO_MAP.items():
        options.append(f"  • {ratio} ({info['size']}) - {info['description']}")
    return "\n".join(options)


def build_enriched_prompt(prompt: str, cfg, aspect_ratio: str, size: str, seconds: int) -> str:
    """
    Build a prompt that includes FULL design and policy guidelines,
    with strict compliance instructions to ensure the model follows them (video-focused).
    """
    try:
        design_guidelines = load_design_guidelines()
    except Exception:
        design_guidelines = ""
    try:
        policy_guidelines = load_policy_guidelines()
    except Exception:
        policy_guidelines = ""

    # Fallbacks if guideline files are unavailable
    if not design_guidelines.strip():
        design_guidelines = """Default Design Guidelines:
- Use ONLY these colors: #FE7743 (Orange), #EFEEEA (Background), #273F4F (Navy), #000000 (Black)
- Flat 2D style only - NO gradients, shadows, or 3D effects
- Geometric shapes and motion only (circles, squares, rectangles, lines, triangles)
- Bauhaus-inspired: balanced asymmetry, interlocking forms, clear visual hierarchy
- Minimalist and clean composition with ample negative space
- Typography: Open Sans font ONLY
- Smooth transitions and stable footage
- Minimum 1080p resolution"""
    
    if not policy_guidelines.strip():
        policy_guidelines = """Default Policy Guidelines:
- No prohibited/sensitive content (violence, discrimination, explicit)
- Professional, authentic tone
- No misleading claims or exaggerated statements
- No copyright violations - 100% original content only
- Accessible design with proper contrast (WCAG 2.1 AA)
- No real individuals or public figures
- Avoid flashing content for accessibility"""

    return f"""=== MANDATORY COMPLIANCE INSTRUCTIONS ===
You MUST strictly follow ALL guidelines below. These guidelines take PRIORITY over the user's creative request.
If ANY part of the user's request conflicts with these guidelines, you MUST prioritize the guidelines.
Non-compliance is NOT acceptable.

=== DESIGN GUIDELINES (MANDATORY) ===
{design_guidelines}

=== POLICY GUIDELINES (MANDATORY) ===
{policy_guidelines}

=== VIDEO OUTPUT REQUIREMENTS ===
- Aspect ratio: {aspect_ratio}
- Resolution: {size}
- Duration: {seconds} seconds

=== USER'S CREATIVE REQUEST ===
{prompt}

=== FINAL REMINDER ===
Generate the video following ALL guidelines above. Use ONLY the approved color palette, flat 2D geometric style with smooth motion, and Open Sans typography. Ensure full compliance with both design and policy guidelines. Maintain stable footage and accessible content."""
    

@tool
def generate_video(
    prompt: str, 
    aspect_ratio: str = "16:9",
    seconds: int = 10
) -> str:
    """
    Generate a video using OpenAI Sora based on the given prompt.
    
    Args:
        prompt: A detailed description of the video to generate. Include details about
                the scene, action, camera movement, lighting, and style for best results.
        aspect_ratio: Video aspect ratio. Options:
                      - "16:9" (1920x1080) - YouTube, LinkedIn, Twitter
                      - "9:16" (1080x1920) - TikTok, Reels, Shorts
                      - "1:1" (1080x1080) - Instagram/Facebook square
                      - "4:5" (1080x1350) - Instagram Feed optimal
                      - "21:9" (2560x1080) - Cinematic ultra-wide
                      Default is "16:9".
        seconds: Video length in seconds (5-60). Default is 10 seconds.
    
    Returns:
        str: URL and local path of the generated video, or error message if generation fails.
    
    Example prompts for social media:
        - "Cinematic drone shot flying over a modern city skyline at sunset, golden hour lighting"
        - "Product reveal animation with sleek transitions and professional lighting"
        - "Behind-the-scenes office footage with natural movement and candid moments"
    """
    try:
        # Validate seconds
        if not 5 <= seconds <= 60:
            seconds = 10
        
        # Get resolution from aspect ratio
        if aspect_ratio not in ASPECT_RATIO_MAP:
            aspect_ratio = "16:9"
        
        size = ASPECT_RATIO_MAP[aspect_ratio]["size"]
        ratio_info = ASPECT_RATIO_MAP[aspect_ratio]
        
        # Get client and generate video using Sora
        client = get_client()
        cfg = get_current_config()
        enriched_prompt = build_enriched_prompt(prompt, cfg, aspect_ratio, size, seconds)
        response = client.videos.create(
            model="sora-2",
            prompt=enriched_prompt,
            size=size,
            seconds=seconds
        )
        
        video_url = response.data[0].url
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{timestamp}.mp4"
        
        # Download video using the API's download method
        output_dir = get_output_dir()
        local_path = output_dir / filename
        
        try:
            # Use the videos.download_content method
            video_content = client.videos.download_content(response.data[0].id)
            with open(local_path, 'wb') as f:
                f.write(video_content)
            download_status = f"💾 Local Path: {local_path.absolute()}"
        except Exception as download_error:
            download_status = f"⚠️  Local download failed: {str(download_error)}\n   Use the URL to download manually."
        
        return f"""✅ Video Generated Successfully!

🎬 Video URL: {video_url}

{download_status}

📊 Video Details:
   • Duration: {seconds} seconds
   • Aspect Ratio: {aspect_ratio}
   • Resolution: {size}

🎯 Recommended Platforms:
   {', '.join(ratio_info['platforms'])}

💡 Platform Recommendations:
   • 16:9 → YouTube, LinkedIn, Twitter
   • 9:16 → TikTok, Instagram Reels, YouTube Shorts
   • 1:1 → Instagram Feed, Facebook
   • 4:5 → Instagram Feed (optimal engagement)
   • 21:9 → Cinematic content

🔒 Guideline Context Applied: design + policy constraints included in the generation prompt."""

    except Exception as e:
        return f"❌ Video generation failed: {str(e)}"
