"""
Configuration module for the Content Generation Agent.
Handles runtime configuration for video generation and caption settings.
"""

from dataclasses import dataclass
from typing import Optional


# Aspect ratio to resolution mapping with descriptions
ASPECT_RATIO_OPTIONS = {
    "16:9": {"size": "1920x1080", "desc": "Landscape - YouTube, LinkedIn, Twitter"},
    "9:16": {"size": "1080x1920", "desc": "Portrait - TikTok, Reels, Shorts"},
    "1:1": {"size": "1080x1080", "desc": "Square - Instagram Feed, Facebook"},
    "4:5": {"size": "1080x1350", "desc": "Portrait - Instagram Feed optimal"},
    "21:9": {"size": "2560x1080", "desc": "Ultra-wide - Cinematic content"}
}


@dataclass
class GenerationConfig:
    """Configuration settings for content generation."""
    
    # Video settings
    video_duration: int = 10  # Duration in seconds (5-60)
    video_aspect_ratio: str = "16:9"  # Options: 16:9, 9:16, 1:1, 4:5, 21:9
    
    # Caption settings
    enable_captions: bool = False
    caption_style: str = "professional"  # Options: professional, casual, creative
    
    # Image settings
    image_size: str = "1024x1024"  # Options: 1024x1024, 1792x1024, 1024x1792
    image_quality: str = "hd"  # Options: standard, hd
    
    # Compliance settings
    auto_compliance_check: bool = False  # Run compliance checks after generation
    
    @property
    def video_resolution(self) -> str:
        """Get video resolution based on aspect ratio."""
        return ASPECT_RATIO_OPTIONS.get(self.video_aspect_ratio, ASPECT_RATIO_OPTIONS["16:9"])["size"]
    
    def __str__(self) -> str:
        resolution = self.video_resolution
        return f"""
┌───────────────────────────────────────────────────────────┐
│              Current Configuration                         │
├───────────────────────────────────────────────────────────┤
│ 📹 VIDEO SETTINGS                                          │
│    Duration: {self.video_duration}s                                         
│    Aspect Ratio: {self.video_aspect_ratio} ({resolution})
│                                                            │
│ 📝 CAPTION SETTINGS                                        │
│    Enabled: {self.enable_captions}                                       
│    Style: {self.caption_style}                                    
│                                                            │
│ 🖼️  IMAGE SETTINGS                                         │
│    Size: {self.image_size}                                    
│    Quality: {self.image_quality}                                         
│                                                            │
│ ✅ COMPLIANCE                                              │
│    Auto-check: {self.auto_compliance_check}                                     
└───────────────────────────────────────────────────────────┘
"""


def get_config_from_user() -> GenerationConfig:
    """Interactive prompt to get configuration from user."""
    
    print("\n🔧 Configuration Setup")
    print("=" * 50)
    
    config = GenerationConfig()
    
    # Video Duration
    print("\n📹 Video Settings:")
    duration_input = input(f"  Duration in seconds (5-60) [default: {config.video_duration}]: ").strip()
    if duration_input:
        try:
            duration = int(duration_input)
            if 5 <= duration <= 60:
                config.video_duration = duration
            else:
                print("  ⚠️  Invalid range. Using default.")
        except ValueError:
            print("  ⚠️  Invalid input. Using default.")
    
    # Aspect Ratio with resolution display
    print("\n  Available aspect ratios:")
    for ratio, info in ASPECT_RATIO_OPTIONS.items():
        print(f"    • {ratio} ({info['size']}) - {info['desc']}")
    
    aspect_input = input(f"\n  Aspect ratio [default: {config.video_aspect_ratio}]: ").strip()
    if aspect_input in ASPECT_RATIO_OPTIONS:
        config.video_aspect_ratio = aspect_input
    elif aspect_input:
        print("  ⚠️  Invalid option. Using default.")
    
    # Caption Toggle
    print("\n📝 Caption Settings:")
    caption_input = input(f"  Enable captions? (yes/no) [default: {'yes' if config.enable_captions else 'no'}]: ").strip().lower()
    if caption_input in ["yes", "y", "true", "1"]:
        config.enable_captions = True
    elif caption_input in ["no", "n", "false", "0"]:
        config.enable_captions = False
    
    # Caption Style (only if captions are enabled)
    if config.enable_captions:
        style_input = input(f"  Caption style (professional/casual/creative) [default: {config.caption_style}]: ").strip().lower()
        if style_input in ["professional", "casual", "creative"]:
            config.caption_style = style_input
        elif style_input:
            print("  ⚠️  Invalid option. Using default.")
    
    # Image Settings
    print("\n🖼️  Image Settings:")
    print("  Available sizes:")
    print("    • 1024x1024 - Square")
    print("    • 1792x1024 - Landscape")
    print("    • 1024x1792 - Portrait")
    
    size_input = input(f"\n  Image size [default: {config.image_size}]: ").strip()
    if size_input in ["1024x1024", "1792x1024", "1024x1792"]:
        config.image_size = size_input
    elif size_input:
        print("  ⚠️  Invalid option. Using default.")
    
    quality_input = input(f"  Image quality (standard/hd) [default: {config.image_quality}]: ").strip().lower()
    if quality_input in ["standard", "hd"]:
        config.image_quality = quality_input
    elif quality_input:
        print("  ⚠️  Invalid option. Using default.")
    
    # Compliance Settings
    print("\n✅ Compliance Settings:")
    compliance_input = input(f"  Auto-run compliance checks after generation? (yes/no) [default: {'yes' if config.auto_compliance_check else 'no'}]: ").strip().lower()
    if compliance_input in ["yes", "y", "true", "1"]:
        config.auto_compliance_check = True
    elif compliance_input in ["no", "n", "false", "0"]:
        config.auto_compliance_check = False
    
    print("\n✅ Configuration saved!")
    print(config)
    
    return config


# Global config instance - will be set by main.py
current_config: Optional[GenerationConfig] = None


def get_current_config() -> GenerationConfig:
    """Get the current configuration, creating default if none exists."""
    global current_config
    if current_config is None:
        current_config = GenerationConfig()
    return current_config


def set_current_config(config: GenerationConfig) -> None:
    """Set the global configuration."""
    global current_config
    current_config = config