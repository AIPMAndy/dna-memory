# DNA Memory MCP Server

MCP (Model Context Protocol) server for DNA Memory system. Exposes DNA Memory functionality to Claude Desktop and Claude Code through standardized MCP interface.

## Features

- **9 Tools**: remember, recall, reflect, decay, stats, working_memory, link, promote, forget
- **4 Resources**: stats summary, working memory, recent memories, high-value memories
- **Reuses existing logic**: No code duplication, adapts `evolve.py` functionality
- **Auto-initialization**: Creates database and files on first run

## Installation

### 1. Install MCP Python SDK

```bash
pip3 install mcp
```

### 2. Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dna-memory": {
      "command": "python3",
      "args": [
        "/Users/andy/Desktop/04 AICode/dna-memory-review/mcp-server/server.py"
      ],
      "env": {
        "DNA_MEMORY_DIR": "/Users/andy/Desktop/04 AICode/dna-memory-review/memory",
        "DNA_MEMORY_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Note**: Adjust paths to match your installation.

### 3. Restart Claude Desktop

Quit and restart Claude Desktop for changes to take effect.

### 4. Quick Installation Script

Run the provided installation script:

```bash
chmod +x install.sh
./install.sh
```

This will:
- Check dependencies
- Create configuration entry
- Backup existing config
- Provide restart instructions

## Usage

### In Claude Desktop or Claude Code

Once configured, DNA Memory tools are available automatically:

```
# Add a memory
Use dna_remember to remember: "User prefers React over Vue"

# Search memories
Use dna_recall to search for "React"

# View statistics
Use dna_stats to show memory statistics

# Working memory operations
Use dna_working_memory with action="get" to see current context
```

### Available Tools

1. **dna_remember** - Add new memory
   - Parameters: content (required), type, tags, importance, short_term, long_term
   
2. **dna_recall** - Search memories
   - Parameters: query (required), limit
   
3. **dna_reflect** - Reflect and extract patterns
   - Parameters: min_weight
   
4. **dna_decay** - Apply weight decay
   - Parameters: factor, use_recency
   
5. **dna_stats** - Get statistics
   - Parameters: detailed
   
6. **dna_working_memory** - Operate working memory
   - Parameters: action (required: add/get/clear), content, importance
   
7. **dna_link** - Create memory association
   - Parameters: memory_id1 (required), memory_id2 (required), relation_type, weight
   
8. **dna_promote** - Promote to long-term
   - Parameters: memory_id (required)
   
9. **dna_forget** - Delete or cleanup
   - Parameters: memory_id, threshold

### Available Resources

Access via URI:

1. `dna://stats/summary` - Statistics summary
2. `dna://working/current` - Current working memory
3. `dna://memories/recent` - Recent memories (20 max)
4. `dna://memories/high-value` - High-value memories (20 max)

## Configuration

### Environment Variables

- `DNA_MEMORY_DIR`: Memory data directory (default: `~/.openclaw/workspace/dna-memory/memory`)
- `DNA_MEMORY_CONFIG`: Config file path (default: `~/.openclaw/workspace/dna-memory/assets/config.json`)
- `DNA_MEMORY_LOG_LEVEL`: Logging level (default: INFO, options: DEBUG, INFO, WARNING, ERROR)

### File Structure

```
mcp-server/
├── server.py          # Main MCP server
├── handlers.py        # Tool handlers (adapts evolve.py)
├── config.py          # Configuration loader
├── requirements.txt   # Python dependencies
├── README.md          # This file
└── install.sh         # Installation script
```

## Verification

### Test Server Directly

```bash
# Test server initialization
echo '{}' | python3 server.py
```

### Test in Claude

In Claude Desktop or Claude Code:

```
Use dna_stats to show memory statistics
```

Expected output: JSON with total, short_term, long_term counts.

## Troubleshooting

### Server Not Appearing

1. Check config path: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Verify JSON syntax (use `jq . < config.json`)
3. Check server logs in Claude Desktop developer console
4. Restart Claude Desktop completely

### Database Errors

1. Check `DNA_MEMORY_DIR` path exists and is writable
2. Run `python3 ../scripts/evolve.py stats` to verify database
3. Check logs for specific SQLite errors

### Import Errors

1. Verify MCP SDK installed: `pip3 show mcp`
2. Check Python version: `python3 --version` (requires 3.8+)
3. Ensure `scripts/evolve.py` exists in parent directory

## Architecture

### Adapter Pattern

MCP server acts as an adapter layer:

```
Claude Desktop/Code
    ↓ (MCP Protocol)
server.py (MCP Server)
    ↓ (Function calls)
handlers.py (Adapter)
    ↓ (Direct imports)
evolve.py (Business Logic)
    ↓
memory.db (SQLite)
```

**Benefits**:
- No code duplication
- Single source of truth
- Easy maintenance
- Consistent behavior

### Error Handling

- SQLite exceptions → Friendly error messages
- Missing files → Auto-initialization
- Invalid parameters → Clear validation errors
- Concurrent access → Reuses evolve.py file locks

## Development

### Adding New Tools

1. Add handler function in `handlers.py`
2. Register tool in `server.py` `list_tools()`
3. Add routing in `server.py` `call_tool()`
4. Update this README

### Testing

```bash
# Run syntax check
python3 -m py_compile server.py handlers.py config.py

# Test specific handler
python3 -c "import handlers; print(handlers.handle_stats(detailed=True))"

# Full integration test
cd .. && python3 -m pytest tests/
```

## License

Same as DNA Memory project (see parent LICENSE file).

## Support

For issues specific to MCP integration, check:
- MCP SDK docs: https://github.com/modelcontextprotocol/python-sdk
- Claude Desktop MCP guide: https://docs.anthropic.com/claude/docs/mcp
- DNA Memory issues: https://github.com/your-repo/issues
