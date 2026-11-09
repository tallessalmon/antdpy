import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react'
import { Renderer } from './renderer.jsx'

const n = (type, props = {}, children = [], key) => ({ $node: type, props, children, ...(key && { key }) })

describe('Renderer', () => {
  it('renderiza Button, Typography e Icon e dispara evento', () => {
    const send = vi.fn()
    const tree = n('div', {}, [
      n('Typography.Title', { level: 3 }, ['Olá']),
      n('Button', { type: 'primary', icon: n('Icon', { name: 'PlusOutlined' }), onClick: { $event: 'r.c1.on_click' } }, ['Salvar']),
    ])
    render(<Renderer tree={tree} send={send} ack={0} />)
    expect(screen.getByText('Olá')).toBeTruthy()
    fireEvent.click(screen.getByText('Salvar'))
    expect(send).toHaveBeenCalledTimes(1)
    const msg = send.mock.calls[0][0]
    expect(msg.type).toBe('event')
    expect(msg.id).toBe('r.c1.on_click')
    expect(msg.seq).toBe(1)
    cleanup()
  })

  it('Input controlado envia o valor (string) e mantém texto local', () => {
    const send = vi.fn()
    const tree = n('Input', { value: '', placeholder: 'nome', onChange: { $event: 'r.on_change' } })
    render(<Renderer tree={tree} send={send} ack={0} />)
    const input = screen.getByPlaceholderText('nome')
    fireEvent.change(input, { target: { value: 'abc' } })
    expect(send.mock.calls[0][0].args).toEqual(['abc'])
    expect(input.value).toBe('abc') // local, sem esperar o servidor
    cleanup()
  })

  it('Input volta ao valor do servidor quando o ack cobre a edição', () => {
    const send = vi.fn()
    const tree = n('Input', { value: '', placeholder: 'x', onChange: { $event: 'h' } })
    const { rerender } = render(<Renderer tree={tree} send={send} ack={0} />)
    const input = screen.getByPlaceholderText('x')
    fireEvent.change(input, { target: { value: 'zzz' } })
    const seq = send.mock.calls[0][0].seq
    rerender(<Renderer tree={tree} send={send} ack={seq} />) // servidor ignorou a edição
    expect(input.value).toBe('')
    cleanup()
  })

  it('Table com colunas, tag, money e ações de linha', () => {
    const send = vi.fn()
    const tree = n('Table', {
      rowKey: 'id',
      dataSource: [{ id: 1, nome: 'Alfa', status: 'ativo', saldo: 10 }],
      columns: [
        { title: 'Nome', dataIndex: 'nome', key: 'nome' },
        { title: 'Status', dataIndex: 'status', key: 'status', render: 'tag' },
        { title: 'Saldo', dataIndex: 'saldo', key: 'saldo', render: 'money' },
        { title: 'Ações', key: 'a', actions: [{ label: 'Editar', onClick: { $event: 'edit' } }] },
      ],
    })
    render(<Renderer tree={tree} send={send} ack={0} />)
    expect(screen.getByText('Alfa')).toBeTruthy()
    expect(screen.getByText('ativo')).toBeTruthy()
    expect(document.body.textContent).toMatch(/R\$\s?10,00/)
    fireEvent.click(screen.getByText('Editar'))
    const msg = send.mock.calls[0][0]
    expect(msg.id).toBe('edit')
    expect(msg.args[0]).toMatchObject({ id: 1, nome: 'Alfa' })
    cleanup()
  })

  it('Form + Form.Item: injeta valor no filho, valida e envia on_finish com os valores', async () => {
    const send = vi.fn()
    const tree = n('Form', { layout: 'vertical', onFinish: { $event: 'fin' } }, [
      n('Form.Item', { name: 'nome', label: 'Nome', rules: [{ required: true, message: 'Informe o nome' }] }, [n('Input', { placeholder: 'n' })]),
      n('Button', { htmlType: 'submit', type: 'primary' }, ['Enviar']),
    ])
    render(<Renderer tree={tree} send={send} ack={0} />)
    await act(async () => { fireEvent.click(screen.getByText('Enviar')) })
    await screen.findByText('Informe o nome') // validação do Antd
    expect(send).not.toHaveBeenCalled()
    fireEvent.change(screen.getByPlaceholderText('n'), { target: { value: 'Maria' } })
    await act(async () => { fireEvent.click(screen.getByText('Enviar')) })
    await vi.waitFor(() => expect(send).toHaveBeenCalled())
    expect(send.mock.calls.at(-1)[0].args[0]).toEqual({ nome: 'Maria' })
    cleanup()
  })

  it('Componente desconhecido mostra alerta em vez de quebrar', () => {
    render(<Renderer tree={n('NaoExiste')} send={() => {}} ack={0} />)
    expect(screen.getByText(/Componente desconhecido: NaoExiste/)).toBeTruthy()
    cleanup()
  })
})
