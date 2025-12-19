import logging
logger = logging.getLogger(__name__)

"""
Exam Assignment Handler
Handles grading of exams where students answer 5 out of 10 questions
Includes score multiplier to adjust final scores while maintaining feedback quality
"""

from typing import Dict, List, Tuple, Optional
from assignment_handlers.base_handler import BaseAssignmentHandler


class ExamHandler(BaseAssignmentHandler):
    """
    Handler for exam assignments where students select 5 of 10 questions to answer.
    Grading policy: Grade up to 5 answered questions, regardless of which questions were answered.
    """
    
    def __init__(self, assignment_key: str, display_name: str, 
                 default_points: int, course_mapping: Dict[int, int],
                 canvas_assignment_id: Optional[int] = None,
                 total_points: Optional[int] = None,
                 rubric: Optional[List[Dict]] = None,
                 score_multiplier: float = 1.0,
                 original_entered_id: Optional[int] = None,
                 is_quiz: bool = False):
        """
        Initialize the exam handler
        
        Args:
            assignment_key: Internal key for this exam
            display_name: Human-readable exam name
            default_points: Default total points (should be 50)
            course_mapping: Mapping of course numbers
            canvas_assignment_id: Canvas assignment ID for this exam (used for uploading grades)
            total_points: Total points for this exam (overrides default_points)
            rubric: Canvas rubric if available
            score_multiplier: Multiplier to apply to each question score (e.g., 1.15 for 15% boost)
            original_entered_id: The original ID entered by user (quiz ID for quizzes, assignment ID for assignments)
            is_quiz: Whether this is a quiz (affects how submissions are downloaded)
        """
        super().__init__(assignment_key, display_name, default_points, course_mapping)
        
        # Exam-specific properties
        self.canvas_assignment_id = canvas_assignment_id
        self.total_points = total_points or default_points
        self.rubric = rubric or []
        self.score_multiplier = score_multiplier
        self.original_entered_id = original_entered_id or canvas_assignment_id
        self.is_quiz = is_quiz
        
        # Exam structure
        self.total_questions = 10
        self.questions_to_grade = 5
        self.points_per_question = 10
        
    def get_submission_download_id(self) -> int:
        """
        Get the correct ID to use for downloading submissions.
        For quizzes, this is the original quiz ID. For assignments, it's the assignment ID.
        """
        if self.is_quiz and self.original_entered_id:
            return self.original_entered_id
        return self.canvas_assignment_id
    
    def requires_module_selection(self) -> bool:
        """Exams don't require module selection"""
        return False
    
    def get_available_modules(self, base_course_number: int) -> List[str]:
        """Exams don't have modules"""
        return []
    
    def get_lecture_content(self, base_course_number: int, module_number: int = None) -> str:
        """
        Get lecture content for exam grading context.
        For exams, we use all course content from embeddings.
        
        Args:
            base_course_number: The base course number (109, 110, etc.)
            module_number: Not used for exams
            
        Returns:
            Instruction to use full course embeddings
        """
        return "Use all course content from embeddings to evaluate exam answers."
    
    def get_questions(self, base_course_number: int, module_number: int = None) -> str:
        """
        Get exam questions if available.
        
        Args:
            base_course_number: The base course number
            module_number: Not used for exams
            
        Returns:
            Exam questions string
        """
        return "Exam questions will be extracted from Canvas assignment."
    
    def get_prompt_string(self, base_course_number: int, module_number: int = None) -> str:
        """
        Get the complete prompt string for exam grading
        
        Args:
            base_course_number: The base course number
            module_number: Not used for exams
            
        Returns:
            Complete grading prompt
        """
        return f"""You are grading an exam for a course. 

EXAM STRUCTURE:
- Total questions available: {self.total_questions}
- Questions student must answer: {self.questions_to_grade}
- Points per question: {self.points_per_question}
- Maximum total score: {self.total_points}

GRADING POLICY:
- Grade up to {self.questions_to_grade} answered questions
- Each graded answer can receive 0-{self.points_per_question} points
- Use course content from embeddings to evaluate answer quality and accuracy

Evaluate each answer based on:
1. Accuracy and completeness
2. Understanding of course concepts
3. Use of relevant examples or evidence
4. Clarity of explanation

Provide specific, constructive feedback for each graded answer.
"""
    
    def parse_exam_submission(self, submission_text: str) -> Tuple[List[Dict[str, str]], List[int]]:
        """
        Parse an exam submission to identify which questions were answered.
        
        Args:
            submission_text: The raw submission text
            
        Returns:
            Tuple of (list of answered questions, list of question numbers)
            Each question dict has 'question_number' and 'answer' keys
        """
        answered_questions = []
        question_numbers = []
        
        # Look for common patterns like "Question 1:", "Q1:", "1.", etc.
        import re
        
        # Split by question markers
        pattern = r'(?:Question\s+(\d+)|Q\s*(\d+)|^(\d+)\.)'
        
        lines = submission_text.split('\n')
        current_q_num = None
        current_answer = []
        
        for line in lines:
            match = re.search(pattern, line, re.IGNORECASE | re.MULTILINE)
            if match:
                # Save previous question if exists
                if current_q_num is not None and current_answer:
                    answered_questions.append({
                        'question_number': current_q_num,
                        'answer': '\n'.join(current_answer).strip()
                    })
                    question_numbers.append(current_q_num)
                
                # Start new question
                current_q_num = int(match.group(1) or match.group(2) or match.group(3))
                current_answer = [line]
            elif current_q_num is not None:
                current_answer.append(line)
        
        # Don't forget the last question
        if current_q_num is not None and current_answer:
            answered_questions.append({
                'question_number': current_q_num,
                'answer': '\n'.join(current_answer).strip()
            })
            question_numbers.append(current_q_num)
        
        return answered_questions, question_numbers
    
    def grade_exam_submission(self, submission_text: str, llm_client, course_embeddings, model: str) -> Dict[str, any]:
        """
        Grade an exam submission according to the exam policy.
        Grades up to 5 answered questions, regardless of which questions were answered.
        Skips empty answers without providing feedback.
        
        Args:
            submission_text: The student's submission
            llm_client: LLM client for grading
            course_embeddings: Course embeddings for context
            model: Model name to use
            
        Returns:
            Dict with grading results including total score and per-question feedback
        """
        # Parse submission to find answered questions
        answered_questions, question_numbers = self.parse_exam_submission(submission_text)
        
        graded_results = []
        total_score = 0
        questions_graded = 0
        
        # Grade up to 5 answered questions (regardless of which questions they answered)
        for question_data in answered_questions:
            # Stop if we've already graded 5 questions
            if questions_graded >= self.questions_to_grade:
                break
            
            q_num = question_data['question_number']
            answer = question_data['answer']
            
            # Skip if no actual answer (empty or just whitespace or too short)
            if not answer or answer.strip() == "" or len(answer.strip()) < 20 or "(No answer provided)" in answer:
                # Don't add to results - just skip
                continue
            
            # Grade this answer
            score, feedback = self._grade_single_answer(
                answer, q_num, llm_client, course_embeddings, model
            )
            
            graded_results.append({
                'question_number': q_num,
                'score': score,
                'max_score': self.points_per_question,
                'feedback': feedback,
                'graded': True
            })
            total_score += score
            questions_graded += 1
        
        return {
            'total_score': round(total_score, 2),  # Round to 2 decimal places
            'max_score': self.total_points,
            'questions_graded': questions_graded,
            'question_results': graded_results,
            'submission_text': submission_text
        }
    
    def _grade_single_answer(self, answer: str, question_num: int, 
                            llm_client, course_embeddings, model: str) -> Tuple[float, str]:
        """
        Grade a single exam answer using LLM and course embeddings.
        
        Args:
            answer: The student's answer text
            question_num: The question number
            llm_client: LLM client (from llm_provider.py)
            course_embeddings: Course document processor with embeddings
            model: Model name to use
            
        Returns:
            Tuple of (score, feedback)
        """
        try:
            # Search for relevant course content
            relevant_docs = []
            if course_embeddings and hasattr(course_embeddings, 'search_documents'):
                search_results = course_embeddings.search_documents(
                    answer, 
                    top_k=5
                )
                # Handle different search result formats
                if isinstance(search_results, str):
                    relevant_docs = [search_results]
                elif isinstance(search_results, list) and search_results:
                    relevant_docs = [doc.get('text', str(doc)) if isinstance(doc, dict) else str(doc) for doc in search_results]
                else:
                    relevant_docs = []
            
            # Construct grading prompt
            context_str = "\n\n".join(relevant_docs) if relevant_docs else "No specific course content found."
            
            grading_prompt = f"""You are grading an exam answer for a FRESHMAN-LEVEL college course.

QUESTION {question_num}:
Evaluate the student's answer based on the course content provided.

COURSE CONTENT (for reference):
{context_str}

STUDENT'S ANSWER:
{answer}

GRADING GUIDELINES FOR FRESHMEN:
This is an introductory-level course. Grade with appropriate expectations:

SCORING RUBRIC:
9-10 points: Excellent - demonstrates strong understanding, accurate, well-explained, uses examples
7-8 points: Good - shows solid understanding, mostly accurate, covers main points
5-6 points: Satisfactory - demonstrates basic understanding, some gaps but shows effort
3-4 points: Needs improvement - shows some effort but significant gaps or misconceptions
1-2 points: Minimal - very limited understanding or minimal effort
0 points: No answer or completely off-topic

IMPORTANT:
- Award PARTIAL CREDIT generously for students who demonstrate effort and basic understanding
- Don't penalize heavily for minor wording issues if the core concept is understood
- Reward students who show they engaged with the material, even if not perfect
- Consider this is likely one of their first college exams
- Be constructive and encouraging in feedback while being honest about areas to improve

INSTRUCTIONS:
1. Award 0-{self.points_per_question} points based on freshman-level expectations
2. Provide specific, constructive, and encouraging feedback
3. Format your response EXACTLY as follows:

SCORE: [numeric score 0-{self.points_per_question}]
FEEDBACK: [Your detailed feedback here - be specific but encouraging]

Remember: This is a freshman course. Be fair, rigorous, but appropriately lenient for their level."""

            # Call the LLM
            response = llm_client.generate(
                model,
                [{"role": "user", "content": grading_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse the response to extract score and feedback
            raw_score, feedback = self._parse_grading_response(response, question_num)
            
            # Apply score multiplier (but cap at max points)
            adjusted_score = min(raw_score * self.score_multiplier, float(self.points_per_question))
            
            # Round to 2 decimal places
            adjusted_score = round(adjusted_score, 2)
            
            return adjusted_score, feedback
            
        except Exception as e:
            logger.error(f"Error grading question {question_num}: {e}")
            return 0.0, f"Error grading this question: {str(e)}"
    
    def _parse_grading_response(self, response: str, question_num: int) -> Tuple[float, str]:
        """
        Parse LLM response to extract score and feedback.
        
        Args:
            response: Raw LLM response text
            question_num: Question number for context
            
        Returns:
            Tuple of (score, feedback)
        """
        import re
        
        # Try to extract score
        score_match = re.search(r'SCORE:\s*([0-9]+(?:\.[0-9]+)?)', response, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            score = max(0.0, min(float(self.points_per_question), score))
        else:
            # If no score found, try to extract a number from the beginning
            num_match = re.search(r'^([0-9]+(?:\.[0-9]+)?)', response.strip())
            score = float(num_match.group(1)) if num_match else 5.0
            score = max(0.0, min(float(self.points_per_question), score))
        
        # Extract feedback
        feedback_match = re.search(r'FEEDBACK:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
        else:
            feedback = response.strip()
        
        # Clean up feedback
        feedback = re.sub(r'SCORE:.*?\n', '', feedback, flags=re.IGNORECASE)
        feedback = feedback.strip()
        
        return score, feedback
    
    def format_grading_output(self, grading_result: Dict) -> str:
        """
        Format the grading results into a readable string for Canvas.
        
        Args:
            grading_result: The result from grade_exam_submission
            
        Returns:
            Formatted feedback string
        """
        lines = []
        total = grading_result['total_score']
        max_score = grading_result['max_score']
        
        # Format total score with 2 decimal places
        lines.append(f"Score: {total:.2f}/{max_score:.2f}")
        lines.append("")
        
        for q_result in grading_result['question_results']:
            score = q_result['score']
            max_pts = q_result['max_score']
            # Format question scores with 2 decimal places
            lines.append(f"\nQuestion {q_result['question_number']} ({score:.2f}/{max_pts:.2f} points):")
            lines.append(f"{q_result['feedback']}")
        
        return '\n'.join(lines)
    
    def validate_configuration(self) -> List[str]:
        """
        Validate exam configuration
        
        Returns:
            List of validation messages/warnings
        """
        messages = super().validate_configuration()
        
        if self.total_points != self.questions_to_grade * self.points_per_question:
            messages.append(
                f"Warning: Total points ({self.total_points}) doesn't match "
                f"{self.questions_to_grade} × {self.points_per_question} = "
                f"{self.questions_to_grade * self.points_per_question}"
            )
        
        if self.total_questions < self.questions_to_grade:
            messages.append(
                f"Error: Cannot grade {self.questions_to_grade} questions when only "
                f"{self.total_questions} questions exist"
            )
        
        return messages
    
    def __str__(self) -> str:
        multiplier_str = f" (×{self.score_multiplier})" if self.score_multiplier != 1.0 else ""
        return (f"{self.display_name} (Exam): Grade {self.questions_to_grade} of "
                f"{self.total_questions} questions, {self.points_per_question} points total{multiplier_str}")