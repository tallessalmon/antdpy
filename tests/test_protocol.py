"""Teste ponta a ponta do protocolo: WebSocket real contra o app de exemplo."""
import json
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
import demo  # noqa: E402
import antdpy as ap  # noqa: E402
from antdpy import ui  # noqa: E402
from antdpy.core import serialize  # noqa: E402


def find(node, pred):
    if isinstance(node, dict):
        if pred(node):
            return node
        for v in list(node.get("props", {}).values()) + node.get("children", []):
            r = find(v, pred)
            if r:
                return r
    elif isinstance(node, list):
        for v in node:
            r = find(v, pred)
            if r:
                return r


def recv_until(ws, kind):
    for _ in range(20):
        m = json.loads(ws.receive_text())
        if m["type"] == kind:
            return m
    raise AssertionError(f"não recebeu {kind}")


def test_serialize_basics():
    tree, handlers = serialize(
        ui.Button("Ok", type="primary", icon="PlusOutlined", on_click=lambda: None, html_type="submit")
    )
    assert tree["$node"] == "Button"
    assert tree["props"]["htmlType"] == "submit"
    assert tree["props"]["onClick"] == {"$event": "r.on_click"}
    assert tree["props"]["icon"]["$node"] == "Icon"
    assert "r.on_click" in handlers
    assert tree["children"] == ["Ok"]


def test_none_vs_unset_and_conditionals():
    tree, _ = serialize(ui.Select(value=None, options=[]))
    assert tree["props"]["value"] is None and "placeholder" not in tree["props"]
    tree, _ = serialize(ui.Space(False and ui.Text("x"), ui.Text("y"), None))
    assert len(tree["children"]) == 1


def test_nan_becomes_null():
    tree, _ = serialize(ui.Table(columns=[], data_source=[{"a": float("nan")}]))
    assert tree["props"]["dataSource"] == [{"a": None}]


def test_dataframe():
    pd = pytest.importorskip("pandas")
    t = ui.Table.from_dataframe(pd.DataFrame({"a": [1, None], "b": ["x", "y"]}))
    tree, _ = serialize(t)
    assert tree["props"]["dataSource"][1]["a"] is None
    assert [c["dataIndex"] for c in tree["props"]["columns"]] == ["a", "b"]


def test_websocket_counter_flow():
    client = TestClient(demo.app.asgi)
    with client.websocket_connect("/_antdpy/ws") as ws:
        cfg = recv_until(ws, "config")
        assert cfg["locale"] == "pt_BR"
        ws.send_text(json.dumps({"type": "init", "path": "/"}))
        first = recv_until(ws, "render")
        stat = find(first["tree"], lambda n: n.get("$node") == "Statistic" and n["props"].get("title") == "Cliques")
        assert stat["props"]["value"] == 0
        btn = find(first["tree"], lambda n: n.get("$node") == "Button" and n["children"] == ["Incrementar"])
        ws.send_text(json.dumps({"type": "event", "id": btn["props"]["onClick"]["$event"], "args": [None], "seq": 1}))
        got_msg = False
        for _ in range(5):
            m = json.loads(ws.receive_text())
            if m["type"] == "message":
                got_msg = True
                assert m["level"] == "success" and "1" in m["content"]
            if m["type"] == "render":
                stat = find(m["tree"], lambda n: n.get("$node") == "Statistic" and n["props"].get("title") == "Cliques")
                assert stat["props"]["value"] == 1
                assert m["ack"] == 1
                break
        assert got_msg


def test_input_echo_and_ack_when_tree_unchanged():
    app = ap.App()

    @app.page("/")
    def page(ctx):
        return ui.Input(value="fixo", on_change=lambda v: None)  # ignora a edição

    with TestClient(app.asgi).websocket_connect("/_antdpy/ws") as ws:
        recv_until(ws, "config")
        ws.send_text(json.dumps({"type": "init", "path": "/"}))
        r = recv_until(ws, "render")
        hid = r["tree"]["props"]["onChange"]["$event"]
        ws.send_text(json.dumps({"type": "event", "id": hid, "args": ["abc"], "seq": 7}))
        m = recv_until(ws, "ack")  # árvore igual -> só ack
        assert m["ack"] == 7


def test_handler_error_reported_and_route_params_and_404():
    app = ap.App()

    @app.page("/u/{uid}")
    def user(ctx):
        return ui.Button(f"user {ctx.params['uid']}", on_click=lambda: 1 / 0)

    with TestClient(app.asgi).websocket_connect("/_antdpy/ws") as ws:
        recv_until(ws, "config")
        ws.send_text(json.dumps({"type": "init", "path": "/u/42"}))
        r = recv_until(ws, "render")
        assert r["tree"]["children"] == ["user 42"]
        ws.send_text(json.dumps({"type": "event", "id": r["tree"]["props"]["onClick"]["$event"], "args": [], "seq": 1}))
        err = recv_until(ws, "error")
        assert "ZeroDivisionError" in err["content"]
        ws.send_text(json.dumps({"type": "init", "path": "/nada"}))
        r = recv_until(ws, "render")
        assert r["tree"]["$node"] == "Result"


def test_serves_spa_and_assets():
    c = TestClient(demo.app.asgi)
    r = c.get("/clientes")
    assert r.status_code == 200 and "<div id=\"root\">" in r.text
    js = [l for l in r.text.split('"') if l.startswith("/assets/")][0]
    assert c.get(js).status_code == 200
