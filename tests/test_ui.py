"""Testes de serialização do ui.AppShell (não dependem de servidor/WebSocket)."""
import inspect
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from antdpy import ui  # noqa: E402
from antdpy.core import serialize  # noqa: E402

ITEMS = [{"key": "/", "label": "Início"}, {"key": "/a", "label": "A"}]


def find_all(node, type_):
    out = []
    if isinstance(node, dict):
        if node.get("$node") == type_:
            out.append(node)
        for v in node.values():
            out += find_all(v, type_)
    elif isinstance(node, list):
        for v in node:
            out += find_all(v, type_)
    return out


def test_estrutura_basica_e_sider_fixo():
    tree, _ = serialize(ui.AppShell(ui.Text("oi"), menu_items=ITEMS, selected_key="/a"))
    assert tree["$node"] == "Layout" and tree["props"]["hasSider"] is True
    [sider] = find_all(tree, "Layout.Sider")
    p = sider["props"]
    assert p["collapsible"] is True and p["breakpoint"] == "lg"
    assert p["style"]["position"] == "sticky" and p["style"]["height"] == "100vh"
    assert p["style"]["overflowY"] == "auto"
    [menu] = find_all(tree, "Menu")
    assert menu["props"]["mode"] == "inline" and menu["props"]["selectedKeys"] == ["/a"]
    assert find_all(tree, "Layout.Content")


def test_opcionais_ausentes_por_padrao():
    tree, _ = serialize(ui.AppShell(menu_items=ITEMS))
    assert not find_all(tree, "Layout.Header")
    assert not find_all(tree, "Layout.Footer")
    assert not find_all(tree, "Breadcrumb")
    assert "selectedKeys" not in find_all(tree, "Menu")[0]["props"]
    assert "onClick" not in find_all(tree, "Menu")[0]["props"]


def test_header_footer_breadcrumb_logo():
    tree, _ = serialize(ui.AppShell(
        menu_items=ITEMS, logo="antdpy", header="Topo", footer="Fim",
        breadcrumb=["Início", {"title": "Clientes"}],
    ))
    assert find_all(tree, "Layout.Header") and find_all(tree, "Layout.Footer")
    [bc] = find_all(tree, "Breadcrumb")
    assert bc["props"]["items"] == [{"title": "Início"}, {"title": "Clientes"}]
    assert "antdpy" in find_all(tree, "div")[0]["children"]


def test_on_navigate_recebe_a_chave():
    seen = []
    tree, handlers = serialize(ui.AppShell(menu_items=ITEMS, on_navigate=seen.append))
    [menu] = find_all(tree, "Menu")
    handlers[menu["props"]["onClick"]["$event"]]({"key": "/a", "keyPath": ["/a"]})
    assert seen == ["/a"]


def test_tema_claro_e_style_extra():
    tree, _ = serialize(ui.AppShell(menu_items=ITEMS, theme="light", style={"background": "#eee"}))
    assert find_all(tree, "Menu")[0]["props"]["theme"] == "light"
    assert find_all(tree, "Layout.Sider")[0]["props"]["theme"] == "light"
    assert tree["props"]["style"]["background"] == "#eee"
    assert tree["props"]["style"]["minHeight"] == "100vh"


def test_demo_usa_appshell():
    sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
    import demo
    import antdpy as ap

    class S:
        def emit(self, c): pass

    for path in ("/", "/clientes", "/componentes"):
        ctx = ap.Context(S()); ctx.path = path
        tree, _ = serialize(demo.app._match(path)[0](ctx))
        assert find_all(tree, "Layout.Sider")
        assert find_all(tree, "Menu")[0]["props"]["selectedKeys"] == [path]


def test_galeria_tem_ver_codigo_com_fonte_real():
    sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
    import demo
    import antdpy as ap

    class S:
        def emit(self, c): pass

    ctx = ap.Context(S()); ctx.path = "/componentes"
    tree, _ = serialize(demo.app._match("/componentes")[0](ctx))
    colapsos = find_all(tree, "Collapse")
    com_codigo = [c for c in colapsos if c["props"].get("items", [{}])[0].get("key") == "codigo"]
    assert len(com_codigo) == len(demo.SECOES) >= 12  # uma por seção da galeria
    esperado = {
        textwrap.dedent(inspect.getsource(f))
        for f in demo.SECOES
    }
    mostrado = {pre["children"][0] for pre in find_all(tree, "pre")}
    assert mostrado == esperado
