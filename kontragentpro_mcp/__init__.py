"""KontragentPro MCP server — тонкая обёртка над публичным API v2.

Экспортирует MCP-инструменты для проверки контрагентов РФ из любого
MCP-клиента (Claude Desktop, Cursor, ...). Вся бизнес-логика — на стороне
https://kontragentpro.ru/api/v2; здесь только маппинг tool → HTTP-вызов.
"""

__version__ = "0.1.0"
