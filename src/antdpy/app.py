"""Servidor, sessões e contexto do antdpy.

Fluxo: o front (React + Antd) abre um WebSocket; o Python devolve a árvore de UI em JSON;
eventos (cliques, digitação...) voltam ao Python, o handler roda, a página é re-renderizada
e a nova árvore é enviada.
"""

from __future__ import annotations

import asyncio
import copy
import inspect
import json
import logging
import re
import traceback
from pathlib import Path
from typing import Any, Awaitable, Callable

from .core import Component, json_default, serialize

log = logging.getLogger("antdpy")
STATIC_DIR = Path(__file__).parent / "static"
WS_PATH = "/_antdpy/ws"


# ------------------------------------------------------------------------- estado
class State:
    """Estado da sessão com acesso por atributo. Use `init` para valores padrão."""

    def __init__(self) -> None:
        object.__setattr__(self, "_data", {})

    def init(self, **defaults: Any) -> "State":
        for k, v in defaults.items():
            self._data.setdefault(k, copy.deepcopy(v))
        return self

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(
                f"state.{name} não foi inicializado (use state.init({name}=...))"
            ) from None

    def __setattr__(self, name: str, value: Any) -> None:
        self._data[name] = value

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


class Messenger:
    """`ctx.message.success("...")` -> toast do Antd (message)."""

    def __init__(self, emit: Callable[[dict], None], kind: str = "message") -> None:
        self._emit, self._kind = emit, kind

    def _send(self, level: str, content: str, **kw: Any) -> None:
        self._emit({"type": self._kind, "level": level, "content": content, **kw})

    def success(self, content: str, **kw: Any) -> None: self._send("success", content, **kw)
    def error(self, content: str, **kw: Any) -> None: self._send("error", content, **kw)
    def info(self, content: str, **kw: Any) -> None: self._send("info", content, **kw)
    def warning(self, content: str, **kw: Any) -> None: self._send("warning", content, **kw)


class Context:
    """Objeto passado para as páginas e disponível nos handlers via closure."""

    def __init__(self, session: "Session") -> None:
        self._session = session
        self.state = State()
        self.message = Messenger(session.emit, "message")
        self.notification = Messenger(session.emit, "notification")
        self.path: str = "/"
        self.params: dict[str, str] = {}

    async def refresh(self) -> None:
        """Re-renderiza e envia a UI agora (útil em handlers async longos)."""
        await self._session.render()

    def navigate(self, path: str) -> None:
        self._session.emit({"type": "navigate", "path": path})


# ----------------------------------------------------------------------- sessão
def _call_with_arity(fn: Callable[..., Any], args: list[Any]) -> Any:
    """Chama `fn` passando só quantos argumentos ela aceita (on_click() ou on_click(e))."""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(*args)
    params = list(sig.parameters.values())
    if any(p.kind is p.VAR_POSITIONAL for p in params):
        return fn(*args)
    n = sum(1 for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))
    return fn(*args[:n])


class Session:
    def __init__(self, app: "App", ws: Any) -> None:
        self.app, self.ws = app, ws
        self.loop = asyncio.get_running_loop()
        self.outq: asyncio.Queue[str] = asyncio.Queue()
        self.ctx = Context(self)
        self.handlers: dict[str, Callable[..., Any]] = {}
        self.lock = asyncio.Lock()
        self.last_tree: str | None = None
        self.ack = 0

    # envio sempre via fila (seguro para chamadas vindas de threads)
    def emit(self, cmd: dict) -> None:
        payload = json.dumps(cmd, default=json_default, allow_nan=False, ensure_ascii=False)
        self.loop.call_soon_threadsafe(self.outq.put_nowait, payload)

    async def sender(self) -> None:
        while True:
            await self.ws.send_text(await self.outq.get())

    async def render(self) -> None:
        match = self.app._match(self.ctx.path)
        if match is None:
            tree: Component | Any = self.app._not_found(self.ctx.path)
            self.ctx.params = {}
        else:
            fn, self.ctx.params = match
            tree = _call_with_arity(fn, [self.ctx])
            if inspect.isawaitable(tree):
                tree = await tree
        if not isinstance(tree, Component):
            raise TypeError(f"A página deve retornar um Component, não {type(tree).__name__}")
        node, handlers = serialize(tree)
        self.handlers = handlers
        payload = json.dumps(node, default=json_default, allow_nan=False, ensure_ascii=False)
        if payload != self.last_tree:
            self.last_tree = payload
            self.emit({"type": "render", "tree": node, "ack": self.ack})
        else:
            self.emit({"type": "ack", "ack": self.ack})

    async def safe_render(self) -> None:
        try:
            await self.render()
        except Exception as exc:  # noqa: BLE001
            log.error("Erro ao renderizar %s\n%s", self.ctx.path, traceback.format_exc())
            self.emit({"type": "error", "content": f"Erro ao renderizar a página: {exc}",
                       "ack": self.ack})

    async def dispatch(self, handler_id: str, args: list[Any], seq: int) -> None:
        async with self.lock:
            fn = self.handlers.get(handler_id)
            try:
                if fn is None:
                    log.warning("handler desconhecido: %s", handler_id)
                elif inspect.iscoroutinefunction(fn):
                    await _call_with_arity(fn, args)
                else:
                    result = await asyncio.to_thread(_call_with_arity, fn, args)
                    if inspect.isawaitable(result):
                        await result
            except Exception as exc:  # noqa: BLE001
                log.error("Erro no handler %s\n%s", handler_id, traceback.format_exc())
                self.emit({"type": "error", "content": f"{type(exc).__name__}: {exc}"})
            self.ack = max(self.ack, seq)
            await self.safe_render()

    async def run(self) -> None:
        await self.ws.accept()
        self.emit({"type": "config", **self.app.client_config()})
        sender = asyncio.create_task(self.sender())
        try:
            while True:
                msg = json.loads(await self.ws.receive_text())
                kind = msg.get("type")
                if kind == "init":
                    self.ctx.path = msg.get("path", "/") or "/"
                    async with self.lock:
                        await self.safe_render()
                elif kind == "event":
                    # cada evento em sua task: um handler lento não trava o recebimento
                    asyncio.create_task(
                        self.dispatch(msg["id"], msg.get("args", []), int(msg.get("seq", 0)))
                    )
        finally:
            sender.cancel()


# -------------------------------------------------------------------------- app
class App:
    """Aplicação antdpy (também é uma app ASGI: `uvicorn meu_modulo:app`)."""

    def __init__(
        self,
        title: str = "antdpy",
        *,
        theme: dict[str, Any] | None = None,
        locale: str = "en_US",  # "en_US" | "pt_BR"
    ) -> None:
        self.title, self.theme, self.locale = title, theme or {}, locale
        self._routes: list[tuple[re.Pattern[str], Callable[..., Any]]] = []
        self._asgi: Any = None

    # ---- rotas
    def page(self, path: str = "/") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Registra uma página. Aceita `{param}` no caminho: "/clientes/{id}"."""
        regex = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path.rstrip("/") or "/")

        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append((re.compile(f"^{regex}$"), fn))
            return fn

        return deco

    def _match(self, path: str) -> tuple[Callable[..., Any], dict[str, str]] | None:
        path = path.split("?")[0]
        path = path.rstrip("/") or "/"
        for rx, fn in self._routes:
            m = rx.match(path)
            if m:
                return fn, m.groupdict()
        return None

    def _not_found(self, path: str) -> Component:
        from . import ui

        return ui.Result(status="404", title="404", sub_title=f"Página não encontrada: {path}")

    def client_config(self) -> dict[str, Any]:
        return {"title": self.title, "theme": self.theme, "locale": self.locale}

    # ---- ASGI
    @property
    def asgi(self) -> Any:
        if self._asgi is None:
            self._asgi = self._build_asgi()
        return self._asgi

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self.asgi(scope, receive, send)

    def _build_asgi(self) -> Any:
        from fastapi import FastAPI
        from fastapi.responses import FileResponse, HTMLResponse
        from fastapi.staticfiles import StaticFiles
        from starlette.routing import WebSocketRoute
        from starlette.websockets import WebSocketDisconnect

        api = FastAPI(title=self.title, docs_url=None, redoc_url=None, openapi_url=None)

        async def ws_endpoint(websocket: Any) -> None:
            try:
                await Session(self, websocket).run()
            except WebSocketDisconnect:
                pass

        # rota Starlette pura (evita a resolução de anotações do FastAPI)
        api.router.routes.insert(0, WebSocketRoute(WS_PATH, ws_endpoint))

        assets = STATIC_DIR / "assets"
        if assets.is_dir():
            api.mount("/assets", StaticFiles(directory=assets), name="assets")

        @api.get("/{full_path:path}")
        async def spa(full_path: str) -> Any:
            candidate = (STATIC_DIR / full_path).resolve()
            if full_path and candidate.is_file() and STATIC_DIR.resolve() in candidate.parents:
                return FileResponse(candidate)
            index = STATIC_DIR / "index.html"
            if index.is_file():
                return FileResponse(index)
            return HTMLResponse(
                "<h3>antdpy: front-end não compilado.</h3>"
                "<p>Rode <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>.</p>",
                status_code=503,
            )

        return api

    def run(self, host: str = "127.0.0.1", port: int = 8000, **uvicorn_kwargs: Any) -> None:
        import uvicorn

        uvicorn.run(self.asgi, host=host, port=port, **uvicorn_kwargs)
