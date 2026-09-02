"""A minimal local MCP server exposing one support-information tool."""

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("sample-support-server")


@mcp.tool()
def get_support_hours(region: str) -> dict[str, str]:
    """Get sample human-support opening hours for a geographic region."""

    hours = {
        "india": "Monday-Friday, 09:00-18:00 IST",
        "usa": "Monday-Friday, 09:00-17:00 ET",
        "uk": "Monday-Friday, 09:00-17:00 GMT",
    }
    normalized_region = region.strip().lower()
    return {
        "region": region,
        "hours": hours.get(normalized_region, "Monday-Friday, 09:00-17:00 local time"),
        "source": "sample-support-mcp-server",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
