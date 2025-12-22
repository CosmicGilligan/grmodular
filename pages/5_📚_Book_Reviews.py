"""
Book Review Grading Application - Streamlined Workflow with Selective Grading
Streamlit app for grading book reviews with AI assistance
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from shared.canvas_submissions import download_submissions_flat, load_submissions_from_folder
from assignment_handlers.book_review_handler import BookReviewHandler
from shared.exam_export import export_book_reviews_to_excel
from shared.config_loader import get_config
from shared.credentials import load_canvas_credentials, load_llm_keys
from shared.llm_provider import make_llm

st.set_page_config(page_title="Book Review Grader", page_icon="📚", layout="wide")

st.title("📚 Book Review Grading: 1984")

# Initialize Session State
if "review_grades" not in st.session_state:
    st.session_state.review_grades = {}  # Changed to dict with user_id as key

if "loaded_reviews" not in st.session_state:
    st.session_state.loaded_reviews = []

if "download_metadata" not in st.session_state:
    st.session_state.download_metadata = {}

if "export_path" not in st.session_state:
    st.session_state.export_path = None

if "selected_students" not in st.session_state:
    st.session_state.selected_students = []

if "config" not in st.session_state:
    try:
        st.session_state.config = get_config()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        st.info("Please check config/courses.json")
        st.stop()

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.header("Configuration")
    
    # Load courses
    try:
        config = st.session_state.config
        COURSES = config.get_courses_dict()
        
        course_name = st.selectbox(
            "Select course",
            options=list(COURSES.keys()),
            key="book_review_course_selector"
        )
        
        if course_name:
            selected_course_id, course_type = COURSES[course_name]
            st.session_state.selected_course_id = selected_course_id
            st.session_state.selected_course_name = course_name
            st.session_state.selected_course_type = course_type
            
            st.info(f"Course ID: {selected_course_id}")
        else:
            st.warning("Please select a course")
            st.stop()
            
    except Exception as e:
        st.error(f"Error loading courses: {e}")
        st.stop()
    
    # Assignment ID
    assignment_id = st.text_input("Canvas Assignment ID")
    
    st.divider()
    model_choice = st.selectbox("LLM Model", ["claude-sonnet-4-20250514", "gpt-4o"])
    
    # Score multiplier
    score_multiplier = st.slider("Score Multiplier (Leniency)", 1.0, 1.3, 1.05, 0.05)
    st.caption(f"Scores will be boosted by {(score_multiplier - 1.0) * 100:.0f}%")

# --- STEP 1: DOWNLOAD SUBMISSIONS ---

st.header("Step 1: Download Submissions from Canvas")

# Get credentials
try:
    canvas_url, canvas_token = load_canvas_credentials()
except Exception as e:
    st.error(f"Error loading credentials: {e}")
    st.info("Please check your credentials file")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Download from Canvas", key="download_button", type="primary"):
        if not assignment_id:
            st.error("Please enter an Assignment ID")
        else:
            with st.spinner("Downloading from Canvas..."):
                try:
                    course_id = st.session_state.selected_course_id
                    num_students, num_files, metadata = download_submissions_flat(
                        canvas_url,
                        canvas_token,
                        course_id,
                        int(assignment_id),
                        dest_dir="./submissions",
                        clean_dest=True
                    )
                    st.session_state.download_metadata = metadata
                    st.success(f"✓ Downloaded {num_students} submissions ({num_files} files)")
                    
                    # AUTO-LOAD submissions after download
                    with st.spinner("Loading submissions..."):
                        submissions = load_submissions_from_folder("./submissions")
                        
                        if submissions:
                            # Match with Canvas metadata to get proper names
                            matched = 0
                            for sub in submissions:
                                user_id = sub['user_id']
                                meta_entry = metadata.get(user_id) or metadata.get(str(user_id))
                                if meta_entry and 'name' in meta_entry:
                                    sub['name'] = meta_entry['name']
                                    matched += 1
                            
                            st.session_state.loaded_reviews = submissions
                            # Select all by default
                            st.session_state.selected_students = [sub['user_id'] for sub in submissions]
                            st.success(f"✓ Auto-loaded {len(submissions)} submissions (matched {matched} names)")
                        else:
                            st.warning("Downloaded but could not load submissions")
                    
                except Exception as e:
                    st.error(f"Error downloading: {e}")
                    import traceback
                    st.error(traceback.format_exc())

with col2:
    # Optional manual load
    if st.button("📂 Load from Folder (Optional)", key="load_button"):
        try:
            with st.spinner("Loading submissions from ./submissions..."):
                submissions = load_submissions_from_folder("./submissions")
                
                if not submissions:
                    st.warning("⚠️ No submissions found in ./submissions directory")
                    st.info("Please download submissions first")
                else:
                    # Match with Canvas metadata if available
                    if st.session_state.download_metadata:
                        metadata = st.session_state.download_metadata
                        matched = 0
                        for sub in submissions:
                            user_id = sub['user_id']
                            meta_entry = metadata.get(user_id) or metadata.get(str(user_id))
                            if meta_entry and 'name' in meta_entry:
                                sub['name'] = meta_entry['name']
                                matched += 1
                        st.success(f"✓ Matched {matched}/{len(submissions)} names with Canvas metadata")
                    
                    st.session_state.loaded_reviews = submissions
                    # Select all by default
                    st.session_state.selected_students = [sub['user_id'] for sub in submissions]
                    st.success(f"✓ Loaded {len(submissions)} submissions")
                            
        except Exception as e:
            st.error(f"Error loading: {e}")
            import traceback
            st.error(traceback.format_exc())

# Status and Student Selection
st.divider()
if st.session_state.loaded_reviews:
    st.success(f"✅ {len(st.session_state.loaded_reviews)} submissions loaded")
    
    # Student Selection
    st.subheader("Select Students to Grade")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("✓ Select All"):
            st.session_state.selected_students = [sub['user_id'] for sub in st.session_state.loaded_reviews]
            st.rerun()
    
    with col2:
        if st.button("✗ Deselect All"):
            st.session_state.selected_students = []
            st.rerun()
    
    # Show students with checkboxes
    st.write("**Students:**")
    
    # Create a dataframe for display
    student_data = []
    for sub in st.session_state.loaded_reviews:
        user_id = sub['user_id']
        graded = user_id in st.session_state.review_grades
        status = "✅ Graded" if graded else "⏳ Not graded"
        student_data.append({
            'Select': user_id in st.session_state.selected_students,
            'Student': sub['name'],
            'ID': user_id,
            'Status': status,
            'Text Length': f"{len(sub['text'])} chars"
        })
    
    df_students = pd.DataFrame(student_data)
    
    # Use data editor for selection
    edited_df = st.data_editor(
        df_students,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select students to grade",
                default=False,
            )
        },
        disabled=["Student", "ID", "Status", "Text Length"],
        hide_index=True,
        use_container_width=True
    )
    
    # Update selected students from edited dataframe
    st.session_state.selected_students = [
        row['ID'] for _, row in edited_df.iterrows() if row['Select']
    ]
    
    selected_count = len(st.session_state.selected_students)
    st.info(f"📌 Selected {selected_count}/{len(st.session_state.loaded_reviews)} students for grading")
    
else:
    st.info("⬆️ Download submissions to begin")

# --- STEP 2: AI GRADING ---

if st.session_state.loaded_reviews and st.session_state.selected_students:
    st.header("Step 2: Grade with AI")
    
    selected_count = len(st.session_state.selected_students)
    st.info(f"📚 Ready to grade {selected_count} selected students")
    
    # Show grading button
    button_label = f"🤖 Grade Selected Students ({selected_count})" if selected_count < len(st.session_state.loaded_reviews) else "🤖 Grade All Students"
    
    if st.button(button_label, key="start_grading_button", type="primary"):
        # Create LLM client
        try:
            llm_keys = load_llm_keys()
            
            # Determine provider from model choice
            if "claude" in model_choice:
                provider = "anthropic"
                from anthropic import Anthropic
                api_key = llm_keys.get('anthropic')
                if not api_key:
                    st.error("Anthropic API key not found")
                    st.stop()
                raw_client = Anthropic(api_key=api_key)
            else:
                provider = "openai"
                from openai import OpenAI
                api_key = llm_keys.get('openai')
                if not api_key:
                    st.error("OpenAI API key not found")
                    st.stop()
                raw_client = OpenAI(api_key=api_key)
            
            llm_client = make_llm(provider, raw_client)
            handler = BookReviewHandler(llm_client)
            st.success(f"✓ LLM client initialized ({provider})")
            
        except Exception as e:
            st.error(f"Error creating LLM client: {e}")
            import traceback
            st.error(traceback.format_exc())
            st.stop()
        
        # Filter submissions to only selected students
        selected_submissions = [
            sub for sub in st.session_state.loaded_reviews 
            if sub['user_id'] in st.session_state.selected_students
        ]
        
        # Grade submissions
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        errors = []
        total = len(selected_submissions)
        
        for i, sub in enumerate(selected_submissions):
            status_text.text(f"Grading {i+1}/{total}: {sub['name']}...")
            
            try:
                # Call grading handler
                result = handler.grade_review(
                    student_name=sub['name'],
                    submission_text=sub['text'],
                    user_id=sub['user_id']
                )
                
                # Check for errors
                if 'error' in result:
                    errors.append(f"{sub['name']}: {result.get('error', 'Unknown error')}")
                    logger.error(f"Grading error for {sub['name']}: {result.get('error')}")
                
                # Apply multiplier & cap at 100
                raw_score = result['score']
                final_score = min(100.0, raw_score * score_multiplier)
                
                # Store in dict by user_id
                st.session_state.review_grades[sub['user_id']] = {
                    "ID": sub['user_id'],
                    "Student": sub['name'],
                    "Raw Score": raw_score,
                    "Final Score": round(final_score, 2),
                    "Feedback": result['feedback'],
                    "Breakdown": str(result.get('sections', {}))
                }
                
            except Exception as e:
                error_msg = f"{sub['name']}: {str(e)}"
                errors.append(error_msg)
                logger.exception(f"Exception grading {sub['name']}")
                
                # Add failed grade
                st.session_state.review_grades[sub['user_id']] = {
                    "ID": sub['user_id'],
                    "Student": sub['name'],
                    "Raw Score": 0,
                    "Final Score": 0,
                    "Feedback": f"Error during grading: {str(e)}",
                    "Breakdown": "{}"
                }
            
            progress_bar.progress((i + 1) / total)
        
        # Show results
        success_count = len([g for g in st.session_state.review_grades.values() if g['Final Score'] > 0])
        st.success(f"🎉 Grading Complete! {success_count}/{total} successfully graded")
        
        if errors:
            with st.expander(f"⚠️ {len(errors)} Errors Occurred"):
                for error in errors:
                    st.error(error)
        
        # Summary stats
        if success_count > 0:
            successful_grades = [g['Final Score'] for g in st.session_state.review_grades.values() if g['Final Score'] > 0]
            avg_score = sum(successful_grades) / len(successful_grades)
            
            st.info(f"📊 Grading Summary:")
            st.write(f"- Successfully graded: {success_count}/{total}")
            st.write(f"- Average score: {avg_score:.1f}/100")
            st.write(f"- Score multiplier: {score_multiplier}x ({(score_multiplier-1)*100:.0f}% boost)")
        
        # AUTO-EXPORT to Excel
        with st.spinner("Saving to Excel..."):
            try:
                # Prepare export list - includes graded + original submissions
                export_grades = []
                
                for sub in st.session_state.loaded_reviews:
                    user_id = sub['user_id']
                    
                    if user_id in st.session_state.review_grades:
                        # Use newly graded data
                        export_grades.append(st.session_state.review_grades[user_id])
                    else:
                        # Use placeholder for non-graded students
                        export_grades.append({
                            "ID": user_id,
                            "Student": sub['name'],
                            "Raw Score": 0,
                            "Final Score": 0,
                            "Feedback": "[Not graded in this session]",
                            "Breakdown": "{}"
                        })
                
                output_path = Path("./submissions") / "book_reviews_graded.xlsx"
                export_book_reviews_to_excel(export_grades, output_path)
                st.session_state.export_path = output_path
                st.success(f"✓ Auto-saved to {output_path}")
                st.info(f"📝 Excel includes all {len(export_grades)} students ({len(st.session_state.review_grades)} newly graded)")
            except Exception as e:
                st.error(f"Error auto-saving Excel: {e}")

elif st.session_state.loaded_reviews and not st.session_state.selected_students:
    st.warning("⚠️ No students selected - Please select students to grade")
else:
    st.info("⚠️ No submissions loaded - Please download submissions first")

# --- STEP 3: REVIEW RESULTS ---

if st.session_state.review_grades:
    st.header("Step 3: Review Graded Results")
    
    graded_count = len(st.session_state.review_grades)
    success_count = len([g for g in st.session_state.review_grades.values() if g['Final Score'] > 0])
    st.success(f"✅ {success_count}/{graded_count} reviews graded successfully")
    
    # Show only graded students
    df = pd.DataFrame(list(st.session_state.review_grades.values()))
    st.dataframe(df[['Student', 'Raw Score', 'Final Score', 'Feedback']], use_container_width=True)
    
    # Download button
    if st.session_state.export_path and Path(st.session_state.export_path).exists():
        total_in_file = len(st.session_state.loaded_reviews)
        with open(st.session_state.export_path, "rb") as f:
            st.download_button(
                label=f"⬇️ Download Excel File ({total_in_file} total students, {graded_count} newly graded)",
                data=f,
                file_name="book_reviews_graded.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- STEP 4: UPLOAD TO CANVAS ---

if st.session_state.export_path and Path(st.session_state.export_path).exists():
    st.header("Step 4: Upload to Canvas")
    
    graded_count = len(st.session_state.review_grades)
    total_count = len(st.session_state.loaded_reviews)
    
    st.info(f"📤 Ready to upload to Canvas")
    st.write(f"- **{graded_count}** students with new grades")
    st.write(f"- **{total_count - graded_count}** students unchanged")
    st.write(f"- **{total_count}** total students in file")
    
    if st.button("🚀 Upload to Canvas", key="upload_button", type="primary"):
        try:
            from shared.grade_uploader import upload_all_from_xlsx
            
            with st.spinner("Uploading to Canvas..."):
                course_id = st.session_state.selected_course_id
                
                successes, failures, failure_details = upload_all_from_xlsx(
                    canvas_url,
                    canvas_token,
                    course_id,
                    int(assignment_id),
                    str(st.session_state.export_path)
                )
                
                st.success(f"✓ Successfully uploaded {successes} grades!")
                
                if failures > 0:
                    st.warning(f"⚠️ {failures} uploads failed:")
                    for student, error in failure_details:
                        st.error(f"- {student}: {error}")
                
        except Exception as e:
            st.error(f"Upload error: {e}")
            import traceback
            st.error(traceback.format_exc())

# Help
st.divider()
st.info("💡 **Workflow:** Download → Select Students → Grade → Upload | Only selected students get new grades")