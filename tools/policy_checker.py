"""
Policy Compliance Checker Agent.
Reviews generated content against policy guidelines.
"""

import os
from pathlib import Path
from langchain.tools import tool
from openai import OpenAI


def get_client():
    """Get OpenAI client with lazy initialization."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_policy_guidelines() -> str:
    """Load policy guidelines from file."""
    guidelines_path = Path(__file__).parent.parent / "guidelines" / "policy_guidelines.md"
    
    if guidelines_path.exists():
        with open(guidelines_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """Default Policy Guidelines:
        - No prohibited content (violence, discrimination, explicit)
        - Professional tone required
        - No misleading claims
        - Proper disclosures for sponsored content
        - No copyright violations"""


@tool
def check_policy_compliance(
    content_description: str,
    caption: str = "",
    platform: str = "general"
) -> str:
    """
    Check if generated content complies with policy guidelines.
    
    Args:
        content_description: Description of the image/video content that was generated.
        caption: The caption/text that accompanies the content (if any).
        platform: Target platform (instagram, linkedin, twitter, etc.)
    
    Returns:
        str: Compliance report with pass/fail status and recommendations.
    """
    try:
        policy_guidelines = load_policy_guidelines()
        
        client = get_client()
        
        system_prompt = f"""You are a content policy compliance reviewer. Your job is to review AI-generated social media content against company policy guidelines.

POLICY GUIDELINES:
{policy_guidelines}

Analyze the content and provide a structured compliance report. Be thorough but fair.

Format your response EXACTLY as:
═══════════════════════════════════════════
      POLICY COMPLIANCE REPORT
═══════════════════════════════════════════

OVERALL STATUS: [✅ PASS / ⚠️ WARNING / ❌ FAIL]

SCORE: [X/10]

───────────────────────────────────────────
CATEGORY ASSESSMENT
───────────────────────────────────────────

1. PROHIBITED CONTENT
   Status: [✅/⚠️/❌]
   Notes: [Brief assessment]

2. BRAND VOICE & TONE
   Status: [✅/⚠️/❌]
   Notes: [Brief assessment]

3. PLATFORM COMPLIANCE
   Status: [✅/⚠️/❌]
   Notes: [Brief assessment]

4. LEGAL & DISCLOSURE
   Status: [✅/⚠️/❌]
   Notes: [Brief assessment]

───────────────────────────────────────────
ISSUES FOUND
───────────────────────────────────────────
[List any issues, or "None" if compliant]

───────────────────────────────────────────
RECOMMENDATIONS
───────────────────────────────────────────
[List actionable recommendations]

═══════════════════════════════════════════
"""

        user_prompt = f"""Review this content for policy compliance:

PLATFORM: {platform}

CONTENT DESCRIPTION:
{content_description}

CAPTION/TEXT:
{caption if caption else "No caption provided"}

Provide your compliance report."""

        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Policy compliance check failed: {str(e)}"