#!/usr/bin/env python3
"""
Embeddings Management CLI Tool
Manage course embeddings: check status, delete, refresh

Usage:
    python manage_embeddings.py status              # Show status of all embeddings
    python manage_embeddings.py delete WorldHistory # Delete embeddings for WorldHistory
    python manage_embeddings.py refresh WorldHistory # Regenerate embeddings for WorldHistory
    python manage_embeddings.py refresh --all       # Regenerate all embeddings
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.config_loader import get_config
from shared.embeddings_manager import EmbeddingsManager


def show_status(manager: EmbeddingsManager):
    """Show status of all embeddings"""
    print("\n" + "=" * 70)
    print("Embeddings Status")
    print("=" * 70)
    
    status = manager.get_all_embeddings_status()
    
    if not status:
        print("\n  No knowledge bases configured")
        return
    
    for course_type, info in status.items():
        print(f"\n📚 {course_type}")
        print("-" * 70)
        
        if info['exists']:
            print(f"  Status:   ✓ Exists")
            print(f"  Path:     {info['filepath']}")
            print(f"  Size:     {info['size_mb']:.2f} MB")
            print(f"  Modified: {info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  Status:   ✗ Not found")
            print(f"  Path:     {info['filepath']}")
            print(f"  Action:   Run 'python manage_embeddings.py refresh {course_type}'")
    
    print("\n" + "=" * 70)
    print()


def delete_embeddings(manager: EmbeddingsManager, course_type: str):
    """Delete embeddings for a course type"""
    print(f"\nDeleting embeddings for {course_type}...")
    
    if not manager.embeddings_exist(course_type):
        print(f"✗ Embeddings for {course_type} do not exist")
        return False
    
    # Confirm deletion
    response = input(f"Are you sure you want to delete {course_type} embeddings? [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("Cancelled")
        return False
    
    success = manager.delete_embeddings(course_type)
    
    if success:
        print(f"✓ Successfully deleted {course_type} embeddings")
        print(f"  Run 'python manage_embeddings.py refresh {course_type}' to regenerate")
    else:
        print(f"✗ Failed to delete {course_type} embeddings")
    
    return success


def refresh_embeddings(manager: EmbeddingsManager, course_type: str):
    """Refresh embeddings for a course type"""
    print(f"\nRefreshing embeddings for {course_type}...")
    print("-" * 70)
    
    def progress_callback(message):
        print(f"  {message}")
    
    processor, msg = manager.load_or_generate_embeddings(
        course_type,
        force_refresh=True,
        progress_callback=progress_callback
    )
    
    if processor:
        print(f"\n✓ Successfully refreshed {course_type}")
        print(f"  {msg}")
        
        stats = processor.get_course_statistics()
        print(f"\n  Statistics:")
        print(f"    - Total chunks: {stats['total_chunks']}")
        print(f"    - Unique documents: {stats['unique_documents']}")
        print(f"    - Average tokens/chunk: {stats['avg_tokens_per_chunk']:.1f}")
        print(f"    - Total tokens: {stats['total_tokens']}")
        
        return True
    else:
        print(f"\n✗ Failed to refresh {course_type}")
        print(f"  {msg}")
        return False


def refresh_all(manager: EmbeddingsManager):
    """Refresh all embeddings"""
    print("\nRefreshing ALL embeddings...")
    print("=" * 70)
    
    def progress_callback(message):
        print(f"  {message}")
    
    results = manager.refresh_all_embeddings(progress_callback)
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    for course_type, result in results.items():
        if result['success']:
            print(f"  ✓ {course_type}: {result['message']}")
        else:
            print(f"  ✗ {course_type}: {result['message']}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Manage course embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_embeddings.py status                    # Show status
  python manage_embeddings.py delete WorldHistory       # Delete embeddings
  python manage_embeddings.py refresh WorldHistory      # Refresh embeddings
  python manage_embeddings.py refresh --all             # Refresh all
        """
    )
    
    parser.add_argument(
        'command',
        choices=['status', 'delete', 'refresh'],
        help='Command to run'
    )
    
    parser.add_argument(
        'course_type',
        nargs='?',
        help='Course type (e.g., WorldHistory, USHistory)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Apply to all course types (only for refresh)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = get_config()
        manager = EmbeddingsManager(config)
        
        # Execute command
        if args.command == 'status':
            show_status(manager)
        
        elif args.command == 'delete':
            if not args.course_type:
                print("Error: course_type required for delete")
                print("Example: python manage_embeddings.py delete WorldHistory")
                sys.exit(1)
            
            if args.course_type not in config.knowledge_bases:
                print(f"Error: Unknown course type '{args.course_type}'")
                print(f"Available: {', '.join(config.knowledge_bases.keys())}")
                sys.exit(1)
            
            delete_embeddings(manager, args.course_type)
        
        elif args.command == 'refresh':
            if args.all:
                refresh_all(manager)
            else:
                if not args.course_type:
                    print("Error: course_type required or use --all flag")
                    print("Example: python manage_embeddings.py refresh WorldHistory")
                    print("     or: python manage_embeddings.py refresh --all")
                    sys.exit(1)
                
                if args.course_type not in config.knowledge_bases:
                    print(f"Error: Unknown course type '{args.course_type}'")
                    print(f"Available: {', '.join(config.knowledge_bases.keys())}")
                    sys.exit(1)
                
                refresh_embeddings(manager, args.course_type)
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
