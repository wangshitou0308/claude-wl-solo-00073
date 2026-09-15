import type { Analysis, Meta } from '../types'

interface Props {
  analysis: Analysis
  meta: Meta
  onSelectCombo: (partIds: Record<string, number>) => Promise<void>
  onClearSelection: () => Promise<void>
  onError: (msg: string) => void
}

export default function AnalysisPanel({ analysis, meta, onSelectCombo, onClearSelection, onError }: Props) {
  const { combos, contradictions, table_note, missing_evidence, next_measurement, selection } = analysis

  const pick = async (partIds: Record<string, number>) => {
    try {
      await onSelectCombo(partIds)
    } catch (ex) {
      onError((ex as Error).message)
    }
  }

  return (
    <section className="panel">
      <h2><span className="idx">3</span>判定分析</h2>

      {table_note && <p className="banner info">{table_note}</p>}

      {contradictions.length > 0 && (
        <div className="banner danger">
          <strong>型号表与实测冲突（{contradictions.length} 项）：</strong>
          <ul>{contradictions.map(c => <li key={c.key}>{c.message}</li>)}</ul>
        </div>
      )}

      {missing_evidence.length > 0 && (
        <div className="banner warn">
          <strong>缺失证据：</strong>
          {missing_evidence.map(k => (
            <span key={k} className="tag warn">{meta.measurement_keys[k]?.label ?? k}</span>
          ))}
          <p className="muted">缺失项保持未知，不按外观或品牌补齐。</p>
        </div>
      )}

      {next_measurement && (
        <div className="banner suggest">
          <strong>建议下一处测量：</strong>{next_measurement.reason}
        </div>
      )}

      <p className="muted">
        有效组合 <strong>{combos.length}</strong> 组
        {analysis.rejected_count > 0 && `（另有 ${analysis.rejected_count} 组因尺寸/公母/止口/耐压不符被淘汰）`}
      </p>

      {selection && (
        <div className="banner ok">
          当前选定：<code>{selection.combo_key}</code>
          <button className="link danger" onClick={() => onClearSelection().catch(e => onError(e.message))}>
            取消选定
          </button>
        </div>
      )}

      {combos.length === 0
        ? <p className="banner danger">当前证据下没有任何完整组合成立，请核对实测值或补充部件档案。</p>
        : (
          <div className="combo-list">
            {combos.map(c => (
              <div key={c.key} className={`combo ${selection?.combo_key === c.key ? 'selected' : ''}`}>
                <div className="combo-parts">
                  {(['hose_connector', 'gun', 'lance', 'o_ring'] as const).map(slot => (
                    <span key={slot} className="chip" title={c.parts[slot].name}>
                      {c.parts[slot].code}
                    </span>
                  ))}
                </div>
                <div className="combo-joints">
                  {c.joints.map(j => (
                    <span key={j.name} className={j.ok ? 'joint ok' : 'joint bad'}
                          title={j.issues.join('\n') || '通过'}>
                      {j.ok ? '✓' : '✗'} {j.name}
                    </span>
                  ))}
                </div>
                {selection?.combo_key !== c.key && (
                  <button onClick={() => pick(c.part_ids as unknown as Record<string, number>)}>
                    选定此组合
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
    </section>
  )
}
