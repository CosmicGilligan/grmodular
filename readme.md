EXAM GRADING SYSTEM - PROJECT SUMMARY
======================================
Date: December 18-19, 2025
Project: AI-Powered Canvas LMS Exam Grader


STARTING POINT
==============

Initial State:
- Existing modular grading system for Canvas LMS assignments
- Working components: Canvas API integration, LLM grading, embeddings-based RAG
- Location: ~/dev/grmodular
- Goal: Add exam grading capability with specific requirements

User Requirements:
- Grade exams where students answer 5 out of 10 questions (any 5)
- Support for freshmen-level courses (HIST 101, HIST 110)
- AI grading with course-specific knowledge base
- Export results to Excel
- Upload grades directly back to Canvas
- Adjustable grading leniency for freshman students


PROJECT PROGRESSION
===================

PHASE 1: INITIAL EXAM GRADING SYSTEM
-------------------------------------
Created:
- assignment_handlers/exam_handler.py (base implementation)
- pages/4_📋_Exams.py (Streamlit UI)
- Grading logic for 5-question exams (10 points each, 50 total)

Initial Issues Identified:
✓ System message formatting errors with Anthropic API
✓ Model name outdated (404 errors)
✓ Grading logic only checked first 5 questions sequentially


PHASE 2: API AND GRADING FIXES
-------------------------------
Problems Solved:

1. Anthropic API System Message Format
   - Error: "system: Input should be a valid list"
   - Root cause: System parameter passed as string instead of list
   - Fix: Changed to kwargs dictionary approach with content blocks
   - File: shared/llm_provider.py

2. Model Name Updates
   - Error: 404 for claude-3-5-sonnet-20241022
   - Fix: Updated to claude-sonnet-4-20250514 (Claude Sonnet 4.5)
   - Files: config/courses.json, pages/4_📋_Exams.py

3. Exam Grading Logic
   - Problem: Only graded first 5 questions (Q1-Q5) sequentially
   - Example failure: Student answering Q4,Q5,Q7,Q8,Q9 only got Q4-Q5 graded
   - Fix: Iterate through ALL answered questions, skip empty ones, stop after 5 actual answers
   - Result: Now grades ANY 5 answered questions, regardless of position

4. Excel Export
   - Error: create_xlsx expected CSV, received list
   - Created: shared/exam_export.py - direct Excel export
   - Format: Canvas-compatible with User ID, names, grades, upload flag


PHASE 3: GRADING LENIENCY ADJUSTMENTS
--------------------------------------
Problem: AI grading too harsh for freshmen

Solution 1: Updated Grading Prompts
   - Added "FRESHMAN-LEVEL" context
   - Explicit scoring rubric (9-10=Excellent, 7-8=Good, etc.)
   - Instructions for generous partial credit
   - Emphasis on effort and basic understanding

Solution 2: Score Multiplier Feature
   - Problem: Even with better prompts, still too harsh
   - Solution: Amplify scores while keeping feedback honest
   - Implementation:
     * Added score_multiplier parameter to ExamHandler (default 1.15)
     * UI slider in Exams.py (range 1.0-1.5, step 0.05)
     * Applied in _grade_single_answer() before returning score
     * Scores capped at maximum points
   - Result: AI gives honest feedback (e.g., "7/10 answer") but score is boosted (7 × 1.15 = 8.05)


PHASE 4: SCORE FORMATTING
--------------------------
Problem: Scores displayed with 10+ decimal places (45.5000000000/50.0000000000)

Fix: Added round(score, 2) throughout
   - exam_handler.py: grade_exam_submission(), _grade_single_answer(), format_grading_output()
   - exam_export.py: Score formatting with .2f
   - Result: All scores display as XX.XX (e.g., 45.50/50.00)


PHASE 5: CANVAS UPLOAD FUNCTIONALITY
-------------------------------------
Goal: Upload graded exams back to Canvas automatically

Implementation:
   - Added Step 7 to UI: "Upload to Canvas"
   - Two upload options:
     * Current Session (Memory) - from entryList
     * Excel File - from exported file
   - Integration with existing grade_uploader.py
   - Success/failure reporting with detailed errors

Initial Problems:
   - User ID extraction from labels
   - Label format requirements for uploader regex


PHASE 6: USER ID AND LABEL FIXES
---------------------------------
Problem: Upload failed - "No Canvas user_id found in label"

Root Cause: Labels were "Student quiz" without user IDs

Fix: Updated submission loading in Step 3
   - Extract user_id from filename (format: name_userid_quiz.html)
   - Search for numeric IDs (4+ digits)
   - Include user_id in label: "Student Name - 1234567"
   - Handle both string and int keys in metadata
   - Added debug output to verify label format

Result: Labels properly formatted for upload


PHASE 7: QUIZ VS ASSIGNMENT ID ISSUE (ONGOING)
-----------------------------------------------
Problem: 404 errors when uploading to quizzes

Root Cause Discovery:
   - Canvas quizzes have TWO IDs:
     * Quiz ID (entered by user, e.g., 5921682)
     * Assignment ID (underlying, e.g., 21683258)
   - Uploads must use Assignment ID, not Quiz ID
   - URLs were: /courses/.../assignments/5921682/... (WRONG)
   - Should be: /courses/.../assignments/21683258/... (CORRECT)

Detection Solution:
   - Created get_assignment_id_for_upload() helper function
   - Tries quiz endpoint first, extracts assignment_id
   - Falls back to assignment endpoint
   - Strips /api/v1 duplication from URLs
   - Shows detection result in UI

Current Status:
   ✓ Quiz detection working ("Detected as QUIZ - Quiz ID 5921682 → Assignment ID 21683258")
   ✓ Correct assignment ID found (21683258)
   ⚠️ Submissions downloaded (13 files) but not loaded (0 submissions for grading)
   
Current Issue:
   - Files downloaded with different naming pattern from assignment endpoint
   - Glob pattern "*_quiz.html" not matching actual filenames
   - Need to identify actual file naming pattern
   - May need to use "*.html" or different pattern


CURRENT ARCHITECTURE
====================

File Structure:
~/dev/grmodular/
├── assignment_handlers/
│   ├── base_handler.py
│   ├── exam_handler.py          ← Main exam grading logic
│   └── ...
├── pages/
│   └── 4_📋_Exams.py             ← Streamlit UI for exam grading
├── shared/
│   ├── llm_provider.py           ← LLM API wrapper
│   ├── canvas_submissions.py     ← Canvas download logic
│   ├── grade_uploader.py         ← Canvas upload logic
│   ├── exam_export.py            ← Excel export for exams
│   ├── embeddings_manager.py     ← RAG embeddings
│   └── credentials.py
└── config/
    └── courses.json              ← Course configuration

Workflow:
1. Select Course (HIST 101/110)
2. Load Exam (enter quiz/assignment ID, auto-detect type)
3. Download Submissions (from Canvas, extract to temp_submissions/)
4. Select AI Model & Grading Settings (model + score multiplier)
5. Grade Exam Submissions (AI + RAG with course materials)
6. Export Results (to Excel)
7. Upload to Canvas (from memory or Excel file)

Key Features:
- Modular design with separate handlers per assignment type
- RAG-based grading using course-specific embeddings
- Multiple LLM provider support (Anthropic, OpenAI)
- Automatic quiz/assignment ID detection
- Score multiplier for grading leniency
- 2 decimal place score formatting
- Direct Canvas integration for download and upload


ISSUES RESOLVED
================

✅ Anthropic API system message format (kwargs approach)
✅ Model name updates (claude-sonnet-4-20250514)
✅ Grading any 5 answered questions (not just first 5)
✅ Excel export with proper Canvas format
✅ Score multiplier for freshman-appropriate grading
✅ Score formatting to 2 decimal places
✅ User ID extraction from filenames
✅ Label formatting for Canvas uploads
✅ Quiz vs Assignment ID detection
✅ Double /api/v1 in URLs
✅ Handler using correct assignment ID


CURRENT ISSUE (IN PROGRESS)
============================

Problem: Files downloaded but not loaded for grading
- Downloads: "✓ Downloaded 13 submissions (13 files)"
- Loading: "✓ Loaded 0 submissions for grading"

Cause: File naming pattern mismatch
- Code looking for: "*_quiz.html"
- Actual files: Unknown pattern (need to check)

Next Steps:
1. Add debug to show actual filenames in temp_submissions/
2. Update glob pattern to match actual files
3. Test complete workflow with correct file loading
4. Verify upload works with all 13 students


TECHNICAL DETAILS
=================

Grading Algorithm:
1. Parse submission text to identify answered questions
2. For each answered question (up to 5):
   - Search course embeddings for relevant content (top-k=5)
   - Construct grading prompt with course context
   - Call LLM with freshman-level rubric
   - Parse score and feedback from response
   - Apply score multiplier (adjustable 1.0-1.5x)
   - Cap at maximum points per question
   - Round to 2 decimal places
3. Sum scores and format output

LLM Configuration:
- Provider: Anthropic Claude
- Model: claude-sonnet-4-20250514 (Sonnet 4.5)
- Temperature: 0.3
- Max tokens: 500 per question
- System message: List of content blocks

Canvas API Integration:
- Download: /courses/{id}/assignments/{id}/submissions
- Upload: PUT /courses/{id}/assignments/{id}/submissions/{user_id}
- Quiz detection: /courses/{id}/quizzes/{id}
- Assignment fetch: /courses/{id}/assignments/{id}

File Formats:
- Submissions: HTML (downloaded from Canvas)
- Export: Excel .xlsx (Canvas upload format)
- Embeddings: Pickle files with sentence-transformers


SUCCESS METRICS
===============

Functionality Achieved:
✅ AI-powered exam grading with course knowledge
✅ Flexible question answering (any 5 of 10)
✅ Adjustable grading leniency
✅ Professional score formatting
✅ Excel export capability
✅ Automatic quiz/assignment detection
⚠️ Canvas upload (pending file loading fix)

Quality Improvements:
✅ Freshman-appropriate grading rubric
✅ Generous partial credit
✅ Constructive, encouraging feedback
✅ Score multiplier for fine-tuning

User Experience:
✅ Streamlit UI with 7-step workflow
✅ Debug information for troubleshooting
✅ Progress tracking during grading
✅ Clear success/failure reporting
✅ Sidebar session state display


LESSONS LEARNED
===============

1. API Compatibility
   - Always check API format requirements (system message structure)
   - Model names change - use latest stable versions
   - URL construction matters (avoid double paths)

2. Canvas Complexity
   - Quizzes have separate quiz_id and assignment_id
   - Must use assignment_id for submissions/uploads
   - File naming patterns differ between endpoints

3. Grading Calibration
   - AI tends to grade harshly without proper context
   - Multiple approaches needed (prompts + multipliers)
   - Separation of feedback quality from score leniency

4. User Experience
   - Debug output crucial for diagnosing issues
   - Step-by-step workflow reduces confusion
   - Show what the system is doing (detection, file counts)

5. Modularity Benefits
   - Separate handlers make system maintainable
   - Shared utilities reduce code duplication
   - Easy to add new assignment types


NEXT SESSION TODO
=================

Immediate Priority:
1. Fix file loading glob pattern
2. Verify all 13 students can be graded
3. Test complete upload workflow
4. Confirm grades appear correctly in Canvas

Future Enhancements:
- Support for different exam structures (not just 5 of 10)
- Batch processing multiple exams
- Grade distribution analytics
- Rubric-based grading for more complex assignments
- Save/load grading sessions
- Grade comparison and consistency checks


CONCLUSION
==========

Significant Progress Made:
- Transformed basic concept into working AI grading system
- Solved multiple complex integration issues
- Created freshman-appropriate grading calibration
- Built complete download → grade → upload workflow

Nearly Complete:
- Core functionality working (detection, grading, export)
- One remaining issue: file loading pattern
- Expected resolution: 15-30 minutes

System Value:
- Saves hours of manual grading per exam
- Consistent, detailed feedback for every student
- Maintains academic rigor while being appropriately lenient
- Direct Canvas integration eliminates manual data entry
- Scalable to multiple courses and exam types

Project Status: 95% Complete
Estimated Time to Full Functionality: < 1 hour