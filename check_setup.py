#!/usr/bin/env python3
"""
Quick diagnostic script to check grmodular project setup
Run this to see what's missing
"""

import os
import sys
from pathlib import Path

def check_file(filepath, description):
    """Check if a file exists and report"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"  ✓ {description}: {filepath} ({size} bytes)")
        return True
    else:
        print(f"  ❌ {description}: {filepath} NOT FOUND")
        return False

def check_directory(dirpath, description):
    """Check if a directory exists"""
    if os.path.isdir(dirpath):
        count = len(os.listdir(dirpath))
        print(f"  ✓ {description}: {dirpath} ({count} items)")
        return True
    else:
        print(f"  ❌ {description}: {dirpath} NOT FOUND")
        return False

def main():
    print("=" * 70)
    print("Grading System Setup Diagnostic")
    print("=" * 70)
    print()
    
    # Check current directory
    cwd = os.getcwd()
    print(f"Current Directory: {cwd}")
    
    if not cwd.endswith('grmodular'):
        print("⚠️  WARNING: You should be in the grmodular directory")
        print("   Run: cd ~/dev/grmodular")
    print()
    
    # Check directory structure
    print("Directory Structure:")
    print("-" * 70)
    check_directory("assignment_handlers", "Assignment handlers")
    check_directory("shared", "Shared modules")
    check_directory("pages", "Streamlit pages")
    check_directory("config", "Configuration")
    check_directory("data", "Data directory")
    print()
    
    # Check key files
    print("Required Files:")
    print("-" * 70)
    
    # __init__.py files
    check_file("assignment_handlers/__init__.py", "__init__.py (assignment_handlers)")
    check_file("shared/__init__.py", "__init__.py (shared)")
    
    # Assignment handlers
    check_file("assignment_handlers/exam_handler.py", "Exam handler")
    check_file("assignment_handlers/base_handler.py", "Base handler")
    
    # Shared modules
    check_file("shared/config_loader.py", "Config loader")
    check_file("shared/embeddings_manager.py", "Embeddings manager")
    check_file("shared/credentials.py", "Credentials")
    check_file("shared/embeddings.py", "Embeddings (CourseDocumentProcessor)")
    check_file("shared/canvas_rubric_api.py", "Canvas rubric API")
    check_file("shared/canvas_submissions.py", "Canvas submissions")
    check_file("shared/llm_provider.py", "LLM provider")
    check_file("shared/client.py", "Client")
    check_file("shared/export_utils.py", "Export utils")
    
    # Pages
    check_file("pages/4_📋_Exams.py", "Exam grader page")
    
    # Config
    check_file("config/courses.json", "Courses configuration")
    
    # Root files
    check_file("requirements.txt", "Requirements")
    check_file(".gitignore", "Gitignore")
    
    print()
    
    # Check Python imports
    print("Python Import Test:")
    print("-" * 70)
    
    errors = []
    
    try:
        import assignment_handlers
        print("  ✓ assignment_handlers package")
    except ImportError as e:
        print(f"  ❌ assignment_handlers package: {e}")
        errors.append("assignment_handlers package")
    
    try:
        from assignment_handlers import exam_handler
        print("  ✓ exam_handler module")
    except ImportError as e:
        print(f"  ❌ exam_handler module: {e}")
        errors.append("exam_handler module")
    
    try:
        from assignment_handlers.exam_handler import ExamHandler
        print("  ✓ ExamHandler class")
    except ImportError as e:
        print(f"  ❌ ExamHandler class: {e}")
        errors.append("ExamHandler class")
    
    try:
        from shared.config_loader import get_config
        print("  ✓ config_loader module")
    except ImportError as e:
        print(f"  ❌ config_loader module: {e}")
        errors.append("config_loader module")
    
    try:
        from shared.embeddings_manager import EmbeddingsManager
        print("  ✓ embeddings_manager module")
    except ImportError as e:
        print(f"  ❌ embeddings_manager module: {e}")
        errors.append("embeddings_manager module")
    
    try:
        from shared.credentials import load_canvas_credentials
        print("  ✓ credentials module")
    except ImportError as e:
        print(f"  ❌ credentials module: {e}")
        errors.append("credentials module")
    
    print()
    
    # Check credentials file
    print("Credentials:")
    print("-" * 70)
    cred_file = Path.home() / "canvas-secrets.key"
    if cred_file.exists():
        print(f"  ✓ Canvas credentials: {cred_file}")
    else:
        print(f"  ❌ Canvas credentials NOT FOUND: {cred_file}")
        print("     Create this file with:")
        print("     Line 1: Canvas API URL")
        print("     Line 2: Canvas API token")
        print("     Line 3: Anthropic API key")
        print("     Line 4: OpenAI API key")
    print()
    
    # Summary
    print("=" * 70)
    if errors:
        print(f"❌ SETUP INCOMPLETE - {len(errors)} issues found")
        print()
        print("Missing/Broken:")
        for error in errors:
            print(f"  - {error}")
        print()
        print("Fix by running the setup commands in IMPORT_ERROR_FIX.md")
    else:
        print("✓ SETUP LOOKS GOOD!")
        print()
        print("You should be able to run:")
        print("  streamlit run pages/4_📋_Exams.py")
    print("=" * 70)

if __name__ == "__main__":
    main()