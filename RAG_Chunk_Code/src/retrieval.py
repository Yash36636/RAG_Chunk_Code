"""
Retrieval Module with Parent Expansion
Implements two-tier retrieval with parent context expansion and deduplication.
"""

from typing import List, Dict, Optional, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .parent_loader import ParentChunkLoader

from .embedding import EmbeddingGenerator, VectorStore
from .two_tier_embedding import TwoTierEmbeddingPipeline


class RetrievalResult:
    """Single retrieval result with full metadata for citations."""
    
    def __init__(
        self,
        chunk_id: str,
        text: str,
        score: float,
        video_id: str,
        start_seconds: float,
        end_seconds: float,
        parent_id: Optional[str] = None,
        speaker: Optional[str] = None,
        tier: Optional[str] = None,
        parent_text: Optional[str] = None,
        video_title: Optional[str] = None,  # Episode title for citations
        guest: Optional[str] = None  # Guest name (fallback for speaker)
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.score = score
        self.video_id = video_id
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.parent_id = parent_id
        self.speaker = speaker
        self.tier = tier
        self.parent_text = parent_text
        self.video_title = video_title
        self.guest = guest
    
    def get_speaker(self) -> str:
        """Get speaker name with fallback to guest."""
        return self.speaker or self.guest or "Unknown"
    
    def get_youtube_url(self) -> str:
        """Get YouTube URL with timestamp."""
        return f"https://www.youtube.com/watch?v={self.video_id}&t={int(self.start_seconds)}s"
    
    def get_timestamp_str(self) -> str:
        """Get formatted timestamp."""
        minutes = int(self.start_seconds // 60)
        seconds = int(self.start_seconds % 60)
        return f"{minutes}m{seconds}s"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'score': self.score,
            'video_id': self.video_id,
            'start_seconds': self.start_seconds,
            'end_seconds': self.end_seconds,
            'parent_id': self.parent_id,
            'speaker': self.speaker,
            'tier': self.tier,
            'parent_text': self.parent_text,
            'video_title': self.video_title,
            'guest': self.guest
        }


class RetrievalPipeline:
    """
    Retrieval pipeline with:
    - Two-tier search (core first, longtail if needed)
    - Parent expansion
    - Deduplication and grouping
    """
    
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        core_store: VectorStore,
        longtail_store: VectorStore,
        two_tier_pipeline: TwoTierEmbeddingPipeline,
        core_top_k: int = 20,  # STEP 2.2: Increased from 12 to 20 for better recall
        longtail_top_k: int = 10,  # Increased from 6 to 10
        min_score_threshold: float = 0.3,  # FIX: Lowered from 0.7 to 0.3 for semantic search
        parent_expansion_percent: float = 0.25  # ±25% of parent text
    ):
        """
        Initialize retrieval pipeline.
        
        Args:
            embedding_generator: Embedding generator for query embedding
            core_store: Core index vector store
            longtail_store: Longtail index vector store
            two_tier_pipeline: Two-tier embedding pipeline (for parent lookup)
            core_top_k: Number of results from core index
            longtail_top_k: Number of results from longtail index (if needed)
            min_score_threshold: Minimum similarity score to consider
            parent_expansion_percent: Percentage of parent text to include (±25%)
        """
        self.embedding_generator = embedding_generator
        self.core_store = core_store
        self.longtail_store = longtail_store
        self.two_tier_pipeline = two_tier_pipeline
        self.core_top_k = core_top_k
        self.longtail_top_k = longtail_top_k
        self.min_score_threshold = min_score_threshold
        self.parent_expansion_percent = parent_expansion_percent
    
    def retrieve(
        self,
        query: str,
        use_longtail: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        use_query_rewriting: bool = True  # STEP 3: Enable query rewriting
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks for a query.
        
        STEP 3: Query rewriting enabled by default
        
        Args:
            query: Search query text
            use_longtail: Whether to also search longtail index
            filters: Optional metadata filters
            use_query_rewriting: Whether to generate query variants
            
        Returns:
            List of retrieval results with parent expansion
        """
        # STEP 3: Query rewriting - generate variants
        if use_query_rewriting:
            from .query_rewriter import QueryRewriter
            rewriter = QueryRewriter()
            query_variants = rewriter.rewrite(query)
        else:
            query_variants = [query]
        
        # Embed all query variants and merge results
        all_results = []
        seen_chunk_ids = set()
        
        for variant in query_variants:
            # Embed query variant
            query_embedding = self.embedding_generator.embed(variant)
            
            # Search core index
            core_results = self.core_store.query(
                query_vector=query_embedding,
                top_k=self.core_top_k,
                filters=filters
            )
            
            # Check if we need longtail (low scores or few results)
            strong_hits = [r for r in core_results if r.get('score', 0) >= self.min_score_threshold]
            
            if use_longtail or len(strong_hits) < 5:
                # Search longtail index
                longtail_results = self.longtail_store.query(
                    query_vector=query_embedding,
                    top_k=self.longtail_top_k,
                    filters=filters
                )
            else:
                longtail_results = []
            
            # Convert to RetrievalResult objects and merge
            for result in core_results:
                retrieval_result = self._create_retrieval_result(result, "core")
                if retrieval_result and retrieval_result.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(retrieval_result.chunk_id)
                    all_results.append(retrieval_result)
            
            for result in longtail_results:
                retrieval_result = self._create_retrieval_result(result, "longtail")
                if retrieval_result and retrieval_result.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(retrieval_result.chunk_id)
                    all_results.append(retrieval_result)
        
        # Sort by score (descending)
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply parent expansion
        expanded_results = self._expand_with_parents(all_results)
        
        # Deduplicate and group
        final_results = self._deduplicate_and_group(expanded_results)
        
        return final_results
    
    def _create_retrieval_result(
        self,
        result: Dict[str, Any],
        tier: str
    ) -> Optional[RetrievalResult]:
        """Create RetrievalResult from store result."""
        if result.get('score', 0) < self.min_score_threshold:
            return None
        
        return RetrievalResult(
            chunk_id=result.get('id', ''),
            text=result.get('text', ''),
            score=result.get('score', 0.0),
            video_id=result.get('video_id', ''),
            start_seconds=result.get('start_seconds', 0.0),
            end_seconds=result.get('end_seconds', 0.0),
            parent_id=result.get('parent_id'),
            speaker=result.get('speaker'),
            tier=tier
        )
    
    def _expand_with_parents(
        self,
        results: List[RetrievalResult],
        parent_loader: Optional['ParentChunkLoader'] = None
    ) -> List[RetrievalResult]:
        """
        STEP 2: Expand results with FULL parent chunk context.
        
        Retrieve with child → answer with parent.
        Fetches complete parent chunk text (not just ±25%).
        """
        expanded = []
        
        for result in results:
            if result.parent_id and result.video_id:
                # STEP 2: Try to get full parent from loader first
                if parent_loader:
                    parent_data = parent_loader.get_parent(result.video_id, result.parent_id)
                    if parent_data:
                        result.parent_text = parent_data['text']
                        # CITATION FIX: Populate video title and guest for proper citations
                        result.video_title = parent_data.get('title', '')
                        result.guest = parent_data.get('guest', '')
                        # Use guest as fallback speaker if speaker is missing
                        if not result.speaker and result.guest:
                            result.speaker = result.guest
                        expanded.append(result)
                        continue
                
                # Fallback: Try two_tier_pipeline (from embedding time)
                parent_text = self.two_tier_pipeline.get_parent_text(result.parent_id)
                if parent_text:
                    # Use FULL parent text (not just ±25%)
                    result.parent_text = parent_text
                else:
                    # No parent found - use child text
                    result.parent_text = result.text
            
            expanded.append(result)
        
        return expanded
    
    def _extract_parent_context(
        self,
        parent_text: str,
        child_text: str,
        percent: float
    ) -> str:
        """
        Extract surrounding context from parent text.
        
        Args:
            parent_text: Full parent chunk text
            child_text: Child chunk text (to find position)
            percent: Percentage of parent text to include (±percent)
            
        Returns:
            Expanded context text
        """
        # Find child text position in parent
        child_pos = parent_text.find(child_text)
        
        if child_pos == -1:
            # Child text not found in parent (shouldn't happen, but fallback)
            return parent_text
        
        # Calculate context window
        parent_len = len(parent_text)
        context_chars = int(parent_len * percent)
        
        # Extract surrounding text
        start = max(0, child_pos - context_chars)
        end = min(parent_len, child_pos + len(child_text) + context_chars)
        
        return parent_text[start:end]
    
    def _deduplicate_and_group(
        self,
        results: List[RetrievalResult],
        max_per_parent: int = 1,  # STEP 1: One idea per (video_id, parent_id)
        max_per_episode: int = 5
    ) -> List[RetrievalResult]:
        """
        Deduplicate and group results.
        
        STEP 1: Semantic deduplication by (video_id, parent_id)
        Rule: One (video_id, parent_id) = one idea
        Keep highest-scoring chunk per parent.
        
        Rules:
        - Keep top 1 chunk per (video_id, parent_id) - highest score
        - Keep top 5 chunks per episode
        """
        # STEP 1: Deduplicate by (video_id, parent_id) - keep highest score
        # This ensures one idea per parent, eliminating noise
        best_per_parent: Dict[tuple, RetrievalResult] = {}
        for result in results:
            if not result.video_id or not result.parent_id:
                continue  # Skip results without proper IDs
            
            key = (result.video_id, result.parent_id)
            
            if key not in best_per_parent:
                best_per_parent[key] = result
            else:
                # Keep the one with higher score
                if result.score > best_per_parent[key].score:
                    best_per_parent[key] = result
        
        # Convert back to list
        deduplicated = list(best_per_parent.values())
        
        # Group by parent_id
        by_parent: Dict[str, List[RetrievalResult]] = {}
        for result in deduplicated:
            parent_key = result.parent_id or "no_parent"
            if parent_key not in by_parent:
                by_parent[parent_key] = []
            by_parent[parent_key].append(result)
        
        # Group by episode (video_id)
        by_episode: Dict[str, List[RetrievalResult]] = {}
        for result in deduplicated:
            episode_key = result.video_id or "no_episode"
            if episode_key not in by_episode:
                by_episode[episode_key] = []
            by_episode[episode_key].append(result)
        
        # Keep top chunks per parent
        selected = []
        seen_texts = set()
        
        for parent_id, parent_results in by_parent.items():
            # Sort by score (already sorted, but ensure)
            parent_results.sort(key=lambda x: x.score, reverse=True)
            
            # Keep top max_per_parent
            for result in parent_results[:max_per_parent]:
                # Skip exact text duplicates
                text_key = result.text[:100]  # Use first 100 chars as key
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    selected.append(result)
        
        # Apply episode-level limit
        final_selected = []
        episode_counts: Dict[str, int] = {}
        
        for result in selected:
            episode_key = result.video_id or "no_episode"
            count = episode_counts.get(episode_key, 0)
            
            if count < max_per_episode:
                final_selected.append(result)
                episode_counts[episode_key] = count + 1
        
        # Re-sort by score
        final_selected.sort(key=lambda x: x.score, reverse=True)
        
        return final_selected
    
    def retrieve_with_parent_loader(
        self,
        query: str,
        parent_loader: 'ParentChunkLoader',
        use_longtail: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        use_query_rewriting: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve with parent loader for full parent expansion.
        
        STEP 2: Uses parent_loader to fetch full parent chunks from JSON.
        
        Args:
            query: Search query text
            parent_loader: ParentChunkLoader instance
            use_longtail: Whether to also search longtail index
            filters: Optional metadata filters
            use_query_rewriting: Whether to generate query variants
            
        Returns:
            List of retrieval results with full parent context
        """
        # Use standard retrieve first
        results = self.retrieve(
            query=query,
            use_longtail=use_longtail,
            filters=filters,
            use_query_rewriting=use_query_rewriting
        )
        
        # Then expand with parent loader
        expanded = self._expand_with_parents(results, parent_loader=parent_loader)
        
        return expanded
    
    def create_deep_link(
        self,
        video_id: str,
        start_seconds: float,
        lead_in: int = 5
    ) -> str:
        """
        Create YouTube deep link with lead-in.
        
        Args:
            video_id: YouTube video ID
            start_seconds: Start time in seconds
            lead_in: Seconds to subtract for lead-in
            
        Returns:
            YouTube URL with timestamp
        """
        adjusted_start = max(0, int(start_seconds) - lead_in)
        return f"https://www.youtube.com/watch?v={video_id}&t={adjusted_start}s"
