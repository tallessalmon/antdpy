# antdpy

Ant Design para Python. Você declara a UI em Python; o front (React + Antd **de verdade**) renderiza
no navegador e os eventos voltam para o Python por WebSocket.

```python
import antdpy as ap
from antdpy import ui

app = ap.App(title="Meu app", locale="pt_BR")

@app.page("/")
def home(ctx):
    s = ctx.state.init(count=0)          # estado por sessão
    return ui.Space(
        ui.Statistic(title="Cliques", value=s.count),
        ui.Button("Somar", type="primary", icon="PlusOutlined",
                  on_click=lambda: setattr(s, "count", s.count + 1)),
    )

app.run()   # http://127.0.0.1:8000   (ou: uvicorn meu_modulo:app)
```

## Como funciona

1. `@app.page` devolve uma árvore de `Component`s (`ui.Button`, `ui.Table`, ...).
2. A árvore vira JSON (`{"$node": "Form.Item", props, children}`); callbacks `on_*` viram ids.
3. O front resolve `"Form.Item"` direto no módulo `antd`, então **qualquer** componente do Antd
   funciona, mesmo sem wrapper: `ui.Antd("Rate", value=3)`.
4. Evento no navegador → Python roda o handler → a página é re-renderizada → nova árvore é enviada
   (só se mudou) e o React faz o diff.

Convenções: props em `snake_case` viram `camelCase`; dicts aninhados (`style`, `options`, linhas de
tabela) ficam no formato nativo do Antd. `None` vira `null`; o padrão `UNSET` significa "não enviar".

## Componentes com wrapper (MVP)

Layout (`Layout/Header/Sider/Content/Footer`, `Row`, `Col`, `Space`, `Flex`, `Divider`, `Card`),
texto (`Title`, `Text`, `Paragraph`), `Button`, `Icon`, `Alert`, `Tag`, `Spin`, `Statistic`,
`Form`/`FormItem`, `Input` (+`TextArea`, `Password`, `Search`), `InputNumber`, `Select`, `Checkbox`,
`Radio`/`RadioGroup`, `Switch`, `Slider`, `Table` (+`Column`, `Action`, `Table.from_dataframe`),
`Modal`, `Tabs`, `Menu`, `Descriptions`, `Badge`, `Progress`, `Result`, `Empty`.

Extras do front: células `render="tag" | "boolean" | "money" | "date"`, botões de linha com
`Column(actions=[Action("Editar", fn)])`, `rules` com `pattern` em string, tema via
`App(theme={"token": {...}, "algorithm": "dark"})`, `ctx.message.success(...)`,
`ctx.notification.info(...)`, `ctx.navigate("/rota")`, rotas com parâmetros (`/clientes/{id}`).

## Layout de aplicação

`ui.AppShell` monta barra lateral fixa (recolhível, com rolagem própria), cabeçalho, conteúdo e rodapé:

```python
def shell(ctx, *content):
    return ui.AppShell(
        *content,
        menu_items=[{"key": "/", "label": "Início", "icon": ui.Icon("HomeOutlined")},
                    {"key": "/clientes", "label": "Clientes", "icon": ui.Icon("TeamOutlined")}],
        selected_key=ctx.path,
        on_navigate=ctx.navigate,
        logo="Meu app",                      # opcionais: logo, header, footer, breadcrumb
        header="Painel",
        breadcrumb=["Início", "Clientes"],
        theme="dark",                        # tema da barra lateral
    )
```

## Desenvolvimento

```bash
pip install -e ".[dev]"
cd frontend && npm install
npm run build        # gera src/antdpy/static (é o que o pacote Python serve)
npm run dev          # dev com HMR; rode `python examples/demo.py` ao lado
npm test             # testes do renderizador (vitest + jsdom)
cd .. && pytest      # testes do núcleo e do protocolo WebSocket
python examples/demo.py
```

## Limitações conhecidas do MVP

- Estado vive na conexão WebSocket: recarregar a página zera `ctx.state`.
- A árvore inteira é reenviada a cada mudança (sem patch incremental).
- Bundle grande (~2,6 MB / 725 KB gzip) porque importa o Antd e todos os ícones por nome dinâmico.
  Próximo passo: gerar o bundle só com os componentes usados / ícones sob demanda.
- Sem wrappers tipados para `DatePicker` (valores `dayjs`), `Upload`, `Tree`, etc. — o `ui.Antd(...)`
  cobre o uso básico, mas valores especiais precisam de adaptador em `renderer.jsx`.
- Handlers sync rodam em thread; `async def` + `await ctx.refresh()` permite mostrar progresso.
- Nunca foi validado visualmente em navegador real (só jsdom + WebSocket real).
