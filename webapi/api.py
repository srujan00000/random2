from fastapi import APIRouter, Request
from uuid import uuid4
from sse_starlette.sse import EventSourceResponse
import json

from .models import StartRequest, ResumeRequest, GraphResponse, ConfigPayload, ConfigResponse
from workflow.graph import graph
from config import GenerationConfig, get_current_config, set_current_config

router = APIRouter()

# In-memory run configs to coordinate create/resume versus stream
run_configs: dict[str, dict] = {}


@router.post("/workflow/stream/create", response_model=GraphResponse)
def create_workflow_stream(request: StartRequest) -> GraphResponse:
    """
    Create a new workflow run (thread) and return thread_id.
    The streaming endpoint will then be called with this thread_id.
    """
    thread_id = str(uuid4())
    run_configs[thread_id] = {
        "type": "start",
        "human_request": request.human_request,
    }
    return GraphResponse(thread_id=thread_id, run_status="pending", assistant_response=None)


@router.post("/workflow/stream/resume", response_model=GraphResponse)
def resume_workflow_stream(request: ResumeRequest) -> GraphResponse:
    """
    Resume an interrupted workflow at a feedback node.
    Supported actions:
      - approve_ideation, feedback_ideation
      - approve_content, feedback_content
      - run_policy, run_design
    """
    thread_id = request.thread_id
    run_configs[thread_id] = {
        "type": "resume",
        "action": request.action,
        "human_comment": request.human_comment,
    }
    return GraphResponse(thread_id=thread_id, run_status="pending", assistant_response=None)


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """
    Return the current GenerationConfig as JSON.
    """
    cfg = get_current_config()
    return ConfigResponse(
        video_duration=cfg.video_duration,
        video_aspect_ratio=cfg.video_aspect_ratio,
        enable_captions=cfg.enable_captions,
        caption_style=cfg.caption_style,
        image_size=cfg.image_size,
        image_quality=cfg.image_quality,
        auto_compliance_check=cfg.auto_compliance_check,
        video_resolution=cfg.video_resolution,
    )


@router.post("/config", response_model=ConfigResponse)
def set_config(payload: ConfigPayload) -> ConfigResponse:
    """
    Set the runtime GenerationConfig via POST.
    Note: Duration is clamped to [5, 60] as a guardrail.
    """
    vd = payload.video_duration
    if vd < 5 or vd > 60:
        vd = 10

    new_cfg = GenerationConfig(
        video_duration=vd,
        video_aspect_ratio=payload.video_aspect_ratio,
        enable_captions=payload.enable_captions,
        caption_style=payload.caption_style,
        image_size=payload.image_size,
        image_quality=payload.image_quality,
        auto_compliance_check=payload.auto_compliance_check,
    )
    set_current_config(new_cfg)

    return ConfigResponse(
        video_duration=new_cfg.video_duration,
        video_aspect_ratio=new_cfg.video_aspect_ratio,
        enable_captions=new_cfg.enable_captions,
        caption_style=new_cfg.caption_style,
        image_size=new_cfg.image_size,
        image_quality=new_cfg.image_quality,
        auto_compliance_check=new_cfg.auto_compliance_check,
        video_resolution=new_cfg.video_resolution,
    )


@router.get("/workflow/stream/{thread_id}")
async def stream_workflow(request: Request, thread_id: str):
    """
    SSE endpoint to stream tokens from the LangGraph workflow.
    Emits events:
      - start/resume (metadata)
      - token (json: {"content": "..."} for certain nodes)
      - status (json: {"status": "ideation_feedback" | "content_feedback" | "finished"})
      - error  (json: {"error": "..."})
    """
    if thread_id not in run_configs:
        return {"error": "Thread ID not found. Call /workflow/stream/create or /workflow/stream/resume first."}

    run_data = run_configs[thread_id]
    config = {"configurable": {"thread_id": thread_id}}

    # Determine input state for graph.run/stream and/or update state when resuming
    input_state = None
    if run_data["type"] == "start":
        event_type = "start"
        # Initial input to begin the graph
        input_state = {"human_request": run_data["human_request"]}
    else:
        event_type = "resume"
        # Update the graph state with the action and optional human comment
        state_update = {"status": run_data.get("action")}
        if run_data.get("human_comment") is not None:
            state_update["human_comment"] = run_data["human_comment"]
        graph.update_state(config, state_update)
        # No new input_state needed for resume

    async def event_generator():
        # Initial event with thread_id
        initial_data = json.dumps({"thread_id": thread_id})
        yield {"event": event_type, "data": initial_data}

        try:
            # Stream messages from selected nodes
            STREAM_NODES = {
                "ideation_node",
                "content_generation_node",
                "policy_review_node",
                "design_review_node",
                "caption_generation_node",
                "linkedin_post_node",
                "social_post_node",
            }

            for msg, metadata in graph.stream(input_state, config, stream_mode="messages"):
                if await request.is_disconnected():
                    break

                node_name = metadata.get("langgraph_node")
                if node_name in STREAM_NODES:
                    payload = json.dumps({"content": getattr(msg, "content", "")})
                    yield {"event": "token", "data": payload}

            # Decide terminal status: which feedback (interrupt) or finished
            state = graph.get_state(config)
            if state.next:
                next_nodes = set(state.next)
                if "feedback_ideation" in next_nodes:
                    yield {"event": "status", "data": json.dumps({"status": "ideation_feedback"})}
                elif "feedback_content" in next_nodes:
                    yield {"event": "status", "data": json.dumps({"status": "content_feedback"})}
                else:
                    # Unknown next state; treat as finished for now
                    yield {"event": "status", "data": json.dumps({"status": "finished"})}
            else:
                yield {"event": "status", "data": json.dumps({"status": "finished"})}

            # Clean up run config
            if thread_id in run_configs:
                del run_configs[thread_id]

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
            if thread_id in run_configs:
                del run_configs[thread_id]

    return EventSourceResponse(event_generator())
