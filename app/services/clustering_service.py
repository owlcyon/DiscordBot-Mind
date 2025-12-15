"""
SEMANTIC CLUSTERING SERVICE
Performs clustering analysis on Discord message embeddings.
Enables topic discovery, author profiling, and ideological mapping.
"""

import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

import numpy as np
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from app.models.message import DiscordMessage
from app.services.embedding_service import get_embedding_service


@dataclass
class TopicCluster:
    """Represents a discovered topic cluster."""
    cluster_id: int
    message_count: int
    representative_messages: List[str]
    top_authors: List[Tuple[str, int]]  # (author_id, message_count)
    centroid: np.ndarray


@dataclass
class AuthorProfile:
    """Semantic profile of an author based on their message embeddings."""
    author_id: str
    message_count: int
    idea_centroid: np.ndarray  # Average embedding = "idea fingerprint"
    sample_messages: List[str]


class ClusteringService:
    """
    Provides semantic analysis through clustering of vector embeddings.
    Implements: Topic discovery, author profiling, similarity matching.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = get_embedding_service()
    
    def get_all_embeddings(self) -> Tuple[List[DiscordMessage], np.ndarray]:
        """Fetch all messages with their embeddings."""
        messages = self.db.scalars(
            select(DiscordMessage).order_by(DiscordMessage.created_at.desc())
        ).all()
        
        if not messages:
            return [], np.array([])
        
        embeddings = np.array([msg.embedding for msg in messages])
        return messages, embeddings
    
    def discover_topics(self, n_clusters: int = 5) -> List[TopicCluster]:
        """
        Discover topic clusters using K-means on message embeddings.
        Returns clusters with representative messages and top contributors.
        """
        messages, embeddings = self.get_all_embeddings()
        
        if len(messages) < n_clusters:
            return []
        
        # Fit K-means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        clusters = []
        for cluster_id in range(n_clusters):
            # Get messages in this cluster
            cluster_mask = labels == cluster_id
            cluster_messages = [m for m, in_cluster in zip(messages, cluster_mask) if in_cluster]
            cluster_embeddings = embeddings[cluster_mask]
            
            if not cluster_messages:
                continue
            
            # Find representative messages (closest to centroid)
            centroid = kmeans.cluster_centers_[cluster_id]
            distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
            sorted_indices = np.argsort(distances)[:3]  # Top 3 closest
            representative = [cluster_messages[i].content[:200] for i in sorted_indices]
            
            # Count authors in cluster
            author_counts = defaultdict(int)
            for msg in cluster_messages:
                author_counts[msg.author_id] += 1
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            clusters.append(TopicCluster(
                cluster_id=cluster_id,
                message_count=len(cluster_messages),
                representative_messages=representative,
                top_authors=top_authors,
                centroid=centroid
            ))
        
        return sorted(clusters, key=lambda c: c.message_count, reverse=True)
    
    def get_author_profile(self, author_id: str) -> Optional[AuthorProfile]:
        """
        Build semantic profile for an author.
        Their "idea fingerprint" is the average of all their message embeddings.
        """
        messages = self.db.scalars(
            select(DiscordMessage)
            .where(DiscordMessage.author_id == author_id)
            .order_by(DiscordMessage.created_at.desc())
        ).all()
        
        if not messages:
            return None
        
        embeddings = np.array([msg.embedding for msg in messages])
        idea_centroid = np.mean(embeddings, axis=0)
        
        # Get sample messages (most recent)
        samples = [msg.content[:200] for msg in messages[:5]]
        
        return AuthorProfile(
            author_id=author_id,
            message_count=len(messages),
            idea_centroid=idea_centroid,
            sample_messages=samples
        )
    
    def find_similar_thinkers(self, author_id: str, top_n: int = 5
                              ) -> List[Tuple[str, float, int]]:
        """
        Find authors with similar thinking patterns.
        Returns list of (author_id, similarity_score, message_count).
        """
        target_profile = self.get_author_profile(author_id)
        if target_profile is None:
            return []
        
        # Get all unique authors
        authors = self.db.execute(
            select(DiscordMessage.author_id, func.count(DiscordMessage.id))
            .group_by(DiscordMessage.author_id)
        ).all()
        
        similarities = []
        for other_author_id, msg_count in authors:
            if other_author_id == author_id:
                continue
            
            other_profile = self.get_author_profile(other_author_id)
            if other_profile is None:
                continue
            
            # Compute cosine similarity between idea centroids
            sim = cosine_similarity(
                target_profile.idea_centroid.reshape(1, -1),
                other_profile.idea_centroid.reshape(1, -1)
            )[0][0]
            
            similarities.append((other_author_id, float(sim), msg_count))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]
    
    def attribute_idea(self, idea_text: str, top_n: int = 3
                       ) -> List[Tuple[str, float, str]]:
        """
        Given an idea/phrase, find which authors are most likely to have said it.
        Returns list of (author_id, similarity_score, sample_message).
        """
        # Embed the idea
        idea_embedding = self.embedding_service.embed_batch([idea_text])[0]
        idea_vec = np.array(idea_embedding).reshape(1, -1)
        
        # Get all unique authors with their profiles
        authors = self.db.execute(
            select(DiscordMessage.author_id).distinct()
        ).scalars().all()
        
        attributions = []
        for author_id in authors:
            profile = self.get_author_profile(author_id)
            if profile is None:
                continue
            
            # Similarity between idea and author's centroid
            sim = cosine_similarity(idea_vec, profile.idea_centroid.reshape(1, -1))[0][0]
            sample = profile.sample_messages[0] if profile.sample_messages else ""
            
            attributions.append((author_id, float(sim), sample))
        
        return sorted(attributions, key=lambda x: x[1], reverse=True)[:top_n]
    
    def get_cluster_summary(self) -> Dict:
        """Get overall clustering statistics."""
        total_messages = self.db.scalar(select(func.count(DiscordMessage.id)))
        unique_authors = self.db.scalar(
            select(func.count(func.distinct(DiscordMessage.author_id)))
        )
        
        return {
            "total_messages": total_messages or 0,
            "unique_authors": unique_authors or 0,
            "embeddings_dimension": 1536,
            "status": "active" if total_messages and total_messages > 0 else "awaiting data"
        }


def get_clustering_service(db: Session) -> ClusteringService:
    """Dependency injection for clustering service."""
    return ClusteringService(db)
