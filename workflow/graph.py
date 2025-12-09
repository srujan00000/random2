"""
LangGraph workflow for content-generation-agent:
START -> ideation_node -> feedback_ideation (interrupt)
      -> content_generation_node -> feedback_content (interrupt)
         - from feedback_content user can:
             * approve_content -> node_to_terminate
             * feedback_content -> ideation_node (improve prompt)
             * run_policy -> policy_review_node -> feedback_content
             * run_design -> design_review_node -> feedback_content
"""

import os
from typing import Literal, Optional, Dict, Any
from dotenv import load_dotenv

import tempfile
import requests

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Local agents
from content_generator_agent import get_agent as get_content_agent
from agents.policy_agent import get_agent as get_policy_agent
from agents.design_agent import get_agent as get_design_agent
from agents.caption_agent import get_agent as get_caption_agent
from integration.linkedin import post_linkedin_image, post_linkedin_video
from integration.facebook import post_facebook_image, post_facebook_video
from integration.instagram import post_to_instagram_local
from tools.caption_generator import create_caption
from config import get_current_config

# Ensure environment variables (OPENAI_API_KEY) are available
load_dotenv()


# --- Model factory for ideation (lazy to avoid import-time API key requirement) ---
def get_ideation_model():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=None,
        timeout=None,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


# --- Graph State Definition ---
class WorkflowState(MessagesState):
    # Initial user intent / brief
    human_request: str

    # When user provides feedback on ideation or content
    human_comment: Optional[str]

    # Next action/status set by resume API at interrupt points
    # Allowed values:
    #   - "approve_ideation", "feedback_ideation"
    #   - "approve_content", "feedback_content"
    #   - "run_policy", "run_design"
    status: Optional[str]

    # Latest assistant text to stream back
    assistant_response: str

    # A concise, structured brief produced by ideation
    ideation_brief: Optional[str]

    # Content generation output (string summarizing images/videos/captions and paths/urls)
    content_result: Optional[str]

    # Compliance reports captured optionally
    compliance_reports: Optional[Dict[str, Optional[str]]]


# --- Nodes ---

def ideation_node(state: WorkflowState) -> WorkflowState:
    """
    Normal conversational agent behavior for ideation with feedback incorporation.
    - If status indicates feedback (feedback or feedback_ideation), embed human_comment
      as a SystemMessage instruction and DO NOT append the human comment to history.
    - Otherwise, respond normally with a general assistant prompt.
    """
    user_message = HumanMessage(content=state["human_request"])
    status = (state.get("status") or "approved").lower()

    if (status in ["feedback", "feedback_ideation"]) and state.get("human_comment"):
        # Create a system message that incorporates the feedback as instructions
        system_message = SystemMessage(content=(f"""
You are an AI assistant revising your previous draft. 

FEEDBACK FROM HUMAN: "{state["human_comment"]}"

Carefully incorporate this feedback into your response. Address all comments, 
corrections, or suggestions. Ensure your revised response fully integrates 
the feedback, improves clarity, and resolves any issues raised.

Then, conclude your reply with a clearly marked section:

GENERATION_PROMPT:
[Write a concise, self-contained prompt the content generator can use directly to create image/video and caption.
Include: target platform(s), content type(s) (image/video), tone/style, key visual details, messaging,
and any constraints such as duration/aspect ratio hints. Avoid mentioning that this is a prompt.]

DO NOT repeat the feedback verbatim in your response.
"""))

        # Only include the original messages and system message with embedded feedback
        messages = [user_message] + state["messages"] + [system_message]
        
        # Don't add the human comment to the message history
        all_messages = state["messages"]

    else:
        system_message = SystemMessage(content=(("""
You are an AI assistant. Your goal is to fully understand and fulfill the user's 
request by preparing a relevant, clear, and helpful draft reply. Focus on addressing 
the user's needs directly and comprehensively. 
Ask brief clarifying questions only if absolutely necessary.

Then, conclude your reply with a clearly marked section:

GENERATION_PROMPT:
[Write a concise, self-contained prompt the content generator can use directly to create image/video and caption.
Include: target platform(s), content type(s) (image/video), tone/style, key visual details, messaging,
and any constraints such as duration/aspect ratio hints. Avoid mentioning that this is a prompt.]

Do not reference any previous human feedback at this stage.
""")))
        messages = [system_message, user_message]
        all_messages = state["messages"]
    
    response = get_ideation_model().invoke(messages)

    all_messages = all_messages + [response]

    # Keep ideation_brief compatibility for downstream usage
    text = response.content
    marker = "GENERATION_PROMPT:"
    if marker in text:
        ideation_brief = text.split(marker, 1)[1].strip()
    else:
        ideation_brief = text

    return {
        **state,
        "messages": all_messages,
        "assistant_response": response.content,
        "ideation_brief": ideation_brief,
    }


def feedback_ideation(state: WorkflowState):
    """Placeholder node used only as an interrupt point (no-op body)."""
    pass


def content_generation_node(state: WorkflowState) -> WorkflowState:
    """
    Uses ContentGeneratorAgent to generate content from ideation_brief.
    The agent may produce images/videos/captions and return a formatted string.
    """
    brief = state.get("ideation_brief") or state.get("human_request") or ""

    agent = get_content_agent()
    user_input = f"""
Using the following ideation brief, generate EXACTLY ONE media asset using the appropriate tool (generate_image or generate_video).
- If ambiguous, DEFAULT TO IMAGE.
- Do NOT generate captions in this step.

Then extract the media URL from the tool output and REPLY WITH THE URL ONLY
(no extra words, no markdown, no local path). If multiple URLs are present, return only the primary one.

IDEATION_BRIEF:
{brief}
"""

    result = agent.chat(user_input)

    all_messages = state["messages"] + [AIMessage(content=result)]

    return {
        **state,
        "messages": all_messages,
        "assistant_response": result,
        "content_result": result,
    }


def policy_review_node(state: WorkflowState) -> WorkflowState:
    """
    Runs the policy compliance agent on the generated content.
    """
    content = state.get("content_result") or state.get("assistant_response") or state.get("human_request") or ""

    p_agent = get_policy_agent()
    prompt = f"""Run policy compliance review on the following generated content (description/text):

{content}

Provide the full structured policy compliance report.
"""
    review = p_agent.chat(prompt)

    reports = dict(state.get("compliance_reports") or {})
    reports["policy"] = review

    all_messages = state["messages"] + [AIMessage(content=f"[PolicyComplianceAgent Report]\n{review}")]

    return {
        **state,
        "messages": all_messages,
        "assistant_response": review,
        "compliance_reports": reports,
    }


def design_review_node(state: WorkflowState) -> WorkflowState:
    """
    Runs the design compliance agent on the generated content.
    """
    content = state.get("content_result") or state.get("assistant_response") or state.get("human_request") or ""

    d_agent = get_design_agent()
    prompt = f"""Run design compliance review for the following content (image/video/caption description):

{content}

Provide the full structured design compliance report.
"""
    review = d_agent.chat(prompt)

    reports = dict(state.get("compliance_reports") or {})
    reports["design"] = review

    all_messages = state["messages"] + [AIMessage(content=f"[DesignComplianceAgent Report]\n{review}")]

    return {
        **state,
        "messages": all_messages,
        "assistant_response": review,
        "compliance_reports": reports,
    }


def caption_generation_node(state: WorkflowState) -> WorkflowState:
    """
    Runs the caption generation agent on the generated content.
    """
    # Prefer content_result; fallback to assistant_response or the original request
    content = state.get("content_result") or state.get("assistant_response") or state.get("human_request") or ""

    c_agent = get_caption_agent()
    prompt = f"""Generate a platform-optimized caption for the following content description.
If platform or style are implied in the description, optimize accordingly.

CONTENT:
{content}

Return the caption output in the tool's expected format."""
    caption_out = c_agent.chat(prompt)

    reports = dict(state.get("compliance_reports") or {})
    reports["caption"] = caption_out

    all_messages = state["messages"] + [AIMessage(content=f"[CaptionAgent Output]\n{caption_out}")]

    return {
        **state,
        "messages": all_messages,
        "assistant_response": caption_out,
        "compliance_reports": reports,
    }


def social_post_node(state: WorkflowState) -> WorkflowState:
    """
    Unified social posting node:
    - post_social_facebook  -> Facebook Page post (image/video)
    - post_social_instagram -> Instagram (image only in v1)
    - post_social_linkedin  -> LinkedIn (delegates to LinkedIn functions)
    """
    url = state.get("content_result") or state.get("assistant_response") or state.get("human_request") or ""
    reports_in = state.get("compliance_reports") or {}
    action = (state.get("status") or "").strip().lower()

    # Extract caption from prior caption node output if present
    def extract_caption(text: Optional[str]) -> str:
        if not text:
            return "New post"
        t = str(text)
        cap_idx = t.find("CAPTION:")
        if cap_idx >= 0:
            t2 = t[cap_idx + len("CAPTION:"):].strip()
            hash_idx = t2.find("HASHTAGS:")
            if hash_idx >= 0:
                t2 = t2[:hash_idx].strip()
            return t2 if t2 else "New post"
        return t.strip()[:500] or "New post"

    caption_text = extract_caption(reports_in.get("caption") if isinstance(reports_in, dict) else None)

    # Download media
    try:
        is_video = any(ext in url.lower() for ext in [".mp4", ".mov", ".webm"])
        suffix = ".mp4" if is_video else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    tf.write(chunk)
            local_path = tf.name
    except Exception as e:
        out = f"Social post aborted (download failed): {str(e)}"
        all_messages = state["messages"] + [AIMessage(content=out)]
        return {**state, "messages": all_messages, "assistant_response": out}

    # Route to platform with caption prompt built from state
    try:
        # Determine platform from action
        if action in ("post_social_linkedin", "post_linkedin"):
            platform = "linkedin"
        elif action == "post_social_facebook":
            platform = "facebook"
        elif action == "post_social_instagram":
            platform = "instagram"
        else:
            raise RuntimeError(f"Unknown social post action: {action}")

        # Build a platform-aware caption prompt from state
        def build_caption_prompt(state, platform: str, media_url: str) -> str:
            cfg = get_current_config()
            base = state.get("ideation_brief") or state.get("human_request") or ""
            is_vid = any(ext in (media_url or "").lower() for ext in [".mp4", ".mov", ".webm"])
            content_type = "video" if is_vid else "image"

            comp = state.get("compliance_reports") or {}

            def summarize(report: Optional[str], max_lines: int = 3) -> str:
                if not report:
                    return ""
                lines = [l.strip() for l in str(report).splitlines() if l.strip()]
                picks = []
                for l in lines:
                    ll = l.lower()
                    if any(k in ll for k in ["recommendation", "notes", "issue", "improv", "optimi"]):
                        picks.append(l)
                    if len(picks) >= max_lines:
                        break
                return "\n".join(picks)

            considerations = []
            if isinstance(comp, dict):
                if comp.get("policy"):
                    s = summarize(comp.get("policy"))
                    if s:
                        considerations.append("Policy notes:\n" + s)
                if comp.get("design"):
                    s = summarize(comp.get("design"))
                    if s:
                        considerations.append("Design notes:\n" + s)

            consider_text = ("\n\n".join(considerations)).strip()

            return f"""Write a {platform} caption for the following {content_type}.
Content brief:
{base}

Constraints:
- Tone/style: {cfg.caption_style}
- Captions enabled: {cfg.enable_captions}
- Video: aspect_ratio={cfg.video_aspect_ratio} resolution={cfg.video_resolution}
- Image: size={cfg.image_size} quality={cfg.image_quality}
{('Considerations:\n' + consider_text) if consider_text else ''}

Requirements:
- Follow {platform} conventions (hashtags/emojis limits)
- Clear CTA if suitable
- Avoid policy/design issues above"""

        caption_prompt = build_caption_prompt(state, platform, url)

        # Platform-specific posting
        if platform == "linkedin":
            # Let integration generate final caption from our prompt
            if is_video:
                result = post_linkedin_video(caption_prompt, local_path, title="Video")
            else:
                result = post_linkedin_image(caption_prompt, local_path)
        elif platform == "facebook":
            # Let integration generate final caption from our prompt
            if is_video:
                result = post_facebook_video(caption_prompt, local_path, title="Video")
            else:
                result = post_facebook_image(caption_prompt, local_path)
        elif platform == "instagram":
            if is_video:
                raise RuntimeError("Instagram video posting not supported in v1 (image only).")
            # If we don't have a good caption, generate one now
            if not caption_text or caption_text == "New post":
                caption_text = create_caption(caption_prompt, platform="instagram")
            result = post_to_instagram_local(local_path, caption_text)

        out = f"Social Post Result ({action}): {result}"
    except Exception as e:
        out = f"Social post failed ({action}): {str(e)}"

    all_messages = state["messages"] + [AIMessage(content=out)]
    reports = dict(state.get("compliance_reports") or {})
    reports["social"] = out

    return {
        **state,
        "messages": all_messages,
        "assistant_response": out,
        "compliance_reports": reports,
    }


def linkedin_post_node(state: WorkflowState) -> WorkflowState:
    """
    Posts the generated media to LinkedIn using integration.linkedin.
    - Downloads the media URL to a temp file
    - Extracts caption from caption report if available
    - Calls post_linkedin_image or post_linkedin_video accordingly
    """
    # Get media URL and optional caption report
    url = state.get("content_result") or state.get("assistant_response") or state.get("human_request") or ""
    reports_in = state.get("compliance_reports") or {}
    caption_raw = None
    if isinstance(reports_in, dict):
        caption_raw = reports_in.get("caption")

    def extract_caption(text: Optional[str]) -> str:
        if not text:
            return "New post"
        t = str(text)
        # Try to extract the section after "CAPTION:" and before "HASHTAGS:"
        cap_idx = t.find("CAPTION:")
        if cap_idx >= 0:
            t2 = t[cap_idx + len("CAPTION:"):].strip()
            hash_idx = t2.find("HASHTAGS:")
            if hash_idx >= 0:
                t2 = t2[:hash_idx].strip()
            return t2 if t2 else "New post"
        # Fallback: return a truncated version
        return t.strip()[:500] or "New post"

    caption_text = extract_caption(caption_raw)

    # Download media to temp file
    try:
        is_video = any(ext in url.lower() for ext in [".mp4", ".mov", ".webm"])
        suffix = ".mp4" if is_video else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    tf.write(chunk)
            local_path = tf.name
    except Exception as e:
        err = f"LinkedIn post aborted (download failed): {str(e)}"
        all_messages = state["messages"] + [AIMessage(content=err)]
        return {
            **state,
            "messages": all_messages,
            "assistant_response": err,
        }

    # Post to LinkedIn
    try:
        if is_video:
            result = post_linkedin_video(caption_text, local_path, title="Video")
        else:
            result = post_linkedin_image(caption_text, local_path)
        out = f"LinkedIn Post Result: {result}"
    except Exception as e:
        out = f"LinkedIn post failed: {str(e)}"

    all_messages = state["messages"] + [AIMessage(content=out)]
    reports = dict(state.get("compliance_reports") or {})
    reports["linkedin"] = out

    return {
        **state,
        "messages": all_messages,
        "assistant_response": out,
        "compliance_reports": reports,
    }


def feedback_content(state: WorkflowState):
    """Placeholder node used only as an interrupt point (no-op body)."""
    pass


def node_to_terminate(state: WorkflowState) -> WorkflowState:
    """
    Final node. Sends a closing message.
    """
    final_msg = "Thank you for using our service."
    all_messages = state["messages"] + [AIMessage(content=final_msg)]
    return {
        **state,
        "messages": all_messages,
        "assistant_response": final_msg,
    }


# --- Routers ---

def router_after_ideation(state: WorkflowState) -> str:
    """
    Decide where to go after ideation feedback interrupt.
    - approve_ideation -> content_generation_node
    - feedback_ideation -> ideation_node
    """
    action = (state.get("status") or "").strip().lower()
    if action == "approve_ideation":
        return "content_generation_node"
    else:
        # default and "feedback_ideation"
        return "ideation_node"


def router_after_content(state: WorkflowState) -> str:
    """
    Decide where to go after content feedback interrupt.
    - approve_content -> node_to_terminate
    - feedback_content -> ideation_node
    - run_policy -> policy_review_node
    - run_design -> design_review_node
    - run_caption -> caption_generation_node
    - post_linkedin -> social_post_node
    - post_social_facebook -> social_post_node
    - post_social_instagram -> social_post_node
    """
    action = (state.get("status") or "").strip().lower()
    if action == "approve_content":
        return "node_to_terminate"
    if action == "run_policy":
        return "policy_review_node"
    if action == "run_design":
        return "design_review_node"
    if action == "run_caption":
        return "caption_generation_node"
    if action == "post_linkedin":
        return "social_post_node"
    if action == "post_social_facebook":
        return "social_post_node"
    if action == "post_social_instagram":
        return "social_post_node"
    # default and "feedback_content"
    return "ideation_node"


# --- Build Graph ---

builder = StateGraph(WorkflowState)

builder.add_node("ideation_node", ideation_node)
builder.add_node("feedback_ideation", feedback_ideation)

builder.add_node("content_generation_node", content_generation_node)
builder.add_node("feedback_content", feedback_content)

builder.add_node("policy_review_node", policy_review_node)
builder.add_node("design_review_node", design_review_node)
builder.add_node("caption_generation_node", caption_generation_node)
builder.add_node("linkedin_post_node", linkedin_post_node)
builder.add_node("social_post_node", social_post_node)

builder.add_node("node_to_terminate", node_to_terminate)

# Edges
builder.add_edge(START, "ideation_node")
builder.add_edge("ideation_node", "feedback_ideation")

builder.add_conditional_edges(
    "feedback_ideation",
    router_after_ideation,
    {
        "content_generation_node": "content_generation_node",
        "ideation_node": "ideation_node",
    },
)

builder.add_edge("content_generation_node", "feedback_content")

builder.add_conditional_edges(
    "feedback_content",
    router_after_content,
    {
        "node_to_terminate": "node_to_terminate",
        "ideation_node": "ideation_node",
        "policy_review_node": "policy_review_node",
        "design_review_node": "design_review_node",
        "caption_generation_node": "caption_generation_node",
        "linkedin_post_node": "linkedin_post_node",
        "social_post_node": "social_post_node",
    },
)

# After running any review, return to feedback_content
builder.add_edge("policy_review_node", "feedback_content")
builder.add_edge("design_review_node", "feedback_content")
builder.add_edge("caption_generation_node", "feedback_content")
builder.add_edge("linkedin_post_node", "feedback_content")
builder.add_edge("social_post_node", "feedback_content")

builder.add_edge("node_to_terminate", END)

memory = MemorySaver()
graph = builder.compile(interrupt_before=["feedback_ideation", "feedback_content"], checkpointer=memory)

__all__ = ["graph", "WorkflowState"]
