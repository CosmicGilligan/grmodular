# Setup Instructions for grmodular

Complete step-by-step setup guide for the Canvas LMS Grading System.

## Prerequisites

- Python 3.9 or higher
- Git
- Canvas LMS account with API access
- Anthropic API key (for Claude) or OpenAI API key (for GPT)

## Step 1: Repository Setup

### Create the Repository

```bash
# Create the directory
mkdir -p ~/dev/grmodular
cd ~/dev/grmodular

# Initialize git
git init

# Create directory structure
mkdir -p pages assignment_handlers shared config data/{embeddings,exports,logs}
mkdir -p config/rubrics tests docs

# Create __init__.py files for Python packages
touch assignment_handlers/__init__.py
touch shared/__init__.py
touch tests/__init__.py

# Create .gitkeep files to preserve empty directories in git
touch data/embeddings/.gitkeep
touch data/exports/.gitkeep
touch data/logs/.gitkeep
touch config/rubrics/.gitkeep
```

### Copy Core Files

From your existing project, copy these files:

```bash
# Assignment handlers
cp /mnt/project/assignment_base.py assignment_handlers/base_handler.py
cp exam_handler.py assignment_handlers/

# Canvas integration
cp /mnt/project/canvas_rubric_api.py shared/
cp /mnt/project/canvas_submissions.py shared/
cp /mnt/project/grade_uploader.py shared/

# LLM and embeddings
cp /mnt/project/llm_provider.py shared/
cp /mnt/project/client.py shared/
cp /mnt/project/course_document_processor.py shared/embeddings.py
cp /mnt/project/local_embeddings.py shared/

# Export utilities
cp /mnt/project/create_xlsx.py shared/export_utils.py

# Streamlit pages
cp exam_grader_app.py pages/4_📋_Exams.py
```

### Copy Configuration Files

```bash
# From this setup
cp requirements.txt .
cp .gitignore .
cp README.md .
cp PROJECT_STRUCTURE.md docs/
cp EXAM_GRADER_README.md docs/
cp INTEGRATION_GUIDE.md docs/
```

## Step 2: Update Import Paths

After copying files, you need to update import statements to use the new modular structure.

### In `assignment_handlers/exam_handler.py`

Change:
```python
from assignment_base import BaseAssignmentHandler
import grade_all
```

To:
```python
from assignment_handlers.base_handler import BaseAssignmentHandler
```

### In `pages/4_📋_Exams.py`

Change:
```python
import sys
sys.path.insert(0, '/home/claude')
from exam_handler import ExamHandler
```

To:
```python
from assignment_handlers.exam_handler import ExamHandler
```

Also update other imports:
```python
# Change these:
from canvas_rubric_api import CanvasRubricAPI
from course_document_processor import CourseDocumentProcessor
from canvas_submissions import download_submissions_flat
from create_xlsx import create_xlsx
from client import get_client
from llm_provider import make_llm
from grade_uploader import upload_all_from_entrylist

# To these:
from shared.canvas_rubric_api import CanvasRubricAPI
from shared.embeddings import CourseDocumentProcessor
from shared.canvas_submissions import download_submissions_flat
from shared.export_utils import create_xlsx
from shared.client import get_client
from shared.llm_provider import make_llm
from shared.grade_uploader import upload_all_from_entrylist
```

## Step 3: Python Environment

### Create Virtual Environment

```bash
cd ~/dev/grmodular
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Verify Installation

```bash
python -c "import streamlit; import anthropic; import pandas; print('All packages installed successfully!')"
```

## Step 4: Configure Credentials

### Create Credentials File

```bash
# Create the credentials file
touch ~/canvas-secrets.key
chmod 600 ~/canvas-secrets.key  # Secure permissions
```

### Add Your Credentials

Edit `~/canvas-secrets.key` and add (one per line):

```
https://your-canvas-instance.instructure.com/api/v1
YOUR_CANVAS_API_TOKEN_HERE
YOUR_ANTHROPIC_API_KEY_HERE
YOUR_OPENAI_API_KEY_HERE
```

**How to get these:**

**Canvas API Token:**
1. Log into Canvas
2. Go to Account → Settings
3. Scroll to "Approved Integrations"
4. Click "+ New Access Token"
5. Enter a purpose and expiration date
6. Copy the token (you won't see it again!)

**Anthropic API Key:**
1. Sign up at https://console.anthropic.com/
2. Go to API Keys
3. Create a new key
4. Copy the key

**OpenAI API Key:**
1. Sign up at https://platform.openai.com/
2. Go to API Keys
3. Create a new key
4. Copy the key

### Update credentials.py

Create `shared/credentials.py`:

```python
"""Credential management for Canvas and LLM providers"""

from pathlib import Path
from typing import Tuple

def load_canvas_credentials() -> Tuple[str, str]:
    """Load Canvas API credentials from ~/canvas-secrets.key"""
    key_path = Path.home() / "canvas-secrets.key"
    
    if not key_path.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {key_path}\n"
            "Create ~/canvas-secrets.key with:\n"
            "Line 1: Canvas API URL\n"
            "Line 2: Canvas API token\n"
            "Line 3: Anthropic API key (optional)\n"
            "Line 4: OpenAI API key (optional)"
        )
    
    lines = [ln.strip() for ln in key_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    
    if len(lines) < 2:
        raise ValueError("canvas-secrets.key must have at least URL and token")
    
    api_url = lines[0].rstrip("/")
    if not api_url.endswith("/api/v1"):
        api_url = api_url + "/api/v1"
    
    token = lines[1]
    
    return api_url, token

def load_llm_keys() -> dict:
    """Load LLM API keys"""
    key_path = Path.home() / "canvas-secrets.key"
    lines = [ln.strip() for ln in key_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    
    keys = {
        'anthropic': lines[2] if len(lines) > 2 else None,
        'openai': lines[3] if len(lines) > 3 else None,
    }
    
    return keys
```

## Step 5: Configure Courses

### Create Course Configuration

Create `config/courses.json`:

```json
{
  "BUS 109": {
    "canvas_id": 2149,
    "base_course_number": 109,
    "embeddings_path": "../db/Transcripts/109/",
    "description": "Business Course 109"
  },
  "BUS 110": {
    "canvas_id": 2150,
    "base_course_number": 110,
    "embeddings_path": "../db/Transcripts/110/",
    "description": "Business Course 110"
  }
}
```

**Replace with your actual:**
- Canvas course IDs (find in Canvas URL: `.../courses/[ID]`)
- Course numbers
- Embeddings paths

## Step 6: Generate Course Embeddings

If you don't have embeddings yet:

```python
from shared.embeddings import CourseDocumentProcessor

processor = CourseDocumentProcessor()

# Process each course
processor.process_course(109)
processor.process_course(110)
```

This creates embedding files in `data/embeddings/`.

## Step 7: Git Setup

### Initialize Repository

```bash
# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Modular grading system with exam support"

# Create GitHub repository (on GitHub website)
# Then connect local to remote:
git remote add origin https://github.com/YOUR_USERNAME/grmodular.git
git branch -M main
git push -u origin main
```

### Verify .gitignore

Make sure sensitive files are ignored:

```bash
# These should NOT be in git status:
git status | grep -E "(secrets|.key|config.ini)"

# Should return nothing (these files are ignored)
```

## Step 8: Test the Installation

### Test Exam Grader

```bash
cd ~/dev/grmodular
source venv/bin/activate  # If not already activated

# Run the exam grader
streamlit run pages/4_📋_Exams.py
```

The app should open in your browser at `http://localhost:8501`.

### Test Workflow

1. Select a course
2. Enter a test exam ID
3. Try downloading submissions
4. Grade 1-2 test submissions
5. Review output
6. **DO NOT upload** until you've verified everything works

## Step 9: Development Setup (Optional)

### VSCode Configuration

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.tabSize": 4
  }
}
```

### Install Development Tools

```bash
pip install black flake8 pytest
```

## Step 10: Documentation

Create a `docs/` directory with:

```bash
mkdir -p docs
mv EXAM_GRADER_README.md docs/
mv INTEGRATION_GUIDE.md docs/
mv PROJECT_STRUCTURE.md docs/
```

## Verification Checklist

Before using with real grades:

- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip list`)
- [ ] Credentials file created and secured
- [ ] Course configuration updated with your courses
- [ ] Embeddings generated for your courses
- [ ] Git repository initialized
- [ ] .gitignore working (no secrets in git)
- [ ] GitHub repository created and pushed
- [ ] App starts without errors
- [ ] Can connect to Canvas API
- [ ] Can load course embeddings
- [ ] Can download test submissions
- [ ] Test grading produces reasonable results
- [ ] Export to XLSX works
- [ ] Manual review of graded output looks good

## Common Setup Issues

### ImportError: No module named 'shared'

**Solution:** Make sure you're running from the project root and `__init__.py` exists:
```bash
cd ~/dev/grmodular
touch shared/__init__.py
```

### Canvas API 401 Error

**Solution:** Check your token is valid and hasn't expired:
```bash
cat ~/canvas-secrets.key
# Verify token looks correct
```

### No embeddings found

**Solution:** Generate embeddings:
```python
from shared.embeddings import CourseDocumentProcessor
processor = CourseDocumentProcessor()
processor.process_course(109)
```

## Next Steps

1. ✅ Test exam grader thoroughly
2. 📝 Create essay grader (similar structure)
3. 💬 Create discussion grader
4. 📋 Create module assignment grader
5. 🏠 Create Home.py for multi-page navigation
6. 📊 Add analytics dashboard
7. 🧪 Write unit tests

## Support

If you encounter issues:
1. Check the verification checklist
2. Review error messages in terminal
3. Consult documentation in `docs/`
4. Check GitHub issues

---

**Setup Complete!** You're ready to start grading exams.
