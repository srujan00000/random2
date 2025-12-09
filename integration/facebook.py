"""
Facebook API Integration.
Handles image and video posting to Facebook Pages using the Graph API.
Uses the unified caption generator from caption_generator.py.
"""

import os
import mimetypes
import requests
from dotenv import load_dotenv

# Import the unified caption generator
from tools.caption_generator import create_caption

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
GRAPH_API_BASE = "https://graph.facebook.com/v24.0"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _check_credentials():
    """Verify Facebook credentials are set."""
    if not META_ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not set in .env")
    if not FB_PAGE_ID:
        raise RuntimeError("FB_PAGE_ID is not set in .env")


def get_page_access_token() -> str:
    """
    Get the Facebook Page access token.
    Falls back to META_ACCESS_TOKEN if page token retrieval fails.
    """
    if not META_ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not set.")
    if not FB_PAGE_ID:
        raise RuntimeError("FB_PAGE_ID is not set.")
    
    url = f"{GRAPH_API_BASE}/{FB_PAGE_ID}"
    params = {"fields": "access_token", "access_token": META_ACCESS_TOKEN}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if response.ok and isinstance(data, dict) and data.get("access_token"):
            return data["access_token"]
        else:
            print(f"[FB] Could not retrieve Page access token; using META_ACCESS_TOKEN. Response: {data}")
            return META_ACCESS_TOKEN
    except Exception as e:
        print(f"[FB] Page token fetch failed: {e}")
        return META_ACCESS_TOKEN


# =============================================================================
# IMAGE POSTING
# =============================================================================

def post_facebook_image(caption_prompt: str, image_path: str, published: bool = True) -> dict:
    """
    Generate caption and post an image to Facebook Page.
    
    Args:
        caption_prompt: Description of the content for caption generation.
        image_path: Local path to the image file.
        published: Whether to publish immediately (True) or save as draft (False).
    
    Returns:
        dict: Facebook API response with post details.
    """
    _check_credentials()
    
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Generate caption using unified generator
    print("[FB] Generating caption...")
    caption = create_caption(caption_prompt, platform="facebook")
    print(f"[FB] Caption: {caption[:100]}...")
    
    # Get page token and prepare upload
    page_token = get_page_access_token()
    url = f"{GRAPH_API_BASE}/{FB_PAGE_ID}/photos"
    
    # Guess MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
    
    params = {
        "access_token": page_token,
        "caption": caption,
        "published": "true" if published else "false",
    }
    
    print(f"[FB] Posting image to Facebook...")
    
    with open(image_path, "rb") as img_file:
        files = {"source": (os.path.basename(image_path), img_file, mime_type)}
        response = requests.post(url, data=params, files=files, timeout=120)
    
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text[:500]}
    
    if response.status_code >= 400:
        print(f"[FB] Image error: {data}")
        raise RuntimeError(f"[FB] Image post failed: {data}")
    
    print(f"[FB] ✅ Image posted successfully! Response: {data}")
    return data


# =============================================================================
# VIDEO POSTING
# =============================================================================

def post_facebook_video(caption_prompt: str, video_path: str, title: str = None, published: bool = True) -> dict:
    """
    Generate caption and post a video to Facebook Page.
    
    Args:
        caption_prompt: Description of the content for caption generation.
        video_path: Local path to the video file.
        title: Optional title for the video.
        published: Whether to publish immediately (True) or save as draft (False).
    
    Returns:
        dict: Facebook API response with post details.
    """
    _check_credentials()
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Generate caption using unified generator
    print("[FB] Generating caption...")
    description = create_caption(caption_prompt, platform="facebook")
    print(f"[FB] Caption: {description[:100]}...")
    
    # Get page token and prepare upload
    page_token = get_page_access_token()
    url = f"{GRAPH_API_BASE}/{FB_PAGE_ID}/videos"
    
    params = {
        "access_token": page_token,
        "description": description,
        "published": "true" if published else "false",
    }
    
    if title:
        params["title"] = title
    
    print(f"[FB] Posting video to Facebook (this may take a while)...")
    
    with open(video_path, "rb") as video_file:
        files = {"source": (os.path.basename(video_path), video_file, "video/mp4")}
        response = requests.post(url, data=params, files=files, timeout=300)
    
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text[:500]}
    
    if response.status_code >= 400:
        print(f"[FB] Video error: {data}")
        raise RuntimeError(f"[FB] Video post failed: {data}")
    
    print(f"[FB] ✅ Video posted successfully! Response: {data}")
    return data


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Test image posting
    # post_facebook_image("Announcing our new AI automation tool.", "test_image.jpg")
    
    # Test video posting
    # post_facebook_video("Demo of our product.", "test_video.mp4", title="Product Demo")
    pass