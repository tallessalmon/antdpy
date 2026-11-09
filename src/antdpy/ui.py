"""Componentes do Antd para Python.

Convenções:
- Props em snake_case (`on_click`, `data_source`) viram camelCase no Antd.
- Dicts aninhados (ex.: `style`, colunas, linhas) seguem o formato nativo do Antd/JS.
- Qualquer componente do Antd sem wrapper pode ser usado com `Antd("Rate", value=3)`.
- `UNSET` (padrão dos parâmetros) = "não enviar"; `None` vira `null` no front.
"""

from __future__ import annotations

from typing import Any, Callable

from .core import UNSET as U
from .core import Component

__all__ = [
    "Component", "Antd", "Html", "Icon",
    # layout
    "Layout", "Header", "Sider", "Content", "Footer", "Row", "Col", "Space", "Flex",
    "Divider", "Card", "AppShell",
    # texto
    "Title", "Text", "Paragraph",
    # geral / feedback
    "Button", "Alert", "Tag", "Spin", "Statistic", "Empty", "Result",
    # entrada
    "Form", "FormItem", "Input", "TextArea", "Password", "Search", "InputNumber",
    "Select", "Checkbox", "Radio", "RadioGroup", "Switch", "Slider",
    # exibição / navegação
    "Table", "Column", "Action", "Modal", "Tabs", "Menu", "Descriptions",
    "DescriptionsItem", "Badge", "Progress",
]


# --------------------------------------------------------------------- genéricos
class Antd(Component):
    """Escape hatch: qualquer componente do Antd pelo nome (ex.: "Rate", "Steps",
    "Typography.Link", "Form.Item")."""

    def __init__(self, name: str, *children: Any, key: Any = None, **props: Any) -> None:
        super().__init__(*children, key=key, **props)
        self.type = name


class Html(Component):
    """Tag HTML nativa (div, span, img...). Ex.: Html("div", "oi", style={"padding": 8})."""

    def __init__(self, tag: str, *children: Any, key: Any = None, **props: Any) -> None:
        super().__init__(*children, key=key, **props)
        self.type = tag


class Icon(Component):
    """Ícone de @ant-design/icons pelo nome. Ex.: Icon("PlusOutlined")."""

    TYPE = "Icon"

    def __init__(self, name: str, *, key: Any = None, **props: Any) -> None:
        super().__init__(key=key, name=name, **props)


def _icon(value: Any) -> Any:
    return Icon(value) if isinstance(value, str) else value


# ------------------------------------------------------------------------ layout
class Layout(Component):
    TYPE = "Layout"


class Header(Component):
    TYPE = "Layout.Header"


class Sider(Component):
    TYPE = "Layout.Sider"


class Content(Component):
    TYPE = "Layout.Content"


class Footer(Component):
    TYPE = "Layout.Footer"


class Row(Component):
    TYPE = "Row"


class Col(Component):
    TYPE = "Col"


class Space(Component):
    TYPE = "Space"


class Flex(Component):
    TYPE = "Flex"


class Divider(Component):
    TYPE = "Divider"


class Card(Component):
    TYPE = "Card"

    def __init__(self, *children: Any, title: Any = U, extra: Any = U, key: Any = None,
                 **props: Any) -> None:
        super().__init__(*children, key=key, title=title, extra=extra, **props)


def AppShell(
    *content: Any,
    menu_items: list[dict],
    selected_key: str | None = None,
    on_navigate: Callable[..., Any] | None = None,
    logo: Any = None,
    header: Any = None,
    footer: Any = None,
    breadcrumb: list[Any] | None = None,
    theme: str = "dark",
    style: dict | None = None,
) -> Layout:
    """Layout de aplicação: barra lateral fixa + cabeçalho + conteúdo + rodapé.

    - `menu_items`: itens do Menu do Antd, ex.: [{"key": "/", "label": "Início",
      "icon": Icon("HomeOutlined")}].
    - `selected_key`: chave do item ativo (normalmente `ctx.path`).
    - `on_navigate(key)`: chamado ao clicar num item (normalmente `ctx.navigate`).
    - `logo` / `header` / `footer`: texto ou componente; cada um só aparece se informado.
    - `breadcrumb`: lista de textos ou de dicts do Antd, ex.: ["Início", "Clientes"].
    - `theme`: tema da barra lateral ("dark" | "light").

    A barra lateral é recolhível, fica fixa na tela e rola independente da página.
    """
    dark = theme == "dark"
    sider_children: list[Any] = []
    if logo is not None:
        logo_node = (
            Html("div", logo, style={"color": "#fff" if dark else "inherit", "fontSize": 18,
                                     "fontWeight": 600, "padding": 16, "textAlign": "center"})
            if isinstance(logo, str) else logo
        )
        sider_children.append(logo_node)
    sider_children.append(
        Menu(
            mode="inline", theme=theme, items=menu_items,
            selected_keys=[selected_key] if selected_key is not None else U,
            on_click=(lambda info: on_navigate(info["key"])) if on_navigate else U,
        )
    )

    body: list[Any] = []
    if breadcrumb:
        body.append(Antd(
            "Breadcrumb",
            items=[c if isinstance(c, dict) else {"title": c} for c in breadcrumb],
            style={"marginBottom": 16},
        ))
    body.extend(content)

    main: list[Any] = []
    if header is not None:
        header_node = (
            Title(header, level=4, style={"margin": 0, "lineHeight": "64px"})
            if isinstance(header, str) else header
        )
        main.append(Header(header_node, style={"background": "#fff", "padding": "0 24px"}))
    main.append(Content(*body, style={"padding": 24}))
    if footer is not None:
        main.append(Footer(footer, style={"textAlign": "center"}))

    return Layout(
        Sider(
            *sider_children,
            theme=theme, collapsible=True, breakpoint="lg",
            # fixa a barra na viewport: o menu rola sozinho e a página rola à parte
            style={"position": "sticky", "top": 0, "height": "100vh",
                   "overflowY": "auto", "alignSelf": "flex-start"},
        ),
        Layout(*main),
        has_sider=True,
        style={"minHeight": "100vh", **(style or {})},
    )


# ------------------------------------------------------------------------- texto
class Title(Component):
    TYPE = "Typography.Title"

    def __init__(self, *children: Any, level: int = U, key: Any = None, **props: Any) -> None:
        super().__init__(*children, key=key, level=level, **props)


class Text(Component):
    TYPE = "Typography.Text"

    def __init__(self, *children: Any, type: str = U, strong: bool = U, key: Any = None,
                 **props: Any) -> None:
        super().__init__(*children, key=key, type=type, strong=strong, **props)


class Paragraph(Component):
    TYPE = "Typography.Paragraph"


# ------------------------------------------------------------- geral / feedback
class Button(Component):
    TYPE = "Button"

    def __init__(
        self,
        *children: Any,
        type: str = U,  # "primary" | "default" | "dashed" | "text" | "link"
        danger: bool = U,
        loading: bool = U,
        disabled: bool = U,
        icon: Any = U,  # str ("PlusOutlined") ou Icon(...)
        html_type: str = U,  # "submit" dentro de Form
        on_click: Callable[..., Any] = U,
        key: Any = None,
        **props: Any,
    ) -> None:
        super().__init__(
            *children, key=key, type=type, danger=danger, loading=loading,
            disabled=disabled, icon=_icon(icon), html_type=html_type,
            on_click=on_click, **props,
        )


class Alert(Component):
    TYPE = "Alert"


class Tag(Component):
    TYPE = "Tag"


class Spin(Component):
    TYPE = "Spin"


class Statistic(Component):
    TYPE = "Statistic"


class Empty(Component):
    TYPE = "Empty"


class Result(Component):
    TYPE = "Result"


class Badge(Component):
    TYPE = "Badge"


class Progress(Component):
    TYPE = "Progress"


# ------------------------------------------------------------------------ entrada
class Form(Component):
    """Form do Antd. Os valores chegam em `on_finish(values: dict)`.

    `initial_values` só vale na montagem; para reiniciar o formulário, mude o `key`.
    """

    TYPE = "Form"

    def __init__(
        self,
        *children: Any,
        layout: str = U,  # "horizontal" | "vertical" | "inline"
        initial_values: dict = U,
        on_finish: Callable[..., Any] = U,
        on_values_change: Callable[..., Any] = U,
        key: Any = None,
        **props: Any,
    ) -> None:
        super().__init__(
            *children, key=key, layout=layout, initial_values=initial_values,
            on_finish=on_finish, on_values_change=on_values_change, **props,
        )


class FormItem(Component):
    """`rules`: lista de dicts do Antd, ex.: [{"required": True, "message": "Obrigatório"}].
    `pattern` aceita string de regex."""

    TYPE = "Form.Item"

    def __init__(
        self,
        *children: Any,
        label: Any = U,
        name: str | list[str] = U,
        rules: list[dict] = U,
        key: Any = None,
        **props: Any,
    ) -> None:
        super().__init__(*children, key=key, label=label, name=name, rules=rules, **props)


class Input(Component):
    TYPE = "Input"

    def __init__(
        self, *, value: Any = U, placeholder: str = U, disabled: bool = U,
        allow_clear: bool = U, on_change: Callable[..., Any] = U,
        on_press_enter: Callable[..., Any] = U, key: Any = None, **props: Any,
    ) -> None:
        super().__init__(
            key=key, value=value, placeholder=placeholder, disabled=disabled,
            allow_clear=allow_clear, on_change=on_change, on_press_enter=on_press_enter,
            **props,
        )


class TextArea(Input):
    TYPE = "Input.TextArea"


class Password(Input):
    TYPE = "Input.Password"


class Search(Input):
    """`on_search(value)` dispara ao pressionar Enter / clicar na lupa."""

    TYPE = "Input.Search"


class InputNumber(Input):
    TYPE = "InputNumber"


class Select(Component):
    """`options`: lista de {"label": ..., "value": ...}."""

    TYPE = "Select"

    def __init__(
        self, *, options: list[dict] = U, value: Any = U, placeholder: str = U,
        mode: str = U,  # "multiple" | "tags"
        allow_clear: bool = U, show_search: bool = U,
        on_change: Callable[..., Any] = U, key: Any = None, **props: Any,
    ) -> None:
        super().__init__(
            key=key, options=options, value=value, placeholder=placeholder, mode=mode,
            allow_clear=allow_clear, show_search=show_search, on_change=on_change, **props,
        )


class Checkbox(Component):
    TYPE = "Checkbox"

    def __init__(self, *children: Any, checked: bool = U,
                 on_change: Callable[..., Any] = U, key: Any = None, **props: Any) -> None:
        super().__init__(*children, key=key, checked=checked, on_change=on_change, **props)


class Radio(Component):
    TYPE = "Radio"


class RadioGroup(Component):
    TYPE = "Radio.Group"


class Switch(Component):
    TYPE = "Switch"

    def __init__(self, *, checked: bool = U, on_change: Callable[..., Any] = U,
                 key: Any = None, **props: Any) -> None:
        super().__init__(key=key, checked=checked, on_change=on_change, **props)


class Slider(Component):
    TYPE = "Slider"


# ------------------------------------------------------------- exibição / navegação
def Column(
    title: str,
    data_index: str | list[str] | None = None,
    *,
    key: str | None = None,
    render: str | None = None,  # "tag" | "boolean" | "money" | "date"
    actions: list[dict] | None = None,
    sorter: Any = None,
    width: Any = None,
    align: str | None = None,
    fixed: str | None = None,
    filters: list[dict] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Coluna de Table (retorna dict no formato do Antd, com chaves camelCase)."""
    col: dict[str, Any] = {"title": title}
    if data_index is not None:
        col["dataIndex"] = data_index
        col["key"] = key or (data_index if isinstance(data_index, str) else ".".join(data_index))
    elif key:
        col["key"] = key
    for k, v in (("render", render), ("actions", actions), ("sorter", sorter),
                 ("width", width), ("align", align), ("fixed", fixed), ("filters", filters)):
        if v is not None:
            col[k] = v
    col.update(extra)
    return col


def Action(label: str, on_click: Callable[..., Any], *, danger: bool = False) -> dict[str, Any]:
    """Botão de linha para `Column(actions=[...])`. `on_click(record: dict)`."""
    return {"label": label, "onClick": on_click, "danger": danger}


class Table(Component):
    """Tabela do Antd.

    - `columns`: lista de `Column(...)`.
    - `data_source`: lista de dicts (use `Table.from_dataframe` com pandas).
    - `on_row_click(record)`; `on_change(pagination, filters, sorter)` para paginação/ordenação
      no servidor.
    """

    TYPE = "Table"

    def __init__(
        self, *, columns: list[dict], data_source: list[dict], row_key: str = U,
        pagination: Any = U, loading: bool = U, size: str = U, bordered: bool = U,
        on_row_click: Callable[..., Any] = U, on_change: Callable[..., Any] = U,
        key: Any = None, **props: Any,
    ) -> None:
        super().__init__(
            key=key, columns=columns, data_source=data_source, row_key=row_key,
            pagination=pagination, loading=loading, size=size, bordered=bordered,
            on_row_click=on_row_click, on_change=on_change, **props,
        )

    @classmethod
    def from_dataframe(cls, df: Any, *, columns: list[dict] | None = None, **props: Any) -> "Table":
        """Cria a tabela direto de um pandas.DataFrame (NaN -> null, datas -> ISO)."""
        import json

        rows = json.loads(df.to_json(orient="records", date_format="iso"))
        cols = columns or [Column(str(c), str(c), sorter=None) for c in df.columns]
        return cls(columns=cols, data_source=rows, **props)


class Modal(Component):
    TYPE = "Modal"

    def __init__(
        self, *children: Any, open: bool = U, title: Any = U, ok_text: str = U,
        cancel_text: str = U, on_ok: Callable[..., Any] = U,
        on_cancel: Callable[..., Any] = U, key: Any = None, **props: Any,
    ) -> None:
        super().__init__(
            *children, key=key, open=open, title=title, ok_text=ok_text,
            cancel_text=cancel_text, on_ok=on_ok, on_cancel=on_cancel, **props,
        )


class Tabs(Component):
    """`items`: [{"key": "1", "label": "Aba", "children": <Component>}]."""

    TYPE = "Tabs"


class Menu(Component):
    """`items`: [{"key": "home", "label": "Início", "icon": Icon("HomeOutlined")}];
    `on_click(info)` recebe {"key": ..., "keyPath": [...]}."""

    TYPE = "Menu"


class Descriptions(Component):
    TYPE = "Descriptions"


class DescriptionsItem(Component):
    TYPE = "Descriptions.Item"
