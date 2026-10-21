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
            default_points: Default total points (should be 150)
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
        # points_per_question is derived from the Canvas assignment's points_possible
        # so it always stays in sync with however the exam is configured in Canvas.
        # (e.g. 150 pts / 10 questions = 15 pts each)
        self.total_questions = 10
        self.questions_to_grade = 5
        self.points_per_question = self.total_points // self.total_questions

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
        """
        return "Use all course content from embeddings to evaluate exam answers."
    
    def get_questions(self, base_course_number: int, module_number: int = None) -> str:
        """Get exam questions if available."""
        return "Exam questions will be extracted from Canvas assignment."
    
    def get_prompt_string(self, base_course_number: int, module_number: int = None) -> str:
        """Get the complete prompt string for exam grading."""
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

        Returns:
            Tuple of (list of answered questions, list of question numbers)
            Each question dict has 'question_number' and 'answer' keys
        """
        answered_questions = []
        question_numbers = []
        
        import re
        pattern = r'(?:Question\s+(\d+)|Q\s*(\d+)|^(\d+)\.)'
        
        lines = submission_text.split('\n')
        current_q_num = None
        current_answer = []
        
        for line in lines:
            match = re.search(pattern, line, re.IGNORECASE | re.MULTILINE)
            if match:
                if current_q_num is not None and current_answer:
                    answered_questions.append({
                        'question_number': current_q_num,
                        'answer': '\n'.join(current_answer).strip()
                    })
                    question_numbers.append(current_q_num)
                
                current_q_num = int(match.group(1) or match.group(2) or match.group(3))
                current_answer = [line]
            elif current_q_num is not None:
                current_answer.append(line)
        
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
        Grades the FIRST 5 SUBSTANTIVE answered questions only (in document order).
        An answer counts as "substantive" only if it receives a nonzero score from
        the grader. Non-answers (blank, "N/A", "no answer provided", or anything the
        grader scores as 0 — off-topic, too short, etc.) are skipped and do NOT
        consume one of the 5 slots, so the app keeps looking at later questions
        until it finds 5 real attempts (or runs out of answered questions).

        The raw sum of per-question scores (max = 5 * points_per_question) is doubled
        to produce the Canvas-ready total. Feedback text is not affected by this doubling.
        """
        answered_questions, question_numbers = self.parse_exam_submission(submission_text)
        
        graded_results = []
        skipped_results = []
        total_score = 0
        questions_graded = 0
        
        for question_data in answered_questions:
            if questions_graded >= self.questions_to_grade:
                break
            
            q_num = question_data['question_number']
            answer = question_data['answer']
            
            if not answer or answer.strip() == "" or len(answer.strip()) < 20 or "(No answer provided)" in answer:
                continue
            
            score, feedback = self._grade_single_answer(
                answer, q_num, llm_client, course_embeddings, model
            )
            
            if score <= 0:
                # Grader found no real attempt here (e.g. "N/A", filler text,
                # or genuinely off-topic/too-short to evaluate). Don't let this
                # consume one of the 5 required slots — keep looking at the
                # student's remaining answers instead.
                skipped_results.append({
                    'question_number': q_num,
                    'score': 0.0,
                    'max_score': self.points_per_question,
                    'feedback': feedback,
                    'graded': False
                })
                continue
            
            graded_results.append({
                'question_number': q_num,
                'score': score,
                'max_score': self.points_per_question,
                'feedback': feedback,
                'graded': True
            })
            total_score += score
            questions_graded += 1
        
        # Students answer 5 of 10 questions. Canvas weights all 10, so the raw
        # sum of 5 answers (max = 5 × points_per_question) is doubled to produce
        # the Canvas-ready score. Feedback per question is not affected.
        raw_total = round(total_score, 2)
        doubled_total = min(round(raw_total * 2, 2), float(self.total_points))

        return {
            'total_score': doubled_total,
            'max_score': self.total_points,
            'questions_graded': questions_graded,
            'question_results': graded_results,
            'skipped_results': skipped_results,
            'submission_text': submission_text,
            'raw_total': raw_total
        }
    
    def _grade_single_answer(self, answer: str, question_num: int,
                             llm_client, course_embeddings, model: str) -> Tuple[float, str]:
        """
        Grade a single exam answer using LLM and course embeddings.

        Returns:
            Tuple of (score, feedback)
        """
        try:
            relevant_docs = []
            if course_embeddings and hasattr(course_embeddings, 'search_documents'):
                search_results = course_embeddings.search_documents(answer, top_k=5)
                if isinstance(search_results, str):
                    relevant_docs = [search_results]
                elif isinstance(search_results, list) and search_results:
                    relevant_docs = [
                        doc.get('text', str(doc)) if isinstance(doc, dict) else str(doc)
                        for doc in search_results
                    ]
            
            context_str = "\n\n".join(relevant_docs) if relevant_docs else "No specific course content found."

            # Derive score thresholds from points_per_question so they scale
            # automatically if the Canvas exam value ever changes.
            pass_threshold  = round(self.points_per_question * 0.6)   # 60% — passing
            strong_threshold = round(self.points_per_question * 0.8)  # 80% — strong
            low_threshold   = round(self.points_per_question * 0.4)   # 40% — below passing
            minimal_threshold = round(self.points_per_question * 0.2) # 20% — minimal

            grading_prompt = f"""You are grading an exam answer for a freshman-level introductory college history course.

QUESTION {question_num}:
Evaluate the student's answer based on the course content provided.

COURSE CONTENT (for reference):
{context_str}

STUDENT'S ANSWER:
{answer}

WHO THESE STUDENTS ARE:
Most of these students are recent high school graduates. Many have had little prior exposure to
serious historical study. Their writing skills are still developing — expect informal phrasing,
grammatical imperfection, and answers that are shorter or less polished than college-level work.
Do NOT penalize imperfect writing as long as the meaning is clear and legible.

CORE GRADING PRINCIPLE:
A student who shows they engaged with the course material and demonstrates a functional
understanding of the relevant facts, people, events, or concepts deserves a PASSING score
({pass_threshold}/{self.points_per_question} or better). You are rewarding engagement and
basic comprehension, not penalizing gaps in sophistication.

SCORING RUBRIC (0–{self.points_per_question} points):

{self.points_per_question} pts — Outstanding: thorough, accurate, uses specific examples,
    shows genuine insight. Reserve for truly impressive answers.

{strong_threshold}–{self.points_per_question - 1} pts — Strong: solid understanding,
    covers the main points accurately, only minor gaps.

{pass_threshold}–{strong_threshold - 1} pts — PASSING (where most sincere answers should land):
    student clearly engaged with the material and demonstrates functional understanding, even
    if the answer is incomplete, informally written, or lacks nuance.
    DEFAULT HERE when you are uncertain between this band and the one below.

{low_threshold}–{pass_threshold - 1} pts — Below passing: minimal engagement, significant
    factual errors, or answer too thin to confirm understanding. Use ONLY when you genuinely
    cannot verify the student grasped the topic at all.

1–{minimal_threshold} pts — Very little: a few relevant words or phrases but no coherent
    understanding demonstrated.

0 pts — No answer, completely off-topic, or too short to evaluate.

FEEDBACK GUIDELINES:
- Open by acknowledging what the student got right before addressing any gaps.
- Be specific: name the concepts, events, or people they addressed (or should have addressed).
- Frame all improvements as coaching ("To strengthen this answer, try adding...") not criticism.
- Keep the tone encouraging — this may be one of their first college exams.
- Do NOT comment on grammar, spelling, or writing style unless it made the answer impossible
  to understand.

INSTRUCTIONS:
1. Award 0–{self.points_per_question} points following the rubric above.
   When genuinely uncertain between two bands, choose the higher one for any student who
   clearly made a sincere effort.
2. Write specific, coaching-style feedback.
3. Format your response EXACTLY as follows — nothing before SCORE, nothing after FEEDBACK:

SCORE: [numeric score 0-{self.points_per_question}]
FEEDBACK: [Your feedback here]"""

            response = llm_client.generate(
                model,
                [{"role": "user", "content": grading_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            raw_score, feedback = self._parse_grading_response(response, question_num)
            
            adjusted_score = min(raw_score * self.score_multiplier, float(self.points_per_question))
            adjusted_score = round(adjusted_score, 2)
            
            return adjusted_score, feedback
            
        except Exception as e:
            logger.error(f"Error grading question {question_num}: {e}")
            return 0.0, f"Error grading this question: {str(e)}"
    
    def _parse_grading_response(self, response: str, question_num: int) -> Tuple[float, str]:
        """Parse LLM response to extract score and feedback."""
        import re
        
        score_match = re.search(r'SCORE:\s*([0-9]+(?:\.[0-9]+)?)', response, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            score = max(0.0, min(float(self.points_per_question), score))
        else:
            num_match = re.search(r'^([0-9]+(?:\.[0-9]+)?)', response.strip())
            score = float(num_match.group(1)) if num_match else 5.0
            score = max(0.0, min(float(self.points_per_question), score))
        
        feedback_match = re.search(r'FEEDBACK:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
        else:
            feedback = response.strip()
        
        feedback = re.sub(r'SCORE:.*?\n', '', feedback, flags=re.IGNORECASE)
        feedback = feedback.strip()
        
        return score, feedback
    
    def format_grading_output(self, grading_result: Dict) -> str:
        """Format the grading results into a readable string for Canvas."""
        lines = []
        total = grading_result['total_score']       # doubled, Canvas-ready
        max_score = grading_result['max_score']     # e.g. 150
        raw_total = grading_result.get('raw_total', total / 2)
        questions_graded = grading_result.get('questions_graded', len(grading_result['question_results']))
        max_raw = self.questions_to_grade * self.points_per_question  # e.g. 75

        lines.append(f"Score: {total:.2f}/{max_score:.2f}")
        lines.append(
            f"(Graded {questions_graded} of {self.questions_to_grade} required questions — "
            f"raw sum: {raw_total:.2f}/{max_raw}, doubled for Canvas)"
        )
        lines.append("")

        for q_result in grading_result['question_results']:
            score = q_result['score']
            max_pts = q_result['max_score']
            lines.append(f"\nQuestion {q_result['question_number']} ({score:.2f}/{max_pts:.2f} points):")
            lines.append(f"{q_result['feedback']}")

        skipped = grading_result.get('skipped_results', [])
        if skipped:
            skipped_nums = ', '.join(str(s['question_number']) for s in skipped)
            lines.append("")
            lines.append(
                f"(Question(s) {skipped_nums} were not counted toward your "
                f"{self.questions_to_grade} required answers — no substantive "
                f"response was found there.)"
            )
        
        return '\n'.join(lines)
    
    def validate_configuration(self) -> List[str]:
        """Validate exam configuration."""
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