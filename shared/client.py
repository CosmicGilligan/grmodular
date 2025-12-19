# client.py — unified raw SDK client loader using canvas-secrets.key
import anthropic
from openai import OpenAI

# Make Google import optional
try:
    from google import genai
    GOOGLE_AVAILABLE = True
except ImportError:
    genai = None
    GOOGLE_AVAILABLE = False

from shared.credentials import load_llm_keys


def get_client(provider: str = "anthropic"):
    """
    Return a low-level SDK client for: 'anthropic' | 'openai' | 'google'
    Uses keys from ~/canvas-secrets.key
    
    Args:
        provider: 'anthropic', 'openai', or 'google'
        
    Returns:
        Client instance
    """
    keys = load_llm_keys()
    p = provider.lower()
    
    if p == "anthropic":
        api_key = keys.get('anthropic')
        if not api_key:
            raise ValueError("Anthropic API key not found in ~/canvas-secrets.key (line 3)")
        return anthropic.Anthropic(api_key=api_key)
    
    elif p == "openai":
        api_key = keys.get('openai')
        if not api_key:
            raise ValueError("OpenAI API key not found in ~/canvas-secrets.key (line 4)")
        return OpenAI(api_key=api_key)
    
    elif p == "google":
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google GenAI not installed.\n"
                "Run: pip install google-generativeai"
            )
        api_key = keys.get('google')
        if not api_key:
            raise ValueError("Google API key not found in ~/canvas-secrets.key (line 5)")
        return genai.Client(api_key=api_key)
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'anthropic', 'openai', or 'google'")
