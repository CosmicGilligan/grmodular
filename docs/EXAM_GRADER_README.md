# Exam Grading System - Standalone App

A specialized Streamlit application for grading exams where students answer 5 out of 10 questions.

## Overview

This application handles a specific exam format:
- **10 questions** available to students
- Students **must answer 5 questions** (their choice)
- **Only the first 5 submitted answers** are graded (10 points each)
- Answers beyond the first 5 automatically receive 0 points
- **Maximum score: 50 points** (5 questions × 10 points)
- Grading uses **course embeddings** and **LLM evaluation**

## Files Created

1. **`exam_handler.py`** - Core exam grading logic
   - Parses exam submissions to identify answered questions
   - Grades first 5 answers using LLM and course embeddings
   - Enforces the "first 5 only" policy
   - Formats results for Canvas upload

2. **`exam_grader_app.py`** - Streamlit user interface
   - Step-by-step workflow for grading exams
   - Course selection and Canvas integration
   - LLM provider selection (Anthropic/OpenAI)
   - Grade review and export to XLSX
   - Direct upload to Canvas

## Setup Instructions

### 1. Prerequisites

The exam grader uses your existing infrastructure:
- Canvas API credentials (in `~/canvas-secrets.key`)
- Course embeddings (from `course_document_processor.py`)
- LLM provider setup (Anthropic or OpenAI)

### 2. File Placement

**Option A: Standalone (recommended for testing)**
```bash
# Place in your project directory
cp exam_handler.py /path/to/your/project/
cp exam_grader_app.py /path/to/your/project/
```

**Option B: Integrated (for production)**
```bash
# Move to proper locations
mv exam_handler.py /path/to/your/project/assignment_handlers/
mv exam_grader_app.py /path/to/your/project/
```

### 3. Update Imports (if using Option B)

If you move `exam_handler.py` to `assignment_handlers/`, update the import in `exam_grader_app.py`:

```python
# Change this:
from exam_handler import ExamHandler

# To this:
from assignment_handlers.exam_handler import ExamHandler
```

## Running the App

### Command Line
```bash
cd /path/to/your/project
streamlit run exam_grader_app.py
```

### The app will open in your browser at `http://localhost:8501`

## Usage Workflow

### Step 1: Select Course
- Choose from your configured courses (BUS 109, BUS 110, etc.)
- The course determines which embeddings are used for grading

### Step 2: Enter Exam Assignment ID
- Find the Canvas assignment ID from the URL: `.../assignments/[ID]`
- Enter the ID and click "Load Exam"
- The app will fetch the exam details and rubric from Canvas

### Step 3: Download Submissions
- Click "Download Submissions" to fetch student answers from Canvas
- Preview shows the first few submissions

### Step 4: Select LLM Provider
- Choose between Anthropic (Claude) or OpenAI (GPT)
- Select the specific model to use for grading

### Step 5: Grade Exams
- Set batch size (how many to grade at once)
- Choose whether to use rubric-based grading
- Click "Start Grading" to begin
- Progress bar shows grading status
- First few results are displayed in real-time

### Step 6: Review and Export
- View graded results in a table
- See grading statistics (average, highest, lowest)
- Export to XLSX for offline review

### Step 7: Upload to Canvas
- Review grades one final time
- Click "Upload Grades to Canvas" to submit
- Success/failure report shows which grades were uploaded

## Exam Answer Format

The exam handler expects submissions in this format:

```
Question 1:
[Student's answer to question 1...]

Question 3:
[Student's answer to question 3...]

Question 5:
[Student's answer to question 5...]

Question 7:
[Student's answer to question 7...]

Question 9:
[Student's answer to question 9...]
```

**Supported question markers:**
- `Question 1:` or `Question 1.`
- `Q1:` or `Q 1:`
- `1.` (at start of line)

## Grading Logic

### How Answers are Graded

For each of the first 5 answers:

1. **Context Retrieval**: The system searches course embeddings to find the 5 most relevant document chunks
2. **LLM Evaluation**: The answer is sent to the LLM along with relevant course content
3. **Scoring**: The LLM assigns 0-10 points based on:
   - **Accuracy**: Correct use of course concepts
   - **Completeness**: Coverage of key points
   - **Understanding**: Demonstration of comprehension
   - **Clarity**: Organization and expression
4. **Feedback**: Specific, constructive comments are generated

### Grading Policy Enforcement

- ✅ **Questions 1-5** (first 5 submitted): Graded normally (0-10 points each)
- ❌ **Questions 6-10**: Automatically receive 0 points with note "Not graded (only first 5 answers are graded)"

## Customization

### Adjust Course List

Edit `COURSES` dictionary in `exam_grader_app.py`:

```python
COURSES = {
    "BUS 109": (2149, 109),  # (Canvas Course ID, Base Course Number)
    "BUS 110": (2150, 110),
    "BUS 111": (2151, 111),
    "ECON 201": (3001, 201),  # Add your courses here
}
```

### Modify Exam Structure

Edit `ExamHandler` initialization in `exam_handler.py`:

```python
# Current settings
self.total_questions = 10
self.questions_to_grade = 5
self.points_per_question = 10
```

### Change Grading Prompt

Modify the `_grade_single_answer()` method in `exam_handler.py` to adjust how questions are evaluated.

## Troubleshooting

### "No course embeddings found"
**Solution**: Make sure embeddings have been generated for your course:
```python
from course_document_processor import CourseDocumentProcessor
processor = CourseDocumentProcessor()
processor.process_course(109)  # Replace with your course number
```

### "Canvas API error"
**Solution**: Check your `~/canvas-secrets.key` file:
```
https://your-canvas-instance.instructure.com/api/v1
your_access_token_here
your_anthropic_or_openai_key_here
```

### "Exam parsing failed"
**Solution**: Verify student submissions follow the expected format. You may need to adjust the regex patterns in `parse_exam_submission()`.

### Grades don't match expected values
**Solution**: Check the exam configuration validation warnings. Ensure:
- Total points = questions_to_grade × points_per_question
- Canvas assignment has correct point value

## Integration with Full Multi-Page App

Once you've tested the exam grader and it's working well, you can integrate it into the full multi-page structure:

1. Move `exam_grader_app.py` to `pages/4_📋_Exams.py`
2. Move `exam_handler.py` to `assignment_handlers/exam_handler.py`
3. Register the handler in `assignment_factory.py`:

```python
from assignment_handlers.exam_handler import ExamHandler

class AssignmentHandlerFactory:
    _handler_registry = {
        'assignment': ModuleAssignmentHandler,
        'discussion': DiscussionHandler,
        'review': ReviewHandler,
        'exam': ExamHandler,  # Add this line
    }
```

## Next Steps

After successfully grading exams:

1. **Test thoroughly** with a small batch of real submissions
2. **Verify** Canvas upload works correctly
3. **Document** any course-specific customizations needed
4. **Expand** to create the essay grading module
5. **Integrate** into the full multi-page app structure

## Support

For issues or questions:
- Check the validation warnings in the app
- Review log output in the terminal running Streamlit
- Verify your Canvas credentials and API access
- Ensure course embeddings are up to date

---

**Note**: This is a standalone app that can be run independently or integrated into a larger multi-page Streamlit application structure.
