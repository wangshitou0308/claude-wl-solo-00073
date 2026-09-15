import { useState } from 'react'
import type { Analysis, Meta } from '../types'

interface Props {
  analysis: Analysis
  meta: Meta
  onAdd: (key: string, value: number, note: string) => Promise<void>
  onDelete: (key: string) => Promise<void>
}

export default function EvidencePanel({ analysis, meta, onAdd, onDelete }: Props) {
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const [note, setNote] = useState('')
  const [err, setErr] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const v = parseFloat(value)
    if (!key || !(v > 0)) {
      setErr('请选择测量项并填写有效数值')
      return
    }
    setErr(null)
    try {
      await onAdd(key, v, note.trim())
      setValue(''); setNote('')
    } catch (ex) {
      setErr((ex as Error).message)
    }
  }

  return (
    <section className="panel">
      <h2><span className="idx">2</span>实测录入</h2>
      <p className="hint">只记录实测值；缺失项不会被外观或品牌推断补齐。</p>
      <form className="evidence-form" onSubmit={submit}>
        <select value={key} onChange={e => setKey(e.target.value)}>
          <option value="">选择测量项…</option>
          {Object.entries(meta.measurement_keys).map(([k, m]) => (
            <option key={k} value={k}>{m.label}（公差 ±{m.tol}）</option>
          ))}
        </select>
        <input value={value} onChange={e => setValue(e.target.value)}
               inputMode="decimal" placeholder="实测值 mm" />
        <input value={note} onChange={e => setNote(e.target.value)} placeholder="备注（可选）" />
        <button type="submit">录入</button>
      </form>
      {err && <p className="err">{err}</p>}

      {analysis.evidence.length === 0
        ? <p className="muted">尚无实测证据。</p>
        : (
          <table className="evidence-table">
            <thead><tr><th>测量项</th><th>实测值</th><th>备注</th><th></th></tr></thead>
            <tbody>
              {analysis.evidence.map(ev => (
                <tr key={ev.key}>
                  <td>{meta.measurement_keys[ev.key]?.label ?? ev.key}</td>
                  <td><strong>{ev.value} mm</strong></td>
                  <td className="muted">{ev.note ?? '—'}</td>
                  <td><button className="link danger" onClick={() => onDelete(ev.key)}>删除</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
    </section>
  )
}
