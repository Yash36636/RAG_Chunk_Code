"""
Query the RAG server (auto-detects Groq/Ollama)
"""

import sys
import requests
import json

SERVER_URL = "http://localhost:8000/query"

def query(question: str, mode: str = "fast"):
    """Query the RAG system."""
    
    print(f"\n{'='*70}")
    print(f"QUERY: {question}")
    print(f"{'='*70}\n")
    
    print(f"[INFO] Mode: {mode.upper()}")
    print("[1/2] Sending request to server...")
    
    try:
        response = requests.post(
            SERVER_URL,
            json={
                "query": question,
                "synthesize_answer": True,
                "include_citations": True,
                "mode": mode,
                "use_longtail": False
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"[ERROR] Server returned status {response.status_code}")
            print(response.text)
            return None
        
        data = response.json()
        
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to server!")
        print("Make sure server is running:")
        print('  python server.py')
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None
    
    latency = data['latency_seconds']
    print(f"[2/2] Response received in {latency}s")
    
    # Performance indicator
    if latency < 1.5:
        perf = "EXCELLENT (Groq)"
    elif latency < 3:
        perf = "GOOD"
    elif latency < 6:
        perf = "ACCEPTABLE"
    else:
        perf = "SLOW"
    
    print(f"     Performance: {perf}")
    
    # Display answer
    print(f"\n{'='*70}")
    print("ANSWER")
    print(f"{'='*70}\n")
    
    if data.get('answer'):
        print(data['answer'])
    else:
        print("(No answer generated)")
    
    # Display GROUND-TRUTH citations (no hallucination)
    # BUT: Don't show if LLM refused (safety feature)
    if data.get('is_refusal'):
        print(f"\n{'='*70}")
        print("[SAFETY] Question was refused - no citations shown")
        print(f"{'='*70}")
    elif data.get('citations'):
        print(f"\n{'='*70}")
        print("CITATIONS (Ground Truth)")
        print(f"{'='*70}\n")
        for citation in data['citations'][:4]:
            source_num = citation.get('source_num', '?')
            speaker = citation.get('speaker', 'Unknown')
            video_title = citation.get('video_title', citation.get('video_id', 'Unknown'))
            timestamp = citation.get('timestamp', '0m0s')
            youtube_url = citation.get('youtube_url', '')
            text_preview = citation.get('text_preview', citation.get('text', '')[:100])
            
            print(f"[SOURCE {source_num}]")
            print(f"    Speaker: {speaker}")
            print(f"    Video: {video_title}")
            print(f"    Time: {timestamp}")
            print(f"    Link: {youtube_url}")
            print(f"    Preview: {text_preview[:80]}...")
            print()
    
    # Display metadata
    print(f"{'='*70}")
    print("METADATA")
    print(f"{'='*70}")
    print(f"Provider: {data.get('provider', 'unknown')}")
    print(f"Mode: {data.get('query_mode', 'unknown')}")
    print(f"Confidence: {data.get('confidence', 'unknown')}")
    print(f"Chunks: {data.get('num_chunks', 0)}")
    print(f"Latency: {latency}s")
    print(f"{'='*70}\n")
    
    return data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "How to prioritize features?"
    
    query(question)
