"""
Rubric Manager - Handles rubric retrieval, storage, and formatting for grading
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RubricManager:
    def __init__(self, cache_dir: str = "data/rubrics"):
        """
        Initialize the Rubric Manager
        
        Args:
            cache_dir: Directory to cache downloaded rubrics
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def create_rubric_cache_key(self, course_id: str, assignment_id: str, is_discussion: bool = False) -> str:
        """
        Create a unique cache key for a rubric
        
        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID
            is_discussion: Whether this is a discussion rubric
            
        Returns:
            Unique cache key string
        """
        key_base = f"{course_id}_{assignment_id}"
        if is_discussion:
            key_base += "_discussion"
        
        return hashlib.md5(key_base.encode()).hexdigest()
    
    def get_cached_rubric_path(self, cache_key: str) -> Path:
        """
        Get the path for a cached rubric file
        
        Args:
            cache_key: Rubric cache key
            
        Returns:
            Path object for the rubric file
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def save_rubric_to_cache(self, cache_key: str, rubric_data: Dict) -> bool:
        """
        Save rubric data to cache
        
        Args:
            cache_key: Rubric cache key
            rubric_data: Rubric data to cache
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_path = self.get_cached_rubric_path(cache_key)
            
            # Add metadata
            rubric_data['_metadata'] = {
                'cached_at': datetime.now().isoformat(),
                'cache_key': cache_key
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(rubric_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved rubric to cache: {cache_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving rubric to cache: {e}")
            return False
    
    def load_rubric_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Load rubric data from cache
        
        Args:
            cache_key: Rubric cache key
            
        Returns:
            Rubric data if found, None otherwise
        """
        try:
            cache_path = self.get_cached_rubric_path(cache_key)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                rubric_data = json.load(f)
            
            logger.info(f"Loaded rubric from cache: {cache_path}")
            return rubric_data
            
        except Exception as e:
            logger.error(f"Error loading rubric from cache: {e}")
            return None
    
    def get_rubric_from_canvas(self, course_id: str, assignment_id: str, 
                              is_discussion: bool = False, 
                              force_refresh: bool = False) -> Optional[Dict]:
        """
        Get rubric from Canvas API with caching
        
        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID
            is_discussion: Whether this is a discussion rubric
            force_refresh: Force refresh from Canvas (ignore cache)
            
        Returns:
            Rubric data dictionary, or None if error
        """
        from shared.canvas_rubric_api import get_rubric_for_assignment
        
        cache_key = self.create_rubric_cache_key(course_id, assignment_id, is_discussion)
        
        # Try to load from cache first
        if not force_refresh:
            cached_rubric = self.load_rubric_from_cache(cache_key)
            if cached_rubric:
                return cached_rubric
        
        # Download from Canvas
        try:
            rubric_data = get_rubric_for_assignment(course_id, assignment_id, is_discussion)
            
            if rubric_data:
                # Save to cache
                self.save_rubric_to_cache(cache_key, rubric_data)
                return rubric_data
            else:
                logger.warning(f"No rubric data returned from Canvas for assignment {assignment_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving rubric from Canvas: {e}")
            return None
    
    def create_custom_rubric(self, rubric_name: str, criteria: List[Dict], 
                           total_points: float, description: str = "") -> Dict:
        """
        Create a custom rubric (not from Canvas)
        
        Args:
            rubric_name: Name for this rubric
            criteria: List of rubric criteria
            total_points: Total points for this rubric
            description: Rubric description
            
        Returns:
            Rubric data dictionary
        """
        return {
            'rubric_name': rubric_name,
            'rubric_criteria': criteria,
            'total_points': total_points,
            'description': description,
            'source': 'custom',
            'created_at': datetime.now().isoformat()
        }
    
    def format_rubric_for_system_prompt(self, rubric_data: Dict) -> str:
        """
        Format rubric data for use in LLM system prompts
        
        Args:
            rubric_data: Rubric data dictionary
            
        Returns:
            Formatted string for system prompt
        """
        if not rubric_data:
            return ""
        
        # Handle both Canvas rubrics and custom rubrics
        if 'rubric_criteria' in rubric_data:
            criteria = rubric_data['rubric_criteria']
        elif 'assignment' in rubric_data and 'rubric_criteria' in rubric_data:
            criteria = rubric_data['rubric_criteria']
        else:
            return ""
        
        total_points = rubric_data.get('total_points', 100)
        
        rubric_text = f"GRADING RUBRIC ({total_points} Points Total):\n\n"
        
        for i, criterion in enumerate(criteria, 1):
            criterion_name = criterion.get('description', f'Criterion {i}')
            criterion_points = criterion.get('points', 0)
            
            rubric_text += f"{i}. {criterion_name} ({criterion_points} pts):\n"
            
            # Add long description if available
            if criterion.get('long_description'):
                rubric_text += f"   {criterion['long_description']}\n"
            
            # Add rating scale if available
            if 'ratings' in criterion and criterion['ratings']:
                rubric_text += "   Rating Scale:\n"
                for rating in criterion['ratings']:
                    rating_desc = rating.get('description', '')
                    rating_points = rating.get('points', 0)
                    rating_long = rating.get('long_description', '')
                    
                    if rating_long:
                        rubric_text += f"   - {rating_desc} ({rating_points} pts): {rating_long}\n"
                    else:
                        rubric_text += f"   - {rating_desc} ({rating_points} pts)\n"
            
            rubric_text += "\n"
        
        return rubric_text
    
    def get_rubric_summary(self, rubric_data: Dict) -> str:
        """
        Get a summary of the rubric for display
        
        Args:
            rubric_data: Rubric data dictionary
            
        Returns:
            Summary string
        """
        if not rubric_data:
            return "No rubric available"
        
        if 'rubric_criteria' in rubric_data:
            criteria_count = len(rubric_data['rubric_criteria'])
            total_points = rubric_data.get('total_points', 100)
            
            if 'assignment' in rubric_data and 'name' in rubric_data['assignment']:
                assignment_name = rubric_data['assignment']['name']
                return f"{assignment_name} ({criteria_count} criteria, {total_points} pts)"
            else:
                return f"{criteria_count} criteria, {total_points} pts"
        
        return "Unknown rubric format"
    
    def list_cached_rubrics(self) -> List[Dict]:
        """
        List all cached rubrics
        
        Returns:
            List of rubric metadata dictionaries
        """
        cached_rubrics = []
        
        if not self.cache_dir.exists():
            return cached_rubrics
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    rubric_data = json.load(f)
                
                metadata = rubric_data.get('_metadata', {})
                
                cached_rubrics.append({
                    'cache_key': metadata.get('cache_key', cache_file.stem),
                    'cached_at': metadata.get('cached_at', 'Unknown'),
                    'summary': self.get_rubric_summary(rubric_data),
                    'file_path': str(cache_file)
                })
                
            except Exception as e:
                logger.error(f"Error reading cached rubric {cache_file}: {e}")
        
        # Sort by cached_at (newest first)
        cached_rubrics.sort(key=lambda x: x['cached_at'], reverse=True)
        
        return cached_rubrics
    
    def clear_rubric_cache(self) -> bool:
        """
        Clear all cached rubrics
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            
            logger.info(f"Cleared rubric cache: {self.cache_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing rubric cache: {e}")
            return False