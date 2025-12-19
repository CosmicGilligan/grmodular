# Integration Guide: Adding Exam Handler to Existing Project

This guide shows how to integrate the new exam grading system with your existing grading infrastructure.

## Quick Start (Recommended)

### 1. Copy Files to Project

```bash
# Assuming you're in the directory where files were created
cp exam_handler.py /mnt/project/
cp exam_grader_app.py /mnt/project/
```

### 2. Test the Standalone App

```bash
cd /mnt/project
streamlit run exam_grader_app.py
```

### 3. Verify Functionality

Test with a real exam:
1. Select a course
2. Enter an exam assignment ID
3. Download submissions
4. Grade 1-2 submissions as a test
5. Review the output
6. Export to XLSX
7. DO NOT upload to Canvas yet (wait until you're confident)

## Integration Points

### 1. Import Path Updates

The exam handler needs to import from your existing modules:

```python
# exam_handler.py currently imports:
from assignment_base import BaseAssignmentHandler
import grade_all

# Make sure these files are accessible:
# - /mnt/project/assignment_base.py ✓
# - /mnt/project/grade_all.py ✓
```

### 2. Course Embeddings Integration

The exam grader uses `CourseDocumentProcessor`:

```python
# In exam_grader_app.py:
from course_document_processor import CourseDocumentProcessor

# When grading:
processor = CourseDocumentProcessor()
course_embeddings = processor.load_course_embeddings(base_course)
```

**Verify embeddings exist:**
```bash
ls -la ../db/embeddings/
# Should show files like: course_109_embeddings.pkl
```

### 3. LLM Provider Integration

Uses your existing `llm_provider.py`:

```python
from client import get_client
from llm_provider import make_llm

# Create LLM client
llm_client = make_llm(provider="anthropic", model="claude-3-5-sonnet-20241022")
```

### 4. Canvas API Integration

Uses existing Canvas functions:

```python
# From canvas_rubric_api.py
from canvas_rubric_api import CanvasRubricAPI

# From canvas_submissions.py
from canvas_submissions import download_submissions_flat

# From grade_uploader.py
from grade_uploader import upload_all_from_entrylist
```

## Required Modifications

### Update exam_grader_app.py Imports

Change the exam handler import based on where you place the file:

```python
# If exam_handler.py is in /mnt/project/ (same directory):
from exam_handler import ExamHandler

# If you move it to assignment_handlers/:
from assignment_handlers.exam_handler import ExamHandler
```

### Update sys.path if needed

Currently the app has:
```python
import sys
sys.path.insert(0, '/home/claude')
from exam_handler import ExamHandler
```

Change to:
```python
# Remove sys.path manipulation
from exam_handler import ExamHandler  # If in same directory
```

### Configure Course Mappings

Update the `COURSES` dictionary in `exam_grader_app.py` with your actual Canvas course IDs:

```python
COURSES = {
    "BUS 109": (YOUR_CANVAS_COURSE_ID, 109),
    "BUS 110": (YOUR_CANVAS_COURSE_ID, 110),
    # etc.
}
```

To find your Canvas course IDs:
1. Go to Canvas course
2. Look at URL: `.../courses/[ID]`
3. Use that ID in the tuple

## Testing Checklist

Before using with real grades:

- [ ] App starts without errors
- [ ] Can select a course
- [ ] Can load exam from Canvas
- [ ] Can download submissions
- [ ] Can see submission previews
- [ ] LLM provider connects successfully
- [ ] Course embeddings load correctly
- [ ] Grading produces reasonable results
- [ ] Can export to XLSX
- [ ] XLSX file contains expected data
- [ ] Can review grades in Excel/LibreOffice
- [ ] **Manual verification**: Check 3-5 graded exams thoroughly
- [ ] Upload to Canvas works (test with 1-2 submissions first)

## Validation

### 1. Check Exam Configuration

When you load an exam, watch for validation warnings:

```
Warning: Total points (60) doesn't match 5 × 10 = 50
```

This means the Canvas assignment has 60 points but the exam expects 50. You can either:
- Change Canvas assignment to 50 points
- Update `default_points` in ExamHandler initialization

### 2. Verify Question Parsing

Test the question parser with sample text:

```python
from exam_handler import ExamHandler

handler = ExamHandler(
    assignment_key="test",
    display_name="Test",
    default_points=50,
    course_mapping={109: 109}
)

sample_text = """
Question 1:
This is my answer to question 1.

Question 3:
This is my answer to question 3.

Question 5:
This is my answer to question 5.

Question 7:
This is my answer to question 7.

Question 9:
This is my answer to question 9.
"""

questions, numbers = handler.parse_exam_submission(sample_text)
print(f"Found {len(questions)} questions: {numbers}")
# Should print: Found 5 questions: [1, 3, 5, 7, 9]
```

### 3. Test Grading Logic

Grade a single answer manually:

```python
from llm_provider import make_llm
from course_document_processor import CourseDocumentProcessor

llm = make_llm("anthropic", "claude-3-5-sonnet-20241022")
processor = CourseDocumentProcessor()
embeddings = processor.load_course_embeddings(109)

answer = "Your test answer here..."
score, feedback = handler._grade_single_answer(answer, 1, llm, embeddings)

print(f"Score: {score}/10")
print(f"Feedback: {feedback}")
```

## Common Issues and Solutions

### Issue: Import Errors

```
ModuleNotFoundError: No module named 'exam_handler'
```

**Solution**: Make sure `exam_handler.py` is in the Python path:
```python
import sys
sys.path.insert(0, '/mnt/project')
from exam_handler import ExamHandler
```

### Issue: No Embeddings Found

```
Error loading embeddings: File not found
```

**Solution**: Generate embeddings for your course:
```python
from course_document_processor import CourseDocumentProcessor
processor = CourseDocumentProcessor()
processor.process_course(109)
```

### Issue: Canvas API Rate Limiting

```
HTTP 403: Rate limit exceeded
```

**Solution**: Add delays between requests:
```python
import time
for entry in entryList:
    # Grade entry
    time.sleep(0.5)  # Wait 0.5 seconds between grades
```

### Issue: Inconsistent Grading

```
Same answer gets different scores on different runs
```

**Solution**: Lower the temperature in `_grade_single_answer`:
```python
response = llm_client.generate(
    prompt=grading_prompt,
    max_tokens=500,
    temperature=0.1  # Lower = more consistent
)
```

## Future Enhancements

Once the exam grader is working well, consider:

1. **Add question bank integration** - Store actual exam questions
2. **Implement answer key matching** - Compare to model answers
3. **Add partial credit logic** - More granular scoring
4. **Support different exam formats** - 7 of 15, 3 of 5, etc.
5. **Batch processing optimizations** - Parallel grading
6. **Grading rubric templates** - Standardized feedback
7. **Student appeal workflow** - Re-grade functionality
8. **Analytics dashboard** - Grade distribution, question difficulty

## Migration to Multi-Page App

When ready to integrate into the full multi-page structure:

### Step 1: Create Directory Structure
```bash
mkdir -p pages assignment_handlers shared config
```

### Step 2: Move Files
```bash
mv exam_handler.py assignment_handlers/
mv exam_grader_app.py pages/4_📋_Exams.py
```

### Step 3: Update Imports
In `pages/4_📋_Exams.py`:
```python
from assignment_handlers.exam_handler import ExamHandler
```

### Step 4: Create Home Page
See the architecture document for creating `Home.py`

## Support

If you encounter issues:

1. Check the Streamlit terminal output for errors
2. Review the application logs
3. Verify all dependencies are installed
4. Test each component individually
5. Consult the main README

---

**Ready to begin?** Start with copying the files to `/mnt/project` and running the standalone app!
