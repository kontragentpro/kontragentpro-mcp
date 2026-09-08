"""KontragentPro MCP server.

Тонкая обёртка над публичным API v2 (https://kontragentpro.ru/api/v2).
Каждый MCP-инструмент = один HTTP-вызов к готовому эндпоинту. Никакой
бизнес-логики и хранения данных на стороне сервера — только транспорт,
авторизация Bearer-ключом и разворот единого конверта ошибок в понятный текст.

Переменные окружения:
  KONTRAGENTPRO_API_KEY   — API-ключ из ЛК (https://kontragentpro.ru/developers).
                            Необязателен: без ключа работает анонимный free-tier
                            (пониженный rate-limit). check_account требует ключ.
  KONTRAGENTPRO_API_BASE  — базовый URL, по умолчанию https://kontragentpro.ru/api/v2.
                            Переопределяется для стейджинга/локальной отладки.
  KONTRAGENTPRO_TIMEOUT   — таймаут HTTP в секундах (по умолчанию 30).
"""
from __future__ import annotations

import functools
import os
from typing import Annotated, Any, Callable, Optional

import httpx
try:                                    # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _MCPServer
except ImportError:                     # mcp 1.x — FastMCP до переименования
    from mcp.server.fastmcp import FastMCP as _MCPServer
from pydantic import Field

from . import __version__

API_BASE = os.environ.get(
    "KONTRAGENTPRO_API_BASE", "https://kontragentpro.ru/api/v2"
).rstrip("/")
API_KEY = os.environ.get("KONTRAGENTPRO_API_KEY", "").strip()
TIMEOUT = float(os.environ.get("KONTRAGENTPRO_TIMEOUT", "30"))

mcp = _MCPServer(
    "kontragentpro",
    instructions=(
        "KontragentPro — проверка российских контрагентов по ИНН. Данные из "
        "открытых реестров: ЕГРЮЛ, ФНС (ГИР БО), ЕФРСБ (банкротства), "
        "Генпрокуратура (проверки), Роспатент, реестры санкций и иноагентов. "
        "Используй search_companies для подбора списка ЮЛ по фильтрам, "
        "get_company для сводной карточки по одному ИНН, get_company_financials "
        "для многолетней финансовой динамики, get_company_timeline для ленты "
        "событий. ИНН юрлица — 10 цифр."
    ),
)


def _headers() -> dict[str, str]:
    h = {
        "Accept": "application/json",
        "User-Agent": f"kontragentpro-mcp/{__version__}",
    }
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h


class ApiError(Exception):
    """Ошибка API v2, развёрнутая из единого конверта §6 в читаемый текст."""


DEVELOPERS_URL = "https://kontragentpro.ru/developers"


def _friendly(code: str, http: int, message: str) -> str:
    """Развернуть код ошибки API в подсказку, которая говорит, что делать дальше.

    Подсказки зависят от того, задан ли ключ: без ключа упереться в лимит легко
    (5 запросов в минуту), и человеку нужен путь к ключу, а не констатация факта.
    """
    if API_KEY:
        rate_hint = (
            "Превышен лимит запросов в минуту для вашего ключа (60/мин, 1000/сутки). "
            "Подождите минуту и повторите."
        )
    else:
        rate_hint = (
            "Анонимный доступ ограничен 5 запросами в минуту. Подождите минуту "
            f"либо возьмите бесплатный ключ на {DEVELOPERS_URL} — с ним лимит "
            "60 запросов в минуту и 1000 в сутки. Ключ передаётся серверу через "
            "переменную окружения KONTRAGENTPRO_API_KEY."
        )
    hints = {
        "unauthorized": (
            f"Нужен API-ключ. Бесплатный выдаётся сразу на {DEVELOPERS_URL}; "
            "задайте его в переменной окружения KONTRAGENTPRO_API_KEY."
        ),
        "forbidden": "У ключа нет нужного scope — проверьте права ключа в личном кабинете.",
        "insufficient_balance": (
            "Дневная бесплатная квота исчерпана. Платные тарифы пока не "
            "подключены — напишите на ceo@kontragentpro.ru, поднимем лимит вручную."
        ),
        "rate_limited": rate_hint,
        "invalid_inn": "ИНН не проходит валидацию: для юрлица ожидается 10 цифр.",
        "not_found": "Такого ИНН нет в наших данных — проверьте написание.",
    }
    hint = hints.get(code)
    parts = [f"[{code}, HTTP {http}] {message}"]
    if hint:
        parts.append(hint)
    return " ".join(parts)


def _safe(fn: Callable) -> Callable:
    """Отдавать ошибку API текстом в результате, а не исключением.

    Зачем: под mcp 2.x исключение инструмента до клиента не доходит — модель
    и пользователь видят только «Error executing tool <имя>», а все наши
    подсказки умирают внутри. Проверено живым прогоном: на шестом анонимном
    запросе приходило ровно это. Возвращая {"error": ...}, мы кладём текст
    в обычный результат, и модель может его прочитать и объяснить человеку.

    functools.wraps сохраняет сигнатуру и аннотации — FastMCP строит схему
    инструмента по ним, поэтому обёртка должна быть прозрачной.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ApiError as e:
            return {"error": str(e)}
    return wrapper


def _request(method: str, path: str, *,
             params: Optional[dict] = None,
             json_body: Optional[dict] = None) -> Any:
    """Выполнить запрос к API v2 и вернуть распарсенный JSON.

    None-значения в params отбрасываются (не шлём пустые фильтры). На не-2xx
    разворачиваем конверт {"error": {code, message, ...}} → ApiError с текстом.
    """
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.request(
                method, url, params=clean, json=json_body, headers=_headers()
            )
    except httpx.RequestError as e:
        raise ApiError(f"Сеть недоступна при обращении к {url}: {e}") from e

    try:
        data = resp.json()
    except ValueError:
        if resp.is_success:
            raise ApiError(f"Ответ {url} не является JSON (HTTP {resp.status_code}).")
        raise ApiError(f"HTTP {resp.status_code} от {url} без JSON-тела.")

    if not resp.is_success:
        err = (data or {}).get("error") or {}
        raise ApiError(_friendly(
            err.get("code", "error"), resp.status_code,
            err.get("message", "неизвестная ошибка"),
        ))
    return data


# ---------------------------------------------------------------------------
# Инструменты
# ---------------------------------------------------------------------------

@mcp.tool()
@_safe
def search_companies(
    status: Annotated[Optional[str], Field(
        description="Фильтр по статусу: 'active' (действующие, по умолчанию) или "
        "'bankrupt' (в процедуре банкротства).")] = None,
    revenue_min: Annotated[Optional[int], Field(
        description="Минимальный годовой ДОХОД в рублях (открытые данные ФНС). "
        "Это совокупные доходы — выручка плюс прочие, — а не строка 2110 "
        "бухотчётности; они больше выручки из ГИР БО.", ge=0)] = None,
    revenue_max: Annotated[Optional[int], Field(
        description="Максимальный годовой доход в рублях (открытые данные ФНС).",
        ge=0)] = None,
    revenue_year: Annotated[int, Field(
        description="Год годового снимка ФНС для фильтра по доходам.",
        ge=2018, le=2030)] = 2025,
    region_code: Annotated[Optional[str], Field(
        description="CSV кодов субъектов РФ (напр. '77,78') — для active.")] = None,
    okved: Annotated[Optional[str], Field(
        description="CSV префиксов ОКВЭД (напр. '47.1,47.2').")] = None,
    employees_min: Annotated[Optional[int], Field(
        description="Минимальная среднесписочная численность сотрудников.", ge=0)] = None,
    order_by: Annotated[str, Field(
        description="Сортировка: revenue_desc | revenue_asc | random | "
        "recent_bankruptcy.")] = "revenue_desc",
    limit: Annotated[int, Field(description="Сколько компаний вернуть (1–500).",
                                ge=1, le=500)] = 25,
    offset: Annotated[int, Field(description="Смещение для пагинации.", ge=0)] = 0,
) -> dict:
    """Подобрать список российских юрлиц по фильтрам (доходы, регион, ОКВЭД,
    штат, статус банкротства). Возвращает items[] с ИНН, названием, финансовыми
    показателями и флагами риска. Для деталей по одному ИНН зовите get_company."""
    return _request("GET", "/companies", params={
        "status": status, "revenue_min": revenue_min, "revenue_max": revenue_max,
        "revenue_year": revenue_year, "region_code": region_code, "okved": okved,
        "employees_min": employees_min, "order_by": order_by,
        "limit": limit, "offset": offset,
    })


@mcp.tool()
@_safe
def get_company(
    inn: Annotated[str, Field(description="ИНН юрлица — 10 цифр.")],
) -> dict:
    """Сводная карточка компании одним запросом по ИНН: идентичность (название,
    ОГРН, адрес), финансы, налоговый режим, риск-флаги (банкротство, санкции,
    иноагент), товарные знаки и связи. Поле completeness показывает, какие блоки
    заполнены. Всегда 200 для валидного ИНН."""
    return _request("GET", f"/companies/{inn.strip()}")


@mcp.tool()
@_safe
def get_company_financials(
    inn: Annotated[str, Field(description="ИНН юрлица — 10 цифр.")],
    year_from: Annotated[Optional[int], Field(
        description="Нижняя граница года (включительно).", ge=2010, le=2030)] = None,
    year_to: Annotated[Optional[int], Field(
        description="Верхняя граница года (включительно).", ge=2010, le=2030)] = None,
) -> dict:
    """Многолетняя финансовая динамика компании по ИНН (выручка, прибыль,
    активы, коэффициенты) из ГИР БО ФНС плюс годовой снимок. Для новых компаний
    многолетний ряд может быть пуст — тогда возвращается годовой снимок и
    предупреждение (warnings)."""
    return _request("GET", f"/companies/{inn.strip()}/financials", params={
        "year_from": year_from, "year_to": year_to,
    })


@mcp.tool()
@_safe
def get_company_timeline(
    inn: Annotated[str, Field(description="ИНН юрлица — 10 цифр.")],
) -> dict:
    """Лента событий компании по датам: банкротные процедуры (ЕФРСБ), включение/
    исключение из реестра иноагентов (Минюст), проверки (ЕРКНМ Генпрокуратуры),
    публикации в Вестнике госрегистрации, регистрации товарных знаков (Роспатент).
    События отсортированы от новых к старым."""
    return _request("GET", f"/companies/{inn.strip()}/timeline")


@mcp.tool()
@_safe
def check_account() -> dict:
    """Состояние API-счёта по текущему ключу: баланс депозита, тарифный план,
    дневная квота и её использование, список ключей. Требует KONTRAGENTPRO_API_KEY."""
    if not API_KEY:
        raise ApiError(_friendly(
            "unauthorized", 401,
            "check_account требует API-ключ, а KONTRAGENTPRO_API_KEY не задан.",
        ))
    return _request("GET", "/account")


def main() -> None:
    """Точка входа: запуск MCP-сервера по stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
