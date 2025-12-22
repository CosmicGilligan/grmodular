# assignment_handlers/book_review_handler.py
import json
import logging
from shared.llm_provider import LLMBase

logger = logging.getLogger(__name__)


class BookReviewHandler:
    """
    Handler for grading book reviews of George Orwell's 1984
    """
    
    def __init__(self, llm_client: LLMBase = None):
        """
        Initialize the handler with an LLM client
        
        Args:
            llm_client: LLM client for grading (from make_llm())
        """
        if llm_client is None:
            raise ValueError("LLM client is required for grading")
        
        self.llm = llm_client
        self.system_prompt = self._get_system_prompt()

    def grade_review(self, student_name: str, submission_text: str, user_id: str = None):
        """
        Grades a single book review submission based on the 1984 rubric.
        
        Args:
            student_name: Name of the student
            submission_text: The book review text
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

        # Construct the user message
        user_message = f"""Please grade the following book review of Orwell's 1984.

STUDENT NAME: {student_name}

SUBMISSION:
{submission_text}

Remember to return ONLY valid JSON with no markdown formatting."""

        try:
            # System message goes in the messages array (your llm_provider extracts it)
            messages = [
                {"role": "system", "content": self.system_prompt},
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
                logger.info(f"Calculated score: {total_score}/100")
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

    def _get_system_prompt(self):
        """Returns the system prompt for grading 1984 book reviews"""
        return """You are an expert history professor grading a freshman-level book review of George Orwell's 1984.

ASSIGNMENT CONTEXT:
- Topic: 1984 – History, Memory, and Control
- Length: 3-4 pages
- Goal: Explain how Orwell's story illustrates the dangers of manipulated history.

GRADING RUBRIC (100 Points Total):
Evaluate the essay based on these 8 specific sections:

1. TITLE (5 pts): Is it focused? Does it highlight book & theme?
2. INTRODUCTION (10 pts): Mentions title/author? Explains relevance? States central question (erasing history)?
3. SUMMARY (15 pts): Concise plot summary? Mentions Winston's work, "Who controls the past...", and rewriting records?
4. AUTHOR'S MESSAGE (15 pts): Identifies message on memory/truth/power? Discusses manipulation as control?
5. STRUCTURE (10 pts): Comments on narrative build/Winston's perspective? Connects structure to theme?
6. HISTORICAL CONTEXT (20 pts): Connects to real history (propaganda/censorship)? Connects to present day? Answers: What lessons for preserving memory?
7. STRENGTHS/WEAKNESSES (10 pts): Insight vs limits of fiction.
8. CONCLUSION (15 pts): Summarizes warning. Answers: What safeguards are needed?

OUTPUT FORMAT:
You must return ONLY valid JSON. No markdown code blocks, no extra text.
{
    "sections": {
        "title": {"score": X, "max": 5, "comment": "Brief comment"},
        "intro": {"score": X, "max": 10, "comment": "Brief comment"},
        "summary": {"score": X, "max": 15, "comment": "Brief comment"},
        "message": {"score": X, "max": 15, "comment": "Brief comment"},
        "structure": {"score": X, "max": 10, "comment": "Brief comment"},
        "context": {"score": X, "max": 20, "comment": "Brief comment"},
        "critique": {"score": X, "max": 10, "comment": "Brief comment"},
        "conclusion": {"score": X, "max": 15, "comment": "Brief comment"}
    },
    "overall_feedback": "A paragraph of constructive feedback addressing the student directly."
}

GRADING STYLE:
- Be encouraging but honest. This is for Freshmen.
- If they miss a section completely, give 0 for that section.
- If the analysis is shallow, give partial credit (e.g., 12/20).
- Reward effort and engagement with the text.
- Ignore minor grammar issues unless they impede meaning.
- Be specific in your feedback - reference what they wrote."""