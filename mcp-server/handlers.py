#!/usr/bin/env python3
"""
Tool handlers for DNA Memory MCP Server
Adapts existing evolve.py functionality to MCP tools
"""

import sys
import json
from pathlib import Path

# Add parent directory to path to import evolve
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import evolve


# ============ Tool Handlers ============

def handle_remember(content: str, type: str = "fact", tags: str = "",
                   importance: float = 0.6, short_term: bool = True,
                   long_term: bool = False) -> dict:
    """
    Handle dna_remember tool
    Add new memory to DNA Memory
    """
    try:
        # Convert boolean parameters to int for evolve.py
        short_term_int = 1 if short_term else 0
        long_term_int = 1 if long_term else 0

        # Call existing function
        memory_id = evolve.add_memory(
            content=content,
            mem_type=type,
            tags=tags,
            importance=importance,
            short_term=short_term_int,
            long_term=long_term_int
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "content": content,
            "type": type,
            "importance": importance,
            "message": f"Memory added successfully (ID: {memory_id})"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add memory: {str(e)}"
        }


def handle_recall(query: str, limit: int = 10) -> dict:
    """
    Handle dna_recall tool
    Search memories with FTS5 and filters
    """
    try:
        memories = evolve.search_memories(query=query, limit=limit)

        return {
            "success": True,
            "count": len(memories),
            "memories": memories,
            "query": query,
            "message": f"Found {len(memories)} memories"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "memories": [],
            "message": f"Search failed: {str(e)}"
        }


def handle_reflect(min_weight: float = 0.7) -> dict:
    """
    Handle dna_reflect tool
    Reflect on memories and auto-promote patterns
    """
    try:
        # Get high-weight short-term memories
        conn = evolve.get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, weight, type
            FROM memory
            WHERE short_term = 1 AND weight >= ?
            ORDER BY weight DESC
            LIMIT 20
        """, (min_weight,))

        candidates = cursor.fetchall()

        # Find patterns
        patterns = evolve.find_patterns()

        # Auto-promote stable memories
        promoted = evolve.auto_promote(threshold=min_weight)

        conn.close()

        return {
            "success": True,
            "candidates_count": len(candidates),
            "patterns_found": len(patterns),
            "promoted_count": promoted,
            "patterns": patterns[:5],  # Return top 5 patterns
            "message": f"Reflection complete: {promoted} memories promoted, {len(patterns)} patterns found"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Reflection failed: {str(e)}"
        }


def handle_decay(factor: float = 0.95, use_recency: bool = True) -> dict:
    """
    Handle dna_decay tool
    Apply weight decay to memories
    """
    try:
        affected = evolve.auto_decay(factor=factor, use_recency=use_recency)

        return {
            "success": True,
            "affected_count": affected,
            "decay_factor": factor,
            "use_recency": use_recency,
            "message": f"Decay applied to {affected} memories"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Decay failed: {str(e)}"
        }


def handle_stats(detailed: bool = False) -> dict:
    """
    Handle dna_stats tool
    Get DNA Memory statistics
    """
    try:
        stats = evolve.get_stats()

        if not detailed:
            # Return basic stats only
            basic_stats = {
                "total": stats.get("total", 0),
                "short_term": stats.get("short_term", 0),
                "long_term": stats.get("long_term", 0),
                "avg_weight": stats.get("avg_weight", 0),
            }
            return {
                "success": True,
                "stats": basic_stats,
                "message": "Statistics retrieved"
            }

        return {
            "success": True,
            "stats": stats,
            "message": "Detailed statistics retrieved"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get statistics: {str(e)}"
        }


def handle_working_memory(action: str, content: str = None, importance: float = 0.8) -> dict:
    """
    Handle dna_working_memory tool
    Operate on working memory (7-item capacity)
    """
    try:
        if action == "add":
            if not content:
                return {
                    "success": False,
                    "error": "content is required for action=add",
                    "message": "Missing content parameter"
                }
            memories = evolve.add_working_memory(content=content, importance=importance)
            return {
                "success": True,
                "action": "add",
                "count": len(memories),
                "memories": memories,
                "message": f"Added to working memory ({len(memories)}/7)"
            }

        elif action == "get":
            memories = evolve.get_working_memory()
            return {
                "success": True,
                "action": "get",
                "count": len(memories),
                "memories": memories,
                "message": f"Retrieved {len(memories)} working memories"
            }

        elif action == "clear":
            evolve.clear_working_memory()
            return {
                "success": True,
                "action": "clear",
                "count": 0,
                "memories": [],
                "message": "Working memory cleared"
            }

        else:
            return {
                "success": False,
                "error": f"Invalid action: {action}",
                "message": "Action must be one of: add, get, clear"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Working memory operation failed: {str(e)}"
        }


def handle_link(memory_id1: int, memory_id2: int,
               relation_type: str = "related", weight: float = 0.5) -> dict:
    """
    Handle dna_link tool
    Create relationship between two memories
    """
    try:
        conn = evolve.get_db()
        cursor = conn.cursor()

        # Verify both memories exist
        cursor.execute("SELECT id FROM memory WHERE id IN (?, ?)", (memory_id1, memory_id2))
        if len(cursor.fetchall()) != 2:
            conn.close()
            return {
                "success": False,
                "error": "One or both memory IDs not found",
                "message": "Invalid memory IDs"
            }

        # Check if link already exists
        cursor.execute("""
            SELECT id FROM memory_relations
            WHERE (memory_id1 = ? AND memory_id2 = ?)
               OR (memory_id1 = ? AND memory_id2 = ?)
        """, (memory_id1, memory_id2, memory_id2, memory_id1))

        if cursor.fetchone():
            conn.close()
            return {
                "success": False,
                "error": "Link already exists",
                "message": "These memories are already linked"
            }

        # Create link
        cursor.execute("""
            INSERT INTO memory_relations (memory_id1, memory_id2, relation_type, weight)
            VALUES (?, ?, ?, ?)
        """, (memory_id1, memory_id2, relation_type, weight))

        link_id = cursor.lastrowid
        conn.commit()
        conn.close()

        evolve.log_operation("link_create", f"{memory_id1} <-{relation_type}-> {memory_id2}")

        return {
            "success": True,
            "link_id": link_id,
            "memory_id1": memory_id1,
            "memory_id2": memory_id2,
            "relation_type": relation_type,
            "weight": weight,
            "message": f"Link created between memories {memory_id1} and {memory_id2}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create link: {str(e)}"
        }


def handle_promote(memory_id: int) -> dict:
    """
    Handle dna_promote tool
    Manually promote memory to long-term layer
    """
    try:
        conn = evolve.get_db()
        cursor = conn.cursor()

        # Check if memory exists
        cursor.execute("SELECT id, content, long_term FROM memory WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {
                "success": False,
                "error": "Memory not found",
                "message": f"No memory with ID {memory_id}"
            }

        if row[2] == 1:
            conn.close()
            return {
                "success": False,
                "error": "Already in long-term",
                "message": "This memory is already in long-term layer"
            }

        # Promote to long-term
        cursor.execute("""
            UPDATE memory
            SET long_term = 1, weight = MAX(weight, 0.8)
            WHERE id = ?
        """, (memory_id,))

        conn.commit()
        conn.close()

        evolve.log_operation("promote", f"Memory {memory_id} promoted to long-term")

        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory {memory_id} promoted to long-term layer"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to promote memory: {str(e)}"
        }


def handle_forget(memory_id: int = None, threshold: float = 0.25) -> dict:
    """
    Handle dna_forget tool
    Delete specific memory or auto-clean low-weight memories
    """
    try:
        if memory_id is not None:
            # Delete specific memory
            conn = evolve.get_db()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM memory WHERE id = ?", (memory_id,))
            if not cursor.fetchone():
                conn.close()
                return {
                    "success": False,
                    "error": "Memory not found",
                    "message": f"No memory with ID {memory_id}"
                }

            cursor.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
            cursor.execute("DELETE FROM memory_relations WHERE memory_id1 = ? OR memory_id2 = ?",
                         (memory_id, memory_id))

            conn.commit()
            conn.close()

            evolve.log_operation("forget", f"Memory {memory_id} deleted")

            return {
                "success": True,
                "memory_id": memory_id,
                "message": f"Memory {memory_id} deleted"
            }
        else:
            # Auto-clean
            deleted = evolve.auto_forget(threshold=threshold)
            return {
                "success": True,
                "deleted_count": deleted,
                "threshold": threshold,
                "message": f"Auto-clean: {deleted} low-weight memories deleted"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Forget operation failed: {str(e)}"
        }


# ============ Resource Handlers ============

def get_stats_summary() -> dict:
    """Get statistics summary resource"""
    try:
        stats = evolve.get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_working_current() -> dict:
    """Get current working memory resource"""
    try:
        memories = evolve.get_working_memory()
        return {
            "success": True,
            "count": len(memories),
            "data": memories
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_recent_memories() -> dict:
    """Get recent memories resource"""
    try:
        conn = evolve.get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, type, weight, short_term, long_term,
                   created, updated, last_accessed
            FROM memory
            ORDER BY updated DESC
            LIMIT 20
        """)

        columns = ["id", "content", "type", "weight", "short_term", "long_term",
                   "created", "updated", "last_accessed"]
        memories = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()

        return {
            "success": True,
            "count": len(memories),
            "data": memories
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_high_value_memories() -> dict:
    """Get high-value memories resource"""
    try:
        conn = evolve.get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, type, weight, short_term, long_term,
                   created, updated, last_accessed
            FROM memory
            ORDER BY weight DESC
            LIMIT 20
        """)

        columns = ["id", "content", "type", "weight", "short_term", "long_term",
                   "created", "updated", "last_accessed"]
        memories = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()

        return {
            "success": True,
            "count": len(memories),
            "data": memories
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
