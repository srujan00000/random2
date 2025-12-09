"""
LinkedIn API Integration.
Handles image and video posting to LinkedIn using the v2 API.
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

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_URN = os.getenv("LINKEDIN_URN")  # e.g., "urn:li:person:abc123"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _check_credentials():
    """Verify LinkedIn credentials are set."""
    if not LINKEDIN_ACCESS_TOKEN:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN is not set in .env")
    if not LINKEDIN_URN:
        raise RuntimeError("LINKEDIN_URN is not set in .env")


def _get_headers(content_type: str = "application/json") -> dict:
    """Get standard headers for LinkedIn API calls."""
    return {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": content_type
    }


def _handle_api_error(response: requests.Response, context: str):
    """Handle API errors with detailed messages."""
    try:
        error_data = response.json()
    except:
        error_data = {"raw": response.text[:500]}
    
    error_msg = f"[LinkedIn] {context} failed (status {response.status_code}): {error_data}"
    print(error_msg)
    raise RuntimeError(error_msg)


# =============================================================================
# IMAGE POSTING
# =============================================================================

def post_linkedin_image(caption_prompt: str, image_path: str) -> dict:
    """
    Generate caption, upload image, and post to LinkedIn feed.
    
    Args:
        caption_prompt: Description of the content for caption generation.
        image_path: Local path to the image file.
    
    Returns:
        dict: LinkedIn API response with post details.
    """
    _check_credentials()
    
    # Verify image exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Step 1: Generate caption using unified generator
    print("[LinkedIn] Generating caption...")
    caption = create_caption(caption_prompt, platform="linkedin")
    print(f"[LinkedIn] Caption: {caption[:100]}...")
    
    # Step 2: Register upload with LinkedIn
    print("[LinkedIn] Registering upload...")
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    register_payload = {
        "registerUploadRequest": {
            "owner": LINKEDIN_URN,
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    
    register_response = requests.post(
        register_url, 
        json=register_payload, 
        headers=_get_headers(),
        timeout=30
    )
    
    if register_response.status_code >= 400:
        _handle_api_error(register_response, "Register upload")
    
    register_data = register_response.json()
    
    # Extract upload URL and asset URN
    try:
        upload_url = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = register_data["value"]["asset"]
    except KeyError as e:
        raise RuntimeError(f"[LinkedIn] Unexpected response format: {register_data}")
    
    print(f"[LinkedIn] Asset URN: {asset_urn}")
    
    # Step 3: Upload the image
    print("[LinkedIn] Uploading image...")
    with open(image_path, "rb") as img_file:
        upload_response = requests.put(
            upload_url,
            data=img_file,
            headers=_get_headers("image/jpeg"),
            timeout=120
        )
    
    if upload_response.status_code not in [200, 201]:
        _handle_api_error(upload_response, "Image upload")
    
    print("[LinkedIn] Image uploaded successfully")
    
    # Step 4: Create the post
    print("[LinkedIn] Creating post...")
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    post_payload = {
        "author": LINKEDIN_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "IMAGE",
                "media": [{
                    "status": "READY",
                    "media": asset_urn
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    post_response = requests.post(
        post_url,
        json=post_payload,
        headers=_get_headers(),
        timeout=30
    )
    
    if post_response.status_code >= 400:
        _handle_api_error(post_response, "Create post")
    
    result = post_response.json()
    print(f"[LinkedIn] ✅ Image posted successfully! Response: {result}")
    return result


# =============================================================================
# VIDEO POSTING
# =============================================================================

def post_linkedin_video(caption_prompt: str, video_path: str, title: str = "Video") -> dict:
    """
    Generate caption, upload video, and post to LinkedIn feed.
    
    Args:
        caption_prompt: Description of the content for caption generation.
        video_path: Local path to the video file.
        title: Optional title for the video.
    
    Returns:
        dict: LinkedIn API response with post details.
    """
    _check_credentials()
    
    # Verify video exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Step 1: Generate caption
    print("[LinkedIn] Generating caption...")
    caption = create_caption(caption_prompt, platform="linkedin")
    print(f"[LinkedIn] Caption: {caption[:100]}...")
    
    # Step 2: Register upload
    print("[LinkedIn] Registering video upload...")
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    register_payload = {
        "registerUploadRequest": {
            "owner": LINKEDIN_URN,
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    
    register_response = requests.post(
        register_url,
        json=register_payload,
        headers=_get_headers(),
        timeout=30
    )
    
    if register_response.status_code >= 400:
        _handle_api_error(register_response, "Register video upload")
    
    register_data = register_response.json()
    
    try:
        upload_url = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = register_data["value"]["asset"]
    except KeyError:
        raise RuntimeError(f"[LinkedIn] Unexpected response format: {register_data}")
    
    print(f"[LinkedIn] Asset URN: {asset_urn}")
    
    # Step 3: Upload video
    print("[LinkedIn] Uploading video (this may take a while)...")
    
    # Determine content type
    from mimetypes import guess_type
    content_type, _ = guess_type(video_path)
    if not content_type:
        content_type = "video/mp4"
    
    with open(video_path, "rb") as video_file:
        upload_response = requests.put(
            upload_url,
            data=video_file,
            headers=_get_headers(content_type),
            timeout=300  # 5 minutes for large videos
        )
    
    if upload_response.status_code not in [200, 201]:
        _handle_api_error(upload_response, "Video upload")
    
    print("[LinkedIn] Video uploaded successfully")
    
    # Step 4: Create post
    print("[LinkedIn] Creating video post...")
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    post_payload = {
        "author": LINKEDIN_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "VIDEO",
                "media": [{
                    "status": "READY",
                    "media": asset_urn,
                    "title": {"text": title}
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    post_response = requests.post(
        post_url,
        json=post_payload,
        headers=_get_headers(),
        timeout=30
    )
    
    if post_response.status_code >= 400:
        _handle_api_error(post_response, "Create video post")
    
    result = post_response.json()
    print(f"[LinkedIn] ✅ Video posted successfully! Response: {result}")
    return result


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Test image posting
    # post_linkedin_image("Announcing our new AI automation tool.", "test_image.jpg")
    
    # Test video posting
    # post_linkedin_video("Demo of our new product.", "test_video.mp4", title="Product Demo")
    pass