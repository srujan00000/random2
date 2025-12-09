# import os
# import base64
# from datetime import datetime
# from pathlib import Path
# import traceback

# from langchain.tools import tool
# from openai import OpenAI
# from config import get_current_config
# from .design_checker import load_design_guidelines
# from .policy_checker import load_policy_guidelines


# def get_client():
#     """Get OpenAI client with lazy initialization."""
#     return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# def get_output_dir() -> Path:
#     """Get or create the output directory for generated content."""
#     output_dir = Path("generated_content/images")
#     output_dir.mkdir(parents=True, exist_ok=True)
#     return output_dir


# def build_enforced_guideline_prompt(
#     user_prompt: str,
#     policy_text: str,
#     design_text: str,
#     size: str,
#     quality: str
# ) -> str:
#     return (
#         "STRICT COMPLIANCE REQUIRED:\n"
#         "- You must strictly adhere to the Policy Guidelines and Design Guidelines provided below.\n"
#         "- If any part of the primary task conflicts with the guidelines, prioritize the guidelines.\n"
#         "- Do not include any elements that violate policy constraints.\n"
#         "\n"
#         "Policy Guidelines:\n"
#         "------------------\n"
#         f"{policy_text}\n"
#         "\n"
#         "Design Guidelines:\n"
#         "------------------\n"
#         f"{design_text}\n"
#         "\n"
#         "Output Requirements:\n"
#         "- Follow all policy constraints.\n"
#         "- Follow all design rules, styles, color usage, and layout conventions.\n"
#         "- Ensure the final image is consistent with the above guidelines.\n"
#         f"- Target image size: {size}\n"
#         f"- Image quality: {quality}\n"
#         "\n"
#         "PRIMARY TASK:\n"
#         f"{user_prompt}\n"
#         "\n"
#         "Ensure the output image conforms to all guidelines above."
#     )


# def save_image_base64(base64_data: str, filename: str) -> str:
#     """Decode a base64 image and save to disk."""
#     output_dir = get_output_dir()
#     filepath = output_dir / filename
#     try:
#         with open(filepath, "wb") as f:
#             f.write(base64.b64decode(base64_data))
#         return str(filepath.absolute())
#     except Exception as e:
#         print(f"Saving failed: {str(e)}")
#         return f"Saving failed: {str(e)}"


# @tool
# def generate_image(prompt: str, size: str = "1024x1024", quality: str = "low",
#                    background: str = "auto", output_format: str = "png",
#                    timeout: int = 180) -> str:
#     """
#     Generate an image using gpt-image-1 based on the given prompt.

#     Args:
#         prompt: A detailed description of the image to generate.
#         size: Image dimensions. Options: "1024x1024", "1536x1024", "1024x1536", or "auto".
#         quality: Image quality. Options: "low", "medium", "high", or "auto".
#         background: "auto", "transparent", or "opaque".
#         output_format: "png", "jpeg", or "webp".
#         timeout: timeout for the API call in seconds (default 180).

#     Returns:
#         str: Local path of the generated image, or error message if generation fails.
#     """
#     try:
#         # Validate parameters
#         valid_sizes = ["1024x1024", "1536x1024", "1024x1536", "auto"]
#         valid_qualities = ["low", "medium", "high", "auto"]
#         valid_backgrounds = ["auto", "transparent", "opaque"]
#         valid_formats = ["png", "jpeg", "webp"]

#         if size not in valid_sizes:
#             size = "1024x1024"
#         if quality not in valid_qualities:
#             quality = "low"
#         if background not in valid_backgrounds:
#             background = "auto"
#         if output_format not in valid_formats:
#             output_format = "png"

#         client = get_client()
#         cfg = get_current_config()

#         # Load guideline texts and fallbacks if missing
#         try:
#             design = load_design_guidelines()
#         except Exception as e:
#             print(f"Could not load design guidelines: {e}")
#             design = "- Maintain high resolution (min 1080p)\n- Accessible contrast\n- Clean composition"
#         try:
#             policy = load_policy_guidelines()
#         except Exception as e:
#             print(f"Could not load policy guidelines: {e}")
#             policy = "- No prohibited/sensitive content\n- Professional, authentic tone\n- No exaggerated claims"

#         enforced_prompt = build_enforced_guideline_prompt(prompt, policy, design, size, quality)

#         print(f"Submitting image generation request: (size={size}, quality={quality}, background={background}, format={output_format}, timeout={timeout})")
#         result = client.images.generate(
#             model="gpt-image-1",
#             prompt=enforced_prompt,
#             size=size,
#             quality=quality,
#             background=background,
#             timeout=timeout,
#         )
#         print("Image generation request completed.")

#         if not result.data or not result.data[0].b64_json:
#             return "❌ Image generation failed: No image data returned."

#         # Read the base64 image data
#         image_base64 = result.data[0].b64_json
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename = f"gptimage1_{timestamp}.{output_format}"
#         local_path = save_image_base64(image_base64, filename)

#         return f"""✅ Image Generated Successfully!

# 💾 Local Path: {local_path}
# 📝 Settings - Model: gpt-image-1 | Size: {size} | Quality: {quality} | Format: {output_format}
# 🔒 Full guideline context applied in prompt.
# """

#     except Exception as e:
#         print("Error during image generation:")
#         traceback.print_exc()
#         return f"❌ Image generation failed: {str(e)}"


"""
Image Generation Tool using DALL-E 3.
Generates images based on text prompts and saves locally.
"""

import os
import requests
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
    output_dir = Path("generated_content/images")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def download_image(url: str, filename: str) -> str:
    """Download image from URL and save locally."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        output_dir = get_output_dir()
        filepath = output_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return str(filepath.absolute())
    except Exception as e:
        return f"Download failed: {str(e)}"


def build_enriched_prompt(prompt: str, cfg, size: str, quality: str) -> str:
    """
    Build a prompt that includes FULL design and policy guidelines,
    with strict compliance instructions to ensure the model follows them.
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
- Geometric shapes only (circles, squares, rectangles, lines, triangles)
- Bauhaus-inspired: balanced asymmetry, interlocking forms, clear visual hierarchy
- Minimalist and clean composition with ample negative space
- Typography: Open Sans font ONLY"""
    
    if not policy_guidelines.strip():
        policy_guidelines = """Default Policy Guidelines:
- No prohibited/sensitive content (violence, discrimination, explicit)
- Professional, authentic tone
- No misleading claims or exaggerated statements
- No copyright violations - 100% original content only
- Accessible design with proper contrast (WCAG 2.1 AA)
- No real individuals or public figures"""

    return f"""=== MANDATORY COMPLIANCE INSTRUCTIONS ===
You MUST strictly follow ALL guidelines below. These guidelines take PRIORITY over the user's creative request.
If ANY part of the user's request conflicts with these guidelines, you MUST prioritize the guidelines.
Non-compliance is NOT acceptable.

=== DESIGN GUIDELINES (MANDATORY) ===
{design_guidelines}

=== POLICY GUIDELINES (MANDATORY) ===
{policy_guidelines}

=== OUTPUT REQUIREMENTS ===
- Target image size: {size}
- Image quality: {quality}

=== USER'S CREATIVE REQUEST ===
{prompt}

=== FINAL REMINDER ===
Generate the image following ALL guidelines above. Use ONLY the approved color palette, flat 2D geometric style, and Open Sans typography. Ensure full compliance with both design and policy guidelines."""


@tool
def generate_image(prompt: str, size: str = "1024x1024", quality: str = "hd") -> str:
    """
    Generate an image using DALL-E 3 based on the given prompt.
    
    Args:
        prompt: A detailed description of the image to generate. Be specific about 
                style, colors, composition, and mood for best results.
        size: Image dimensions. Options: "1024x1024", "1792x1024" (landscape), 
              "1024x1792" (portrait). Default is "1024x1024".
        quality: Image quality. Options: "standard" or "hd". Default is "hd".
    
    Returns:
        str: URL and local path of the generated image, or error message if generation fails.
    
    Example prompts for social media:
        - "Professional LinkedIn banner showing a modern tech conference with diverse attendees"
        - "Vibrant Instagram post for a summer sale with tropical colors and bold typography"
        - "Minimalist product showcase on white background with soft shadows"
    """
    try:
        # Validate size parameter
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
        if size not in valid_sizes:
            size = "1024x1024"
        
        # Validate quality parameter
        valid_qualities = ["standard", "hd"]
        if quality not in valid_qualities:
            quality = "hd"
        
        # Get client and generate image using DALL-E 3
        client = get_client()
        cfg = get_current_config()
        enriched_prompt = build_enriched_prompt(prompt, cfg, size, quality)
        response = client.images.generate(
            model="dall-e-3",
            prompt=enriched_prompt,
            size=size,
            quality=quality,
            n=1
        )
        
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_{timestamp}.png"
        
        # Download and save locally
        local_path = download_image(image_url, filename)
        
        return f"""✅ Image Generated Successfully!

🖼️  Image URL: {image_url}

💾 Local Path: {local_path}

📝 DALL-E's Interpretation: {revised_prompt}

📐 Size: {size} | Quality: {quality}

💡 Tip: The image has been saved locally and can be accessed at the path above.

🔒 Guideline Context Applied: design + policy constraints included in the generation prompt."""

    except Exception as e:
        return f"❌ Image generation failed: {str(e)}"
