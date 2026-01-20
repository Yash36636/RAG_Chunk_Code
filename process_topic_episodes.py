"""
Process transcripts from a specific topic index file (e.g., product-management.md)
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add the current directory to Python path so it can find 'src'
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from src import VideoRAGPipeline
from src.github_integration import GitHubRepo, TopicIndexParser
from src.storage import ChunkStorage


def process_topic_from_github(
    repo_url: str,
    topic_file: str = "index/product-management.md",
    clone_repo: bool = True,
    index: bool = False,
    embedding_api_key: Optional[str] = None,
    output_dir: str = "chunks_product_management",
    clean_output: bool = True
):
    """
    Process all transcripts referenced in a topic index file from GitHub.
    
    Args:
        repo_url: GitHub repository URL
        topic_file: Path to topic index file (e.g., "index/product-management.md")
        clone_repo: Whether to clone the repo (False if already cloned)
        index: Whether to index the processed chunks
        embedding_api_key: OpenAI API key for embeddings (optional)
    """
    print("=" * 70)
    print("Video RAG Pipeline - Topic-Based Processing")
    print("=" * 70)
    
    # Initialize GitHub repo
    repo = GitHubRepo(repo_url)
    
    # Clone repository if needed
    if clone_repo:
        repo.clone()
    else:
        repo.pull()  # Update if exists
    
    # Parse topic file to get episode references
    print(f"\nParsing topic file: {topic_file}")
    parser = TopicIndexParser(repo)
    topic_data = parser.parse_topic_file(topic_file)
    
    print(f"Found {topic_data['total_episodes']} episodes in {topic_file}")
    
    if topic_data['total_episodes'] == 0:
        print("⚠ No episodes found. Please check the topic file format.")
        return []
    
    # Show episodes to be processed
    print("\nEpisodes to process:")
    for i, episode in enumerate(topic_data['episodes'], 1):
        print(f"  {i}. {episode['guest']} - {episode['title'] or 'N/A'}")
    
    # Initialize pipeline
    # Use the repo's local path as the base directory
    pipeline = VideoRAGPipeline(
        transcripts_dir=str(repo.local_path),  # Base directory
        embedding_api_key=embedding_api_key or os.getenv("OPENAI_API_KEY"),
        parent_window_tokens=2000,
        child_window_tokens=250
    )
    
    # Initialize storage for saving chunks to JSON
    storage = ChunkStorage(output_dir=output_dir)
    
    # Clean output directory if requested (to avoid overlap)
    if clean_output and storage.output_dir.exists():
        import shutil
        print(f"\nCleaning existing output directory: {storage.output_dir}")
        shutil.rmtree(storage.output_dir)
        print("Existing chunks deleted. Starting fresh.\n")
    
    # Recreate output directory
    storage.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each episode
    results = []
    print(f"\nProcessing {len(topic_data['episodes'])} episodes...")
    print("-" * 70)
    
    for i, episode in enumerate(topic_data['episodes'], 1):
        transcript_path = episode['path']
        full_path = repo.local_path / transcript_path
        
        if not full_path.exists():
            print(f"⚠ [{i}/{len(topic_data['episodes'])}] Skipping {episode['guest']}: File not found")
            continue
        
        print(f"\n[{i}/{len(topic_data['episodes'])}] Processing: {episode['guest']}")
        print(f"   File: {transcript_path}")
        
        try:
            # Extract guest name for metadata
            guest_name = episode['guest'].replace('-', ' ').title()
            
            # Process the transcript
            result = pipeline.process_file(
                file_path=str(full_path),
                metadata_override={
                    'guest': guest_name,
                    'title': episode['title'] or f"Episode with {guest_name}",
                    'topics': [Path(topic_file).stem.replace('-', ' ').title()]
                },
                index=index
            )
            
            # Extract episode identifier for saving
            episode_id = result['metadata'].video_id or episode['guest']
            
            # Save chunks to JSON
            output_file = storage.save_episode_chunks(
                episode_id=episode_id,
                parent_chunks=result['parent_chunks'],
                child_chunks=result['child_chunks'],
                metadata=result['metadata'],
                enriched_texts=result.get('enriched_texts')
            )
            
            results.append({
                'episode': episode,
                'result': result
            })
            
            parent_count = len(result['parent_chunks'])
            child_count = len(result['child_chunks'])
            print(f"   Created {parent_count} parent chunks, {child_count} child chunks")
            print(f"   Saved to: {output_file}")
            
        except Exception as e:
            import traceback
            print(f"   Error: {e}")
            print(f"   Error details:")
            traceback.print_exc()
            continue
    
    # Save consolidated JSON file with all chunks
    print("\n" + "=" * 70)
    print("Saving consolidated chunks file...")
    all_episode_results = [r['result'] for r in results]
    consolidated_file = storage.save_all_chunks(
        all_episodes=all_episode_results,
        output_file="all_chunks.json"
    )
    print(f"Consolidated file saved to: {consolidated_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("Processing Summary")
    print("=" * 70)
    print(f"Topic file: {topic_file}")
    print(f"Total episodes: {topic_data['total_episodes']}")
    print(f"Successfully processed: {len(results)}")
    
    total_parent_chunks = sum(len(r['result']['parent_chunks']) for r in results)
    total_child_chunks = sum(len(r['result']['child_chunks']) for r in results)
    print(f"Total parent chunks: {total_parent_chunks}")
    print(f"Total child chunks: {total_child_chunks}")
    print(f"Total chunks: {total_parent_chunks + total_child_chunks}")
    print(f"\nOutput directory: {Path(output_dir).absolute()}")
    print("=" * 70)
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process transcripts from a GitHub repository topic index"
    )
    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="GitHub repository URL (e.g., https://github.com/user/repo)"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="index/product-management.md",
        help="Path to topic index file (default: index/product-management.md)"
    )
    parser.add_argument(
        "--no-clone",
        action="store_true",
        help="Don't clone repo (use existing local copy)"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Index chunks to vector store (requires API keys)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key for embeddings (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="chunks_product_management",
        help="Output directory for JSON files (default: chunks_product_management)"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Don't delete existing output directory (append to existing)"
    )
    
    args = parser.parse_args()
    
    # Process
    results = process_topic_from_github(
        repo_url=args.repo,
        topic_file=args.topic,
        clone_repo=not args.no_clone,
        index=args.index,
        embedding_api_key=args.api_key,
        output_dir=args.output_dir,
        clean_output=not args.no_clean
    )
    
    return results


if __name__ == "__main__":
    main()
