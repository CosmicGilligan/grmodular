# assignment_handlers/generic_essay_handler.py
import json
import logging
from typing import Dict, List, Optional
from shared.llm_provider import LLMBase
from shared.rubric_manager import RubricManager

logger = logging.getLogger(__name__)


class GenericEssayHandler:
    """
    Generic handler for grading essays using external rubrics
    Can handle any essay assignment by loading rubrics from Canvas or using custom rubrics
    """
    
    def __init__(self, llm_client: LLMBase = None, rubric_manager: RubricManager = None):
        """
        Initialize the handler with an LLM client and rubric manager
        
        Args:
            llm_client: LLM client for grading (from make_llm())
            rubric_manager: Rubric manager for loading rubrics
        """
        if llm_client is None:
            raise ValueError("LLM client is required for grading")
            
        self.llm = llm_client
        self.rubric_manager = rubric_manager or RubricManager()
        self.current_rubric = None
        self.system_prompt_template = self._get_base_system_prompt()
    
    def load_rubric(self, rubric_data: Dict) -> bool:
        """
        Load a rubric for grading
        
        Args:
            rubric_data: Rubric data dictionary
            
        Returns:
            True if rubric loaded successfully, False otherwise
        """
        try:
            if not rubric_data or 'rubric_criteria' not in rubric_data:
                logger.error("Invalid rubric data format")
                return False
                
            self.current_rubric = rubric_data
            logger.info(f"Loaded rubric with {len(rubric_data['rubric_criteria'])} criteria")
            return True
            
        except Exception as e:
            logger.error(f"Error loading rubric: {e}")
            return False
    
    def load_rubric_from_canvas(self, course_id: str, assignment_id: str, 
                               is_discussion: bool = False, 
                               force_refresh: bool = False) -> bool:
        """
        Load a rubric directly from Canvas
        
        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID
            is_discussion: Whether this is a discussion rubric
            force_refresh: Force refresh from Canvas (ignore cache)
            
        Returns:
            True if rubric loaded successfully, False otherwise
        """
        try:
            rubric_data = self.rubric_manager.get_rubric_from_canvas(
                course_id, assignment_id, is_discussion, force_refresh
            )
            
            if rubric_data:
                return self.load_rubric(rubric_data)
            else:
                logger.error(f"Could not retrieve rubric for assignment {assignment_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading rubric from Canvas: {e}")
            return False
    
    def grade_essay(self, student_name: str, submission_text: str, user_id: str = None) -> Dict:
        """
        Grades an essay submission using the loaded rubric
        
        Args:
            student_name: Name of the student
            submission_text: The essay text
            user_id: Canvas user ID (for logging)
            
        Returns:
            Dict with score, feedback, and sections breakdown
        """
        # Validate input
        if not submission_text or len(submission_text.strip()) < 100:
            logger.warning(f"Submission too short for {student_name}: {len(submission_text)} chars")
            return {
                "score": 0,
                "feedback": "Submission appears empty or too short to grade (minimum 100 characters required).",
                "sections": {}
            }
        
        # Check if rubric is loaded
        if not self.current_rubric:
            logger.error(f"No rubric loaded for grading {student_name}")
            return {
                "score": 0,
                "feedback": "Error: No grading rubric loaded. Please load a rubric first.",
                "sections": {}
            }
        
        # Format the rubric for the system prompt
        rubric_text = self.rubric_manager.format_rubric_for_system_prompt(self.current_rubric)
        
        # Construct the user message
        user_message = f"""Please grade the following essay submission.

STUDENT NAME: {student_name}

SUBMISSION:
{submission_text}

Remember to return ONLY valid JSON with no markdown formatting."""
        
        try:
            # Build the complete system prompt
            system_prompt = self.system_prompt_template.replace("{{RUBRIC}}", rubric_text)
            
            # System message goes in the messages array
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            logger.info(f"Grading {student_name}...")
            
            response = self.llm.generate(
                model="claude-sonnet-4-20250514",
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )
            
            logger.info(f"Got response ({len(response)} chars)")
            
            # Clean response (remove markdown code blocks if present)
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            try:
                result = json.loads(cleaned_response)
                logger.info(f"Parsed JSON successfully")
            except json.JSONDecodeError as e:
                logger.error(f"JSON Error: {e}")
                logger.error(f"Response was: {cleaned_response[:300]}")
                return {
                    "score": 0,
                    "feedback": f"Error parsing AI response. Please contact instructor.",
                    "sections": {},
                    "error": f"JSON decode error: {str(e)}"
                }
            
            # Validate structure
            if 'sections' not in result or 'overall_feedback' not in result:
                logger.error(f"Missing keys. Found: {list(result.keys())}")
                return {
                    "score": 0,
                    "feedback": "Error: AI returned invalid structure.",
                    "sections": {},
                    "error": "Missing required keys in response"
                }
            
            # Calculate score
            try:
                total_score = sum(item['score'] for item in result['sections'].values())
                logger.info(f"Calculated score: {total_score}/{self.current_rubric.get('total_points', 100)}")
            except (KeyError, TypeError) as e:
                logger.error(f"Score calculation error: {e}")
                logger.error(f"Sections: {result.get('sections', {})}")
                return {
                    "score": 0,
                    "feedback": f"Error calculating score from AI response.",
                    "sections": result.get('sections', {}),
                    "error": f"Score calculation error: {str(e)}"
                }
            
            return {
                "score": total_score,
                "feedback": result['overall_feedback'],
                "sections": result['sections']
            }
            
        except Exception as e:
            logger.exception(f"Unexpected error grading {student_name}")
            return {
                "score": 0,
                "feedback": f"Error during AI grading: {str(e)}",
                "sections": {},
                "error": str(e)
            }
    
    def _get_base_system_prompt(self) -> str:
        """
        Returns the base system prompt template for grading essays
        The {{RUBRIC}} placeholder will be replaced with the actual rubric
        """
        return """You are an expert professor grading a college-level essay.

{{RUBRIC}}

GRADING INSTRUCTIONS:
- Evaluate the essay based on the rubric criteria above
- Be encouraging but honest. This is for college students.
- If they miss a section completely, give 0 for that section.
- If the analysis is shallow, give partial credit.
- Reward effort and engagement with the text.
- Ignore minor grammar issues unless they impede meaning.
- Be specific in your feedback - reference what they wrote.

OUTPUT FORMAT:
You must return ONLY valid JSON. No markdown code blocks, no extra text.
{
    "sections": {
        "criterion_1_key": {"score": X, "max": Y, "comment": "Brief comment"},
        "criterion_2_key": {"score": X, "max": Y, "comment": "Brief comment"},
        // ... one entry per rubric criterion
    },
    "overall_feedback": "A paragraph of constructive feedback addressing the student directly."
}

Use lowercase keys without spaces for the sections (e.g., 'thesis_statement', 'evidence_quality').
The 'max' value for each section should match the points specified in the rubric."""
    
    def get_current_rubric_summary(self) -> str:
        """
        Get a summary of the currently loaded rubric
        
        Returns:
            Summary string
        """
        if self.current_rubric:
            return self.rubric_manager.get_rubric_summary(self.current_rubric)
        else:
            return "No rubric loaded"
    
    def get_current_rubric_details(self) -> Optional[Dict]:
        """
        Get detailed information about the currently loaded rubric
        
        Returns:
            Rubric data dictionary, or None if no rubric loaded
        """
        return self.current_rubric