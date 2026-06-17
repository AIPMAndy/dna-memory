#!/bin/bash
# DNA Memory MCP Server Installation Script

set -e

echo "🧬 DNA Memory MCP Server Installation"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get absolute paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
SERVER_PATH="$SCRIPT_DIR/server.py"
MEMORY_DIR="$PROJECT_DIR/memory"
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

echo ""
echo "📁 Detected paths:"
echo "   Server: $SERVER_PATH"
echo "   Memory: $MEMORY_DIR"
echo "   Config: $CONFIG_FILE"
echo ""

# Step 1: Check Python
echo "1️⃣  Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "   Please install Python 3.8+ first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Step 2: Check MCP SDK
echo ""
echo "2️⃣  Checking MCP SDK..."
if ! python3 -c "import mcp" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  MCP SDK not found${NC}"
    echo "   Installing MCP SDK..."
    pip3 install -q mcp
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MCP SDK installed${NC}"
    else
        echo -e "${RED}❌ Failed to install MCP SDK${NC}"
        echo "   Try manually: pip3 install mcp"
        exit 1
    fi
else
    echo -e "${GREEN}✅ MCP SDK already installed${NC}"
fi

# Step 3: Verify files
echo ""
echo "3️⃣  Verifying server files..."
for file in server.py handlers.py config.py requirements.txt; do
    if [ ! -f "$SCRIPT_DIR/$file" ]; then
        echo -e "${RED}❌ Missing file: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All server files present${NC}"

# Step 4: Check evolve.py
echo ""
echo "4️⃣  Checking evolve.py..."
if [ ! -f "$PROJECT_DIR/scripts/evolve.py" ]; then
    echo -e "${RED}❌ evolve.py not found at $PROJECT_DIR/scripts/evolve.py${NC}"
    exit 1
fi
echo -e "${GREEN}✅ evolve.py found${NC}"

# Step 5: Test syntax
echo ""
echo "5️⃣  Checking Python syntax..."
python3 -m py_compile "$SCRIPT_DIR/server.py" "$SCRIPT_DIR/handlers.py" "$SCRIPT_DIR/config.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All files pass syntax check${NC}"
else
    echo -e "${RED}❌ Syntax errors detected${NC}"
    exit 1
fi

# Step 6: Create memory directory
echo ""
echo "6️⃣  Setting up memory directory..."
mkdir -p "$MEMORY_DIR"
echo -e "${GREEN}✅ Memory directory ready${NC}"

# Step 7: Configure Claude Desktop
echo ""
echo "7️⃣  Configuring Claude Desktop..."

# Create config directory if needed
CONFIG_DIR="$(dirname "$CONFIG_FILE")"
mkdir -p "$CONFIG_DIR"

# Backup existing config
if [ -f "$CONFIG_FILE" ]; then
    BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Backed up existing config to:${NC}"
    echo "   $BACKUP_FILE"
fi

# Generate new config entry
NEW_ENTRY=$(cat <<EOF
{
  "mcpServers": {
    "dna-memory": {
      "command": "python3",
      "args": [
        "$SERVER_PATH"
      ],
      "env": {
        "DNA_MEMORY_DIR": "$MEMORY_DIR",
        "DNA_MEMORY_LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF
)

# Merge or create config
if [ -f "$CONFIG_FILE" ]; then
    # Check if jq is available for JSON merging
    if command -v jq &> /dev/null; then
        # Merge with existing config
        TEMP_FILE=$(mktemp)
        echo "$NEW_ENTRY" | jq -s '.[0] * .[1]' "$CONFIG_FILE" - > "$TEMP_FILE"
        mv "$TEMP_FILE" "$CONFIG_FILE"
        echo -e "${GREEN}✅ Config merged with existing settings${NC}"
    else
        echo -e "${YELLOW}⚠️  jq not found, cannot auto-merge config${NC}"
        echo ""
        echo "Please manually add this to $CONFIG_FILE:"
        echo ""
        echo "$NEW_ENTRY" | sed 's/^/   /'
        echo ""
    fi
else
    # Create new config
    echo "$NEW_ENTRY" > "$CONFIG_FILE"
    echo -e "${GREEN}✅ Config file created${NC}"
fi

# Step 8: Verify config
echo ""
echo "8️⃣  Verifying configuration..."
if python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
    echo -e "${GREEN}✅ Config file is valid JSON${NC}"
else
    echo -e "${RED}❌ Config file has JSON syntax errors${NC}"
    echo "   Please check: $CONFIG_FILE"
    exit 1
fi

# Done
echo ""
echo "======================================"
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo "======================================"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Restart Claude Desktop:"
echo "   - Quit Claude Desktop completely"
echo "   - Start it again"
echo ""
echo "2. Test the server:"
echo "   In Claude Desktop or Claude Code, try:"
echo "   'Use dna_stats to show memory statistics'"
echo ""
echo "3. Check logs if issues occur:"
echo "   - Open Claude Desktop Developer Console"
echo "   - Look for 'dna-memory' server logs"
echo ""
echo "📚 Documentation: $SCRIPT_DIR/README.md"
echo ""
