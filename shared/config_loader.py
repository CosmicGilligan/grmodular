"""
Configuration loader for grading system
Loads course configurations from config/courses.json
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage configuration from config files"""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.courses_config = None
        self.knowledge_bases = None
        self.settings = None
        
        # Load configuration on init
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from courses.json"""
        config_file = self.config_dir / "courses.json"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}\n"
                f"Please create config/courses.json with your course configuration."
            )
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            self.courses_config = config.get('courses', {})
            self.knowledge_bases = config.get('knowledge_bases', {})
            self.settings = config.get('settings', {})
            
            logger.info(f"Loaded configuration for {len(self.courses_config)} courses")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}")
    
    def get_courses_dict(self) -> Dict[str, Tuple[int, str]]:
        """
        Get courses dictionary for UI selection
        
        Returns:
            Dictionary mapping course names to (canvas_id, course_type) tuples
            Example: {"HIST 101 - Section 1": (12345, "WorldHistory")}
        """
        courses_dict = {}
        
        for course_name, course_config in self.courses_config.items():
            if course_config.get('enabled', True):
                canvas_id = course_config['canvas_id']
                course_type = course_config['course_type']
                courses_dict[course_name] = (canvas_id, course_type)
        
        return courses_dict
    
    def get_course_names(self) -> List[str]:
        """
        Get list of enabled course names
        
        Returns:
            List of course names
        """
        return [
            name for name, config in self.courses_config.items()
            if config.get('enabled', True)
        ]
    
    def get_course_config(self, course_name: str) -> Optional[Dict]:
        """
        Get configuration for a specific course
        
        Args:
            course_name: Name of the course
            
        Returns:
            Course configuration dictionary or None if not found
        """
        return self.courses_config.get(course_name)
    
    def get_knowledge_base_path(self, course_type: str) -> str:
        """
        Get the path to knowledge base for a course type
        
        Args:
            course_type: Course type (e.g., "WorldHistory", "USHistory")
            
        Returns:
            Path to knowledge base
        """
        kb_config = self.knowledge_bases.get(course_type, {})
        path = kb_config.get('path', '')
        
        # Expand ~ to home directory
        return os.path.expanduser(path)
    
    def get_embeddings_file(self, course_type: str) -> str:
        """
        Get the embeddings filename for a course type
        
        Args:
            course_type: Course type (e.g., "WorldHistory", "USHistory")
            
        Returns:
            Embeddings filename
        """
        kb_config = self.knowledge_bases.get(course_type, {})
        return kb_config.get('embeddings_file', f'embeddings_{course_type}.pkl')
    
    def get_setting(self, key: str, default=None):
        """
        Get a setting value
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration
        
        Returns:
            List of validation messages (errors/warnings)
        """
        messages = []
        
        # Check courses
        if not self.courses_config:
            messages.append("ERROR: No courses configured in courses.json")
            return messages
        
        for course_name, course_config in self.courses_config.items():
            # Check required fields
            required_fields = ['canvas_id', 'course_type', 'embeddings_path']
            for field in required_fields:
                if field not in course_config:
                    messages.append(f"ERROR: Course '{course_name}' missing required field: {field}")
            
            # Check canvas_id is numeric
            if 'canvas_id' in course_config:
                if not isinstance(course_config['canvas_id'], int):
                    messages.append(f"WARNING: Course '{course_name}' canvas_id should be a number")
            
            # Check embeddings path exists
            if 'embeddings_path' in course_config:
                path = os.path.expanduser(course_config['embeddings_path'])
                if not os.path.exists(path):
                    messages.append(f"WARNING: Course '{course_name}' embeddings path not found: {path}")
        
        # Check knowledge bases
        if not self.knowledge_bases:
            messages.append("WARNING: No knowledge bases configured")
        
        for kb_name, kb_config in self.knowledge_bases.items():
            if 'path' not in kb_config:
                messages.append(f"ERROR: Knowledge base '{kb_name}' missing path")
            else:
                path = os.path.expanduser(kb_config['path'])
                if not os.path.exists(path):
                    messages.append(f"WARNING: Knowledge base '{kb_name}' path not found: {path}")
        
        return messages
    
    def __repr__(self) -> str:
        return f"<ConfigLoader: {len(self.courses_config)} courses, {len(self.knowledge_bases)} knowledge bases>"


# Global config instance (singleton pattern)
_config_instance = None

def get_config(config_dir: str = "config") -> ConfigLoader:
    """
    Get the global config instance (singleton)
    
    Args:
        config_dir: Directory containing configuration files
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader(config_dir)
    
    return _config_instance


def reload_config(config_dir: str = "config") -> ConfigLoader:
    """
    Force reload of configuration
    
    Args:
        config_dir: Directory containing configuration files
        
    Returns:
        New ConfigLoader instance
    """
    global _config_instance
    _config_instance = ConfigLoader(config_dir)
    return _config_instance


# Convenience functions
def get_courses() -> Dict[str, Tuple[int, str]]:
    """Get courses dictionary for UI"""
    return get_config().get_courses_dict()


def get_course_names() -> List[str]:
    """Get list of course names"""
    return get_config().get_course_names()


def get_kb_path(course_type: str) -> str:
    """Get knowledge base path for course type"""
    return get_config().get_knowledge_base_path(course_type)


def get_embeddings_file(course_type: str) -> str:
    """Get embeddings filename for course type"""
    return get_config().get_embeddings_file(course_type)


if __name__ == "__main__":
    # Test configuration loading
    print("Testing configuration loader...")
    print()
    
    try:
        config = get_config()
        print(f"✓ Configuration loaded: {config}")
        print()
        
        print("Courses:")
        for name, (canvas_id, course_type) in config.get_courses_dict().items():
            print(f"  - {name}")
            print(f"    Canvas ID: {canvas_id}")
            print(f"    Type: {course_type}")
            print(f"    KB Path: {config.get_knowledge_base_path(course_type)}")
            print()
        
        print("Knowledge Bases:")
        for kb_name, kb_config in config.knowledge_bases.items():
            print(f"  - {kb_name}")
            print(f"    Path: {kb_config.get('path')}")
            print(f"    Embeddings: {kb_config.get('embeddings_file')}")
            print()
        
        print("Validation:")
        messages = config.validate_config()
        if messages:
            for msg in messages:
                print(f"  {msg}")
        else:
            print("  ✓ No issues found")
        
    except Exception as e:
        print(f"✗ Error: {e}")
