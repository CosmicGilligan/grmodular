# Complete Setup Checklist for ~/dev/grmodular

## 📋 Pre-Setup Checklist

- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] Canvas LMS access with API permissions
- [ ] At least one API key (Anthropic or OpenAI)
- [ ] Downloaded all files from this package

## 🗂️ File Organization

### Files Included in This Package

**Core Application Files:**
- `exam_handler.py` - Exam grading logic (→ `assignment_handlers/`)
- `exam_grader_app.py` - Streamlit UI (→ `pages/4_📋_Exams.py`)
- `credentials.py` - Credential management (→ `shared/`)

**Configuration Files:**
- `requirements.txt` - Python dependencies (→ root)
- `courses.json` - Course configuration template (→ `config/`)
- `gitignore` - Git ignore patterns (rename to `.gitignore` → root)

**Documentation:**
- `README.md` - Main project README (→ root)
- `SETUP_INSTRUCTIONS.md` - Detailed setup guide (→ `docs/`)
- `PROJECT_STRUCTURE.md` - Architecture overview (→ `docs/`)
- `EXAM_GRADER_README.md` - Exam grader documentation (→ `docs/`)
- `INTEGRATION_GUIDE.md` - Integration instructions (→ `docs/`)
- `QUICK_SETUP.md` - Quick reference (→ `docs/`)

## 📁 Step 1: Create Directory Structure

```bash
# Create main project directory
mkdir -p ~/dev/grmodular
cd ~/dev/grmodular

# Create subdirectories
mkdir -p pages
mkdir -p assignment_handlers
mkdir -p shared
mkdir -p config/rubrics
mkdir -p data/{embeddings,exports,logs}
mkdir -p tests
mkdir -p docs

# Create Python package markers
touch assignment_handlers/__init__.py
touch shared/__init__.py
touch tests/__init__.py

# Create .gitkeep files for empty directories
touch data/embeddings/.gitkeep
touch data/exports/.gitkeep
touch data/logs/.gitkeep
touch config/rubrics/.gitkeep
```

**Verify:**
```bash
tree -L 2 ~/dev/grmodular
# Should show the structure above
```

- [ ] Directory structure created
- [ ] __init__.py files created
- [ ] .gitkeep files created

## 📄 Step 2: Copy Downloaded Files

```bash
# From your downloads location
DOWNLOADS=~/Downloads  # Adjust if needed
DEST=~/dev/grmodular

# Copy to appropriate locations
cp $DOWNLOADS/exam_handler.py $DEST/assignment_handlers/
cp $DOWNLOADS/exam_grader_app.py $DEST/pages/4_📋_Exams.py
cp $DOWNLOADS/credentials.py $DEST/shared/

cp $DOWNLOADS/requirements.txt $DEST/
cp $DOWNLOADS/courses.json $DEST/config/
cp $DOWNLOADS/gitignore $DEST/.gitignore  # Note: rename!

cp $DOWNLOADS/README.md $DEST/
cp $DOWNLOADS/*.md $DEST/docs/  # All other .md files
```

**Verify:**
```bash
ls ~/dev/grmodular/assignment_handlers/exam_handler.py
ls ~/dev/grmodular/pages/4_📋_Exams.py
ls ~/dev/grmodular/shared/credentials.py
ls ~/dev/grmodular/requirements.txt
ls ~/dev/grmodular/.gitignore
```

- [ ] All files copied to correct locations
- [ ] gitignore renamed to .gitignore
- [ ] Exam app renamed to 4_📋_Exams.py

## 📦 Step 3: Copy Existing Infrastructure

From your current working project at `/mnt/project`:

```bash
SOURCE=/mnt/project
DEST=~/dev/grmodular

# Assignment base class
cp $SOURCE/assignment_base.py $DEST/assignment_handlers/base_handler.py

# Canvas API integration
cp $SOURCE/canvas_rubric_api.py $DEST/shared/
cp $SOURCE/canvas_submissions.py $DEST/shared/
cp $SOURCE/grade_uploader.py $DEST/shared/

# LLM providers
cp $SOURCE/llm_provider.py $DEST/shared/
cp $SOURCE/client.py $DEST/shared/

# Embeddings
cp $SOURCE/course_document_processor.py $DEST/shared/embeddings.py
cp $SOURCE/local_embeddings.py $DEST/shared/

# Export utilities
cp $SOURCE/create_xlsx.py $DEST/shared/export_utils.py
```

**Verify:**
```bash
ls ~/dev/grmodular/shared/
# Should show: canvas_*.py, embeddings.py, local_embeddings.py, 
#              llm_provider.py, client.py, export_utils.py, credentials.py
```

- [ ] Base handler copied
- [ ] Canvas API files copied
- [ ] LLM provider files copied
- [ ] Embeddings files copied
- [ ] Export utilities copied

## 🔧 Step 4: Update Import Paths

### In `assignment_handlers/exam_handler.py`

**Find:**
```python
from assignment_base import BaseAssignmentHandler
```

**Replace with:**
```python
from assignment_handlers.base_handler import BaseAssignmentHandler
```

### In `pages/4_📋_Exams.py`

**Find and remove:**
```python
import sys
sys.path.insert(0, '/home/claude')
```

**Find:**
```python
from exam_handler import ExamHandler
from canvas_rubric_api import CanvasRubricAPI
from course_document_processor import CourseDocumentProcessor
from canvas_submissions import download_submissions_flat
from create_xlsx import create_xlsx
from client import get_client
from llm_provider import make_llm
from grade_uploader import upload_all_from_entrylist
```

**Replace with:**
```python
from assignment_handlers.exam_handler import ExamHandler
from shared.canvas_rubric_api import CanvasRubricAPI
from shared.embeddings import CourseDocumentProcessor
from shared.canvas_submissions import download_submissions_flat
from shared.export_utils import create_xlsx
from shared.client import get_client
from shared.llm_provider import make_llm
from shared.grade_uploader import upload_all_from_entrylist
```

**Also update credentials loading:**
```python
# Find:
def load_canvas_credentials_local() -> Tuple[str, str]:
    key_path = Path.home() / "canvas-secrets.key"
    # ... rest of function

# Replace with:
from shared.credentials import load_canvas_credentials

# And change:
st.session_state.canvas_url, st.session_state.canvas_token = load_canvas_credentials_local()

# To:
st.session_state.canvas_url, st.session_state.canvas_token = load_canvas_credentials()
```

- [ ] Imports updated in exam_handler.py
- [ ] Imports updated in 4_📋_Exams.py
- [ ] Credentials import updated

## 🐍 Step 5: Python Environment

```bash
cd ~/dev/grmodular

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import streamlit, anthropic, pandas; print('✓ All packages installed')"
```

- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Test import successful

## 🔑 Step 6: Configure Credentials

```bash
# Create credentials file
touch ~/canvas-secrets.key
chmod 600 ~/canvas-secrets.key  # Secure permissions
```

Edit `~/canvas-secrets.key` with your credentials (one per line):
```
https://your-canvas-instance.instructure.com/api/v1
YOUR_CANVAS_API_TOKEN
YOUR_ANTHROPIC_API_KEY
YOUR_OPENAI_API_KEY
```

**Test credentials:**
```bash
cd ~/dev/grmodular
source venv/bin/activate
python shared/credentials.py
# Should show: ✓ Available for each credential you provided
```

- [ ] Credentials file created
- [ ] Permissions secured (chmod 600)
- [ ] Canvas URL added
- [ ] Canvas token added
- [ ] At least one LLM key added
- [ ] Credentials test successful

## ⚙️ Step 7: Configure Courses

Edit `config/courses.json` with YOUR actual course information:

```json
{
  "courses": {
    "YOUR COURSE NAME": {
      "canvas_id": YOUR_CANVAS_COURSE_ID,
      "base_course_number": YOUR_BASE_NUMBER,
      "embeddings_path": "PATH_TO_EMBEDDINGS",
      "description": "Course description",
      "enabled": true
    }
  }
}
```

**To find Canvas Course ID:**
1. Go to your course in Canvas
2. Look at URL: `https://.../courses/[THIS_NUMBER]`
3. Use that number as `canvas_id`

- [ ] courses.json updated with your courses
- [ ] Canvas IDs verified
- [ ] Embeddings paths set

## 📚 Step 8: Set Up Course Embeddings

**Option A: Copy existing embeddings**
```bash
# If you have existing embeddings
cp -r /path/to/existing/embeddings/* ~/dev/grmodular/data/embeddings/
```

**Option B: Generate new embeddings**
```bash
cd ~/dev/grmodular
source venv/bin/activate
python
```

```python
from shared.embeddings import CourseDocumentProcessor

processor = CourseDocumentProcessor()
processor.process_course(109)  # Your course number
```

- [ ] Embeddings available for your courses
- [ ] Embeddings path matches courses.json

## 🔄 Step 9: Initialize Git Repository

```bash
cd ~/dev/grmodular

# Initialize git
git init

# Add all files
git add .

# Check what will be committed (verify no secrets!)
git status
# Should NOT see: canvas-secrets.key, *.key, config.ini

# Initial commit
git commit -m "Initial commit: Modular grading system with exam support"
```

**Create GitHub repository:**
1. Go to https://github.com/new
2. Name: `grmodular` (or your choice)
3. Don't initialize with README (we have one)
4. Create repository

**Connect and push:**
```bash
git remote add origin https://github.com/YOUR_USERNAME/grmodular.git
git branch -M main
git push -u origin main
```

- [ ] Git initialized
- [ ] .gitignore working (no secrets shown in git status)
- [ ] Initial commit created
- [ ] GitHub repository created
- [ ] Code pushed to GitHub

## ✅ Step 10: Test Installation

```bash
cd ~/dev/grmodular
source venv/bin/activate

# Test imports
python -c "from assignment_handlers.exam_handler import ExamHandler; print('✓ Exam handler imports')"
python -c "from shared.credentials import load_canvas_credentials; print('✓ Credentials module imports')"
python -c "from shared.embeddings import CourseDocumentProcessor; print('✓ Embeddings module imports')"

# Run the app
streamlit run pages/4_📋_Exams.py
```

**In the app, test:**
1. App loads without errors
2. Can select a course
3. Credentials are loaded
4. Can connect to Canvas (try loading an exam)

- [ ] All import tests pass
- [ ] App starts successfully
- [ ] Can select course
- [ ] Canvas connection works

## 🚀 Step 11: Test Grading (Critical!)

**Use a TEST exam first!**

1. Create a test exam in Canvas with 1-2 fake submissions
2. In the app:
   - Select course
   - Enter test exam ID
   - Download submissions
   - Grade them
   - Review output carefully
3. **DO NOT upload to Canvas yet**
4. Export to Excel and review

**Questions to verify:**
- Does the grading make sense?
- Is the scoring appropriate?
- Is the feedback helpful?
- Are the first 5 answers being graded?
- Are questions 6-10 getting 0 points?

- [ ] Test exam created in Canvas
- [ ] Test submissions graded
- [ ] Output reviewed and looks good
- [ ] Exported to Excel successfully

## 📊 Step 12: Production Use (When Ready)

After thorough testing:

1. Start with a small batch (5-10 real submissions)
2. Review graded output manually
3. Adjust settings if needed
4. Export and double-check
5. Upload to Canvas
6. Verify in Canvas that grades uploaded correctly
7. Scale up to full batches

- [ ] Small batch tested with real data
- [ ] Output manually verified
- [ ] Grades uploaded successfully to Canvas
- [ ] Verified in Canvas
- [ ] Ready for full production use

## 🎯 Common Issues & Solutions

### ImportError: No module named 'shared'
```bash
# Make sure you're in the right directory
cd ~/dev/grmodular
# Make sure __init__.py exists
touch shared/__init__.py
```

### Canvas API 401 Unauthorized
```bash
# Check your token
cat ~/canvas-secrets.key
# Generate new token if expired
```

### No embeddings found
```bash
# Generate embeddings
python -c "from shared.embeddings import CourseDocumentProcessor; CourseDocumentProcessor().process_course(109)"
```

### Git shows canvas-secrets.key
```bash
# Remove from git
git rm --cached ~/canvas-secrets.key
# Verify .gitignore has *.key
```

## 📝 Final Verification

Run this verification script:

```bash
cd ~/dev/grmodular
echo "Checking project setup..."
echo ""
echo "Directory structure:"
[ -d pages ] && echo "✓ pages/" || echo "✗ pages/"
[ -d assignment_handlers ] && echo "✓ assignment_handlers/" || echo "✗ assignment_handlers/"
[ -d shared ] && echo "✓ shared/" || echo "✗ shared/"
[ -d config ] && echo "✓ config/" || echo "✗ config/"
[ -d data ] && echo "✓ data/" || echo "✗ data/"
echo ""
echo "Key files:"
[ -f pages/4_📋_Exams.py ] && echo "✓ Exam grader app" || echo "✗ Exam grader app"
[ -f assignment_handlers/exam_handler.py ] && echo "✓ Exam handler" || echo "✗ Exam handler"
[ -f shared/credentials.py ] && echo "✓ Credentials module" || echo "✗ Credentials module"
[ -f requirements.txt ] && echo "✓ requirements.txt" || echo "✗ requirements.txt"
[ -f .gitignore ] && echo "✓ .gitignore" || echo "✗ .gitignore"
echo ""
echo "Virtual environment:"
[ -d venv ] && echo "✓ venv exists" || echo "✗ venv missing"
echo ""
echo "Security:"
[ -f ~/canvas-secrets.key ] && echo "✓ Credentials file exists" || echo "✗ Credentials file missing"
git check-ignore ~/canvas-secrets.key && echo "✓ Secrets ignored by git" || echo "⚠ WARNING: Secrets NOT ignored!"
```

## 🎉 Setup Complete!

If all checks pass, you're ready to use the exam grader!

**Next Steps:**
1. Read `docs/EXAM_GRADER_README.md` for usage instructions
2. Test with a small batch of real exams
3. Create additional assignment type handlers as needed
4. Build out the full multi-page app

**Getting Help:**
- Check documentation in `docs/`
- Review error messages carefully
- Test each component individually
- Consult INTEGRATION_GUIDE.md

---

**Estimated Setup Time:** 30-45 minutes
**Difficulty:** Moderate (requires familiarity with Python, git, and command line)
