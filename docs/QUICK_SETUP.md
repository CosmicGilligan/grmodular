# Quick Setup - File Checklist

## Essential Files to Copy

### From /home/claude (newly created exam grader)
```bash
SOURCE=/home/claude
DEST=~/dev/grmodular

# Core exam files
cp $SOURCE/exam_handler.py $DEST/assignment_handlers/
cp $SOURCE/exam_grader_app.py $DEST/pages/4_📋_Exams.py

# Documentation
cp $SOURCE/EXAM_GRADER_README.md $DEST/docs/
cp $SOURCE/INTEGRATION_GUIDE.md $DEST/docs/

# Configuration
cp $SOURCE/requirements.txt $DEST/
cp $SOURCE/.gitignore $DEST/
cp $SOURCE/README.md $DEST/
cp $SOURCE/PROJECT_STRUCTURE.md $DEST/docs/
cp $SOURCE/SETUP_INSTRUCTIONS.md $DEST/docs/
cp $SOURCE/courses.json $DEST/config/
```

### From /mnt/project (existing infrastructure)
```bash
SOURCE=/mnt/project
DEST=~/dev/grmodular

# Assignment base
cp $SOURCE/assignment_base.py $DEST/assignment_handlers/base_handler.py

# Canvas integration
cp $SOURCE/canvas_rubric_api.py $DEST/shared/
cp $SOURCE/canvas_submissions.py $DEST/shared/
cp $SOURCE/grade_uploader.py $DEST/shared/

# LLM providers
cp $SOURCE/llm_provider.py $DEST/shared/
cp $SOURCE/client.py $DEST/shared/
cp $SOURCE/claude_client.py $DEST/shared/  # if you use it

# Embeddings and document processing
cp $SOURCE/course_document_processor.py $DEST/shared/embeddings.py
cp $SOURCE/local_embeddings.py $DEST/shared/

# Export utilities
cp $SOURCE/create_xlsx.py $DEST/shared/export_utils.py
```

## Create Empty Structure Files

```bash
cd ~/dev/grmodular

# Python package markers
touch assignment_handlers/__init__.py
touch shared/__init__.py
touch tests/__init__.py

# Keep empty directories in git
touch data/embeddings/.gitkeep
touch data/exports/.gitkeep
touch data/logs/.gitkeep
touch config/rubrics/.gitkeep
```

## Import Path Updates Required

After copying files, these imports need updating:

### In assignment_handlers/exam_handler.py
- Change: `from assignment_base import` 
- To: `from assignment_handlers.base_handler import`

### In pages/4_📋_Exams.py
- Change: `from exam_handler import`
- To: `from assignment_handlers.exam_handler import`
- Change: `from canvas_rubric_api import`
- To: `from shared.canvas_rubric_api import`
- Change: `from course_document_processor import`
- To: `from shared.embeddings import CourseDocumentProcessor`
- And so on for all shared imports...

## Quick Test Commands

```bash
# 1. Create virtual environment
cd ~/dev/grmodular
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test import structure
python -c "from assignment_handlers.exam_handler import ExamHandler; print('✓ Imports working')"

# 4. Run the app
streamlit run pages/4_📋_Exams.py
```

## Checklist

- [ ] Directory structure created
- [ ] Files copied from /home/claude
- [ ] Files copied from /mnt/project
- [ ] __init__.py files created
- [ ] .gitkeep files created
- [ ] Import paths updated in exam_handler.py
- [ ] Import paths updated in 4_📋_Exams.py
- [ ] credentials.py created in shared/
- [ ] courses.json configured with your courses
- [ ] ~/canvas-secrets.key created with credentials
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Test imports successful
- [ ] App runs without errors
- [ ] Git initialized and pushed to GitHub

## File Count Check

You should have approximately:
- **Pages**: 1 file (4_📋_Exams.py)
- **Assignment Handlers**: 2 files (base_handler.py, exam_handler.py) + __init__.py
- **Shared**: ~9 files + __init__.py
- **Config**: courses.json + .gitkeep
- **Docs**: 4-5 markdown files
- **Root**: README.md, requirements.txt, .gitignore, SETUP_INSTRUCTIONS.md

Total: ~20-25 files plus directory structure

## Common Mistakes to Avoid

❌ **Don't**: Copy grade_all.py (has hardcoded paths)
❌ **Don't**: Copy test scripts or migration scripts
❌ **Don't**: Commit canvas-secrets.key to git
❌ **Don't**: Use absolute paths like /home/claude in imports

✅ **Do**: Use relative imports (from shared.xxx import)
✅ **Do**: Verify .gitignore is working before first commit
✅ **Do**: Test with small batch before grading real exams
✅ **Do**: Keep credentials secure (chmod 600)
