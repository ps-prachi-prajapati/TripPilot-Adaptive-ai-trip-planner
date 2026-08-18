import asyncio
import sys
import os
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import StructuredTool

class MultiServerMCPClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions = {} # server_name -> ClientSession
        self.available_tools = []
        
        # Define the server scripts to run via stdio
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mcp_dir = os.path.join(base_dir, "mcp_servers")
        
        self.servers = {
            "weather": os.path.join(mcp_dir, "weather_server.py"),
            "places": os.path.join(mcp_dir, "places_server.py"),
            "transport": os.path.join(mcp_dir, "transport_server.py"),
            "budget": os.path.join(mcp_dir, "budget_server.py")
        }

    async def connect(self):
        """Connect to all MCP servers."""
        # Always reset state before connecting on a fresh event loop
        try:
            await self.exit_stack.aclose()
        except Exception:
            pass
        self.exit_stack = AsyncExitStack()
        self.sessions = {}
        self.available_tools = []
        
        for name, script_path in self.servers.items():
            try:
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=[script_path],
                    env=os.environ.copy()
                )
                
                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                read, write = stdio_transport
                session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                
                self.sessions[name] = session
                print(f"[OK] Connected to {name} MCP server")
                
                # Fetch tools and register them
                response = await session.list_tools()
                for t in response.tools:
                    self.available_tools.append({
                        "server": name,
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema
                    })
            except Exception as e:
                print(f"[FAIL] Failed to connect to {name} MCP server: {e}")

    async def disconnect(self):
        """Disconnect from all servers."""
        try:
            await self.exit_stack.aclose()
        except Exception:
            pass
        finally:
            self.sessions.clear()
            self.available_tools.clear()
            self.exit_stack = AsyncExitStack()

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a specific tool on the appropriate server."""
        # Find which server has this tool
        target_server = None
        for t in self.available_tools:
            if t["name"] == tool_name:
                target_server = t["server"]
                break
                
        if not target_server:
            raise ValueError(f"Tool {tool_name} not found in any connected server.")
            
        session = self.sessions[target_server]
        result = await session.call_tool(tool_name, arguments)
        return result
        
    def get_langchain_tools(self):
        """
        Dynamically convert the MCP tools into LangChain tools.
        """
        lc_tools = []
        for t in self.available_tools:
            tool_name = t["name"]
            tool_description = t["description"] or f"MCP tool: {tool_name}"

            def create_tool_func(name, description):
                async def async_tool_func(**kwargs) -> str:
                    res = await self.call_tool(name, kwargs)
                    # Convert MCP CallToolResult to a string for the LLM
                    output = "\n".join(c.text for c in res.content if hasattr(c, 'text'))
                    return output

                async_tool_func.__name__ = name
                async_tool_func.__doc__ = description

                return StructuredTool.from_function(
                    coroutine=async_tool_func,
                    name=name,
                    description=description,
                )

            lc_tools.append(create_tool_func(tool_name, tool_description))

        return lc_tools

# Singleton instance to be used by the app
mcp_client = MultiServerMCPClient()
