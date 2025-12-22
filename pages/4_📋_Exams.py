"""
Exam Grader Application
Streamlit app for grading exams with AI assistance
"""

import sys
from pathlib import Path

# Add project root to Python path - CRITICAL FOR IMPORTS
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from typing import List, Tuple
import logging

# Now import project modules
from assignment_handlers.exam_handler import ExamHandler
from shared.canvas_rubric_api import CanvasRubricAPI
from shared.canvas_submissions import download_submissions_flat
from shared.credentials import load_canvas_credentials, load_llm_keys
from shared.llm_provider import make_llm
from shared.config_loader import get_config
from shared.embeddings_manager import EmbeddingsManager
from shared.export_utils import create_xlsx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Exam Grader",
    page_icon="📋",
    layout="wide"
)

import requests  # Add this if not already there

def get_assignment_id_for_upload(canvas_url, canvas_token, course_id, entered_id):
    """Auto-detect quiz vs assignment and return correct ID for uploads"""
    
    # Strip /api/v1 if it's already in the URL
    base_url = canvas_url.rstrip('/').replace('/api/v1', '')
    
    headers = {"Authorization": f"Bearer {canvas_token}"}
    
    # Try as quiz
    try:
        quiz_url = f"{base_url}/api/v1/courses/{course_id}/quizzes/{entered_id}"
        response = requests.get(quiz_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            quiz_data = response.json()
            assignment_id = quiz_data.get('assignment_id')
            
            if assignment_id:
                # Get assignment data
                assign_url = f"{base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}"
                assign_resp = requests.get(assign_url, headers=headers, timeout=10)
                
                if assign_resp.status_code == 200:
                    return str(assignment_id), True, assign_resp.json()
    except Exception as e:
        pass
    
    # Try as assignment
    try:
        assign_url = f"{base_url}/api/v1/courses/{course_id}/assignments/{entered_id}"
        response = requests.get(assign_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return str(entered_id), False, response.json()
    except Exception as e:
        pass
    
    return str(entered_id), False, {}

# ═══════════════════════════════════════════════════════════════════
# Initialize Session State
# ═══════════════════════════════════════════════════════════════════

if "selected_course" not in st.session_state:
    st.session_state.selected_course = None

if "exam_handler" not in st.session_state:
    st.session_state.exam_handler = None

if "entryList" not in st.session_state:
    st.session_state.entryList = None

# ═══════════════════════════════════════════════════════════════════
# Load Credentials
# ═══════════════════════════════════════════════════════════════════

try:
    canvas_url, canvas_token = load_canvas_credentials()
    llm_keys = load_llm_keys()
except Exception as e:
    st.error(f"Credentials Error: {e}")
    st.info("Please create ~/canvas-secrets.key with your API credentials")
    st.stop()

# Initialize embeddings manager
if "embeddings_manager" not in st.session_state:
    config = get_config()
    st.session_state.embeddings_manager = EmbeddingsManager(config)
    st.session_state.config = config

# ═══════════════════════════════════════════════════════════════════
# Step 1: Select Course
# ═══════════════════════════════════════════════════════════════════

st.header("Step 1: Select Course")

try:
    if "config" not in st.session_state:
        st.session_state.config = get_config()
    
    config = st.session_state.config
    COURSES = config.get_courses_dict()
    
    # Validation messages
    validation_messages = config.validate_config()
    if validation_messages:
        with st.expander("⚠️ Configuration Warnings", expanded=False):
            for msg in validation_messages:
                if msg.startswith("ERROR"):
                    st.error(msg)
                else:
                    st.warning(msg)
except Exception as e:
    st.error(f"Error loading configuration: {e}")
    st.info("Please check config/courses.json")
    st.stop()

# Course selector
course_name = st.selectbox(
    "Select course",
    options=list(COURSES.keys()),
    key="course_selector"
)

if course_name:
    selected_course_id, course_type = COURSES[course_name]
    
    # Get full course configuration
    course_config = config.get_course_config(course_name)
    
    st.session_state.selected_course = (course_name, selected_course_id, course_type)
    st.session_state.course_config = course_config
    
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"✓ **Course:** {course_name}")
        st.info(f"**Canvas ID:** {selected_course_id}")
    
    with col2:
        st.info(f"**Knowledge Base:** {course_type}")
        
        # Show embeddings status
        manager = st.session_state.embeddings_manager
        embeddings_info = manager.get_embeddings_info(course_type)
        
        if embeddings_info:
            st.success(f"✓ Embeddings exist")
            with st.expander("📊 Embeddings Info"):
                st.text(f"Size: {embeddings_info['size_mb']:.2f} MB")
                st.text(f"Modified: {embeddings_info['modified'].strftime('%Y-%m-%d %H:%M')}")
        else:
            st.warning("⚠️ Embeddings not found - will be generated automatically")

# ═══════════════════════════════════════════════════════════════════
# Step 2: Load Exam
# ═══════════════════════════════════════════════════════════════════

st.header("Step 2: Load Exam")

if st.session_state.selected_course:
    course_name, course_id, course_type = st.session_state.selected_course
    
    exam_id = st.number_input(
        "Enter Exam/Quiz ID from Canvas",
        min_value=1,
        value=None,
        help="Find this in the Canvas URL when viewing the exam",
        key="exam_id_input"
    )
    
    if exam_id and st.button("Load Exam"):
        try:
            with st.spinner("Loading exam from Canvas..."):
                course_name, course_id, course_type = st.session_state.selected_course
                
                # Get correct assignment ID (handles quizzes automatically)
                upload_id, is_quiz, assignment_data = get_assignment_id_for_upload(
                    canvas_url, canvas_token, course_id, exam_id
                )
                
                if not assignment_data:
                    st.error(f"Could not load exam/quiz with ID {exam_id}")
                    st.stop()
                
                # Show detection result
                if is_quiz:
                    st.success(f"✓ Detected as QUIZ - will use correct assignment ID for uploads")
                    st.info(f"Quiz ID {exam_id} → Assignment ID {upload_id}")
                else:
                    st.success(f"✓ Detected as regular assignment")
                
                # Create exam handler (score_multiplier will be set when grading starts)
                handler = ExamHandler(
                    assignment_key=str(exam_id),
                    display_name=assignment_data.get('name', f'Exam {exam_id}'),
                    default_points=int(assignment_data.get('points_possible', 50)),
                    course_mapping={},  # Empty for now
                    canvas_assignment_id=upload_id,
                    total_points=int(assignment_data.get('points_possible', 50)),
                    rubric=None,
                    score_multiplier=1.0,  # Default, will be updated when grading
                    original_entered_id=exam_id,
                    is_quiz=is_quiz
                )
                st.session_state.exam_handler = handler
                
                st.success(f"✓ Loaded exam: {assignment_data.get('name', 'Unknown')}")
                
                with st.expander("Exam Details"):
                    st.write(f"**Name:** {assignment_data.get('name')}")
                    st.write(f"**Points:** {assignment_data.get('points_possible')}")
                    st.write(f"**Type:** {'Quiz' if 'quiz' in assignment_data.get('submission_types', []) else 'Assignment'}")
                
        except Exception as e:
            st.error(f"Error loading exam: {e}")
            logger.exception("Error loading exam")

else:
    st.info("⬆️ Please select a course in Step 1 first")

# ═══════════════════════════════════════════════════════════════════
# Step 3: Download Submissions
# ═══════════════════════════════════════════════════════════════════

st.header("Step 3: Download Submissions")

if st.session_state.selected_course and st.session_state.exam_handler:
    course_name, course_id, course_type = st.session_state.selected_course
    handler = st.session_state.exam_handler
    
    if st.button("Download Submissions from Canvas"):
        try:
            with st.spinner("Downloading exam submissions..."):
                # Download submissions to submissions directory
                # Use the correct ID for downloading (quiz ID for quizzes, assignment ID for assignments)
                download_id = handler.get_submission_download_id()
                num_students, num_files, metadata = download_submissions_flat(
                    canvas_url,
                    canvas_token,
                    course_id,
                    download_id,
                    dest_dir="./submissions",
                    clean_dest=True
                )
                
                # Save metadata to session state for later use
                st.session_state.metadata = metadata

                st.success(f"✓ Downloaded {num_students} submissions ({num_files} files)")
                
                # Load submissions into entry list format
                # Format: [student_name, submission_text, feedback]
                from pathlib import Path
                submissions_dir = Path("./submissions")
                
                # DEBUG: Show metadata structure
                with st.expander("🔍 Debug Info - Metadata Structure"):
                    st.write(f"**Metadata keys (first 5):**")
                    metadata_keys = list(metadata.keys())[:5]
                    for key in metadata_keys:
                        st.write(f"  - Key: `{key}` (type: {type(key).__name__})")
                        if key in metadata:
                            st.write(f"    Name: {metadata[key].get('name', 'N/A')}")
                    
                    st.write(f"\n**Submission files (first 5):**")
                    files = list(submissions_dir.glob("*_quiz.html"))
                    for f in files[:5]:
                        st.write(f"  - File: `{f.name}`")
                
                entryList = []
                missing_metadata = []
                
                for file_path in submissions_dir.glob("*.html"):
                    # Extract student info from filename
                    # Typical format: lastname_firstname_userid_quiz.html
                    # or: studentname_userid_quiz.html
                    filename = file_path.stem
                    parts = filename.split("_")
                    
                    # Find the user_id (should be numeric, 4+ digits, before "quiz")
                    user_id = None
                    for i, part in enumerate(parts):
                        if part.isdigit() and len(part) >= 4:
                            # Make sure it's not after "quiz" marker
                            if i < len(parts) - 1 or parts[-1] != "quiz":
                                user_id = part
                                break
                    
                    # Try to find student info in metadata
                    student_name = None
                    if user_id:
                        # Try user_id as string (most common)
                        if user_id in metadata:
                            student_info = metadata[user_id]
                            student_name = student_info.get('name', f"Student {user_id}")
                        # Try as int (fallback)
                        elif int(user_id) in metadata:
                            student_info = metadata[int(user_id)]
                            student_name = student_info.get('name', f"Student {user_id}")
                    
                    # Create label
                    if student_name and user_id:
                        # CRITICAL: Include user_id in label for upload to work
                        # Format: "Last, First - 1234567"
                        label = f"{student_name} - {user_id}"
                    elif user_id:
                        # Have user_id but no name
                        label = f"Student {user_id} - {user_id}"
                        missing_metadata.append(f"User ID {user_id}: No name in metadata")
                    else:
                        # No user_id found - upload will fail
                        label = f"Unknown Student - {filename}"
                        missing_metadata.append(f"File {filename}: No user ID found")
                    
                    # Read submission text
                    submission_text = file_path.read_text(encoding="utf-8")
                    
                    # Get existing grade/feedback
                    existing_feedback = ""
                    if user_id:
                        # Try both string and int keys
                        if user_id in metadata:
                            existing_feedback = metadata[user_id].get('current_feedback', "")
                        elif int(user_id) in metadata:
                            existing_feedback = metadata[int(user_id)].get('current_feedback', "")
                    
                    entryList.append([label, submission_text, existing_feedback])
                
                st.session_state.entryList = entryList
                st.info(f"✓ Loaded {len(entryList)} submissions for grading")
                
                # Show warnings if any metadata was missing
                if missing_metadata:
                    with st.expander("⚠️ Metadata Warnings", expanded=False):
                        st.warning(f"Found {len(missing_metadata)} submissions with missing or incomplete metadata:")
                        for msg in missing_metadata[:10]:  # Show first 10
                            st.text(f"• {msg}")
                        if len(missing_metadata) > 10:
                            st.text(f"... and {len(missing_metadata) - 10} more")
                
                # Show sample labels
                with st.expander("📋 Sample Student Labels"):
                    st.write("First 5 labels that will be used:")
                    for i, entry in enumerate(entryList[:5]):
                        st.text(f"{i+1}. {entry[0]}")
                
        except Exception as e:
            st.error(f"Error downloading submissions: {e}")
            logger.exception("Error downloading submissions")

else:
    st.info("⬆️ Please complete Steps 1 and 2 first")

# ═══════════════════════════════════════════════════════════════════
# Step 4: Select LLM Provider and Grading Settings
# ═══════════════════════════════════════════════════════════════════

st.header("Step 4: Select AI Model & Grading Settings")

col1, col2 = st.columns(2)

with col1:
    provider = st.selectbox(
        "AI Provider",
        options=["anthropic", "openai"],
        index=0,
        help="Select which AI provider to use for grading"
    )

with col2:
    if provider == "anthropic":
        models = [
            "claude-sonnet-4-20250514",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ]
    else:  # openai
        models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo"
        ]
    
    selected_model = st.selectbox(
        "Model",
        options=models,
        help="Select the specific model to use"
    )

# Check if API key is available
api_key = llm_keys.get(provider)
if api_key:
    st.success(f"✓ {provider.capitalize()} API key loaded")
else:
    st.error(f"❌ {provider.capitalize()} API key not found")
    st.info(f"Add {provider.capitalize()} API key to ~/canvas-secrets.key")

# ═══════════════════════════════════════════════════════════════════
# Grading Settings (Score Multiplier)
# ═══════════════════════════════════════════════════════════════════

st.markdown("---")
st.subheader("⚙️ Grading Settings")

score_multiplier = st.slider(
    "Score Multiplier",
    min_value=1.0,
    max_value=1.5,
    value=1.15,
    step=0.05,
    help="Amplify individual question scores by this percentage while keeping feedback unchanged. 1.15 = 15% boost."
)

# Show example
example_base = 7.0
example_adjusted = min(example_base * score_multiplier, 10.0)
st.info(f"📊 Example: With {score_multiplier}x multiplier, a {example_base:.2f}/10 score becomes {example_adjusted:.2f}/10")

if score_multiplier > 1.0:
    st.warning(f"⚠️ Scores will be boosted by {(score_multiplier - 1.0) * 100:.0f}% while maintaining honest feedback")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# Step 5: Grade Exam Submissions
# ═══════════════════════════════════════════════════════════════════

st.header("Step 5: Grade Exam Submissions")

if st.session_state.entryList and st.session_state.exam_handler:
    handler = st.session_state.exam_handler
    entryList = st.session_state.entryList
    
    st.info(f"Ready to grade {len(entryList)} exam submissions")
    
    # Grading options
    col1, col2 = st.columns(2)
    with col1:
        batch_size = st.number_input(
            "Batch size",
            min_value=1,
            max_value=len(entryList),
            value=min(10, len(entryList)),
            help="Number of exams to grade at once"
        )
    with col2:
        use_rubric_grading = st.checkbox(
            "Use rubric-based grading",
            value=False,
            help="Use Canvas rubric for grading if available"
        )
    
    if st.button("Start Grading", type="primary"):
        # Update handler with current score multiplier
        handler.score_multiplier = score_multiplier
        
        # Initialize LLM client
        # Create the actual API client
        if provider == "anthropic":
            from anthropic import Anthropic
            raw_client = Anthropic(api_key=llm_keys['anthropic'])
        elif provider == "openai":
            from openai import OpenAI
            raw_client = OpenAI(api_key=llm_keys['openai'])
        else:
            st.error(f"Unknown provider: {provider}")
            st.stop()

        # Wrap it in our LLM abstraction
        llm_client = make_llm(provider, raw_client)
        
        # Load or generate course embeddings automatically
        course_name, course_id, course_type = st.session_state.selected_course
        manager = st.session_state.embeddings_manager
        
        with st.spinner(f"Loading embeddings for {course_type}..."):
            try:
                # This will automatically generate embeddings if they don't exist
                processor, msg = manager.load_or_generate_embeddings(
                    course_type,
                    force_refresh=False
                )
                
                if processor is None:
                    st.error(f"Failed to load embeddings: {msg}")
                    st.info("Please check that your knowledge base directory has course materials:")
                    kb_path = manager.config.get_knowledge_base_path(course_type)
                    st.code(kb_path)
                    st.stop()
                
                course_embeddings = processor
                stats = processor.get_course_statistics()
                
                st.success(f"✓ {msg}")
                with st.expander("📊 Embeddings Statistics"):
                    st.write(f"- Total chunks: {stats['total_chunks']}")
                    st.write(f"- Unique documents: {stats['unique_documents']}")
                    st.write(f"- Average tokens per chunk: {stats['avg_tokens_per_chunk']:.1f}")
                
            except Exception as e:
                st.error(f"Error with embeddings: {e}")
                logger.exception("Error loading embeddings")
                st.stop()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        total_graded = 0
        
        # Grade submissions
        for i, entry in enumerate(entryList):
            student_label = entry[0]
            submission_text = entry[1]
            
            status_text.text(f"Grading {i+1}/{len(entryList)}: {student_label}")
            
            try:
                # Grade using the exam handler
                grading_result = handler.grade_exam_submission(
                    submission_text,
                    llm_client,
                    course_embeddings,
                    selected_model
                )
                
                # Format feedback
                score = grading_result['total_score']
                max_score = grading_result['max_score']
                detailed_feedback = handler.format_grading_output(grading_result)
                feedback = f"{score:.2f}/{max_score:.2f}\n\n{detailed_feedback}"
                
                # Update entry with feedback
                entry[2] = feedback
                total_graded += 1
                
                # Update progress
                progress_bar.progress((i + 1) / len(entryList))
                
                # Show result
                with results_container:
                    if (i + 1) <= 3:  # Show first 3
                        with st.expander(f"✓ {student_label}"):
                            st.text(feedback)
                
            except Exception as e:
                st.error(f"Error grading {student_label}: {e}")
                import traceback
                st.error(traceback.format_exc())
        
        status_text.text("✓ Grading complete!")
        st.success(f"Successfully graded {total_graded}/{len(entryList)} exams")
        
        if score_multiplier > 1.0:
            st.info(f"✨ Scores were boosted by {(score_multiplier - 1.0) * 100:.0f}% using the score multiplier")
        
        # Automatically export to Excel
        try:
            from shared.exam_export import export_exam_to_excel
            output_path = Path("./submissions") / f"graded_exam_{handler.canvas_assignment_id}.xlsx"
            metadata = st.session_state.get('metadata', {})
            export_exam_to_excel(entryList, metadata, output_path, handler.total_points)
            st.success(f"✓ Automatically exported to {output_path}")
            
            # Store export path for upload
            st.session_state.export_path = output_path
            
        except Exception as e:
            st.error(f"Error creating Excel file: {e}")
            import traceback
            st.error(traceback.format_exc())
        
        # Update session state
        st.session_state.entryList = entryList

else:
    st.info("⬆️ Please complete previous steps first")

# ═══════════════════════════════════════════════════════════════════
# Step 6: Export Results
# ═══════════════════════════════════════════════════════════════════

st.header("Step 6: Export Results")

if st.session_state.entryList:
    entryList = st.session_state.entryList
    handler = st.session_state.exam_handler
    
    # Check if any have been graded
    graded_count = sum(1 for entry in entryList if entry[2])
    
    if graded_count > 0:
        st.info(f"{graded_count}/{len(entryList)} submissions have been graded")
        
        if st.button("📤 Export to Excel", type="primary"):
            try:
                from shared.exam_export import export_exam_to_excel
                output_path = Path("./submissions") / f"graded_exam_{handler.canvas_assignment_id}.xlsx"
                metadata = st.session_state.get('metadata', {})
                export_exam_to_excel(entryList, metadata, output_path, handler.total_points)
                st.success(f"✓ Exported to {output_path}")
                
                # Store export path for upload
                st.session_state.export_path = output_path
                
                # Provide download link
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Graded Exams (Excel)",
                        data=f,
                        file_name=f"graded_exam_{handler.canvas_assignment_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"Error creating Excel file: {e}")
                import traceback
                st.error(traceback.format_exc())
    else:
        st.warning("No submissions have been graded yet")

else:
    st.info("⬆️ No submissions loaded")

# ═══════════════════════════════════════════════════════════════════
# Step 7: Upload to Canvas
# ═══════════════════════════════════════════════════════════════════

st.header("Step 7: Upload to Canvas")

if st.session_state.entryList and st.session_state.exam_handler:
    entryList = st.session_state.entryList
    handler = st.session_state.exam_handler

    # Show debug info about IDs
    st.write("🔍 DEBUG INFO:")
    st.write(f"Handler assignment ID (for uploads): {handler.canvas_assignment_id}")
    st.write(f"Original entered ID: {handler.original_entered_id}")
    st.write(f"Is quiz: {handler.is_quiz}")
    st.write(f"Submission download ID: {handler.get_submission_download_id()}")
    
    # Check if any have been graded
    graded_count = sum(1 for entry in entryList if entry[2])
    
    if graded_count > 0:
        st.info(f"Ready to upload {graded_count} graded exams to Canvas")
        
        st.warning("⚠️ **Important:** Review all grades before uploading to Canvas. This action cannot be easily undone.")
        
        # Show sample of what will be uploaded
        with st.expander("👀 Preview Upload Data (First 3 Students)"):
            for i, entry in enumerate(entryList[:3]):
                if entry[2]:  # If graded
                    st.text(f"\n{i+1}. Label: {entry[0]}")
                    # Extract user ID from label
                    import re
                    uid_match = re.search(r'(\d{4,})', entry[0])
                    if uid_match:
                        st.text(f"   User ID: {uid_match.group(1)} ✓")
                    else:
                        st.text(f"   User ID: NOT FOUND ❌")
                    
                    # Show first line of feedback
                    first_line = entry[2].split('\n')[0]
                    st.text(f"   Score: {first_line}")
        
        # Upload options
        col1, col2 = st.columns(2)
        with col1:
            upload_from = st.radio(
                "Upload from:",
                options=["Current Session (Memory)", "Excel File"],
                help="Choose whether to upload from the current grading session or from a saved Excel file"
            )
        
        with col2:
            if upload_from == "Excel File":
                st.info("If uploading from Excel, ensure the 'Upload?' column is set to 'yes' for rows you want to upload")
        
        if st.button("🚀 Upload Grades to Canvas", type="primary"):
            try:
                from shared.grade_uploader import upload_all_from_entrylist, upload_all_from_xlsx
                
                course_name, course_id, course_type = st.session_state.selected_course
                
                if upload_from == "Current Session (Memory)":
                    with st.spinner("Uploading grades to Canvas..."):
                        successes, failures_count, failures = upload_all_from_entrylist(
                            canvas_url,
                            canvas_token,
                            course_id,
                            handler.canvas_assignment_id,
                            entryList
                        )
                        
                        if successes > 0:
                            st.success(f"✓ Successfully uploaded {successes} grades to Canvas!")
                        
                        if failures_count > 0:
                            st.error(f"❌ Failed to upload {failures_count} grades")
                            with st.expander("View Failures"):
                                for label, reason in failures:
                                    st.text(f"• {label}: {reason}")
                
                else:  # Upload from Excel
                    export_path = st.session_state.get('export_path')
                    if not export_path or not Path(export_path).exists():
                        st.error("Excel file not found. Please export to Excel first (Step 6).")
                    else:
                        with st.spinner("Uploading grades from Excel to Canvas..."):
                            successes, failures_count, failures = upload_all_from_xlsx(
                                canvas_url,
                                canvas_token,
                                course_id,
                                handler.canvas_assignment_id,
                                str(export_path),
                                respect_upload_flag=True
                            )
                            
                            if successes > 0:
                                st.success(f"✓ Successfully uploaded {successes} grades to Canvas!")
                            
                            if failures_count > 0:
                                st.error(f"❌ Failed to upload {failures_count} grades")
                                with st.expander("View Failures"):
                                    for label, reason in failures:
                                        st.text(f"• {label}: {reason}")
                
            except Exception as e:
                st.error(f"Error uploading to Canvas: {e}")
                import traceback
                st.error(traceback.format_exc())
    else:
        st.warning("No graded submissions to upload")

else:
    st.info("⬆️ Please complete previous steps first")

# ═══════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("Current Session")
    
    if "selected_course" in st.session_state and st.session_state.selected_course:
        course_name, course_id, course_type = st.session_state.selected_course
        st.write(f"**Course:** {course_name}")
        st.write(f"**Canvas ID:** {course_id}")
        st.write(f"**Knowledge Base:** {course_type}")
        
        # Show embeddings status in sidebar
        if "embeddings_manager" in st.session_state:
            manager = st.session_state.embeddings_manager
            embeddings_info = manager.get_embeddings_info(course_type)
            
            if embeddings_info:
                st.success("✓ Embeddings loaded")
            else:
                st.warning("⚠️ Embeddings missing")
    
    if st.session_state.exam_handler:
        handler = st.session_state.exam_handler
        st.write(f"**Exam ID:** {handler.original_entered_id}")
        st.write(f"**Upload ID:** {handler.canvas_assignment_id}")
        if handler.is_quiz:
            st.write("**Type:** Quiz")
        if handler.score_multiplier != 1.0:
            st.write(f"**Score Multiplier:** {handler.score_multiplier}x")
    
    if st.session_state.entryList:
        st.write(f"**Submissions:** {len(st.session_state.entryList)}")
        graded = sum(1 for e in st.session_state.entryList if e[2])
        st.write(f"**Graded:** {graded}")
    
    st.divider()
    
    if st.button("🔄 Reset All"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.divider()
    st.caption("Exam Grader v2.0")
    st.caption("Built with Streamlit")