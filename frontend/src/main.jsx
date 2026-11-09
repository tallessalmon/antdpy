import React, { useCallback, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ConfigProvider, Result, Spin, message, notification, theme as antdTheme } from 'antd'
import en_US from 'antd/locale/en_US'
import pt_BR from 'antd/locale/pt_BR'
import { Renderer } from './renderer.jsx'

const LOCALES = { en_US, pt_BR }

function buildTheme(cfg = {}) {
  const algos = [].concat(cfg.algorithm ?? []).map((a) => ({
    dark: antdTheme.darkAlgorithm,
    compact: antdTheme.compactAlgorithm,
    default: antdTheme.defaultAlgorithm,
  })[a]).filter(Boolean)
  return { ...cfg, ...(algos.length && { algorithm: algos }) }
}

function App() {
  const [config, setConfig] = useState({ title: 'antdpy', theme: {}, locale: 'en_US' })
  const [tree, setTree] = useState(null)
  const [ack, setAck] = useState(0)
  const [online, setOnline] = useState(false)
  const wsRef = useRef(null)
  const [msgApi, msgHolder] = message.useMessage()
  const [noteApi, noteHolder] = notification.useNotification()

  const send = useCallback((obj) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj))
  }, [])

  useEffect(() => {
    let closed = false
    let timer
    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/_antdpy/ws`)
      wsRef.current = ws
      ws.onopen = () => {
        setOnline(true)
        ws.send(JSON.stringify({ type: 'init', path: location.pathname + location.search }))
      }
      ws.onmessage = (e) => {
        const m = JSON.parse(e.data)
        if (m.ack !== undefined) setAck(m.ack)
        switch (m.type) {
          case 'config': setConfig(m); document.title = m.title; break
          case 'render': setTree(m.tree); break
          case 'message': msgApi.open({ type: m.level, content: m.content, duration: m.duration }); break
          case 'notification': noteApi[m.level]?.({ message: m.content, description: m.description }); break
          case 'error': msgApi.error(m.content, 6); break
          case 'navigate':
            history.pushState({}, '', m.path)
            send({ type: 'init', path: m.path })
            break
        }
      }
      ws.onclose = () => {
        setOnline(false)
        if (!closed) timer = setTimeout(connect, 1500)
      }
    }
    const onPop = () => send({ type: 'init', path: location.pathname + location.search })
    window.addEventListener('popstate', onPop)
    connect()
    return () => {
      closed = true
      clearTimeout(timer)
      window.removeEventListener('popstate', onPop)
      wsRef.current?.close()
    }
  }, [])

  return (
    <ConfigProvider locale={LOCALES[config.locale] ?? en_US} theme={buildTheme(config.theme)}>
      {msgHolder}
      {noteHolder}
      {tree ? (
        <Renderer tree={tree} send={send} ack={ack} />
      ) : (
        <div style={{ display: 'grid', placeItems: 'center', height: '100vh' }}>
          {online ? <Spin size="large" /> : <Result status="warning" title="Conectando ao servidor…" />}
        </div>
      )}
    </ConfigProvider>
  )
}

createRoot(document.getElementById('root')).render(<App />)
