import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

def export_exam_to_excel(entry_list: List[List], metadata: dict, output_path: Path, total_points: float = 50.0) -> None:
    """
    Export exam results to Excel format matching Canvas structure.
    
    Args:
        entry_list: List of [student_name, submission_text, feedback]
        metadata: Dict mapping user_id to student info
        output_path: Path to save Excel file
        total_points: Total possible points
    """
    
    # Build reverse lookup: name -> user_id
    name_to_id = {}
    for user_id, info in metadata.items():
        name = info.get('name', '')
        name_to_id[name] = user_id
    
    rows = []
    for student_name, submission_text, feedback in entry_list:
        # Get user ID
        user_id = name_to_id.get(student_name, '')
        
        # Split name into first/last
        name_parts = student_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
        else:
            first_name = student_name
            last_name = ''
        
        # Extract score from feedback
        # Feedback format: "Score: 45.0/50.0\n\n..."
        import re
        score_match = re.search(r'Score:\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)', feedback)
        if score_match:
            score = float(score_match.group(1))
            max_score = float(score_match.group(2))
            # Format as "45.50/50.00 - <feedback>"
            grade_str = f"{score:.2f}/{max_score:.2f} - {feedback}"
        else:
            grade_str = feedback if feedback else f"0.00/{total_points:.2f}"
        
        rows.append({
            'Canvas User ID': user_id,
            'Student Last Name': last_name,
            'Student First Name': first_name,
            'Student Submission Text': submission_text[:500] + '...' if len(submission_text) > 500 else submission_text,
            'Grade': grade_str,
            'Upload?': 'yes'
        })
    
    # Create DataFrame and save
    df = pd.DataFrame(rows)
    
    # Create Excel writer with formatting
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Submissions', index=False)
        
        # Get the worksheet
        worksheet = writer.sheets['Submissions']
        
        # Adjust column widths
        worksheet.column_dimensions['A'].width = 15  # User ID
        worksheet.column_dimensions['B'].width = 20  # Last Name
        worksheet.column_dimensions['C'].width = 20  # First Name
        worksheet.column_dimensions['D'].width = 50  # Submission Text
        worksheet.column_dimensions['E'].width = 60  # Grade
        worksheet.column_dimensions['F'].width = 10  # Upload?
    
    print(f"✓ Exported {len(rows)} graded exams to {output_path}")


# UPDATE for shared/exam_export.py
# Replace or update the export_book_reviews_to_excel function

def export_book_reviews_to_excel(grades: List[Dict], output_path: Path) -> None:
    """
    Export book review grades to Excel format for Canvas upload.
    Handles selective grading - only uploads students with actual grades.
    
    Args:
        grades: List of grade dicts with ID, Student, Final Score, Feedback, Breakdown
        output_path: Path to save Excel file
    """
    import ast
    
    rows = []
    for grade in grades:
        # Skip students not graded in this session
        if grade.get('Feedback') == "[Not graded in this session]":
            # Don't include in Excel - they won't be uploaded
            continue
        
        # Format feedback with score and breakdown
        feedback_parts = [
            f"Score: {grade['Final Score']:.2f}/100.00",
            "",
            grade['Feedback']
        ]
        
        # Add section breakdown if available
        if grade.get('Breakdown'):
            feedback_parts.append("")
            feedback_parts.append("Section Breakdown:")
            try:
                breakdown = ast.literal_eval(grade['Breakdown']) if isinstance(grade['Breakdown'], str) else grade['Breakdown']
                for section, details in breakdown.items():
                    if isinstance(details, dict):
                        score = details.get('score', 0)
                        max_score = details.get('max', 0)
                        comment = details.get('comment', '')
                        feedback_parts.append(f"  {section.title()}: {score}/{max_score} - {comment}")
            except Exception as e:
                print(f"Warning: Could not parse breakdown for {grade.get('Student')}: {e}")
        
        full_feedback = '\n'.join(feedback_parts)
        
        # Parse student name
        student_name = grade['Student']
        last_name = ''
        first_name = ''
        
        if ',' in student_name:
            last_name, first_name = student_name.split(',', 1)
            last_name = last_name.strip()
            first_name = first_name.strip()
        else:
            first_name = student_name
            last_name = ''
        
        rows.append({
            'Canvas User ID': grade['ID'],
            'Student Last Name': last_name,
            'Student First Name': first_name,
            'Student Submission Text': '',
            'Grade': f"{grade['Final Score']:.2f}/100.00 - {full_feedback}",
            'Upload?': 'yes'
        })
    
    # Create DataFrame and save
    df = pd.DataFrame(rows)
    
    # Create Excel writer with formatting
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Submissions', index=False)
        
        # Get the worksheet
        worksheet = writer.sheets['Submissions']
        
        # Adjust column widths
        worksheet.column_dimensions['A'].width = 15  # User ID
        worksheet.column_dimensions['B'].width = 20  # Last Name
        worksheet.column_dimensions['C'].width = 20  # First Name
        worksheet.column_dimensions['D'].width = 50  # Submission Text (empty)
        worksheet.column_dimensions['E'].width = 80  # Grade (with feedback)
        worksheet.column_dimensions['F'].width = 10  # Upload?
    
    print(f"✓ Exported {len(rows)} graded book reviews to {output_path}")