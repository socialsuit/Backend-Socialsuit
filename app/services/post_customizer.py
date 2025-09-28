def customize(content: str, platform: str) -> dict:
    """
    Optimizes content for specific social platforms
    
    Args:
        content: Input text to customize
        platform: Target platform (twitter/instagram/linkedin/etc)
    
    Returns:
        {"custom": formatted_text} or {"error": message}
    """
    if not isinstance(content, str):
        return {"error": "Content must be string"}
        
    content = content.strip()
    if not content:
        return {"error": "Empty content"}
    
    platform_rules = {
        "twitter": {"max_len": 280, "hashtags": []},
        "instagram": {"max_len": 2200, "hashtags": ["#instagood", "#reels"]},
        "linkedin": {"max_len": 3000, "hashtags": ["#career", "#networking"]},
        "tiktok": {"max_len": 150, "hashtags": ["#fyp", "#viral"]}
    }
    
    config = platform_rules.get(platform.lower(), {})
    
    # Apply length limit
    if config.get("max_len"):
        content = content[:config["max_len"]]
    
    # Add hashtags
    if config.get("hashtags"):
        content += " " + " ".join(config["hashtags"])
    
    return {"custom": content.strip()}