"""KontragentPro MCP server — тонкая обёртка над публичным API v2.

Экспортирует MCP-инструменты для проверки контрагентов РФ из любого
MCP-клиента (Claude Desktop, Cursor, ...). Вся бизнес-логика — на стороне
https://kontragentpro.ru/api/v2; здесь только маппинг tool → HTTP-вызов.
"""

# Версию берём из метаданных установленного пакета, а не константой: здесь был
# захардкоженный "0.1.0", разошедшийся с pyproject.toml на две версии — и все
# запросы к API уходили с неверным User-Agent.
try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version

    __version__ = _pkg_version("kontragentpro-mcp")
except (ImportError, PackageNotFoundError):  # запуск из исходников без установки
    __version__ = "0.0.0+local"
