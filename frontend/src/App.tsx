import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import type { Analysis, Combo, Machine, Meta, Part, Slot, StepState } from './types'
import MachinePanel from './components/MachinePanel'
import EvidencePanel from './components/EvidencePanel'
import AnalysisPanel from './components/AnalysisPanel'
import ExplodedView from './components/ExplodedView'
import StepsPanel from './components/StepsPanel'

const EMPTY_SLOTS: Record<Slot, Part | null> = { gun: null, lance: null, hose_connector: null, o_ring: null }

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [parts, setParts] = useState<Part[]>([])
  const [machines, setMachines] = useState<Machine[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [steps, setSteps] = useState<StepState[]>([])
  const [slots, setSlots] = useState<Record<Slot, Part | null>>(EMPTY_SLOTS)
  const [validation, setValidation] = useState<Combo | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const showError = (msg: string) => { setError(msg); setNotice(null) }

  const refreshMachines = useCallback(async () => {
    setMachines(await api.machines())
  }, [])

  const refreshSteps = useCallback(async (id: number) => {
    setSteps(await api.steps(id))
  }, [])

  const applyAnalysis = useCallback(async (a: Analysis) => {
    setAnalysis(a)
    if (a.invalidated?.selection_cleared) {
      setNotice('证据已变化：原选定组合不再成立，已仅使该组合及相关步骤失效。')
      setError(null)
    }
    if (a.steps_reset?.length) {
      setNotice(`组合已变更：${a.steps_reset.length} 个依赖组合的步骤已重置。`)
    }
    await refreshSteps(a.machine.id)
  }, [refreshSteps])

  const selectMachine = useCallback(async (id: number) => {
    setCurrentId(id)
    setValidation(null)
    setNotice(null); setError(null)
    const a = await api.analysis(id)
    setAnalysis(a)
    await refreshSteps(id)
  }, [refreshSteps])

  useEffect(() => {
    void (async () => {
      const [m, p, ms] = await Promise.all([api.meta(), api.parts(), api.machines()])
      setMeta(m); setParts(p); setMachines(ms)
      if (ms.length) await selectMachine(ms[0].id)
    })().catch(e => showError((e as Error).message))
  }, [selectMachine])

  // 选定组合变化时同步爆炸图槽位
  useEffect(() => {
    if (!analysis) return
    if (analysis.selection) {
      const p = analysis.selection.parts
      setSlots({
        gun: p.gun ?? null, lance: p.lance ?? null,
        hose_connector: p.hose_connector ?? null, o_ring: p.o_ring ?? null,
      })
    }
  }, [analysis])

  if (!meta) return <div className="loading">加载中…</div>

  const createMachine = async (b: { model_name: string; revision_code: string; rated_pressure_bar: number }) => {
    const m = await api.createMachine(b)
    await refreshMachines()
    await selectMachine(m.id)
  }

  const addEvidence = async (key: string, value: number, note: string) => {
    if (!currentId) return
    const a = await api.addEvidence(currentId, note ? { key, value, note } : { key, value })
    await applyAnalysis(a)
    await refreshMachines()
  }

  const deleteEvidence = async (key: string) => {
    if (!currentId) return
    const a = await api.deleteEvidence(currentId, key)
    await applyAnalysis(a)
  }

  const slotIds = (): Record<Slot, number> | null => {
    const ids = {} as Record<Slot, number>
    for (const s of ['gun', 'lance', 'hose_connector', 'o_ring'] as Slot[]) {
      const p = slots[s]
      if (!p) return null
      ids[s] = p.id
    }
    return ids
  }

  const validateExploded = async (): Promise<Combo | null> => {
    if (!currentId) return null
    const ids = slotIds()
    if (!ids) { showError('请先在爆炸图中放满四个槽位'); return null }
    setBusy(true)
    try {
      const c = await api.validateCombo(currentId, ids)
      setValidation(c)
      return c
    } catch (ex) {
      showError((ex as Error).message)
      return null
    } finally {
      setBusy(false)
    }
  }

  const useSelection = async (ids: Record<Slot, number>) => {
    if (!currentId) return
    setBusy(true)
    try {
      const a = await api.setSelection(currentId, ids)
      await applyAnalysis(a)
      await refreshMachines()
      setNotice(prev => prev ?? '组合已选定，复装步骤已解锁。')
    } catch (ex) {
      showError((ex as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const useExploded = async () => {
    const ids = slotIds()
    if (!ids) { showError('请先在爆炸图中放满四个槽位'); return }
    await useSelection(ids)
  }

  const clearSelection = async () => {
    if (!currentId) return
    await api.clearSelection(currentId)
    const a = await api.analysis(currentId)
    setAnalysis(a)
    await refreshSteps(currentId)
    await refreshMachines()
    setNotice('已取消选定，依赖组合的步骤已重置。')
  }

  const confirmStep = async (key: string, checks: Record<string, boolean>) => {
    if (!currentId) return
    setSteps(await api.confirmStep(currentId, key, checks))
  }

  const revokeStep = async (key: string) => {
    if (!currentId) return
    setSteps(await api.revokeStep(currentId, key))
  }

  return (
    <div className="app">
      <header>
        <h1>高压清洗机枪杆接头复装判定台</h1>
        <p className="muted">社区工具共享点 · 判定仅依据实测证据与部件档案，不按外观或品牌补齐缺失证据</p>
      </header>

      {notice && <div className="toast info" onClick={() => setNotice(null)}>{notice} ✕</div>}
      {error && <div className="toast danger" onClick={() => setError(null)}>{error} ✕</div>}

      <main>
        <div className="col">
          <MachinePanel machines={machines} currentId={currentId} meta={meta}
                        onSelect={id => void selectMachine(id)}
                        onCreate={createMachine} />
          {analysis && (
            <EvidencePanel analysis={analysis} meta={meta}
                           onAdd={addEvidence} onDelete={deleteEvidence} />
          )}
        </div>

        <div className="col wide">
          {analysis ? (
            <>
              <AnalysisPanel analysis={analysis} meta={meta}
                             onSelectCombo={ids => useSelection(ids as unknown as Record<Slot, number>)}
                             onClearSelection={clearSelection}
                             onError={showError} />
              <ExplodedView parts={parts} slots={slots}
                            onDrop={(slot, part) => { setSlots(s => ({ ...s, [slot]: part })); setValidation(null) }}
                            onClearSlot={slot => { setSlots(s => ({ ...s, [slot]: null })); setValidation(null) }}
                            onValidate={validateExploded}
                            onUse={useExploded}
                            validation={validation} busy={busy} />
              <StepsPanel steps={steps} onConfirm={confirmStep} onRevoke={revokeStep} onError={showError} />
            </>
          ) : (
            <section className="panel empty">
              <p>请先登记一台整机，或从左侧列表选择。</p>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}
