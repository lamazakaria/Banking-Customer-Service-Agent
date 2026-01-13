"""
Google ADK MCP Client using MCPToolset
Connects to FastMCP server and imports tools for agent use
"""
import asyncio
import threading
import logging
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset,SseConnectionParams

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global thread and loop for MCP tools
_mcp_thread = None
_mcp_loop = None
_mcp_tools_ready = threading.Event()
_mcp_tools_result = None
_mcp_tools_error = None


class MCPTools(BaseModel):
    """Manages tools from MCP Server with Google ADK"""
    
    sse_url: str = "http://localhost:8000/sse"  # MCP Server SSE endpoint
    

    
    async def get_tools_async(self,tool_filter: Optional[list] = None):
        """
        Gets tools from MCP Server asynchronously.
        
        Returns:
            MCPToolset instance with all registered tools
        """
        logger.info(f"🔌 Attempting to connect to MCP server at {self.sse_url}...")
        
        try:
            # Create toolset with SSE connection
            toolset = MCPToolset(
                connection_params=SseConnectionParams(url=self.sse_url),
                tool_filter=tool_filter  # None = import all tools
            )
            
            logger.info("✅ MCP Toolset created successfully")
            tools = await toolset.get_tools()  # await the coroutine
            logger.info(f"📦 Available tools: {len(tools)} tools loaded")
            
            # List all tools
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description}")
            
            return toolset
            
        except Exception as e:
            logger.error(f"❌ Error connecting to MCP server: {e}")
            raise e
    
    def get_tools_sync(self):
        """
        Gets tools from MCP Server synchronously (for Google ADK agent).
        Runs async code in a separate thread.
        
        Returns:
            MCPToolset instance
        """
        global _mcp_thread, _mcp_loop, _mcp_tools_ready, _mcp_tools_result, _mcp_tools_error
        
        def run_async_in_thread():
            """Run async event loop in separate thread"""
            global _mcp_loop, _mcp_tools_result, _mcp_tools_error
            
            _mcp_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_mcp_loop)
            
            try:
                _mcp_tools_result = _mcp_loop.run_until_complete(
                    self.get_tools_async()
                )
            except Exception as e:
                _mcp_tools_error = e
            finally:
                _mcp_tools_ready.set()
        
        # Start thread if not already running
        if _mcp_thread is None or not _mcp_thread.is_alive():
            _mcp_tools_ready.clear()
            _mcp_thread = threading.Thread(target=run_async_in_thread, daemon=True)
            _mcp_thread.start()
        
        # Wait for tools to be ready
        _mcp_tools_ready.wait()
        
        if _mcp_tools_error:
            raise _mcp_tools_error
        
        return _mcp_tools_result


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

async def example_async_usage():
    """Example: Use MCP tools asynchronously"""
    logger.info("\n" + "="*60)
    logger.info("🧪 ASYNC USAGE EXAMPLE")
    logger.info("="*60)
    
    mcp_tools = MCPTools(
        sse_url="http://localhost:8000/sse"
    )
    
    # Get all tools from MCP server
    toolset = await mcp_tools.get_tools_async()
    
    # Now toolset can be used with Google ADK Agent
    logger.info("\n✅ Toolset ready for Google ADK Agent integration")
    
    return toolset


def example_sync_usage():
    """Example: Use MCP tools synchronously (for agent integration)"""
    logger.info("\n" + "="*60)
    logger.info("🧪 SYNC USAGE EXAMPLE (For Google ADK Agent)")
    logger.info("="*60)
    
    mcp_tools = MCPTools(
        sse_url="http://localhost:8000/mcp/sse",
        # Optional: filter specific tools
        # tool_filter=['get_customer', 'get_account', 'add']
    )
    
    # Get tools synchronously (blocks until ready)
    toolset = mcp_tools.get_tools_sync()
    
    logger.info("\n✅ Toolset ready for Google ADK Agent")
    logger.info(f"📊 Total tools available: {len(toolset.get_tools())}")
    
    return toolset


async def example_filtered_tools():
    """Example: Import only specific tools"""
    logger.info("\n" + "="*60)
    logger.info("🧪 FILTERED TOOLS EXAMPLE")
    logger.info("="*60)
    
    mcp_tools = MCPTools(
        sse_url="http://localhost:8000/mcp/sse",
        tool_filter=[
            'get_customer',
            'get_account', 
            'get_account_transactions',
            'add',
            'multiply'
        ]
    )
    
    toolset = await mcp_tools.get_tools_async()
    
    logger.info(f"\n✅ Filtered toolset ready")
    logger.info(f"📊 Loaded {len(toolset.get_tools())} tools (filtered from 11 total)")
    
    return toolset



# ============================================================================
# MAIN
# ============================================================================

# async def main():
#     """Main function - run examples"""
    
#     # Choose which example to run:
    
#     # 1. Async usage
#     await example_async_usage()
    
    # 2. Sync usage (for agent)
    # example_sync_usage()
    
    # 3. Filtered tools
    # await example_filtered_tools()
    
    # 4. Full Google ADK integration
    # await integrate_with_google_adk_agent()


# if __name__ == "__main__":
#     asyncio.run(main())