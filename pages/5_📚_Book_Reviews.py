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
from assignment_handlers.generic_essay_handler import GenericEssayHandler
from shared.rubric_manager import RubricManager
from shared.exam_export import export_book_reviews_to_excel
from shared.config_loader import get_config
from shared.credentials import load_canvas_credentials, load_llm_keys
from shared.llm_provider import make_llm

st.set_page_config(page_title="Book Review Grader", page_icon="📚", layout="wide")

st.title("📚 Book Review Grading: 1984")

# ── Session State Init ────────────────────────────────────────────────────────
if "review_grades" not in st.session_state:
    st.session_state.review_grades = {}

if "loaded_reviews" not in st.session_state:
    st.session_state.loaded_reviews = []

if "download_metadata" not in st.session_state:
    st.session_state.download_metadata = {}

if "export_path" not in st.session_state:
    st.session_state.export_path = None

# FIX: selected_students stored as a set for stable checkbox state
if "selected_students" not in st.session_state:
    st.session_state.selected_students = set()

if "config" not in st.session_state:
    try:
        st.session_state.config = get_config()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        st.info("Please check config/config.json")
        st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")

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

    assignment_id = st.text_input("Canvas Assignment ID")

    st.subheader("📋 Rubric Selection")

    if "rubric_manager" not in st.session_state:
        st.session_state.rubric_manager = RubricManager()
    if "current_rubric" not in st.session_state:
        st.session_state.current_rubric = None
    if "rubric_loaded" not in st.session_state:
        st.session_state.rubric_loaded = False

    rubric_tab1, rubric_tab2, rubric_tab3 = st.tabs(["🔄 Load from Canvas", "💾 Load Cached", "📝 Custom Rubric"])

    with rubric_tab1:
        if st.button("📥 Load Rubric from Canvas", key="load_rubric_button"):
            if not assignment_id:
                st.error("Please enter an Assignment ID first")
            else:
                with st.spinner("Loading rubric from Canvas..."):
                    try:
                        course_id = st.session_state.selected_course_id
                        rubric_data = st.session_state.rubric_manager.get_rubric_from_canvas(
                            course_id, assignment_id, is_discussion=False, force_refresh=True
                        )
                        if rubric_data:
                            st.session_state.current_rubric = rubric_data
                            st.session_state.rubric_loaded = True
                            st.success(f"✓ Loaded rubric: {st.session_state.rubric_manager.get_rubric_summary(rubric_data)}")
                        else:
                            st.error("Could not retrieve rubric from Canvas")
                    except Exception as e:
                        st.error(f"Error loading rubric: {e}")
                        import traceback
                        st.error(traceback.format_exc())

    with rubric_tab2:
        cached_rubrics = st.session_state.rubric_manager.list_cached_rubrics()
        if cached_rubrics:
            rubric_options = {r['summary']: r['cache_key'] for r in cached_rubrics}
            selected_cache_key = st.selectbox("Select cached rubric:", list(rubric_options.keys()))
            if st.button("📥 Load Selected Rubric"):
                cache_key = rubric_options[selected_cache_key]
                rubric_data = st.session_state.rubric_manager.load_rubric_from_cache(cache_key)
                if rubric_data:
                    st.session_state.current_rubric = rubric_data
                    st.session_state.rubric_loaded = True
                    st.success(f"✓ Loaded cached rubric: {selected_cache_key}")
                else:
                    st.error("Could not load selected rubric")
        else:
            st.info("No cached rubrics found")

    with rubric_tab3:
        st.info("Custom rubric creation coming soon...")

    if st.session_state.rubric_loaded and st.session_state.current_rubric:
        rubric_summary = st.session_state.rubric_manager.get_rubric_summary(st.session_state.current_rubric)
        st.success(f"📋 Current Rubric: {rubric_summary}")
    else:
        st.warning("⚠️ No rubric loaded. Please load a rubric before grading.")

    st.divider()
    from shared.model_catalog import list_anthropic_models
    _default_model = config.get_default_model()
    _model_options = list_anthropic_models(load_llm_keys().get("anthropic"), _default_model) + ["gpt-4o"]
    _default_index = _model_options.index(_default_model) if _default_model in _model_options else 0
    model_choice = st.selectbox("LLM Model", _model_options, index=_default_index)

    score_multiplier = st.slider("Score Multiplier (Leniency)", 1.0, 1.3, 1.05, 0.05)
    st.caption(f"Scores will be boosted by {(score_multiplier - 1.0) * 100:.0f}%")

# ── Step 1: Download ──────────────────────────────────────────────────────────
st.header("Step 1: Download Submissions from Canvas")

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
                    st.session_state.review_grades = {}
                    st.session_state.export_path = None
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

                    st.session_state.review_grades = {}
                    st.session_state.export_path = None
                    with st.spinner("Loading submissions..."):
                        submissions = load_submissions_from_folder("./submissions")

                        if submissions:
                            matched = 0
                            for sub in submissions:
                                user_id = sub['user_id']
                                meta_entry = metadata.get(user_id) or metadata.get(str(user_id))
                                if meta_entry and 'name' in meta_entry:
                                    sub['name'] = meta_entry['name']
                                    matched += 1

                            # Deduplicate by user_id, keeping the most recently modified file
                            import re
                            seen = {}
                            seen_mtime = {}
                            for sub in submissions:
                                uid = sub['user_id']
                                # Find the file this submission came from
                                matching = list(Path("./submissions").glob(f"*{uid}*"))
                                mtime = max((f.stat().st_mtime for f in matching), default=0)
                                if uid not in seen or mtime > seen_mtime[uid]:
                                    seen[uid] = sub
                                    seen_mtime[uid] = mtime
                            submissions = list(seen.values())        

                            st.session_state.loaded_reviews = submissions

                            # FIX: auto-select only students without an existing Canvas grade
                            st.session_state.selected_students = {
                                sub['user_id'] for sub in submissions
                                if not (
                                    metadata.get(str(sub['user_id'])) or
                                    metadata.get(sub['user_id']) or {}
                                ).get('current_score')
                            }
                            already_graded = len(submissions) - len(st.session_state.selected_students)
                            st.success(f"✓ Auto-loaded {len(submissions)} submissions (matched {matched} names)")
                            if already_graded:
                                st.info(f"ℹ️ {already_graded} student(s) already have Canvas grades and were deselected automatically")
                        else:
                            st.warning("Downloaded but could not load submissions")

                except Exception as e:
                    st.error(f"Error downloading: {e}")
                    import traceback
                    st.error(traceback.format_exc())

with col2:
    if st.button("📂 Load from Folder (Optional)", key="load_button"):
        try:
            with st.spinner("Loading submissions from ./submissions..."):
                submissions = load_submissions_from_folder("./submissions")

                if not submissions:
                    st.warning("⚠️ No submissions found in ./submissions directory")
                    st.info("Please download submissions first")
                else:
                    metadata = st.session_state.download_metadata
                    if metadata:
                        matched = 0
                        for sub in submissions:
                            user_id = sub['user_id']
                            meta_entry = metadata.get(user_id) or metadata.get(str(user_id))
                            if meta_entry and 'name' in meta_entry:
                                sub['name'] = meta_entry['name']
                                matched += 1
                        st.success(f"✓ Matched {matched}/{len(submissions)} names with Canvas metadata")

                    # Deduplicate by user_id, keeping the most recently modified file
                    import re
                    seen = {}
                    seen_mtime = {}
                    for sub in submissions:
                        uid = sub['user_id']
                        # Find the file this submission came from
                        matching = list(Path("./submissions").glob(f"*{uid}*"))
                        mtime = max((f.stat().st_mtime for f in matching), default=0)
                        if uid not in seen or mtime > seen_mtime[uid]:
                            seen[uid] = sub
                            seen_mtime[uid] = mtime
                    submissions = list(seen.values())
                    st.session_state.loaded_reviews = submissions
                    st.session_state.selected_students = {
                        sub['user_id'] for sub in submissions
                        if not (
                            metadata.get(str(sub['user_id'])) or
                            metadata.get(sub['user_id']) or {}
                        ).get('current_score')
                    }
                    st.success(f"✓ Loaded {len(submissions)} submissions")

        except Exception as e:
            st.error(f"Error loading: {e}")
            import traceback
            st.error(traceback.format_exc())

# ── Student Selection Table ───────────────────────────────────────────────────
st.divider()
if st.session_state.loaded_reviews:
    st.success(f"✅ {len(st.session_state.loaded_reviews)} submissions loaded")
    st.subheader("Select Students to Grade")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("✓ Select All"):
            st.session_state.selected_students = {
                sub['user_id'] for sub in st.session_state.loaded_reviews
            }
            st.rerun()
    with col2:
        if st.button("✗ Deselect All"):
            st.session_state.selected_students = set()
            st.rerun()

    st.write("**Students:**")

    metadata = st.session_state.download_metadata

    # FIX: render individual checkboxes with stable keys instead of data_editor
    # data_editor rebuilds on every interaction and resets the scroll position
    header_cols = st.columns([1, 4, 2, 2, 2])
    header_cols[0].markdown("**Select**")
    header_cols[1].markdown("**Student**")
    header_cols[2].markdown("**Canvas Grade**")
    header_cols[3].markdown("**Status**")
    header_cols[4].markdown("**Text Length**")

    for sub in st.session_state.loaded_reviews:
        user_id = sub['user_id']
        meta = metadata.get(str(user_id)) or metadata.get(user_id) or {}
        existing_score = meta.get('current_score')

        if user_id in st.session_state.review_grades:
            status = "✅ Graded this session"
        elif existing_score is not None:
            status = "✅ Already graded"
        else:
            status = "⏳ Not graded"

        canvas_grade = f"{existing_score}" if existing_score is not None else "—"
        text_len = f"{len(sub['text'])} chars"

        row_cols = st.columns([1, 4, 2, 2, 2])
        with row_cols[0]:
            # FIX: key is stable per student; checking session_state directly avoids
            # the re-render loop that was resetting checkboxes
            checked = st.checkbox(
                label="",
                value=(user_id in st.session_state.selected_students),
                key=f"chk_{user_id}",
                label_visibility="collapsed"
            )
            if checked:
                st.session_state.selected_students.add(user_id)
            else:
                st.session_state.selected_students.discard(user_id)

        row_cols[1].write(sub['name'])
        row_cols[2].write(canvas_grade)
        row_cols[3].write(status)
        row_cols[4].write(text_len)

    selected_count = len(st.session_state.selected_students)
    st.info(f"📌 Selected {selected_count}/{len(st.session_state.loaded_reviews)} students for grading")

else:
    st.info("⬆️ Download submissions to begin")

# ── Step 2: Grade ─────────────────────────────────────────────────────────────
if st.session_state.loaded_reviews and st.session_state.selected_students:
    st.header("Step 2: Grade with AI")

    selected_count = len(st.session_state.selected_students)
    st.info(f"📚 Ready to grade {selected_count} selected students")

    button_label = (
        f"🤖 Grade Selected Students ({selected_count})"
        if selected_count < len(st.session_state.loaded_reviews)
        else "🤖 Grade All Students"
    )

    if st.button(button_label, key="start_grading_button", type="primary"):
        # Create LLM client
        try:
            llm_keys = load_llm_keys()

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

            if not st.session_state.rubric_loaded or not st.session_state.current_rubric:
                st.error("❌ No rubric loaded. Please load a rubric before grading.")
                st.stop()

            handler = GenericEssayHandler(llm_client, st.session_state.rubric_manager, model=model_choice)

            if not handler.load_rubric(st.session_state.current_rubric):
                st.error("❌ Failed to load rubric into grading handler")
                st.stop()

            st.success(f"✓ LLM client initialized ({provider})")
            st.success(f"✓ Using rubric: {handler.get_current_rubric_summary()}")

        except Exception as e:
            st.error(f"Error creating LLM client: {e}")
            import traceback
            st.error(traceback.format_exc())
            st.stop()

        selected_submissions = [
            sub for sub in st.session_state.loaded_reviews
            if sub['user_id'] in st.session_state.selected_students
        ]

        # Track only what's graded in THIS button press
        newly_graded_ids = set()

        progress_bar = st.progress(0)
        status_text = st.empty()
        errors = []
        total = len(selected_submissions)

        # FIX: try/except is INSIDE the for loop so every student gets graded
        for i, sub in enumerate(selected_submissions):
            status_text.text(f"Grading {i+1}/{total}: {sub['name']}...")

            try:
                result = handler.grade_essay(
                    student_name=sub['name'],
                    submission_text=sub['text'],
                    user_id=sub['user_id']
                )

                if 'error' in result:
                    errors.append(f"{sub['name']}: {result.get('error', 'Unknown error')}")
                    logger.error(f"Grading error for {sub['name']}: {result.get('error')}")

                raw_score = result['score']

                st.session_state.review_grades[sub['user_id']] = {
                    "ID": sub['user_id'],
                    "Student": sub['name'],
                    "Raw Score": raw_score,
                    "Final Score": raw_score,
                    "Feedback": result['feedback'],
                    "Breakdown": str(result.get('sections', {}))
                }
                newly_graded_ids.add(sub['user_id'])

            except Exception as e:
                error_msg = f"{sub['name']}: {str(e)}"
                errors.append(error_msg)
                logger.exception(f"Exception grading {sub['name']}")

                st.session_state.review_grades[sub['user_id']] = {
                    "ID": sub['user_id'],
                    "Student": sub['name'],
                    "Raw Score": 0,
                    "Final Score": 0,
                    "Feedback": f"Error during grading: {str(e)}",
                    "Breakdown": "{}"
                }
                # Don't add to newly_graded_ids on error — don't upload failed grades

            progress_bar.progress((i + 1) / total)

        status_text.text("Grading complete!")

        success_count = len(newly_graded_ids)
        st.success(f"🎉 Grading Complete! {success_count}/{total} successfully graded")

        if errors:
            with st.expander(f"⚠️ {len(errors)} Errors Occurred"):
                for error in errors:
                    st.error(error)

        if success_count > 0:
            successful_grades = [
                st.session_state.review_grades[uid]['Final Score']
                for uid in newly_graded_ids
            ]
            avg_score = sum(successful_grades) / len(successful_grades)

            display_total = 100
            if st.session_state.rubric_loaded and st.session_state.current_rubric:
                display_total = st.session_state.current_rubric.get('total_points', 100)

            st.info("📊 Grading Summary:")
            st.write(f"- Successfully graded: {success_count}/{total}")
            st.write(f"- Average score: {avg_score:.1f}/{display_total}")
            st.write(f"- Score multiplier: {score_multiplier}x ({(score_multiplier-1)*100:.0f}% boost)")

        # AUTO-EXPORT — only newly graded students get Upload?: yes
        with st.spinner("Saving to Excel..."):
            try:
                export_grades = []

                for sub in st.session_state.loaded_reviews:
                    user_id = sub['user_id']
                    if user_id in newly_graded_ids:
                        export_grades.append(st.session_state.review_grades[user_id])
                    else:
                        export_grades.append({
                            "ID": user_id,
                            "Student": sub['name'],
                            "Raw Score": 0,
                            "Final Score": 0,
                            "Feedback": "[Not graded in this session]",
                            "Breakdown": "{}"
                        })

                output_path = Path("./submissions") / "book_reviews_graded.xlsx"

                total_points = 100.0
                if st.session_state.rubric_loaded and st.session_state.current_rubric:
                    total_points = st.session_state.current_rubric.get('total_points', 100.0)

                export_book_reviews_to_excel(export_grades, output_path, total_points)
                st.session_state.export_path = output_path
                st.success(f"✓ Auto-saved to {output_path}")
                st.info(f"📝 {len(newly_graded_ids)} newly graded students marked for upload")

            except Exception as e:
                st.error(f"Error auto-saving Excel: {e}")

elif st.session_state.loaded_reviews and not st.session_state.selected_students:
    st.warning("⚠️ No students selected - Please select students to grade")
else:
    st.info("⚠️ No submissions loaded - Please download submissions first")

# ── Step 3: Review Results ────────────────────────────────────────────────────
if st.session_state.review_grades:
    st.header("Step 3: Review Graded Results")

    graded_count = len(st.session_state.review_grades)
    success_count = len([g for g in st.session_state.review_grades.values() if g['Final Score'] > 0])
    st.success(f"✅ {success_count}/{graded_count} reviews graded successfully")

    df = pd.DataFrame(list(st.session_state.review_grades.values()))
    st.dataframe(df[['Student', 'Raw Score', 'Final Score', 'Feedback']], use_container_width=True)

    if st.session_state.export_path and Path(st.session_state.export_path).exists():
        total_in_file = len(st.session_state.loaded_reviews)
        with open(st.session_state.export_path, "rb") as f:
            st.download_button(
                label=f"⬇️ Download Excel File ({total_in_file} total students, {graded_count} newly graded)",
                data=f,
                file_name="book_reviews_graded.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ── Step 4: Upload to Canvas ──────────────────────────────────────────────────
if st.session_state.export_path and Path(st.session_state.export_path).exists():
    st.header("Step 4: Upload to Canvas")

    graded_count = len(st.session_state.review_grades)
    total_count = len(st.session_state.loaded_reviews)

    st.info("📤 Ready to upload to Canvas")
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
                    str(st.session_state.export_path),
                    respect_upload_flag=True
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

# ── Help ──────────────────────────────────────────────────────────────────────
st.divider()
st.info("💡 **Workflow:** Download → Select Students → Grade → Upload | Only selected students get new grades")