# """
# Content Generation Agent - CLI Entry Point
# A conversational AI agent for generating social media content.
# """

# import os
# import sys
# from dotenv import load_dotenv

# # Load environment variables first
# load_dotenv()

# from config import get_config_from_user, set_current_config, get_current_config
# from content_generator_agent import ContentGeneratorAgent
# from agents.design_agent import DesignComplianceAgent
# from agents.policy_agent import PolicyComplianceAgent


# def print_banner():
#     """Print the application banner."""
#     banner = """
# ╔═══════════════════════════════════════════════════════════════════╗
# ║                                                                   ║
# ║   🎨 CONTENT GENERATION AGENT                                     ║
# ║   ─────────────────────────────────────────────────────────────   ║
# ║   AI-Powered Social Media Content Creator                         ║
# ║                                                                   ║
# ║   Powered by: GPT-5 | DALL-E 3 | Sora                            ║
# ║                                                                   ║
# ╚═══════════════════════════════════════════════════════════════════╝
# """
#     print(banner)


# def print_help():
#     """Print available commands."""
#     help_text = """
# ┌─────────────────────────────────────────────────────────────────┐
# │  Available Commands                                             │
# ├─────────────────────────────────────────────────────────────────┤
# │  /config    - Reconfigure generation settings                  │
# │  /settings  - View current settings                            │
# │  /clear     - Clear conversation history                       │
# │  /design    - Run design compliance review                     │
# │  /policy    - Run policy compliance review                     │
# │  /help      - Show this help message                           │
# │  /exit      - Exit the application                             │
# │  /quit      - Exit the application                             │
# └─────────────────────────────────────────────────────────────────┘

# 💡 Tips:
#    • Describe your event/theme and ask for content suggestions
#    • Request specific platforms: "Create an Instagram post for..."
#    • Ask for variations: "Give me 3 different styles for..."
#    • Refine results: "Make it more professional" or "Add more energy"
# """
#     print(help_text)


# def run_compliance_flow():
#     """Interactive flow to run both policy and design compliance checks."""
#     try:
#         print("\n🔎 Compliance Check")
#         content_description = input("  Describe the generated content (required): ").strip()
#         if not content_description:
#             print("  ⚠️  Content description is required. Skipping compliance.")
#             return

#         # Design inputs
#         content_type = (input("  Content type (image/video) [default: image]: ").strip().lower() or "image")
#         resolution = input("  Resolution (e.g., 1920x1080) [optional]: ").strip()
#         additional_context = input("  Additional context for design check [optional]: ").strip()

#         # Policy inputs
#         platform = (input("  Target platform (instagram/linkedin/twitter/etc.) [default: general]: ").strip().lower() or "general")
#         caption = input("  Caption text used (if any) [optional]: ").strip()

#         # Run Design check
#         print("\n🧪 Running Design Compliance...")
#         d_agent = DesignComplianceAgent()
#         d_prompt = f"""Run design compliance check.

# content_type: {content_type}
# resolution: {resolution if resolution else 'Not specified'}
# content_description:
# {content_description}

# {f'additional_context: {additional_context}' if additional_context else ''}
# Provide the full structured report."""
#         d_result = d_agent.chat(d_prompt)
#         print(d_result)

#         # Run Policy check
#         print("\n🧪 Running Policy Compliance...")
#         p_agent = PolicyComplianceAgent()
#         p_prompt = f"""Run policy compliance check.

# platform: {platform}
# caption: {caption if caption else 'No caption provided'}
# content_description:
# {content_description}

# Provide the full structured report."""
#         p_result = p_agent.chat(p_prompt)
#         print(p_result)

#     except Exception as e:
#         print(f"❌ Compliance flow failed: {str(e)}")


# def check_api_key() -> bool:
#     """Verify that the OpenAI API key is configured."""
#     api_key = os.getenv("OPENAI_API_KEY")
    
#     if not api_key or api_key == "your_openai_api_key_here":
#         print("\n❌ ERROR: OpenAI API key not configured!")
#         print("\nPlease set your API key in the .env file:")
#         print("  OPENAI_API_KEY=sk-your-actual-api-key-here")
#         print("\nGet your API key from: https://platform.openai.com/api-keys")
#         return False
    
#     return True


# def main():
#     """Main entry point for the CLI application."""
    
#     # Print banner
#     print_banner()
    
#     # Check API key
#     if not check_api_key():
#         sys.exit(1)
    
#     print("✅ API key found!")
    
#     # Get configuration from user
#     print("\nLet's configure your content generation settings.")
#     print("(Press Enter to accept default values)")
    
#     config = get_config_from_user()
#     set_current_config(config)
    
#     # Initialize agent
#     print("\n🚀 Initializing Content Generation Agent...")
#     agent = ContentGeneratorAgent()
#     print("✅ Agent ready!\n")
    
#     # Print help
#     print_help()
    
#     # Main chat loop
#     print("\n" + "=" * 65)
#     print("  Start chatting! Tell me about your event or content needs.")
#     print("=" * 65 + "\n")
    
#     while True:
#         try:
#             # Get user input
#             user_input = input("\n🧑 You: ").strip()
            
#             # Skip empty input
#             if not user_input:
#                 continue
            
#             # Handle commands
#             if user_input.startswith("/"):
#                 command = user_input.lower()
                
#                 if command in ["/exit", "/quit"]:
#                     print("\n👋 Goodbye! Thanks for using Content Generation Agent.")
#                     break
                
#                 elif command == "/help":
#                     print_help()
#                     continue

#                 elif command == "/design":
#                     print("\n🎨 Design Compliance")
#                     content_type = (input("  Content type (image/video) [default: image]: ").strip().lower() or "image")
#                     resolution = input("  Resolution (e.g., 1920x1080) [optional]: ").strip()
#                     content_description = input("  Describe the content (required): ").strip()
#                     additional_context = input("  Additional context [optional]: ").strip()
#                     if not content_description:
#                         print("  ⚠️  Content description is required.")
#                         continue
#                     d_agent = DesignComplianceAgent()
#                     prompt = f"""Run design compliance check.

# content_type: {content_type}
# resolution: {resolution if resolution else 'Not specified'}
# content_description:
# {content_description}

# {f'additional_context: {additional_context}' if additional_context else ''}

# Provide the full structured report."""
#                     print("\n🤖 Design Agent: ")
#                     print("-" * 55)
#                     print(d_agent.chat(prompt))
#                     print("-" * 55)
#                     continue

#                 elif command == "/policy":
#                     print("\n🛡️ Policy Compliance")
#                     platform = (input("  Target platform (instagram/linkedin/twitter/etc.) [default: general]: ").strip().lower() or "general")
#                     content_description = input("  Describe the content (required): ").strip()
#                     caption = input("  Caption text used (if any) [optional]: ").strip()
#                     if not content_description:
#                         print("  ⚠️  Content description is required.")
#                         continue
#                     p_agent = PolicyComplianceAgent()
#                     prompt = f"""Run policy compliance check.

# platform: {platform}
# caption: {caption if caption else 'No caption provided'}
# content_description:
# {content_description}

# Provide the full structured report."""
#                     print("\n🤖 Policy Agent: ")
#                     print("-" * 55)
#                     print(p_agent.chat(prompt))
#                     print("-" * 55)
#                     continue
                
#                 elif command == "/config":
#                     print("\n🔄 Reconfiguring settings...")
#                     new_config = get_config_from_user()
#                     set_current_config(new_config)
#                     agent.refresh_agent()
#                     print("✅ Agent updated with new configuration!")
#                     continue
                
#                 elif command == "/settings":
#                     print(get_current_config())
#                     continue
                
#                 elif command == "/clear":
#                     agent.reset_history()
#                     print("✅ Conversation history cleared!")
#                     continue
                
#                 else:
#                     print(f"❓ Unknown command: {user_input}")
#                     print("   Type /help to see available commands.")
#                     continue
            
#             # Send to agent and get response
#             print("\n🤖 Agent: ", end="")
#             print("-" * 55)
            
#             response = agent.chat(user_input)
#             print(response)
            
#             print("-" * 55)

#             # Optional auto compliance prompt
#             try:
#                 cfg = get_current_config()
#                 if cfg.auto_compliance_check:
#                     choice = input("\n🔎 Run policy/design compliance checks now? (yes/no) [default: no]: ").strip().lower()
#                     if choice in ["yes", "y"]:
#                         run_compliance_flow()
#             except Exception:
#                 # Non-fatal: continue normal loop if any issue in auto-check
#                 pass
        
#         except KeyboardInterrupt:
#             print("\n\n👋 Goodbye! Thanks for using Content Generation Agent.")
#             break
        
#         except Exception as e:
#             print(f"\n❌ An error occurred: {str(e)}")
#             print("   Please try again or type /help for assistance.")


# if __name__ == "__main__":
#     main()


from fastapi import FastAPI
from webapi.api import router
from webapi.cors_config import add_cors_middleware

app = FastAPI(title="Content Workflow (LangGraph + SSE)")
add_cors_middleware(app)
app.include_router(router)

# Optional root probe
@app.get("/")
def root():
    return {"status": "ok", "service": "content-workflow", "routes": [
        "/workflow/stream/create",
        "/workflow/stream/resume",
        "/workflow/stream/{thread_id}"
    ]}
