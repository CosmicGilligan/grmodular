import pandas as pd
from pathlib import Path
from typing import List, Dict

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