# KontragentPro MCP server

[![PyPI](https://img.shields.io/pypi/v/kontragentpro-mcp.svg)](https://pypi.org/project/kontragentpro-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kontragentpro-mcp.svg)](https://pypi.org/project/kontragentpro-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Look up Russian companies by INN (tax ID) directly from **Claude Desktop, Cursor**
and any MCP-compatible client. A thin wrapper over the public
[KontragentPro API v2](https://kontragentpro.ru/api/v2/docs), serving data from
Russian open registries: EGRUL (company registry), Federal Tax Service financial
statements, bankruptcy register, state inspections, trademarks, sanctions and
foreign-agent lists.

**Works without an API key** — anonymous free tier is enabled by default, so you
can try it in under a minute.

*Русское описание — [ниже](#по-русски).*

## Tools

| Tool | What it does |
|---|---|
| `search_companies` | Filter legal entities by revenue, region, industry code, headcount, bankruptcy status |
| `get_company` | Full company card by INN in a single call |
| `get_company_financials` | Multi-year financial history from official tax filings |
| `get_company_timeline` | Event feed: bankruptcies, inspections, trademarks, official gazette |
| `check_account` | Balance, plan and daily quota (requires API key) |

## Install

Run without installing, via [`uv`](https://docs.astral.sh/uv/):

```bash
uvx kontragentpro-mcp
```

Or with pip:

```bash
pip install kontragentpro-mcp
kontragentpro-mcp
```

## Claude Desktop

Open `Settings → Developer → Edit Config` and add to `mcpServers`:

```json
{
  "mcpServers": {
    "kontragentpro": {
      "command": "uvx",
      "args": ["kontragentpro-mcp"]
    }
  }
}
```

Restart Claude Desktop — the tools will appear in the list. To raise rate limits,
add `"env": {"KONTRAGENTPRO_API_KEY": "your_key"}`.

## Cursor

`Settings → MCP → Add new server`, type **command**:

```json
{
  "command": "uvx",
  "args": ["kontragentpro-mcp"]
}
```

## Example

> "Check the company with INN 7736207543 and show its revenue over the last 5 years"

The client calls `get_company` and `get_company_financials`, returning the company
card and the financial series.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `KONTRAGENTPRO_API_KEY` | — | Bearer key from your account (optional) |
| `KONTRAGENTPRO_API_BASE` | `https://kontragentpro.ru/api/v2` | API base URL |
| `KONTRAGENTPRO_TIMEOUT` | `30` | HTTP timeout, seconds |

Get a free key at **https://kontragentpro.ru/developers**.

## Data sources

All data comes from official Russian open registries — EGRUL/EGRIP, the Federal
Tax Service (financial statements, tax regimes), the federal bankruptcy register,
the Prosecutor General's inspection registry, Rospatent trademarks, and public
sanctions lists. Each block on a company card carries its source and retrieval date.

---

<a name="по-русски"></a>

## По-русски

Проверка российских контрагентов по ИНН прямо в **Claude Desktop, Cursor** и любом
MCP-совместимом клиенте. Тонкая обёртка над публичным
[API KontragentPro v2](https://kontragentpro.ru/api/v2/docs) — данные из открытых
реестров: ЕГРЮЛ, ФНС (ГИР БО), ЕФРСБ (банкротства), Генпрокуратура (проверки),
Роспатент, реестры санкций и иноагентов.

**Ключ необязателен:** без него сервер работает в анонимном free-tier
с пониженным лимитом запросов — попробовать можно сразу. Ключ для повышенных
лимитов и `check_account` выдаётся в личном кабинете:
**https://kontragentpro.ru/developers**

### Инструменты

| Инструмент | Что делает |
|---|---|
| `search_companies` | Подбор списка ЮЛ по фильтрам: выручка, регион, ОКВЭД, штат, статус банкротства |
| `get_company` | Сводная карточка компании одним запросом по ИНН |
| `get_company_financials` | Многолетняя финансовая динамика (ГИР БО ФНС) |
| `get_company_timeline` | Лента событий: банкротства, проверки, иноагенты, ТЗ, Вестник |
| `check_account` | Баланс депозита, план, дневная квота (нужен ключ) |

### Установка

```bash
uvx kontragentpro-mcp        # запуск без установки
pip install kontragentpro-mcp # либо через pip
```

### Пример

> «Проверь контрагента с ИНН 7736207543 и покажи динамику выручки за 5 лет»

Клиент вызовет `get_company` и `get_company_financials`, вернёт карточку
и финансовый ряд.

## Лицензия / License

MIT. Данные предоставляются «как есть» из открытых источников; сервис не является
заменой официальной выписки.

MIT. Data is provided as-is from public sources and is not a substitute for an
official registry extract.
