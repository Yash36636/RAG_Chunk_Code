"""
Simple script to run the pipeline on Lenny's Podcast Transcripts
"""

import sys
from pathlib import Path

# Add the current directory to Python path so it can find 'src'
sys.path.insert(0, str(Path(__file__).parent))

from process_topic_episodes import process_topic_from_github

# Your repository URL
REPO_URL = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"

def main():
    """Main function to process episodes."""
    
    # Default: process product-management.md
    topic_file = "index/product-management.md"
    
    # Allow override via command line
    if len(sys.argv) > 1:
        topic_file = sys.argv[1]
    
    print(f"Starting pipeline for: {topic_file}")
    print(f"Repository: {REPO_URL}\n")
    
    # Process episodes and save chunks to JSON
    results = process_topic_from_github(
        repo_url=REPO_URL,
        topic_file=topic_file,
        clone_repo=False,  # Use existing repo
        index=False,  # Set to True if you want to index to vector store
        output_dir="chunks_product_management",  # Separate folder for product management
        clean_output=True  # Delete existing chunks to start fresh
    )
    
    if results:
        print(f"\nSuccessfully processed {len(results)} episodes!")
    else:
        print("\nNo episodes were processed. Check the output above for errors.")

if __name__ == "__main__":
    main()
