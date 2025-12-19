# Project Structure for ~/dev/grmodular

## Directory Structure

```
grmodular/
├── .gitignore
├── README.md
├── requirements.txt
├── setup_instructions.md
│
├── Home.py                          # Main Streamlit entry point (optional for now)
│
├── pages/                           # Streamlit pages for each assignment type
│   ├── 1_📝_Module_Assignments.py   # Future: Module assignments
│   ├── 2_💬_Discussions.py          # Future: Discussions
│   ├── 3_📄_Essays.py               # Future: Essays
│   └── 4_📋_Exams.py                # Exam grading (our new app)
│
├── assignment_handlers/             # Assignment-specific grading logic
│   ├── __init__.py
│   ├── base_handler.py              # BaseAssignmentHandler
│   └── exam_handler.py              # ExamHandler (our new handler)
│
├── shared/                          # Shared utilities and infrastructure
│   ├── __init__.py
│   ├── canvas_api.py                # Canvas API wrapper
│   ├── canvas_submissions.py        # Submission download
│   ├── canvas_rubric_api.py         # Rubric handling
│   ├── credentials.py               # Credential management
│   ├── embeddings.py                # Course embeddings
│   ├── llm_provider.py              # LLM abstraction layer
│   ├── client.py                    # Client factory
│   ├── grade_uploader.py            # Grade upload to Canvas
│   └── export_utils.py              # XLSX export utilities
│
├── config/                          # Configuration files
│   ├── courses.json                 # Course definitions
│   └── rubrics/                     # Rubric configurations
│       └── .gitkeep
│
├── data/                            # Data directory (gitignored)
│   ├── embeddings/                  # Course embeddings
│   ├── exports/                     # Exported grade files
│   └── logs/                        # Application logs
│
└── tests/                           # Unit tests (future)
    ├── __init__.py
    └── test_exam_handler.py
```

## Files to Copy from Existing Project

### Core Assignment Handling
- `/mnt/project/assignment_base.py` → `assignment_handlers/base_handler.py`
- `/home/claude/exam_handler.py` → `assignment_handlers/exam_handler.py`

### Canvas Integration
- `/mnt/project/canvas_rubric_api.py` → `shared/canvas_rubric_api.py`
- `/mnt/project/canvas_submissions.py` → `shared/canvas_submissions.py`
- `/mnt/project/grade_uploader.py` → `shared/grade_uploader.py`

### LLM and Embeddings
- `/mnt/project/llm_provider.py` → `shared/llm_provider.py`
- `/mnt/project/client.py` → `shared/client.py`
- `/mnt/project/claude_client.py` → `shared/claude_client.py` (if used)
- `/mnt/project/course_document_processor.py` → `shared/embeddings.py`
- `/mnt/project/local_embeddings.py` → `shared/local_embeddings.py`

### Export Utilities
- `/mnt/project/create_xlsx.py` → `shared/export_utils.py`

### Streamlit Apps
- `/home/claude/exam_grader_app.py` → `pages/4_📋_Exams.py`

### Optional (for future expansion)
- `/mnt/project/rubric_grade_ui.py` → Reference for building other pages
- `/mnt/project/rubric_assignment_handler.py` → For rubric-based grading

## Files NOT to Copy (Project-Specific)
- Migration scripts
- Test scripts with hardcoded paths
- Batch grading scripts (until refactored)
- Old/deprecated files
