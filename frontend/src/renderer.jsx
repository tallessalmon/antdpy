// Renderizador genérico: transforma a árvore JSON enviada pelo Python em elementos React/Antd.
//
// Formato dos nós:   { "$node": "Form.Item", props: {...}, children: [...], key?: "..." }
// Callbacks:         { "$event": "<id>" }  -> função que envia o evento ao Python
import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import * as antd from 'antd'
import * as Icons from '@ant-design/icons'

const { Alert, Button, Space, Tag } = antd

// ack = último seq de evento já processado pelo servidor (evita sobrescrever digitação em curso)
export const AckContext = createContext(0)
export const RenderContext = createContext(null) // { send, handler(id) }

// ------------------------------------------------------------------ utilidades
function resolveType(type) {
  if (type === 'Icon') return 'Icon'
  if (type === 'Fragment') return React.Fragment
  if (/^[a-z]/.test(type)) return type // tag HTML
  return type.split('.').reduce((o, k) => (o == null ? undefined : o[k]), antd)
}

const isNode = (v) => v && typeof v === 'object' && '$node' in v

/** Converte args de eventos do React/Antd em valores JSON simples para o Python. */
export function toJsonArg(a) {
  if (a && typeof a === 'object' && typeof a.preventDefault === 'function') {
    const t = a.target
    if (!t) return null
    return t.type === 'checkbox' ? t.checked : (t.value ?? null)
  }
  if (a && typeof a === 'object' && typeof a.toISOString === 'function') return a.toISOString()
  try {
    return JSON.parse(
      JSON.stringify(a, (_k, v) => {
        if (typeof v === 'function') return undefined
        if (typeof Node !== 'undefined' && v instanceof Node) return undefined
        if (v && typeof v === 'object' && (v.nativeEvent || v.$$typeof)) return undefined
        return v
      }),
    ) ?? null
  } catch {
    return null
  }
}

function revive(v, rc) {
  if (Array.isArray(v)) return v.map((x, i) => reviveItem(x, rc, i))
  if (v && typeof v === 'object') {
    if ('$event' in v) return rc.handler(v.$event)
    if (isNode(v)) return <Node node={v} />
    const out = {}
    for (const k of Object.keys(v)) out[k] = revive(v[k], rc)
    return out
  }
  return v
}

function reviveItem(x, rc, i) {
  if (isNode(x)) return <Node key={x.key ?? i} node={x} />
  return revive(x, rc)
}

// ---------------------------------------------------- adaptadores por tipo de componente
const CELL_RENDERERS = {
  tag: (v) => (v == null || v === '' ? null : <Tag>{String(v)}</Tag>),
  boolean: (v) => (v ? <Icons.CheckOutlined /> : <Icons.CloseOutlined />),
  money: (v) =>
    v == null ? '' : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  date: (v) => (v ? new Date(v).toLocaleDateString('pt-BR') : ''),
}

function adaptColumns(columns = []) {
  return columns.map(({ render, actions, sorter, ...col }) => {
    const out = { ...col }
    if (sorter === true && col.dataIndex != null) {
      // ordenação local (cliente) simples; para ordenar no servidor use `on_change`
      out.sorter = (a, b) => {
        const get = (r) => [].concat(col.dataIndex).reduce((o, k) => o?.[k], r)
        const x = get(a), y = get(b)
        return typeof x === 'number' && typeof y === 'number'
          ? x - y
          : String(x ?? '').localeCompare(String(y ?? ''))
      }
    } else if (sorter != null && sorter !== false) {
      out.sorter = sorter
    }
    if (actions) {
      out.render = (_, record) => (
        <Space size="small">
          {actions.map((a, i) => (
            <Button key={i} size="small" type="link" danger={a.danger} onClick={() => a.onClick?.(record)}>
              {a.label}
            </Button>
          ))}
        </Space>
      )
    } else if (typeof render === 'string' && CELL_RENDERERS[render]) {
      out.render = CELL_RENDERERS[render]
    }
    return out
  })
}

const PROP_ADAPTERS = {
  'Form.Item': ({ rules, ...p }) => ({
    ...p,
    ...(rules && {
      rules: rules.map((r) => (typeof r.pattern === 'string' ? { ...r, pattern: new RegExp(r.pattern) } : r)),
    }),
  }),
  Table: ({ columns, onRowClick, onChange, rowKey, dataSource, ...p }) => ({
    ...p,
    dataSource,
    columns: adaptColumns(columns),
    rowKey: rowKey ?? ((_, i) => i),
    ...(onRowClick && { onRow: (record) => ({ onClick: () => onRowClick(record), style: { cursor: 'pointer' } }) }),
    ...(onChange && { onChange: (pagination, filters, sorter) => onChange(pagination, filters, sorter) }),
  }),
}

// Componentes cujo valor é mantido localmente (digitação fluida) e sincronizado com o Python.
const LOCAL_VALUE = {
  Input: 'value', 'Input.TextArea': 'value', 'Input.Password': 'value', 'Input.Search': 'value',
  InputNumber: 'value', Select: 'value', 'Radio.Group': 'value', Slider: 'value',
  Switch: 'checked', Checkbox: 'checked',
}

function LocalValue({ Comp, valueProp, rc, ...props }) {
  const { [valueProp]: external, onChange, ...rest } = props
  const ack = useContext(AckContext)
  const [local, setLocal] = useState(external)
  const lastSeq = useRef(0)
  useEffect(() => {
    // só aceita o valor do servidor quando ele já processou todas as minhas edições
    if (ack >= lastSeq.current) setLocal(external)
  }, [external, ack])
  return (
    <Comp
      {...rest}
      {...{ [valueProp]: local }}
      onChange={(...a) => {
        const isEvent = a[0] && typeof a[0].preventDefault === 'function'
        setLocal(isEvent ? toJsonArg(a[0]) : a[0])
        if (onChange) lastSeq.current = rc.nextSeq()
        onChange?.(...a)
      }}
    />
  )
}

// ----------------------------------------------------------------------------- Node
export function Node({ node, ...injected }) {
  const rc = useContext(RenderContext)
  const Comp = resolveType(node.$node)

  if (node.$node === 'Icon') {
    const I = Icons[node.props.name]
    return I ? <I {...injected} style={node.props.style} /> : null
  }
  if (!Comp) {
    return <Alert type="error" showIcon message={`Componente desconhecido: ${node.$node}`} />
  }

  const adapter = PROP_ADAPTERS[node.$node]
  let props = revive(node.props, rc)
  if (adapter) props = adapter(props)

  // Form.Item injeta value/onChange no filho: compõe com o on_change vindo do Python
  const { onChange: injectedOnChange, ...injectedRest } = injected
  props = { ...props, ...injectedRest }
  if (injectedOnChange) {
    const own = props.onChange
    props.onChange = (...a) => { injectedOnChange(...a); own?.(...a) }
  }

  const children = node.children.map((c, i) => (isNode(c) ? <Node key={c.key ?? i} node={c} /> : c))
  const valueProp = LOCAL_VALUE[node.$node]

  if (valueProp && !injectedOnChange && valueProp in props && typeof Comp !== 'string') {
    return React.createElement(LocalValue, { Comp, valueProp, rc, ...props }, ...children)
  }
  return React.createElement(Comp, props, ...children)
}

export function Renderer({ tree, send, ack }) {
  const handlers = useRef(new Map())
  const seq = useRef(0)
  const rcRef = useRef(null)
  if (!rcRef.current) {
    rcRef.current = {
      nextSeq: () => ++seq.current,
      handler(id) {
        let fn = handlers.current.get(id)
        if (!fn) {
          fn = (...args) => {
            const s = rcRef.current.nextSeq()
            rcRef.current.send({ type: 'event', id, args: args.slice(0, 4).map(toJsonArg), seq: s })
          }
          handlers.current.set(id, fn)
        }
        return fn
      },
    }
  }
  rcRef.current.send = send
  return (
    <RenderContext.Provider value={rcRef.current}>
      <AckContext.Provider value={ack}>
        <Node node={tree} />
      </AckContext.Provider>
    </RenderContext.Provider>
  )
}
