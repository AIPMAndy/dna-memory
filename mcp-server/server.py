#!/opt/homebrew/opt/python@3.11/bin/python3.11
"""
DNA Memory MCP Server
Exposes DNA Memory functionality through Model Context Protocol
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import handlers
import config
import evolve

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get_log_level()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dna-memory-mcp")

# Initialize MCP server
app = Server("dna-memory")

# ============ Tools Registration ============

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available DNA Memory tools"""
    return [
        Tool(
            name="dna_remember",
            description="Add new memory to DNA Memory. Supports different types (fact, preference, skill, error, pattern, insight) and importance weights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["fact", "preference", "skill", "error", "pattern", "insight"],
                        "default": "fact",
                        "description": "Memory type"
                    },
                    "tags": {
                        "type": "string",
                        "default": "",
                        "description": "Tags, comma-separated"
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.6,
                        "description": "Importance weight (0-1)"
                    },
                    "short_term": {
                        "type": "boolean",
                        "default": True,
                        "description": "Add to short-term memory"
                    },
                    "long_term": {
                        "type": "boolean",
                        "default": False,
                        "description": "Add directly to long-term memory"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="dna_recall",
            description="Search memories. Supports multi-keyword AND search, type filters (type:error), and FTS5 full-text search. Returns list of relevant memories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords, supports 'type:skill keyword' format for filtering"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of results"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="dna_reflect",
            description="Reflect on memories. Extract patterns from high-weight short-term memories and auto-promote stable memories to long-term layer. Recommended after completing important tasks or periodically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_weight": {
                        "type": "number",
                        "default": 0.7,
                        "description": "Minimum weight threshold for reflection"
                    }
                }
            }
        ),
        Tool(
            name="dna_decay",
            description="Execute weight decay. Reduce weights of long-unaccessed memories, letting unimportant memories fade. Supports recency-sensitive mode (recent access = slower decay).",
            inputSchema={
                "type": "object",
                "properties": {
                    "factor": {
                        "type": "number",
                        "default": 0.95,
                        "minimum": 0.5,
                        "maximum": 0.99,
                        "description": "Decay factor, closer to 1 = slower decay"
                    },
                    "use_recency": {
                        "type": "boolean",
                        "default": True,
                        "description": "Use recency-sensitive decay (recent access = slower decay)"
                    }
                }
            }
        ),
        Tool(
            name="dna_stats",
            description="Get DNA Memory statistics. Returns total memories, short-term/long-term counts, average weight, type distribution, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Return detailed statistics (including type distribution, weight distribution)"
                    }
                }
            }
        ),
        Tool(
            name="dna_working_memory",
            description="Operate on working memory (7-item capacity for current session context). Can add, view, or clear working memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "get", "clear"],
                        "description": "Operation: add, get, or clear"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to add (required when action=add)"
                    },
                    "importance": {
                        "type": "number",
                        "default": 0.8,
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Importance (only for add)"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="dna_link",
            description="Create memory association. Establish relationship link between two memories for knowledge graph construction.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id1": {
                        "type": "integer",
                        "description": "First memory ID"
                    },
                    "memory_id2": {
                        "type": "integer",
                        "description": "Second memory ID"
                    },
                    "relation_type": {
                        "type": "string",
                        "default": "related",
                        "description": "Relation type (e.g., related, causes, improves)"
                    },
                    "weight": {
                        "type": "number",
                        "default": 0.5,
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Relation strength"
                    }
                },
                "required": ["memory_id1", "memory_id2"]
            }
        ),
        Tool(
            name="dna_promote",
            description="Manually promote memory to long-term layer. Elevate important short-term memory to long-term for permanent retention.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "Memory ID to promote (from recall results)"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="dna_forget",
            description="Delete specified memory or execute auto-cleanup. Can delete single memory or clean all memories below threshold.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "integer",
                        "description": "Memory ID to delete (omit for auto-cleanup)"
                    },
                    "threshold": {
                        "type": "number",
                        "default": 0.25,
                        "description": "Weight threshold for auto-cleanup"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")

        # Route to appropriate handler
        if name == "dna_remember":
            result = handlers.handle_remember(**arguments)
        elif name == "dna_recall":
            result = handlers.handle_recall(**arguments)
        elif name == "dna_reflect":
            result = handlers.handle_reflect(**arguments)
        elif name == "dna_decay":
            result = handlers.handle_decay(**arguments)
        elif name == "dna_stats":
            result = handlers.handle_stats(**arguments)
        elif name == "dna_working_memory":
            result = handlers.handle_working_memory(**arguments)
        elif name == "dna_link":
            result = handlers.handle_link(**arguments)
        elif name == "dna_promote":
            result = handlers.handle_promote(**arguments)
        elif name == "dna_forget":
            result = handlers.handle_forget(**arguments)
        else:
            result = {
                "success": False,
                "error": f"Unknown tool: {name}"
            }

        # Return result as TextContent
        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Tool execution failed: {str(e)}"
            }, ensure_ascii=False, indent=2)
        )]


# ============ Resources Registration ============

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available DNA Memory resources"""
    return [
        Resource(
            uri="dna://stats/summary",
            name="DNA Memory Statistics Summary",
            mimeType="application/json",
            description="Real-time statistics including total memories, short-term/long-term distribution, average weight"
        ),
        Resource(
            uri="dna://working/current",
            name="Current Working Memory",
            mimeType="application/json",
            description="Current session working memory list (max 7 items)"
        ),
        Resource(
            uri="dna://memories/recent",
            name="Recent Memories",
            mimeType="application/json",
            description="Recently added or accessed memories list (max 20 items)"
        ),
        Resource(
            uri="dna://memories/high-value",
            name="High-Value Memories",
            mimeType="application/json",
            description="Highest-weight memories list (max 20 items)"
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Handle resource read requests"""
    try:
        logger.info(f"Resource requested: {uri}")

        if uri == "dna://stats/summary":
            result = handlers.get_stats_summary()
        elif uri == "dna://working/current":
            result = handlers.get_working_current()
        elif uri == "dna://memories/recent":
            result = handlers.get_recent_memories()
        elif uri == "dna://memories/high-value":
            result = handlers.get_high_value_memories()
        else:
            result = {
                "success": False,
                "error": f"Unknown resource: {uri}"
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


# ============ Main Entry Point ============

async def main():
    """Main entry point for MCP server"""
    logger.info("Starting DNA Memory MCP Server")

    # Initialize database
    try:
        evolve.init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP server running on stdio")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
