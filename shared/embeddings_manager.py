"""
Embeddings Manager
Handles automatic generation, loading, and refresh of course embeddings
"""

import os
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
from datetime import datetime

from shared.embeddings import CourseDocumentProcessor

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Manage course embeddings with automatic generation and refresh"""
    
    def __init__(self, config_loader):
        """
        Initialize embeddings manager
        
        Args:
            config_loader: ConfigLoader instance
        """
        self.config = config_loader
    
    def get_embeddings_filepath(self, course_type: str) -> str:
        """
        Get the full path to embeddings file
        
        Args:
            course_type: Course type (e.g., "WorldHistory")
            
        Returns:
            Full path to embeddings pickle file
        """
        embeddings_file = self.config.get_embeddings_file(course_type)
        
        # Check if using custom embeddings directory from settings
        embeddings_dir = self.config.get_setting('embeddings_cache_dir', '.')
        
        if embeddings_dir and embeddings_dir != '.':
            embeddings_dir = os.path.expanduser(embeddings_dir)
            os.makedirs(embeddings_dir, exist_ok=True)
            return os.path.join(embeddings_dir, embeddings_file)
        else:
            return embeddings_file
    
    def embeddings_exist(self, course_type: str) -> bool:
        """
        Check if embeddings file exists for a course type
        
        Args:
            course_type: Course type (e.g., "WorldHistory")
            
        Returns:
            True if embeddings file exists
        """
        filepath = self.get_embeddings_filepath(course_type)
        return os.path.exists(filepath)
    
    def get_embeddings_info(self, course_type: str) -> Optional[Dict]:
        """
        Get information about embeddings file
        
        Args:
            course_type: Course type
            
        Returns:
            Dictionary with embeddings info or None if doesn't exist
        """
        filepath = self.get_embeddings_filepath(course_type)
        
        if not os.path.exists(filepath):
            return None
        
        stat = os.stat(filepath)
        
        return {
            'filepath': filepath,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'exists': True
        }
    
    def delete_embeddings(self, course_type: str) -> bool:
        """
        Delete embeddings file for a course type
        
        Args:
            course_type: Course type
            
        Returns:
            True if deleted successfully
        """
        filepath = self.get_embeddings_filepath(course_type)
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted embeddings file: {filepath}")
                return True
            else:
                logger.warning(f"Embeddings file not found: {filepath}")
                return False
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            return False
    
    def load_or_generate_embeddings(
        self, 
        course_type: str,
        force_refresh: bool = False,
        progress_callback=None
    ) -> Tuple[Optional[CourseDocumentProcessor], str]:
        """
        Load existing embeddings or generate new ones
        
        Args:
            course_type: Course type (e.g., "WorldHistory")
            force_refresh: If True, regenerate even if embeddings exist
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (processor, status_message)
        """
        kb_path = self.config.get_knowledge_base_path(course_type)
        
        # Check if knowledge base directory exists
        if not os.path.exists(kb_path):
            msg = f"Knowledge base directory not found: {kb_path}"
            logger.error(msg)
            return None, msg
        
        # Check if directory has files
        files = [f for f in os.listdir(kb_path) if os.path.isfile(os.path.join(kb_path, f))]
        if not files:
            msg = f"Knowledge base directory is empty: {kb_path}"
            logger.warning(msg)
            return None, msg
        
        # Check if embeddings exist
        embeddings_exist = self.embeddings_exist(course_type)
        
        if embeddings_exist and not force_refresh:
            # Load existing embeddings
            if progress_callback:
                progress_callback("Loading existing embeddings...")
            
            try:
                processor = CourseDocumentProcessor(kb_path)
                
                # Try to load from custom location first
                embeddings_file = self.get_embeddings_filepath(course_type)
                
                if os.path.exists(embeddings_file):
                    import pandas as pd
                    df = pd.read_pickle(embeddings_file)
                    processor.df = df
                    
                    stats = processor.get_course_statistics()
                    msg = f"Loaded {stats['total_chunks']} chunks from existing embeddings"
                    logger.info(msg)
                    
                    return processor, msg
                else:
                    # Fall back to original load method
                    df = processor.load_or_create_embeddings(course_type, force_refresh=False)
                    
                    if df is not None and len(df) > 0:
                        stats = processor.get_course_statistics()
                        msg = f"Loaded {stats['total_chunks']} chunks from existing embeddings"
                        logger.info(msg)
                        return processor, msg
                    else:
                        # Embeddings file exists but couldn't load, regenerate
                        force_refresh = True
                        
            except Exception as e:
                logger.error(f"Error loading embeddings: {e}")
                # If loading fails, try to regenerate
                force_refresh = True
        
        # Generate new embeddings
        if progress_callback:
            progress_callback(f"Generating embeddings for {course_type}...")
        
        try:
            processor = CourseDocumentProcessor(kb_path)
            
            if progress_callback:
                progress_callback(f"Processing documents in {kb_path}...")
            
            # Create embeddings
            df = processor.load_or_create_embeddings(course_type, force_refresh=True)
            
            if df is not None and len(df) > 0:
                # Save to custom location if configured
                embeddings_file = self.get_embeddings_filepath(course_type)
                if embeddings_file != processor.get_embedding_filename(course_type):
                    df.to_pickle(embeddings_file)
                    logger.info(f"Saved embeddings to {embeddings_file}")
                
                stats = processor.get_course_statistics()
                msg = f"Generated {stats['total_chunks']} chunks from {stats['unique_documents']} documents"
                logger.info(msg)
                
                if progress_callback:
                    progress_callback(msg)
                
                return processor, msg
            else:
                msg = "Failed to generate embeddings - no documents processed"
                logger.error(msg)
                return None, msg
                
        except Exception as e:
            msg = f"Error generating embeddings: {e}"
            logger.error(msg, exc_info=True)
            return None, msg
    
    def get_all_embeddings_status(self) -> Dict[str, Dict]:
        """
        Get status of all knowledge base embeddings
        
        Returns:
            Dictionary mapping course_type to status info
        """
        status = {}
        
        for kb_name in self.config.knowledge_bases.keys():
            info = self.get_embeddings_info(kb_name)
            
            if info:
                status[kb_name] = {
                    'exists': True,
                    'size_mb': info['size_mb'],
                    'modified': info['modified'],
                    'filepath': info['filepath']
                }
            else:
                status[kb_name] = {
                    'exists': False,
                    'filepath': self.get_embeddings_filepath(kb_name)
                }
        
        return status
    
    def refresh_all_embeddings(self, progress_callback=None):
        """
        Refresh all embeddings for all knowledge bases
        
        Args:
            progress_callback: Optional callback for progress updates
        """
        results = {}
        
        for kb_name in self.config.knowledge_bases.keys():
            if progress_callback:
                progress_callback(f"Refreshing {kb_name}...")
            
            processor, msg = self.load_or_generate_embeddings(
                kb_name, 
                force_refresh=True,
                progress_callback=progress_callback
            )
            
            results[kb_name] = {
                'success': processor is not None,
                'message': msg
            }
        
        return results


def get_embeddings_manager(config_loader):
    """
    Get embeddings manager instance
    
    Args:
        config_loader: ConfigLoader instance
        
    Returns:
        EmbeddingsManager instance
    """
    return EmbeddingsManager(config_loader)


if __name__ == "__main__":
    # Test embeddings manager
    from shared.config_loader import get_config
    
    print("Testing Embeddings Manager...")
    print()
    
    config = get_config()
    manager = EmbeddingsManager(config)
    
    # Show status of all embeddings
    print("Current Embeddings Status:")
    print("=" * 60)
    
    status = manager.get_all_embeddings_status()
    for course_type, info in status.items():
        print(f"\n{course_type}:")
        if info['exists']:
            print(f"  ✓ Exists: {info['filepath']}")
            print(f"    Size: {info['size_mb']:.2f} MB")
            print(f"    Modified: {info['modified']}")
        else:
            print(f"  ✗ Not found: {info['filepath']}")
    
    print("\n" + "=" * 60)
