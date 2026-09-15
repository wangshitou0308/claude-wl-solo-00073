import { useMemo, useState } from 'react'
import type { Combo, Part, Slot } from '../types'
import { SLOT_LABEL } from '../types'

interface Props {
  parts: Part[]
  slots: Record<Slot, Part | null>
  onDrop: (slot: Slot, part: Part) => void
  onClearSlot: (slot: Slot) => void
  onValidate: () => Promise<Combo | null>
  onUse: () => Promise<void>
  validation: Combo | null
  busy: boolean
}

/** 爆炸图槽位布局（viewBox 960×340） */
const SLOT_POS: Record<Slot, { x: number; y: number }> = {
  hose_connector: { x: 130, y: 200 },
  gun: { x: 380, y: 200 },
  lance: { x: 700, y: 200 },
  o_ring: { x: 540, y: 78 },
}

const SLOT_ORDER: Slot[] = ['hose_connector', 'gun', 'lance', 'o_ring']

function SlotShape({ slot, filled }: { slot: Slot; filled: boolean }) {
  const stroke = filled ? '#4ade80' : '#64748b'
  const common = { fill: filled ? 'rgba(74,222,128,0.08)' : 'rgba(100,116,139,0.06)', stroke, strokeWidth: 1.6, strokeDasharray: filled ? 'none' : '6 4' }
  switch (slot) {
    case 'hose_connector':
      return (<g>
        <rect x={-46} y={-16} width={56} height={32} rx={5} {...common} />
        <polygon points="10,-20 34,-10 34,10 10,20" {...common} />
      </g>)
    case 'gun':
      return (<g>
        <path d="M-70,-18 L30,-18 L30,-4 L58,-4 L58,6 L30,6 L26,14 L-6,14 L-14,44 L-34,44 L-30,14 L-70,14 Z" {...common} />
        <rect x={-16} y={14} width={10} height={8} rx={2} {...common} />
      </g>)
    case 'lance':
      return (<g>
        <rect x={-90} y={-8} width={150} height={16} rx={8} {...common} />
        <polygon points="60,-5 84,0 60,5" {...common} />
      </g>)
    case 'o_ring':
      return (<g>
        <circle r={22} {...common} />
        <circle r={11} fill="none" stroke={stroke} strokeWidth={1.4} strokeDasharray={filled ? 'none' : '4 3'} />
      </g>)
  }
}

export default function ExplodedView({ parts, slots, onDrop, onClearSlot, onValidate, onUse, validation, busy }: Props) {
  const [held, setHeld] = useState<Part | null>(null)
  const [dragOver, setDragOver] = useState<Slot | null>(null)

  const byType = useMemo(() => {
    const g: Record<Slot, Part[]> = { gun: [], lance: [], hose_connector: [], o_ring: [] }
    for (const p of parts) g[p.part_type].push(p)
    return g
  }, [parts])

  const usedIds = useMemo(() => new Set(Object.values(slots).filter(Boolean).map(p => (p as Part).id)), [slots])
  const complete = SLOT_ORDER.every(s => slots[s])

  const place = (slot: Slot, part: Part) => {
    if (part.part_type !== slot) return
    onDrop(slot, part)
    setHeld(null)
  }

  return (
    <section className="panel">
      <h2><span className="idx">4</span>爆炸图 · 拖放候选部件</h2>
      <p className="hint">从下方候选区拖入（或点选后点击槽位）。判定只依据接口尺寸、公母端、止口深度与耐压；品牌与外观仅供参考。</p>

      <svg viewBox="0 0 960 340" className="exploded" role="img" aria-label="爆炸图">
        {/* 装配轴线与爆炸虚线 */}
        <line x1={60} y1={200} x2={900} y2={200} stroke="#334155" strokeWidth={1} strokeDasharray="2 6" />
        <line x1={176} y1={200} x2={310} y2={200} stroke="#475569" strokeWidth={1.4} strokeDasharray="7 5" />
        <line x1={438} y1={200} x2={610} y2={200} stroke="#475569" strokeWidth={1.4} strokeDasharray="7 5" />
        <line x1={540} y1={104} x2={540} y2={186} stroke="#475569" strokeWidth={1.4} strokeDasharray="7 5" />

        {/* 接口标注 */}
        <g className="joint-label">
          <circle cx={243} cy={200} r={11} /><text x={243} y={204}>①</text>
          <text x={243} y={232} className="joint-name">软管→枪</text>
        </g>
        <g className="joint-label">
          <circle cx={524} cy={200} r={11} /><text x={524} y={204}>②</text>
          <text x={524} y={232} className="joint-name">枪→杆</text>
        </g>
        <g className="joint-label">
          <circle cx={540} cy={142} r={11} /><text x={540} y={146}>◎</text>
          <text x={540} y={40} className="joint-name">密封圈</text>
        </g>

        {SLOT_ORDER.map(slot => {
          const pos = SLOT_POS[slot]
          const part = slots[slot]
          const over = dragOver === slot
          return (
            <g key={slot}
               transform={`translate(${pos.x},${pos.y})`}
               className={`slot ${over ? 'over' : ''} ${held && held.part_type === slot ? 'accepts' : ''}`}
               onDragOver={e => { e.preventDefault(); setDragOver(slot) }}
               onDragLeave={() => setDragOver(s => (s === slot ? null : s))}
               onDrop={e => {
                 e.preventDefault(); setDragOver(null)
                 try {
                   const p = JSON.parse(e.dataTransfer.getData('application/x-part')) as Part
                   place(slot, p)
                 } catch { /* 非部件拖拽 */ }
               }}
               onClick={() => { if (held) place(slot, held) }}>
              <rect x={-100} y={-60} width={200} height={120} fill="transparent" />
              <SlotShape slot={slot} filled={!!part} />
              <text y={slot === 'o_ring' ? 44 : 66} className="slot-label">
                {SLOT_LABEL[slot]}{part ? `：${part.code}` : '（空）'}
              </text>
              {part && (
                <text y={slot === 'o_ring' ? 58 : 80} className="slot-sub"
                      onClick={e => { e.stopPropagation(); onClearSlot(slot) }}>
                  点击移除
                </text>
              )}
            </g>
          )
        })}
      </svg>

      {/* 候选部件区 */}
      <div className="palette">
        {SLOT_ORDER.map(type => (
          <div key={type} className="palette-group">
            <h3>{SLOT_LABEL[type]}</h3>
            {byType[type].map(p => {
              const used = usedIds.has(p.id)
              const isHeld = held?.id === p.id
              return (
                <div key={p.id}
                     className={`part-card ${used ? 'used' : ''} ${isHeld ? 'held' : ''}`}
                     draggable={!used}
                     onDragStart={e => e.dataTransfer.setData('application/x-part', JSON.stringify(p))}
                     onClick={() => !used && setHeld(isHeld ? null : p)}
                     title={`${p.name}｜最低耐压 ${p.min_pressure_bar}bar｜${p.brand ?? ''}（品牌不参与判定）`}>
                  <strong>{p.code}</strong>
                  <span>{p.name}</span>
                  <em>{p.min_pressure_bar} bar</em>
                </div>
              )
            })}
          </div>
        ))}
      </div>
      {held && <p className="hint">已拿起 <strong>{held.code}</strong>，点击对应槽位放入；再点卡片放回。</p>}

      <div className="combo-actions">
        <button disabled={!complete || busy} onClick={onValidate}>校验此组合</button>
        <button className="primary" disabled={!complete || !validation?.ok || busy} onClick={onUse}>
          采用此组合
        </button>
        {!complete && <span className="muted">四个槽位都放入部件后才能校验</span>}
      </div>

      {validation && (
        <div className={`validation ${validation.ok ? 'ok' : 'bad'}`}>
          {validation.joints.map(j => (
            <div key={j.name} className="joint-row">
              <span className={j.ok ? 'mark ok' : 'mark bad'}>{j.ok ? '✓' : '✗'}</span>
              <span className="joint-title">{j.name}</span>
              {!j.ok && <ul>{j.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>}
            </div>
          ))}
          {validation.ok && <p className="ok-text">全部接口与实测证据核对通过，可采用此组合。</p>}
        </div>
      )}
    </section>
  )
}
