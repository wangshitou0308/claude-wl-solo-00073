import { useEffect, useState } from 'react'
import type { StepState } from '../types'

interface Props {
  steps: StepState[]
  onConfirm: (key: string, checks: Record<string, boolean>) => Promise<void>
  onRevoke: (key: string) => Promise<void>
  onError: (msg: string) => void
}

const STATUS_LABEL = { pending: '待执行', confirmed: '已确认', failed: '已失败' } as const

function StepCard({ step, index, onConfirm, onRevoke, onError }: {
  step: StepState
  index: number
  onConfirm: Props['onConfirm']
  onRevoke: Props['onRevoke']
  onError: Props['onError']
}) {
  const [values, setValues] = useState<Record<string, boolean>>(step.values)
  const [busy, setBusy] = useState(false)

  useEffect(() => setValues(step.values), [step.values, step.status])

  const locked = !!step.locked_reason
  const done = step.status === 'confirmed'
  const failed = step.status === 'failed'
  const editable = !locked && !done

  const toggle = (id: string) => {
    if (!editable) return
    setValues(v => ({ ...v, [id]: !v[id] }))
  }

  const confirm = async () => {
    setBusy(true)
    try {
      await onConfirm(step.key, values)
    } catch (ex) {
      onError((ex as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const revoke = async () => {
    setBusy(true)
    try {
      await onRevoke(step.key)
    } catch (ex) {
      onError((ex as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className={`step ${step.status} ${locked ? 'locked' : ''}`}>
      <div className="step-head">
        <span className={`step-no ${step.status}`}>{done ? '✓' : failed ? '✗' : index + 1}</span>
        <div>
          <h3>{step.title}<span className={`status ${step.status}`}>{STATUS_LABEL[step.status]}</span></h3>
          <p className="muted">{step.desc}</p>
        </div>
      </div>

      {locked && <p className="banner warn">🔒 {step.locked_reason}</p>}
      {failed && <p className="banner danger">已报告异常，流程被阻止。处理后可撤回本步重新确认。</p>}

      <ul className="checks">
        {step.check_defs.map(c => (
          <li key={c.id}
              className={`check ${c.kind} ${values[c.id] ? 'on' : ''} ${!editable ? 'readonly' : ''}`}
              onClick={() => toggle(c.id)}>
            <span className="box">{values[c.id] ? (c.kind === 'failure' ? '!' : '✓') : ''}</span>
            <span>{c.kind === 'failure' ? '⚠ 报告异常：' : ''}{c.label}</span>
          </li>
        ))}
      </ul>

      <div className="step-actions">
        {editable && (
          <button className="primary" disabled={busy} onClick={confirm}>确认本步</button>
        )}
        {(done || failed) && (
          <button className="link" disabled={busy} onClick={revoke}>撤回（本步及后续回到待办）</button>
        )}
      </div>
    </li>
  )
}

export default function StepsPanel({ steps, onConfirm, onRevoke, onError }: Props) {
  const doneCount = steps.filter(s => s.status === 'confirmed').length
  return (
    <section className="panel">
      <h2><span className="idx">5</span>复装步骤 <span className="muted">（{doneCount}/{steps.length}）</span></h2>
      <ol className="steps">
        {steps.map((s, i) => (
          <StepCard key={s.key} step={s} index={i}
                    onConfirm={onConfirm} onRevoke={onRevoke} onError={onError} />
        ))}
      </ol>
    </section>
  )
}
