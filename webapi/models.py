from pydantic import BaseModel
from typing import Optional, Literal


class StartRequest(BaseModel):
    human_request: str


class ResumeRequest(BaseModel):
    thread_id: str
    action: Literal[
        "approve_ideation",
        "feedback_ideation",
        "approve_content",
        "feedback_content",
        "run_policy",
        "run_design",
        "run_caption",
        "post_linkedin",
        "post_social_facebook",
        "post_social_instagram",
    ]
    human_comment: Optional[str] = None


class GraphResponse(BaseModel):
    thread_id: str
    run_status: Literal["pending", "finished", "ideation_feedback", "content_feedback"]
    assistant_response: Optional[str] = None


class ConfigPayload(BaseModel):
    video_duration: int
    video_aspect_ratio: Literal["16:9", "9:16", "1:1", "4:5", "21:9"]
    enable_captions: bool
    caption_style: Literal["professional", "casual", "creative"]
    image_size: Literal["1024x1024", "1792x1024", "1024x1792"]
    image_quality: Literal["standard", "hd"]
    auto_compliance_check: bool


class ConfigResponse(ConfigPayload):
    # Include computed resolution in the response for convenience
    video_resolution: str
