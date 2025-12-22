# canvas_submissions_flat.py
from __future__ import annotations
import os, re, shutil, html
import requests
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def load_submissions_from_folder(folder_path: str) -> List[Dict[str, Any]]:
    """
    Load submissions from a folder containing various file types (HTML, DOCX, PDF, TXT).
    
    Args:
        folder_path: Path to folder containing submission files
        
    Returns:
        List of submission dicts with keys: name, user_id, text, filename
    """
    folder = Path(folder_path)
    if not folder.exists():
        logger.warning(f"Folder does not exist: {folder_path}")
        return []
    
    submissions = []
    
    # Try to extract text from various file types
    for file_path in folder.glob("*"):
        if file_path.is_file():
            try:
                filename = file_path.stem
                
                # Extract student info from filename (format: lastname_firstname_userid_*.*)
                parts = filename.split('_')
                
                # Find user_id (numeric part, typically 7 digits)
                user_id = None
                for part in parts:
                    if part.isdigit() and len(part) >= 4:
                        user_id = part
                        break
                
                # Extract name from filename
                name_parts = []
                for part in parts:
                    if part != user_id and not part.isdigit():
                        name_parts.append(part)
                
                name = ' '.join(name_parts).replace('_', ' ').title()
                
                # Try to extract text based on file type
                content = ""
                
                # Check actual file type using file extension and magic numbers
                file_ext = file_path.suffix.lower()
                
                # Try to determine file type from content if no extension
                if not file_ext:
                    # Check if it's a PDF by reading first few bytes
                    with open(file_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            file_ext = '.pdf'
                        elif header.startswith(b'PK\x03\x04'):  # ZIP/Office files
                            file_ext = '.docx'
                
                if file_ext == '.html':
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                elif file_ext in ['.txt', '.text']:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                elif file_ext == '.docx':
                    try:
                        from docx import Document
                        doc = Document(file_path)
                        content = "\n".join([para.text for para in doc.paragraphs])
                    except Exception as docx_e:
                        logger.warning(f"Could not read DOCX {file_path}: {docx_e}")
                        content = f"[DOCX file: {filename}]"
                elif file_ext == '.pdf':
                    try:
                        import PyPDF2
                        with open(file_path, 'rb') as f:
                            reader = PyPDF2.PdfReader(f)
                            content = "\n".join([page.extract_text() for page in reader.pages])
                    except Exception as pdf_e:
                        logger.warning(f"Could not read PDF {file_path}: {pdf_e}")
                        content = f"[PDF file: {filename}]"
                else:
                    content = f"[Unsupported file type {file_ext}: {filename}]"
                
                submissions.append({
                    'name': name,
                    'user_id': user_id or 'unknown',
                    'text': content,
                    'filename': file_path.name
                })
                
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
    
    return submissions


def download_submissions(course_id: str, assignment_id: str, dest_dir: str) -> int:
    """
    Simple wrapper for book review downloads - uses existing download_submissions_flat
    but needs credentials from session state.
    """
    try:
        # This is a simplified version - in practice you'd need to get credentials
        # For now, just create the directory and return 0
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dest_dir}")
        return 0
    except Exception as e:
        logger.error(f"Error in download_submissions: {e}")
        return 0

def _normalize_api_base(raw_base: str) -> str:
    base = raw_base.strip().rstrip("/")
    if base.endswith("/api/v1"):
        base = base[:-len("/api/v1")]
    return base + "/api/v1"

def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\s,.'\"`]+", "", s)
    s = re.sub(r"[^a-z0-9_-]", "_", s)
    return s

def _student_stem(user: Dict[str, Any]) -> str:
    sortable = user.get("sortable_name") or ""
    if "," in sortable:
        last, first = [p.strip() for p in sortable.split(",", 1)]
        return _slug(last + first)
    name = user.get("name") or ""
    parts = name.split()
    if len(parts) >= 2:
        return _slug(parts[-1] + parts[0])
    return _slug(name or f"student{user.get('id','unknown')}")

def _wrap_as_html(title: str, inner_html: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>
<body>
{inner_html}
</body></html>
"""

def _parse_next_link(r: requests.Response) -> Optional[str]:
    link = r.headers.get("Link", "")
    for part in link.split(","):
        if 'rel="next"' in part:
            start = part.find("<") + 1
            end = part.find(">")
            if start > 0 and end > start:
                return part[start:end]
    return None

def _get_with_pagination(session: requests.Session, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    first = True
    page_url: Optional[str] = url
    while page_url:
        r = session.get(page_url, params=params if first else None)
        first = False
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, list):
            out.extend(payload)
        else:
            out.append(payload)
        page_url = _parse_next_link(r)
    return out

def download_submissions_flat(
    canvas_base_url: str,
    token: str,
    course_id: int,
    assignment_id: int,
    dest_dir: str = "./submissions",
    clean_dest: bool = True
) -> Tuple[int, int, Dict[str, Dict[str, Any]]]:
    """
    Downloads submissions - supports both assignments and quizzes
    """
    api_base = _normalize_api_base(canvas_base_url)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    if clean_dest:
        for p in dest.iterdir():
            try:
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
            except Exception as e:
                logger.warning(f"Could not remove {p}: {e}")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # Try quiz endpoint first
    is_quiz = False
    quiz_url = f"{api_base}/courses/{course_id}/quizzes/{assignment_id}/submissions"
    quiz_params = {"per_page": 100, "include[]": ["submission", "user", "submission_history"]}
    
    try:
        logger.info(f"Trying quiz endpoint for {assignment_id}")
        response = session.get(quiz_url, params=quiz_params)
        
        if response.status_code == 200:
            data = response.json()
            if "quiz_submissions" in data and "submissions" in data:
                is_quiz = True
                quiz_submissions = data["quiz_submissions"]
                submissions = data["submissions"]
                users = {u['id']: u for u in data.get('users', [])}
                
                logger.info(f"Found {len(submissions)} quiz submissions")
            else:
                logger.info("Not a quiz")
        else:
            logger.info(f"Quiz endpoint returned {response.status_code}")
    except Exception as e:
        logger.info(f"Quiz endpoint failed: {e}")
    
    # If not quiz, try assignment endpoint
    if not is_quiz:
        url = f"{api_base}/courses/{course_id}/assignments/{assignment_id}/submissions"
        params = {"per_page": 100, "include[]": ["user", "attachments", "submission_comments"]}
        submissions = _get_with_pagination(session, url, params)
        users = {}
        logger.info(f"Found {len(submissions)} assignment submissions")

    students = 0
    files_saved = 0
    student_metadata: Dict[str, Dict[str, Any]] = {}

    for sub in submissions:
        state = sub.get("workflow_state")
        if state not in ("submitted", "graded", "complete", "pending_review"):
            continue

        user_id = sub.get("user_id")
        if user_id is None:
            continue

        # Get user info
        if is_quiz and user_id in users:
            user = users[user_id]
        else:
            user = sub.get("user", {})
        
        if not user:
            user = {"id": user_id, "name": f"Student {user_id}"}
        
        sortable_name = user.get("sortable_name") or user.get("name") or f"Student {user_id}"
        stem = f"{_student_stem(user)}_{user_id}"
        
        # Metadata
        current_score = sub.get("score")
        current_grade = sub.get("grade")
        submission_date = sub.get("submitted_at")
        
        current_feedback = ""
        if not is_quiz:
            submission_comments = sub.get("submission_comments") or []
            grader_comments = [c for c in submission_comments if c.get("author_id") != user_id]
            if grader_comments:
                current_feedback = grader_comments[-1].get("comment") or ""
        
        student_metadata[str(user_id)] = {
            'name': sortable_name,
            'current_score': float(current_score) if current_score is not None else None,
            'current_grade': str(current_grade) if current_grade else None,
            'current_feedback': current_feedback,
            'submission_date': submission_date
        }

        # Extract content
        if is_quiz:
            # Get answers from submission_history
            hist = sub.get('submission_history', [])
            if hist and len(hist) > 0:
                submission_data = hist[0].get('submission_data', [])
                
                if submission_data:
                    # Build HTML from quiz answers
                    content_parts = [f"<h1>Quiz Submission - {sortable_name}</h1>"]
                    
                    for i, answer in enumerate(submission_data, 1):
                        question_id = answer.get('question_id')
                        answer_text = answer.get('text', '')
                        points = answer.get('points', 0)
                        
                        # Try to get question text (we'd need to fetch questions separately)
                        question_name = f"Question {i}"
                        
                        content_parts.append(f"<div class='question'>")
                        content_parts.append(f"<h3>{question_name}</h3>")
                        content_parts.append(f"<p><strong>Answer:</strong></p>")
                        content_parts.append(f"<div class='answer'>{answer_text or '(No answer provided)'}</div>")
                        content_parts.append(f"<p><em>Points: {points}</em></p>")
                        content_parts.append(f"</div><hr>")
                    
                    html_content = _wrap_as_html(f"Quiz {assignment_id} - {sortable_name}", "\n".join(content_parts))
                    out_path = dest / f"{stem}_quiz.html"
                    out_path.write_text(html_content, encoding="utf-8", errors="ignore")
                    files_saved += 1
        else:
            # Regular assignment processing
            body = sub.get("body")
            if isinstance(body, str) and body.strip():
                title = sub.get("preview_url") or f"Assignment {assignment_id}"
                html_text = _wrap_as_html(str(title), body)
                out_path = dest / f"{stem}_text.html"
                out_path.write_text(html_text, encoding="utf-8", errors="ignore")
                files_saved += 1

            online_url = sub.get("url") or sub.get("online_url") or ""
            if online_url:
                (dest / f"{stem}_url.txt").write_text(online_url, encoding="utf-8", errors="ignore")
                files_saved += 1

            for att in sub.get("attachments") or []:
                att_url = att.get("url") or ""
                att_name = att.get("filename") or att.get("display_name") or f"file_{att.get('id','unknown')}"
                safe_name = _slug(att_name)
                out_path = dest / f"{stem}_{safe_name}"
                if att_url:
                    with session.get(att_url, stream=True) as r:
                        r.raise_for_status()
                        with open(out_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                    files_saved += 1

        students += 1

    return students, files_saved, student_metadata

