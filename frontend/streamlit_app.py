import streamlit as st
import requests
import json
import re
from typing import Optional, Tuple

DEFAULT_BASE_URL = "http://localhost:8000"

# ---------- Utilities for API ----------


def api_create(base_url: str, human_request: str) -> Optional[str]:
    """Create a new workflow run and return thread_id."""
    try:
        r = requests.post(
            f"{base_url}/workflow/stream/create",
            json={"human_request": human_request},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("thread_id")
    except Exception as e:
        st.error(f"Create failed: {e}")
        return None


def api_resume(
    base_url: str, thread_id: str, action: str, human_comment: Optional[str] = None
) -> bool:
    """Resume an existing workflow with a specific action and optional feedback."""
    try:
        payload = {"thread_id": thread_id, "action": action}
        if human_comment is not None and human_comment.strip():
            payload["human_comment"] = human_comment.strip()
        r = requests.post(
            f"{base_url}/workflow/stream/resume", json=payload, timeout=30
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Resume failed: {e}")
        return False


def api_get_config(base_url: str) -> Optional[dict]:
    try:
        r = requests.get(f"{base_url}/config", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Get config failed: {e}")
        return None


def api_set_config(base_url: str, payload: dict) -> Optional[dict]:
    try:
        r = requests.post(f"{base_url}/config", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Set config failed: {e}")
        return None


def sse_stream(base_url: str, thread_id: str):
    """
    Generator yielding (event, data_str) tuples from the SSE endpoint.
    """
    url = f"{base_url}/workflow/stream/{thread_id}"
    headers = {"Accept": "text/event-stream"}
    with requests.get(url, headers=headers, stream=True, timeout=None) as r:
        r.raise_for_status()
        event = None
        data_lines = []
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()

            # Blank line indicates dispatch boundary
            if line == "":
                if event is not None:
                    data = "\n".join(data_lines) if data_lines else ""
                    yield (event, data)
                event = None
                data_lines = []
                continue

            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
            # Ignore other SSE fields (retry:, id:) for simplicity

        # Final dispatch if stream ends without trailing newline
        if event is not None:
            data = "\n".join(data_lines) if data_lines else ""
            yield (event, data)


def stream_and_render(base_url: str, thread_id: str) -> Tuple[str, str]:
    """
    Stream tokens and render them into a single assistant message.
    Returns (assistant_text, terminal_status).
    terminal_status ∈ {"ideation_feedback", "content_feedback", "finished"}
    """
    assistant_accum = ""
    terminal_status = "finished"

    # Create a single assistant chat message container for this stream
    with st.chat_message("assistant"):
        assistant_placeholder = st.empty()
        assistant_placeholder.markdown("Generating…")

    for event, data in sse_stream(base_url, thread_id):
        if event in ("start", "resume"):
            # Optional: display metadata
            continue

        if event == "token":
            try:
                payload = json.loads(data or "{}")
                content = payload.get("content", "")
            except json.JSONDecodeError:
                content = ""
            if content:
                assistant_accum += content
                assistant_placeholder.markdown(assistant_accum)
        elif event == "status":
            try:
                payload = json.loads(data or "{}")
                terminal_status = payload.get("status", "finished")
            except json.JSONDecodeError:
                terminal_status = "finished"
            break
        elif event == "error":
            try:
                payload = json.loads(data or "{}")
                err = payload.get("error", "Unknown error")
            except json.JSONDecodeError:
                err = data or "Unknown error"
            st.error(f"SSE error: {err}")
            break

    

    # If the final accumulated text looks like a media URL, embed it in-place
    if assistant_accum:
        m = re.search(r'https?://\S+', assistant_accum.strip())
        if m:
            url = m.group(0)
            if any(ext in url.lower() for ext in [".mp4", ".webm", ".mov"]):
                assistant_placeholder.video(url)
            else:
                assistant_placeholder.image(url, width=800)
        else:
            assistant_placeholder.markdown(assistant_accum)

    return assistant_accum, terminal_status


# ---------- Streamlit App ----------

st.set_page_config(page_title="Content Workflow", page_icon="🎨", layout="wide")

# Optional CSS: align both user and assistant messages to the right
st.markdown(
    """
    <style>
    [data-testid="stChatMessage"] { justify-content: flex-end !important; }
    [data-testid="stChatMessage"] > div { max-width: 75% !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "base_url" not in st.session_state:
    st.session_state.base_url = DEFAULT_BASE_URL
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "run_status" not in st.session_state:
    st.session_state.run_status = None

with st.sidebar:
    st.title("Content Workflow")
    st.caption("LangGraph + FastAPI + SSE")
    st.session_state.base_url = st.text_input(
        "API Base URL", st.session_state.base_url
    )
    if st.button("New session"):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.session_state.run_status = None
        st.rerun()
    st.subheader("Project Configuration")

    # Load current configuration (lazy + manual reload)
    if "cfg" not in st.session_state:
        cfg_resp = api_get_config(st.session_state.base_url)
        st.session_state.cfg = cfg_resp or {
            "video_duration": 10,
            "video_aspect_ratio": "16:9",
            "enable_captions": True,
            "caption_style": "professional",
            "image_size": "1024x1024",
            "image_quality": "hd",
            "auto_compliance_check": False,
            "video_resolution": "1920x1080",
        }
    if st.button("Reload config"):
        cfg_resp = api_get_config(st.session_state.base_url)
        if cfg_resp:
            st.session_state.cfg = cfg_resp
            st.success("Config reloaded from server.")

    cfg = st.session_state.get("cfg", {})

    aspect_options = ["16:9","9:16","1:1","4:5","21:9"]
    style_options = ["professional","casual","creative"]
    size_options = ["1024x1024","1792x1024","1024x1792"]
    quality_options = ["standard","hd"]

    def idx(options, value, default=0):
        try:
            return options.index(value)
        except Exception:
            return default

    with st.form("config_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            duration = st.number_input(
                "Video Duration (seconds)", min_value=5, max_value=60, value=int(cfg.get("video_duration", 10))
            )
            aspect = st.selectbox(
                "Video Aspect Ratio", aspect_options, index=idx(aspect_options, cfg.get("video_aspect_ratio","16:9"), 0)
            )
            enable_caps = st.checkbox("Enable Captions", value=bool(cfg.get("enable_captions", True)))
            auto_check = st.checkbox("Auto Compliance Prompt", value=bool(cfg.get("auto_compliance_check", False)))
        with col_b:
            style = st.selectbox(
                "Caption Style", style_options, index=idx(style_options, cfg.get("caption_style","professional"), 0)
            )
            img_size = st.selectbox(
                "Image Size", size_options, index=idx(size_options, cfg.get("image_size","1024x1024"), 0)
            )
            img_quality = st.selectbox(
                "Image Quality", quality_options, index=idx(quality_options, cfg.get("image_quality","hd"), 1)
            )

        st.caption(f"Computed Video Resolution: {cfg.get('video_resolution','')}")
        save = st.form_submit_button("Save configuration")

    if save:
        payload = {
            "video_duration": int(duration),
            "video_aspect_ratio": aspect,
            "enable_captions": bool(enable_caps),
            "caption_style": style,
            "image_size": img_size,
            "image_quality": img_quality,
            "auto_compliance_check": bool(auto_check),
        }
        saved = api_set_config(st.session_state.base_url, payload)
        if saved:
            st.session_state.cfg = saved
            st.success("Configuration updated on server.")
        else:
            st.error("Failed to update configuration on server.")

st.title("Chat")

# Render chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        content = m.get("content", "")
        # If assistant message contains a direct media URL, embed it
        match = re.search(r'https?://\S+', str(content).strip())
        if match and m.get("role") == "assistant":
            url = match.group(0)
            if any(ext in url.lower() for ext in [".mp4", ".webm", ".mov"]):
                st.video(url)
            else:
                st.image(url, width=800)
        else:
            st.markdown(content)


def start_run(user_text: str):
    # Create new thread
    thread_id = api_create(st.session_state.base_url, user_text)
    if not thread_id:
        return
    st.session_state.thread_id = thread_id
    st.session_state.run_status = None
    st.session_state.messages.append({"role": "user", "content": user_text})

    # Stream assistant
    assistant_text, status = stream_and_render(st.session_state.base_url, thread_id)
    if assistant_text:
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_text}
        )
    st.session_state.run_status = status


def resume_run(action: str, human_comment: Optional[str] = None):
    if not st.session_state.thread_id:
        st.warning("No active thread")
        return
    ok = api_resume(
        st.session_state.base_url, st.session_state.thread_id, action, human_comment
    )
    if not ok:
        return
    # Stream assistant after resume
    assistant_text, status = stream_and_render(
        st.session_state.base_url, st.session_state.thread_id
    )
    if assistant_text:
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_text}
        )
    st.session_state.run_status = status
    if status == "finished":
        # Clear the thread so user can start a new one
        st.session_state.thread_id = None


# Input area / actions
if st.session_state.thread_id is None:
    user_text = st.chat_input("Describe your campaign, platform, tone, etc.")
    if user_text:
        # Immediately render the user's message bubble
        with st.chat_message("user"):
            st.markdown(user_text)
        start_run(user_text)
        st.rerun()
else:
    # Show action panel based on current run_status
    status = st.session_state.run_status
    if status == "ideation_feedback":
        st.info("Options: type 'approve' to proceed, or type feedback to refine ideation.")
        user_reply = st.chat_input("Type 'approve' to approve, or enter feedback to refine ideation")
        if user_reply:
            # Immediately render the user's message bubble
            with st.chat_message("user"):
                st.markdown(user_reply)
            st.session_state.messages.append({"role": "user", "content": user_reply})
            if user_reply.strip().lower() in ("approve", "approved", "yes", "y"):
                resume_run("approve_ideation")
            else:
                resume_run("feedback_ideation", human_comment=user_reply)
            st.rerun()

    elif status == "content_feedback":
        st.info("Options: type 'approve' to finalize, 'policy' to run policy review, 'design' to run design review, 'caption' to generate a caption, 'linkedin' to post on LinkedIn, 'facebook' to post on Facebook, 'instagram' to post on Instagram (image only), or type feedback to improve content.")
        user_reply = st.chat_input("Type 'approve' | 'policy' | 'design' | 'caption' | 'linkedin' | 'facebook' | 'instagram' or enter feedback")
        if user_reply:
            # Immediately render the user's message bubble
            with st.chat_message("user"):
                st.markdown(user_reply)
            st.session_state.messages.append({"role": "user", "content": user_reply})
            cmd = user_reply.strip().lower()
            if cmd in ("approve", "approved", "yes", "y"):
                resume_run("approve_content")
            elif cmd in ("policy", "run policy", "policy review"):
                resume_run("run_policy")
            elif cmd in ("design", "run design", "design review"):
                resume_run("run_design")
            elif cmd in ("caption", "run caption", "caption only"):
                resume_run("run_caption")
            elif cmd in ("linkedin", "post linkedin", "post to linkedin", "publish linkedin", "publish to linkedin"):
                resume_run("post_linkedin")
            elif cmd in ("facebook", "post facebook", "post to facebook", "publish facebook", "publish to facebook"):
                resume_run("post_social_facebook")
            elif cmd in ("instagram", "post instagram", "post to instagram", "publish instagram", "publish to instagram"):
                resume_run("post_social_instagram")
            else:
                resume_run("feedback_content", human_comment=user_reply)
            st.rerun()
    else:
        # Waiting for status or finished; allow cancel
        st.write(f"Status: {status or 'running...'}")
        if st.button("End current run"):
            st.session_state.thread_id = None
            st.session_state.run_status = None
            st.rerun()
