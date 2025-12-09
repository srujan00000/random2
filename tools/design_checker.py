"""
Design Compliance Checker Agent.
Reviews generated visual content against design guidelines.
"""

import os
from pathlib import Path
from langchain.tools import tool
from openai import OpenAI


def get_client():
    """Get OpenAI client with lazy initialization."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_design_guidelines() -> str:
    """Load design guidelines from file."""
    guidelines_path = Path(__file__).parent.parent / "guidelines" / "design_guidelines.md"
    
    if guidelines_path.exists():
        with open(guidelines_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """Default Design Guidelines:
        - Use brand-approved colors
        - High resolution (min 1080p)
        - Proper composition and framing
        - Accessible design (good contrast)
        - Professional quality"""


@tool
def check_design_compliance(
    content_description: str,
    content_type: str = "image",
    resolution: str = "",
    additional_context: str = ""
) -> str:
    """
    Check if generated visual content complies with design guidelines.
    
    Args:
        content_description: Description of the image/video content, including 
                            visual elements, colors, composition, etc.
        content_type: Type of content ("image" or "video").
        resolution: Resolution of the content if known (e.g., "1920x1080").
        additional_context: Any additional context about the visual elements.
    
    Returns:
        str: Design compliance report with pass/fail status and recommendations.
    """
    try:
        design_guidelines = load_design_guidelines()
        
        client = get_client()
        
        system_prompt = f"""You are a design compliance reviewer. Your job is to review AI-generated visual content (images/videos) against brand design guidelines.

DESIGN GUIDELINES:
{design_guidelines}

Analyze the content description and provide a structured design compliance report. Since you cannot see the actual image/video, base your assessment on the description provided and flag any potential concerns.

Format your response EXACTLY as:
═══════════════════════════════════════════
      DESIGN COMPLIANCE REPORT
═══════════════════════════════════════════

OVERALL STATUS: [✅ PASS / ⚠️ WARNING / ❌ FAIL]

SCORE: [X/10]

CONTENT TYPE: [{content_type.upper()}]

───────────────────────────────────────────
CATEGORY ASSESSMENT
───────────────────────────────────────────

1. COLOR & BRANDING
   Status: [✅/⚠️/❌]
   Notes: [Assessment based on description]

2. COMPOSITION & FRAMING
   Status: [✅/⚠️/❌]
   Notes: [Assessment based on description]

3. TECHNICAL QUALITY
   Status: [✅/⚠️/❌]
   Notes: [Assessment based on resolution and description]

4. ACCESSIBILITY
   Status: [✅/⚠️/❌]
   Notes: [Assessment of accessibility considerations]

5. PLATFORM OPTIMIZATION
   Status: [✅/⚠️/❌]
   Notes: [Assessment of format/size for intended use]

───────────────────────────────────────────
POTENTIAL ISSUES
───────────────────────────────────────────
[List any potential design issues, or "None identified" if appears compliant]

───────────────────────────────────────────
RECOMMENDATIONS
───────────────────────────────────────────
[List actionable design recommendations]

───────────────────────────────────────────
MANUAL REVIEW NEEDED
───────────────────────────────────────────
[List aspects that require human visual review]

═══════════════════════════════════════════
"""

        user_prompt = f"""Review this visual content for design compliance:

CONTENT TYPE: {content_type}
RESOLUTION: {resolution if resolution else "Not specified"}

CONTENT DESCRIPTION:
{content_description}

{f"ADDITIONAL CONTEXT: {additional_context}" if additional_context else ""}

Provide your design compliance report. Note: Since you cannot see the actual {content_type}, focus on the description and flag items that need manual visual review."""

        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Design compliance check failed: {str(e)}"