"""Demo do antdpy. Rode:  python examples/demo.py  e abra http://127.0.0.1:8000"""

import inspect
import textwrap
import time

import antdpy as ap
from antdpy import ui

app = ap.App(title="antdpy demo", locale="pt_BR", theme={"token": {"colorPrimary": "#1677ff"}})

CLIENTES = [
    {"id": 1, "nome": "Construtora Alfa", "cidade": "Campinas", "status": "ativo", "saldo": 12500.5},
    {"id": 2, "nome": "Beta Locações", "cidade": "São Paulo", "status": "inativo", "saldo": 0},
    {"id": 3, "nome": "Gama Engenharia", "cidade": "Sorocaba", "status": "ativo", "saldo": 830.9},
]


ITENS_MENU = [
    {"key": "/", "label": "Contador", "icon": ui.Icon("ThunderboltOutlined")},
    {"key": "/clientes", "label": "Clientes", "icon": ui.Icon("TeamOutlined")},
    {"key": "/componentes", "label": "Componentes", "icon": ui.Icon("AppstoreOutlined")},
]
TITULOS = {i["key"]: i["label"] for i in ITENS_MENU}


def shell(ctx: ap.Context, *content):
    return ui.AppShell(
        *content,
        menu_items=ITENS_MENU,
        selected_key=ctx.path,
        on_navigate=ctx.navigate,
        logo="antdpy",
        header="Ant Design para Python",
        footer="antdpy · Ant Design para Python",
        breadcrumb=["antdpy", TITULOS.get(ctx.path, ctx.path)],
    )


@app.page("/")
def home(ctx: ap.Context):
    s = ctx.state.init(count=0, nome="", plano=None, aceito=False)

    def inc():
        s.count += 1
        ctx.message.success(f"Contador em {s.count}")

    return shell(
        ctx,
        ui.Space(
            ui.Title("Olá, antdpy 👋", level=2),
            ui.Alert(message="Tudo aqui é Ant Design real, controlado pelo Python.",
                     type="info", show_icon=True, closable=True),
            ui.Row(
                ui.Col(ui.Card(ui.Statistic(title="Clientes", value=len(CLIENTES),
                                            prefix=ui.Icon("TeamOutlined"))), span=8),
                ui.Col(ui.Card(ui.Statistic(title="Ativos", value=sum(c["status"] == "ativo" for c in CLIENTES),
                                            value_style={"color": "#3f8600"})), span=8),
                ui.Col(ui.Card(ui.Statistic(title="Saldo total", value=sum(c["saldo"] for c in CLIENTES),
                                            precision=2, prefix="R$")), span=8),
                gutter=16,
            ),
            ui.Card(
                ui.Space(
                    ui.Statistic(title="Cliques", value=s.count),
                    ui.Button("Incrementar", type="primary", icon="PlusOutlined", on_click=inc),
                    ui.Button("Zerar", on_click=lambda: setattr(s, "count", 0)),
                    ui.Antd("Progress", type="circle", size=64, percent=min(s.count * 10, 100)),
                    ui.Antd("Tooltip", ui.Badge(ui.Tag("cliques"), count=s.count, overflow_count=99),
                            title="Badge com o total de cliques"),
                ),
                title="Contador",
            ),
            ui.Card(
                ui.Space(
                    ui.Input(
                        value=s.nome, placeholder="Seu nome", allow_clear=True,
                        on_change=lambda v: setattr(s, "nome", v),
                    ),
                    ui.Select(
                        value=s.plano, placeholder="Plano", style={"width": 160},
                        options=[{"label": "Básico", "value": "basic"},
                                 {"label": "Pro", "value": "pro"}],
                        on_change=lambda v: setattr(s, "plano", v),
                    ),
                    ui.Checkbox("Aceito os termos", checked=s.aceito,
                                on_change=lambda v: setattr(s, "aceito", v)),
                    orientation="vertical",
                ),
                ui.Paragraph(f"Nome: {s.nome or '—'} | Plano: {s.plano or '—'} | "
                             f"Termos: {'sim' if s.aceito else 'não'}", style={"marginTop": 16}),
                title="Entradas controladas pelo Python",
            ),
            orientation="vertical",
            style={"width": "100%"},
        ),
    )


@app.page("/clientes")
def clientes(ctx: ap.Context):
    s = ctx.state.init(busca="", modal=False, editando=None, detalhe=None)

    def abrir_novo():
        s.editando = None
        s.modal = True

    def editar(rec):
        s.editando = rec
        s.modal = True

    def excluir(rec):
        CLIENTES[:] = [c for c in CLIENTES if c["id"] != rec["id"]]
        ctx.message.info(f"{rec['nome']} removido")

    def salvar(values):
        if s.editando:
            s.editando.update(values)
        else:
            CLIENTES.append({"id": max([c["id"] for c in CLIENTES] + [0]) + 1,
                             "saldo": 0, **values})
        s.modal = False
        ctx.message.success("Cliente salvo")

    dados = [c for c in CLIENTES if s.busca.lower() in c["nome"].lower()]

    return shell(
        ctx,
        ui.Space(
            ui.Search(placeholder="Buscar cliente", allow_clear=True,
                      on_change=lambda v: setattr(s, "busca", v), value=s.busca),
            ui.Button("Novo cliente", type="primary", icon="PlusOutlined", on_click=abrir_novo),
            style={"marginBottom": 16},
        ),
        ui.Antd("Drawer", 
                ui.Descriptions(
                    *[ui.DescriptionsItem(str(v), label=k) for k, v in (
                        ("Nome", (s.detalhe or {}).get("nome", "")),
                        ("Cidade", (s.detalhe or {}).get("cidade", "")),
                        ("Status", (s.detalhe or {}).get("status", "")),
                        ("Saldo", f"R$ {(s.detalhe or {}).get('saldo', 0):,.2f}"),
                    )],
                    column=1, bordered=True,
                ),
                open=s.detalhe is not None, title="Detalhes do cliente", width=420,
                on_close=lambda: setattr(s, "detalhe", None)),
        ui.Table(
            data_source=dados,
            row_key="id",
            pagination={"pageSize": 5, "showSizeChanger": False},
            columns=[
                ui.Column("Nome", "nome", sorter=True),
                ui.Column("Cidade", "cidade"),
                ui.Column("Status", "status", render="tag"),
                ui.Column("Saldo", "saldo", render="money", align="right"),
                ui.Column("Ações", key="acoes", actions=[
                    ui.Action("Detalhes", lambda rec: setattr(s, "detalhe", rec)),
                    ui.Action("Editar", editar),
                    ui.Action("Excluir", excluir, danger=True),
                ]),
            ],
        ),
        ui.Modal(
            ui.Form(
                ui.FormItem(ui.Input(), label="Nome", name="nome",
                            rules=[{"required": True, "message": "Informe o nome"}]),
                ui.FormItem(ui.Input(), label="Cidade", name="cidade"),
                ui.FormItem(
                    ui.Select(options=[{"label": "Ativo", "value": "ativo"},
                                       {"label": "Inativo", "value": "inativo"}]),
                    label="Status", name="status",
                ),
                ui.Button("Salvar", type="primary", html_type="submit"),
                layout="vertical",
                initial_values=s.editando or {"status": "ativo"},
                on_finish=salvar,
                key=f"form-{(s.editando or {}).get('id', 'novo')}",
            ),
            open=s.modal,
            title="Editar cliente" if s.editando else "Novo cliente",
            footer=None,
            on_cancel=lambda: setattr(s, "modal", False),
            destroy_on_hidden=True,
        ),
    )


A = ui.Antd  # atalho usado nos exemplos abaixo


def secao(fonte, titulo, *children):
    """Card de exemplo com botão "</> Ver código" (mostra o fonte de `fonte`)."""
    codigo = textwrap.dedent(inspect.getsource(fonte))
    return ui.Card(
        *children,
        ui.Antd(
            "Collapse", ghost=True, style={"marginTop": 8},
            items=[{
                "key": "codigo",
                "label": ui.Space(ui.Icon("CodeOutlined"), "Ver código"),
                "children": ui.Html(
                    "div",
                    ui.Antd("Typography.Text", "Copiar código",
                            copyable={"text": codigo, "tooltips": False},
                            style={"display": "block", "marginBottom": 8}),
                    ui.Html(
                        "pre", codigo,
                        style={"margin": 0, "padding": 12, "overflowX": "auto", "fontSize": 12,
                               "background": "rgba(0,0,0,0.04)", "borderRadius": 6},
                    ),
                ),
            }],
        ),
        title=titulo, style={"width": "100%"},
    )


def _feedback(ctx, s):
    return secao(
        _feedback,
        "Feedback",
        ui.Space(
            ui.Button("Message", on_click=lambda: ctx.message.success("Deu certo!")),
            ui.Button("Notification", on_click=lambda: ctx.notification.info("Nova notificação")),
            A("Popconfirm", ui.Button("Apagar tudo", danger=True), title="Tem certeza?",
              ok_text="Sim", cancel_text="Não",
              on_confirm=lambda: ctx.message.warning("Nada foi apagado (é só demo)")),
            ui.Button("Abrir Drawer", on_click=lambda: setattr(s, "drawer", True)),
            A("Dropdown", ui.Button("Menu ▾"), menu={
                "items": [{"key": "a", "label": "Opção A"}, {"key": "b", "label": "Opção B"}],
                "onClick": lambda info: ctx.message.info(f"Escolheu {info['key']}"),
            }),
            wrap=True,
        ),
        ui.Alert(message="Atenção", description="Alerts aceitam descrição e ícone.",
                 type="warning", show_icon=True, style={"marginTop": 16}),
        A("Drawer", ui.Paragraph("Conteúdo do drawer, aberto pelo estado Python."),
          open=s.drawer, title="Drawer", on_close=lambda: setattr(s, "drawer", False)),
    )


def _entradas(ctx, s):
    return secao(
        _entradas,
        "Entradas",
        ui.Space(
            ui.Space(
                ui.Text("Nota:"),
                A("Rate", value=s.nota, on_change=lambda v: setattr(s, "nota", v)),
                ui.Text(f"{s.nota}/5"),
            ),
            A("Segmented", options=["Lista", "Grade", "Mapa"], value=s.visao,
              on_change=lambda v: setattr(s, "visao", v)),
            ui.Space(
                ui.Text("Volume:"),
                ui.Slider(value=s.volume, style={"width": 200},
                          on_change=lambda v: setattr(s, "volume", v)),
            ),
            ui.Space(
                ui.Text("Notificações"),
                ui.Switch(checked=s.notificacoes, on_change=lambda v: setattr(s, "notificacoes", v)),
            ),
            A("DatePicker", placeholder="Escolha uma data",
              on_change=lambda _d, texto: setattr(s, "data", texto or "—")),
            A("TimePicker", placeholder="Hora"),
            A("ColorPicker", default_value="#1677ff"),
            A("AutoComplete", placeholder="Cidade", style={"width": 160},
              options=[{"value": c} for c in ("Campinas", "São Paulo", "Sorocaba", "Santos")]),
            ui.RadioGroup(ui.Radio("Sim", value=1), ui.Radio("Não", value=2), default_value=1),
            wrap=True,
        ),
        ui.Paragraph(f"Visão: {s.visao} · Data: {s.data}", style={"marginTop": 16}),
    )


def _exibicao(ctx, s):
    return secao(
        _exibicao,
        "Exibição",
        ui.Space(
            A("Avatar.Group", A("Avatar", "AB", style={"background": "#1677ff"}),
              A("Avatar", "CD", style={"background": "#52c41a"}),
              A("Avatar", icon=ui.Icon("UserOutlined")), max_count=2),
            ui.Badge(A("Avatar", shape="square", icon=ui.Icon("BellOutlined")), count=5),
            ui.Badge(status="processing", text="Em andamento"),
            ui.Tag("sucesso", color="success"), ui.Tag("erro", color="error"),
            ui.Tag("custom", color="purple", icon=ui.Icon("StarOutlined")),
            A("Progress", percent=s.volume, style={"width": 200}),
            A("Progress", type="circle", percent=s.nota * 20, size=48),
            wrap=True,
        ),
        ui.Divider(),
        A("Collapse", accordion=True, default_active_key=["1"], items=[
            {"key": "1", "label": "O que é o antdpy?",
             "children": ui.Paragraph("Ant Design controlado por Python via WebSocket.")},
            {"key": "2", "label": "Qualquer componente funciona?",
             "children": ui.Paragraph('Sim, com ui.Antd("Nome", ...).')},
        ]),
    )


def _navegacao(ctx, s):
    passos = A("Steps", current=s.passo, items=[
        {"title": "Cadastro", "description": "Dados básicos"},
        {"title": "Contrato", "description": "Revisão"},
        {"title": "Conclusão", "description": "Pronto!"},
    ])

    return secao(
        _navegacao,
        "Navegação e fluxo",
        passos,
        ui.Space(
            ui.Button("Anterior", disabled=s.passo <= 0,
                      on_click=lambda: setattr(s, "passo", max(s.passo - 1, 0))),
            ui.Button("Próximo", type="primary", disabled=s.passo >= 2,
                      on_click=lambda: setattr(s, "passo", min(s.passo + 1, 2))),
            style={"margin": "16px 0"},
        ),
        A("Pagination", current=s.pagina, total=87, show_size_changer=False,
          on_change=lambda p: setattr(s, "pagina", p)),
        ui.Paragraph(f"Página atual: {s.pagina}", style={"marginTop": 8}),
    )


def _dados(ctx, s):
    return secao(
        _dados,
        "Dados",
        ui.Row(
            ui.Col(A("Timeline", items=[
                {"children": "Pedido criado"},
                {"children": "Pagamento aprovado", "color": "green"},
                {"children": "Em transporte", "color": "blue"},
                {"children": "Entregue", "color": "gray"},
            ]), span=8),
            ui.Col(A("Tree", default_expand_all=True,
                     on_select=lambda keys: ctx.message.info(f"Selecionou {keys}"),
                     tree_data=[{"title": "Brasil", "key": "br", "children": [
                         {"title": "São Paulo", "key": "sp", "children": [
                             {"title": "Campinas", "key": "cps"}, {"title": "Sorocaba", "key": "sor"}]},
                         {"title": "Minas Gerais", "key": "mg"}]}]), span=8),
            ui.Col(ui.Descriptions(
                ui.DescriptionsItem("Borborema", label="Empresa"),
                ui.DescriptionsItem("Ativo", label="Status"),
                ui.DescriptionsItem("Campinas", label="Cidade"),
                column=1, size="small", bordered=True), span=8),
            gutter=16,
        ),
        ui.Divider(),
        ui.Space(
            A("Skeleton", active=True, paragraph={"rows": 2}, style={"width": 260}),
            A("Skeleton.Avatar", active=True),
            ui.Empty(description="Nada por aqui", image_style={"height": 48}),
            ui.Spin(tip="Carregando..."),
            wrap=True, align="start",
        ),
    )


# imagem embutida (SVG) para o exemplo de Image, sem depender de rede
_IMG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='160'>"
        "<rect width='100%25' height='100%25' fill='%231677ff'/>"
        "<text x='50%25' y='54%25' fill='white' font-size='28' text-anchor='middle'>antdpy</text></svg>")
_PRAZO = int((time.time() + 3 * 3600) * 1000)  # Countdown: 3h a partir de agora (ms)


def _geral(ctx, s):
    return secao(
        _geral,
        "Geral: botões e tipografia",
        ui.Space(
            ui.Button("Primary", type="primary"), ui.Button("Default"),
            ui.Button("Dashed", type="dashed"), ui.Button("Text", type="text"),
            ui.Button("Link", type="link"), ui.Button("Danger", danger=True),
            ui.Button("Ghost", type="primary", ghost=True),
            ui.Button("Carregando", type="primary", loading=True),
            ui.Button(icon="SearchOutlined", shape="circle"),
            ui.Button("Pequeno", size="small"), ui.Button("Grande", size="large"),
            ui.Button("Desabilitado", disabled=True),
            wrap=True,
        ),
        ui.Divider(),
        ui.Title("Título nível 3", level=3),
        ui.Space(
            ui.Text("normal"), ui.Text("secondary", type="secondary"),
            ui.Text("success", type="success"), ui.Text("warning", type="warning"),
            ui.Text("danger", type="danger"), ui.Text("strong", strong=True),
            A("Typography.Text", "riscado", delete=True),
            A("Typography.Text", "marcado", mark=True),
            A("Typography.Text", "code", code=True),
            A("Typography.Text", "Ctrl", keyboard=True),
            A("Typography.Link", "link", href="https://ant.design", target="_blank"),
            wrap=True,
        ),
        A("Typography.Paragraph", "Texto longo que será truncado com reticências quando passar "
          "de duas linhas. " * 4, ellipsis={"rows": 2, "expandable": True, "symbol": "mais"},
          copyable=True, style={"marginTop": 8}),
    )


def _layout(ctx, s):
    caixa = {"background": "#e6f4ff", "padding": 12, "textAlign": "center", "borderRadius": 6}
    return secao(
        _layout,
        "Layout: grid, flex, space e splitter",
        ui.Row(
            *[ui.Col(ui.Html("div", f"span {n}", style=caixa), span=n) for n in (4, 8, 12)],
            gutter=8,
        ),
        ui.Row(
            ui.Col(ui.Html("div", "responsivo", style=caixa), xs=24, md=12, lg=8),
            ui.Col(ui.Html("div", "responsivo", style=caixa), xs=24, md=12, lg=8),
            ui.Col(ui.Html("div", "responsivo", style=caixa), xs=24, md=24, lg=8),
            gutter=8, style={"marginTop": 8},
        ),
        ui.Divider("Flex"),
        ui.Flex(*[ui.Html("div", str(i), style=caixa) for i in range(1, 5)],
                justify="space-between", align="center", gap=8),
        ui.Divider("Space.Compact"),
        A("Space.Compact", ui.Input(placeholder="Domínio", style={"width": 200}),
          ui.Button("Buscar", type="primary")),
        ui.Divider("Splitter"),
        A("Splitter",
          A("Splitter.Panel", ui.Html("div", "Painel A (arraste a divisória)", style={"padding": 12}),
            default_size="40%", min="20%", max="70%"),
          A("Splitter.Panel", ui.Html("div", "Painel B", style={"padding": 12})),
          style={"height": 100, "border": "1px solid rgba(5,5,5,0.06)"}),
    )


def _formulario(ctx, s):
    return secao(
        _formulario,
        "Formulário com validação",
        ui.Form(
            ui.FormItem(ui.Input(placeholder="voce@exemplo.com"), label="E-mail", name="email",
                        rules=[{"required": True, "message": "Informe o e-mail"},
                               {"type": "email", "message": "E-mail inválido"}]),
            ui.FormItem(ui.Password(placeholder="Senha"), label="Senha", name="senha",
                        rules=[{"required": True, "min": 6, "message": "Mínimo de 6 caracteres"}]),
            ui.FormItem(ui.InputNumber(min=18, max=99, style={"width": 120}), label="Idade", name="idade"),
            ui.FormItem(ui.TextArea(rows=2, placeholder="Observações"), label="Notas", name="notas"),
            ui.FormItem(A("Input.OTP", length=4), label="Código", name="otp"),
            ui.FormItem(ui.Checkbox("Lembrar de mim"), name="lembrar", value_prop_name="checked"),
            ui.FormItem(ui.Button("Entrar", type="primary", html_type="submit")),
            layout="vertical", style={"maxWidth": 360},
            on_finish=lambda v: ctx.message.success(f"Enviado: {sorted(v)}"),
        ),
    )


def _selecao(ctx, s):
    return secao(
        _selecao,
        "Seleção avançada",
        ui.Space(
            ui.Select(mode="multiple", placeholder="Várias opções", style={"width": 220},
                      options=[{"label": x, "value": x} for x in ("Python", "React", "Antd", "SQL")]),
            ui.Select(mode="tags", placeholder="Tags livres", style={"width": 180}),
            ui.Select(show_search=True, placeholder="Buscar", style={"width": 160}, allow_clear=True,
                      options=[{"label": x, "value": x} for x in ("Campinas", "Santos", "Sorocaba")]),
            A("Cascader", placeholder="Estado / cidade", style={"width": 200}, options=[
                {"value": "sp", "label": "São Paulo", "children": [
                    {"value": "cps", "label": "Campinas"}, {"value": "sto", "label": "Santos"}]},
                {"value": "mg", "label": "Minas Gerais", "children": [
                    {"value": "bh", "label": "Belo Horizonte"}]},
            ]),
            A("TreeSelect", placeholder="Árvore", style={"width": 180}, tree_default_expand_all=True,
              tree_data=[{"title": "Brasil", "value": "br", "children": [
                  {"title": "São Paulo", "value": "sp"}, {"title": "Minas", "value": "mg"}]}]),
            A("Mentions", placeholder="Digite @ para mencionar", style={"width": 220},
              options=[{"value": "ana", "label": "ana"}, {"value": "bruno", "label": "bruno"}]),
            wrap=True,
        ),
        ui.Divider(),
        ui.Space(
            A("Checkbox.Group", options=["Maçã", "Pera", "Uva"], default_value=["Pera"]),
            A("Radio.Group", options=["A", "B", "C"], default_value="A", option_type="button"),
            A("InputNumber", default_value=3, min=0, max=10, addon_after="un"),
            A("Input.Search", placeholder="Buscar", enter_button=True, style={"width": 220},
              on_search=lambda v: ctx.message.info(f"Buscou: {v}")),
            wrap=True,
        ),
    )


def _cartoes(ctx, s):
    return secao(
        _cartoes,
        "Cartões, abas e mídia",
        ui.Row(
            ui.Col(A("Card", A("Card.Meta", title="Card.Meta", description="Descrição do cartão",
                               avatar=A("Avatar", icon=ui.Icon("UserOutlined"))),
                     hoverable=True,
                     actions=[ui.Icon("EditOutlined"), ui.Icon("SettingOutlined"),
                              ui.Icon("EllipsisOutlined")]), span=8),
            ui.Col(A("Tabs", default_active_key="1", items=[
                {"key": "1", "label": "Aba 1", "children": ui.Paragraph("Conteúdo da aba 1")},
                {"key": "2", "label": "Aba 2", "children": ui.Paragraph("Conteúdo da aba 2")},
                {"key": "3", "label": "Desabilitada", "disabled": True, "children": ""},
            ]), span=8),
            ui.Col(ui.Space(
                A("QRCode", value="https://ant.design", size=120),
                A("Image", src=_IMG, width=120, alt="exemplo"),
                orientation="vertical"), span=8),
            gutter=16,
        ),
        ui.Divider(),
        A("Carousel", *[
            ui.Html("div", f"Slide {n}", style={"height": 80, "lineHeight": "80px", "textAlign": "center",
                                                 "background": "#364d79", "color": "#fff"})
            for n in range(1, 4)
        ], autoplay=True),
    )


def _interacao(ctx, s):
    return secao(
        _interacao,
        "Popover, Tag selecionável, Countdown e mais",
        ui.Space(
            A("Popover", ui.Button("Popover"), title="Título", content="Conteúdo do popover"),
            A("Tooltip", ui.Button("Tooltip"), title="Dica rápida", placement="bottom"),
            A("Tag.CheckableTag", "Selecionável", checked=s.tag_marcada,
              on_change=lambda v: setattr(s, "tag_marcada", v)),
            A("Statistic.Countdown", title="Promoção termina em", value=_PRAZO),
            ui.Button("Abrir Modal", on_click=lambda: setattr(s, "modal", True)),
            A("Modal", ui.Paragraph("Modal controlado pelo estado Python."), open=s.modal,
              title="Modal", ok_text="OK", cancel_text="Cancelar",
              on_ok=lambda: setattr(s, "modal", False), on_cancel=lambda: setattr(s, "modal", False)),
            wrap=True, align="start",
        ),
        ui.Divider(),
        A("Watermark", ui.Html("div", "Área com marca d'água", style={"height": 80, "padding": 16}),
          content="antdpy"),
        A("Result", status="success", title="Operação concluída",
          sub_title="Resultado usado para telas de confirmação.",
          extra=[ui.Button("Voltar", type="primary")]),
    )


def _calendario(ctx, s):
    return secao(
        _calendario,
        "Calendário",
        A("Calendar", fullscreen=False, style={"maxWidth": 320}),
    )


SECOES = [_feedback, _entradas, _exibicao, _navegacao, _dados, _geral, _layout, _formulario,
          _selecao, _cartoes, _interacao, _calendario]


@app.page("/componentes")
def componentes(ctx: ap.Context):
    s = ctx.state.init(passo=1, nota=3, visao="Lista", pagina=1, volume=30, drawer=False,
                       notificacoes=True, data="—", tag_marcada=True, modal=False)
    return shell(
        ctx,
        ui.Space(ui.Title("Galeria de componentes", level=2), *[f(ctx, s) for f in SECOES],
                 orientation="vertical", style={"width": "100%"}),
    )


if __name__ == "__main__":
    app.run()
