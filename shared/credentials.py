"""
Credential management for Canvas and LLM providers
Handles loading from ~/canvas-secrets.key
"""

from pathlib import Path
from typing import Tuple, Dict, Optional
import os


class CredentialsError(Exception):
    """Raised when credentials cannot be loaded"""
    pass


def get_credentials_path() -> Path:
    """
    Get the path to the credentials file.
    
    Returns:
        Path to canvas-secrets.key
    """
    return Path.home() / "canvas-secrets.key"


def load_canvas_credentials() -> Tuple[str, str]:
    """
    Load Canvas API credentials from ~/canvas-secrets.key
    
    Returns:
        Tuple of (api_url, token)
        
    Raises:
        CredentialsError: If credentials file not found or invalid
    """
    key_path = get_credentials_path()
    
    if not key_path.exists():
        raise CredentialsError(
            f"Credentials file not found: {key_path}\n\n"
            f"Create ~/canvas-secrets.key with the following format:\n"
            f"Line 1: Canvas base URL (e.g., https://canvas.instructure.com)\n"
            f"Line 2: Canvas API token\n"
            f"Line 3: Anthropic API key (optional)\n"
            f"Line 4: OpenAI API key (optional)\n"
            f"Line 5: Google GenAI API key (optional)"
        )
    
    try:
        lines = [
            line.strip() 
            for line in key_path.read_text(encoding="utf-8").splitlines() 
            if line.strip()
        ]
    except Exception as e:
        raise CredentialsError(f"Error reading credentials file: {e}")
    
    if len(lines) < 2:
        raise CredentialsError(
            "canvas-secrets.key must have at least 2 lines:\n"
            "Line 1: Canvas API URL\n"
            "Line 2: Canvas API token"
        )
    
    # Normalize API URL - just clean it, don't add /api/v1
    # The Canvas API methods will handle adding /api/v1 to the path
    api_url = lines[0].rstrip("/")
    
    token = lines[1]
    
    # Validate
    if not api_url.startswith("http"):
        raise CredentialsError(f"Invalid Canvas API URL: {api_url}")
    
    if not token or len(token) < 10:
        raise CredentialsError("Invalid Canvas API token (too short)")
    
    return api_url, token


def load_llm_keys() -> Dict[str, Optional[str]]:
    """
    Load LLM API keys from credentials file.
    
    Returns:
        Dictionary with 'anthropic', 'openai', and 'google' keys
        Values are None if not provided in credentials file
    """
    key_path = get_credentials_path()
    
    if not key_path.exists():
        return {'anthropic': None, 'openai': None, 'google': None}
    
    try:
        lines = [
            line.strip() 
            for line in key_path.read_text(encoding="utf-8").splitlines() 
            if line.strip()
        ]
    except Exception:
        return {'anthropic': None, 'openai': None, 'google': None}
    
    keys = {
        'anthropic': lines[2] if len(lines) > 2 and lines[2] else None,
        'openai': lines[3] if len(lines) > 3 and lines[3] else None,
        'google': lines[4] if len(lines) > 4 and lines[4] else None,
    }
    
    # Also check environment variables as fallback
    if not keys['anthropic']:
        keys['anthropic'] = os.getenv('ANTHROPIC_API_KEY')
    
    if not keys['openai']:
        keys['openai'] = os.getenv('OPENAI_API_KEY')
    
    if not keys['google']:
        keys['google'] = os.getenv('GOOGLE_API_KEY')
    
    return keys


def get_llm_key(provider: str) -> str:
    """
    Get API key for a specific LLM provider.
    
    Args:
        provider: 'anthropic', 'openai', or 'google'
        
    Returns:
        API key string
        
    Raises:
        CredentialsError: If key not found for provider
    """
    keys = load_llm_keys()
    key = keys.get(provider.lower())
    
    if not key:
        raise CredentialsError(
            f"No API key found for {provider}.\n"
            f"Add it to ~/canvas-secrets.key or set {provider.upper()}_API_KEY environment variable."
        )
    
    return key


def validate_credentials() -> Dict[str, bool]:
    """
    Validate all credentials.
    
    Returns:
        Dictionary showing which credentials are available
    """
    results = {
        'canvas_url': False,
        'canvas_token': False,
        'anthropic_key': False,
        'openai_key': False,
        'google_key': False,
    }
    
    # Check Canvas credentials
    try:
        url, token = load_canvas_credentials()
        results['canvas_url'] = bool(url)
        results['canvas_token'] = bool(token)
    except CredentialsError:
        pass
    
    # Check LLM keys
    llm_keys = load_llm_keys()
    results['anthropic_key'] = bool(llm_keys.get('anthropic'))
    results['openai_key'] = bool(llm_keys.get('openai'))
    results['google_key'] = bool(llm_keys.get('google'))
    
    return results


def print_credentials_status():
    """
    Print a human-readable status of credentials.
    Useful for debugging setup issues.
    """
    status = validate_credentials()
    
    print("Credentials Status:")
    print("=" * 50)
    print(f"✓ Canvas URL:       {'✓ Available' if status['canvas_url'] else '✗ Missing'}")
    print(f"✓ Canvas Token:     {'✓ Available' if status['canvas_token'] else '✗ Missing'}")
    print(f"✓ Anthropic Key:    {'✓ Available' if status['anthropic_key'] else '✗ Missing'}")
    print(f"✓ OpenAI Key:       {'✓ Available' if status['openai_key'] else '✗ Missing'}")
    print(f"✓ Google Key:       {'✓ Available' if status['google_key'] else '✗ Missing'}")
    print("=" * 50)
    
    # Show warnings
    if not all([status['canvas_url'], status['canvas_token']]):
        print("\n⚠️  Canvas credentials missing!")
        print("Create ~/canvas-secrets.key with Canvas URL and token")
    
    if not (status['anthropic_key'] or status['openai_key'] or status['google_key']):
        print("\n⚠️  No LLM API keys found!")
        print("Add Anthropic, OpenAI, or Google key to ~/canvas-secrets.key")


# Convenience function for Streamlit apps
def init_streamlit_credentials():
    """
    Initialize credentials in Streamlit session state.
    Call this at the start of your Streamlit app.
    
    Returns:
        Tuple of (canvas_url, canvas_token, llm_keys)
    """
    import streamlit as st
    
    if 'canvas_url' not in st.session_state:
        try:
            canvas_url, canvas_token = load_canvas_credentials()
            st.session_state.canvas_url = canvas_url
            st.session_state.canvas_token = canvas_token
        except CredentialsError as e:
            st.error(f"Credentials Error: {e}")
            st.stop()
    
    if 'llm_keys' not in st.session_state:
        st.session_state.llm_keys = load_llm_keys()
    
    return (
        st.session_state.canvas_url,
        st.session_state.canvas_token,
        st.session_state.llm_keys
    )


if __name__ == "__main__":
    # Test credentials when run directly
    print_credentials_status()