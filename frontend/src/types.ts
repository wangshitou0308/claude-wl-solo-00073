export type Slot = 'gun' | 'lance' | 'hose_connector' | 'o_ring'

export interface Machine {
  id: number
  model_name: string
  revision_code: string
  rated_pressure_bar: number
  created_at: string
  has_selection?: boolean
}

export interface Part {
  id: number
  code: string
  name: string
  part_type: Slot
  in_type: string | null
  in_gender: string | null
  out_type: string | null
  out_gender: string | null
  thread_core_mm: number | null
  quick_mm: number | null
  bayonet_ear_mm: number | null
  spigot_depth_mm: number | null
  insert_length_mm: number | null
  groove_cross_mm: number | null
  oring_cross_mm: number | null
  min_pressure_bar: number
  brand: string | null
  appearance: string | null
}

export interface Evidence {
  id: number
  machine_id: number
  kind: string
  key: string
  value: number
  note: string | null
  created_at: string
}

export interface Joint {
  name: string
  ok: boolean
  issues: string[]
}

export interface Combo {
  key: string
  ok: boolean
  issues: string[]
  joints: Joint[]
  part_ids: Record<Slot, number>
  parts: Record<Slot, Part>
}

export interface Contradiction {
  key: string
  table: number
  measured: number
  message: string
}

export interface NextMeasurement {
  key: string
  label: string
  buckets: number
  combos: number
  reason: string
}

export interface Analysis {
  machine: Machine
  evidence: Evidence[]
  measurements: Record<string, number>
  combos: Combo[]
  rejected_count: number
  contradictions: Contradiction[]
  table_note: string | null
  missing_evidence: string[]
  next_measurement: NextMeasurement | null
  selection: { combo_key: string; parts: Record<Slot, Part | null> } | null
  invalidated: { selection_cleared: boolean; steps_reset: string[] } | null
  steps_reset?: string[]
}

export interface CheckDef {
  id: string
  label: string
  kind: 'require_true' | 'failure'
}

export interface StepState {
  key: string
  title: string
  desc: string
  check_defs: CheckDef[]
  status: 'pending' | 'confirmed' | 'failed'
  values: Record<string, boolean>
  locked_reason: string | null
}

export interface Meta {
  measurement_keys: Record<string, { label: string; tol: number }>
  steps: unknown[]
  model_table: Array<Record<string, string | number>>
}

export const SLOT_LABEL: Record<Slot, string> = {
  hose_connector: '软管接头',
  gun: '喷枪',
  lance: '延长杆',
  o_ring: '密封圈',
}
