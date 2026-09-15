import type { Analysis, Combo, Machine, Meta, Part, Slot, StepState } from './types'

const BASE = '/api'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j)
    } catch {
      /* keep default */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body: unknown, method = 'POST') =>
  req<T>(path, { method, body: JSON.stringify(body) })

export const api = {
  meta: () => req<Meta>('/meta'),
  parts: () => req<Part[]>('/parts'),
  machines: () => req<Machine[]>('/machines'),
  createMachine: (b: { model_name: string; revision_code: string; rated_pressure_bar: number }) =>
    post<Machine>('/machines', b),
  analysis: (id: number) => req<Analysis>(`/machines/${id}/analysis`),
  addEvidence: (id: number, b: { key: string; value: number; note?: string }) =>
    post<Analysis>(`/machines/${id}/evidence`, b),
  deleteEvidence: (id: number, key: string) =>
    req<Analysis>(`/machines/${id}/evidence/${key}`, { method: 'DELETE' }),
  validateCombo: (id: number, b: Record<Slot, number>) =>
    post<Combo>(`/machines/${id}/validate-combo`, b),
  setSelection: (id: number, b: Record<Slot, number>) =>
    req<Analysis>(`/machines/${id}/selection`, { method: 'PUT', body: JSON.stringify(b) }),
  clearSelection: (id: number) =>
    req<{ steps_reset: string[] }>(`/machines/${id}/selection`, { method: 'DELETE' }),
  steps: (id: number) => req<StepState[]>(`/machines/${id}/steps`),
  confirmStep: (id: number, key: string, checks: Record<string, boolean>) =>
    post<StepState[]>(`/machines/${id}/steps/${key}/confirm`, { checks }),
  revokeStep: (id: number, key: string) =>
    post<StepState[]>(`/machines/${id}/steps/${key}/revoke`, {}),
}
