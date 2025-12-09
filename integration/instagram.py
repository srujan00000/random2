"""
Instagram API Integration via Facebook Graph API.
Handles image posting to Instagram using the Facebook CDN upload method.
Uses the unified caption generator from caption_generator.py.
"""

import os
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
IG_USER_ID = os.getenv("IG_USER_ID")
GRAPH_API_BASE = "https://graph.facebook.com/v24.0"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _check_credentials():
    """Verify Instagram/Meta credentials are set."""
    if not META_ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not set in .env")
    if not FB_PAGE_ID:
        raise RuntimeError("FB_PAGE_ID is not set in .env")
    if not IG_USER_ID:
        raise RuntimeError("IG_USER_ID is not set in .env")


def get_page_access_token() -> str:
    """Get the Facebook Page access token."""
    if not META_ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not set.")
    
    url = f"{GRAPH_API_BASE}/{FB_PAGE_ID}"
    params = {"fields": "access_token", "access_token": META_ACCESS_TOKEN}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if response.ok and isinstance(data, dict) and data.get("access_token"):
            return data["access_token"]
        else:
            print("[IG] Could not retrieve Page access token; using META_ACCESS_TOKEN.")
            return META_ACCESS_TOKEN
    except Exception as e:
        print(f"[IG] Page token fetch failed: {e}")
        return META_ACCESS_TOKEN


# =============================================================================
# IMAGE UPLOAD VIA FACEBOOK
# =============================================================================

def upload_image_via_facebook_page(image_path: str) -> str:
    """
    Upload image to Facebook CDN to get a public URL for Instagram.
    
    Args:
        image_path: Local path to the image file.
    
    Returns:
        str: Public URL of the uploaded image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    url = f"{GRAPH_API_BASE}/{FB_PAGE_ID}/photos"
    page_token = get_page_access_token()
    
    print("[IG] Uploading image to Facebook CDN...")
    
    with open(image_path, "rb") as imgfile:
        files = {"source": imgfile}
        params = {"access_token": page_token, "published": "false"}
        response = requests.post(url, data=params, files=files, timeout=60)
    
    data = response.json()
    
    if response.status_code >= 400:
        raise RuntimeError(f"[IG] Facebook upload error: {data}")
    
    photo_id = data.get("id")
    if not photo_id:
        raise RuntimeError("[IG] Facebook upload did not return a photo id.")
    
    # Get the direct CDN URL
    info_url = f"{GRAPH_API_BASE}/{photo_id}"
    info_params = {"fields": "images,link", "access_token": page_token}
    info_response = requests.get(info_url, params=info_params, timeout=30)
    info = info_response.json()
    
    if info_response.status_code >= 400:
        raise RuntimeError(f"[IG] Query error: {info}")
    
    # Try to get image source URL
    images = info.get("images", [])
    if images:
        src = images[0].get("source")
        if src and src.startswith("http"):
            print(f"[IG] Uploaded to Facebook CDN: {src[:80]}...")
            return src
    
    # Fallback to link
    possible = info.get("link")
    if possible and isinstance(possible, str) and possible.startswith("http"):
        print(f"[IG] Using Facebook link: {possible[:80]}...")
        return possible
    
    raise RuntimeError("[IG] Failed to obtain a public URL from Facebook upload.")


# =============================================================================
# INSTAGRAM POSTING
# =============================================================================

def create_ig_media_container(image_url: str, caption: str) -> str:
    """Create an Instagram media container."""
    url = f"{GRAPH_API_BASE}/{IG_USER_ID}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": META_ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload, timeout=30)
    data = response.json()
    
    if response.status_code >= 400:
        raise RuntimeError(f"[IG] Container error: {data}")
    
    return data["id"]


def publish_ig_container(container_id: str) -> str:
    """Publish an Instagram media container."""
    url = f"{GRAPH_API_BASE}/{IG_USER_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": META_ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload, timeout=30)
    data = response.json()
    
    if response.status_code >= 400:
        raise RuntimeError(f"[IG] Publish error: {data}")
    
    return data.get("id", "")


def post_to_instagram_local(image_path: str, caption: str) -> str:
    """
    Post an image to Instagram using a local file.
    
    Args:
        image_path: Local path to the image file.
        caption: Caption text for the post.
    
    Returns:
        str: Instagram media ID of the published post.
    """
    _check_credentials()
    
    # Step 1: Upload to Facebook CDN to get public URL
    public_url = upload_image_via_facebook_page(image_path)
    
    # Step 2: Create media container
    print("[IG] Creating media container...")
    container_id = create_ig_media_container(public_url, caption)
    print(f"[IG] Container created: {container_id}")
    
    # Step 3: Publish
    print("[IG] Publishing...")
    media_id = publish_ig_container(container_id)
    print(f"[IG] ✅ Published on Instagram! Media ID: {media_id}")
    
    return media_id


def post_instagram_image(caption_prompt: str, image_path: str) -> str:
    """
    Generate caption and post image to Instagram.
    This is the main function called by social_publisher.py.
    
    Args:
        caption_prompt: Description of the content for caption generation.
        image_path: Local path to the image file.
    
    Returns:
        str: Instagram media ID.
    """
    _check_credentials()
    
    # Generate caption using unified generator
    print("[IG] Generating caption...")
    caption = create_caption(caption_prompt, platform="instagram")
    print(f"[IG] Caption: {caption[:100]}...")
    
    # Post to Instagram
    return post_to_instagram_local(image_path, caption)


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Test posting
    # post_instagram_image("Announcing our new AI automation tool.", "test_image.jpg")
    pass