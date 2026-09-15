import { useState } from 'react'
import type { Machine, Meta } from '../types'

interface Props {
  machines: Machine[]
  currentId: number | null
  meta: Meta | null
  onSelect: (id: number) => void
  onCreate: (b: { model_name: string; revision_code: string; rated_pressure_bar: number }) => Promise<void>
}

export default function MachinePanel({ machines, currentId, meta, onSelect, onCreate }: Props) {
  const [model, setModel] = useState('')
  const [rev, setRev] = useState('')
  const [pressure, setPressure] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const p = parseFloat(pressure)
    if (!model.trim() || !rev.trim() || !(p > 0)) {
      setErr('请完整填写整机型号、修订码与额定压力')
      return
    }
    setBusy(true)
    setErr(null)
    try {
      await onCreate({ model_name: model.trim(), revision_code: rev.trim(), rated_pressure_bar: p })
      setModel(''); setRev(''); setPressure('')
    } catch (ex) {
      setErr((ex as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2><span className="idx">1</span>机型登记</h2>
      <form className="machine-form" onSubmit={submit}>
        <label>整机型号
          <input value={model} onChange={e => setModel(e.target.value)} placeholder="如 K-200" />
        </label>
        <label>修订码
          <input value={rev} onChange={e => setRev(e.target.value)} placeholder="如 B" />
        </label>
        <label>额定压力 (bar)
          <input value={pressure} onChange={e => setPressure(e.target.value)} inputMode="decimal" placeholder="如 250" />
        </label>
        <button type="submit" disabled={busy}>登记</button>
      </form>
      {err && <p className="err">{err}</p>}

      {machines.length > 0 && (
        <ul className="machine-list">
          {machines.map(m => (
            <li key={m.id}
                className={m.id === currentId ? 'active' : ''}
                onClick={() => onSelect(m.id)}>
              <strong>{m.model_name}</strong>
              <span className="tag">修订 {m.revision_code}</span>
              <span className="tag">{m.rated_pressure_bar} bar</span>
              {m.has_selection && <span className="tag ok">已选定组合</span>}
            </li>
          ))}
        </ul>
      )}

      {meta && meta.model_table.length > 0 && (
        <details className="model-table">
          <summary>内置型号表（{meta.model_table.length} 条，仅用于与实测比对）</summary>
          <table>
            <thead><tr><th>型号</th><th>修订</th><th>额定 bar</th><th>接口规格</th></tr></thead>
            <tbody>
              {meta.model_table.map(r => (
                <tr key={String(r.model_name) + '-' + String(r.revision_code)}>
                  <td>{r.model_name}</td><td>{r.revision_code}</td><td>{r.rated_pressure_bar}</td>
                  <td>{Object.entries(r)
                    .filter(([k]) => !['model_name', 'revision_code', 'rated_pressure_bar'].includes(k))
                    .map(([k, v]) => `${meta.measurement_keys[k]?.label ?? k}: ${v}`)
                    .join('；')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  )
}
