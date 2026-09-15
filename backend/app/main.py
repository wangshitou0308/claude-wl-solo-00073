"""高压清洗机枪杆接头复装判定台 —— FastAPI 后端。

数据流：
  登记机型 → 录入实测证据 → 后端枚举有效组合 / 列矛盾 / 建议下一处测量
  → 选定组合 → 按步骤复装（失败即阻止，误确认可撤回）
  → 证据变化时，仅使相关组合与依赖步骤失效。
"""
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, logic
from .seed import seed_parts

app = FastAPI(title="高压清洗机枪杆接头复装判定台")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.init_db()
    seed_parts()


# ------------------------------------------------------------------ 请求模型
class MachineIn(BaseModel):
    model_name: str = Field(min_length=1)
    revision_code: str = Field(min_length=1)
    rated_pressure_bar: float = Field(gt=0)


class EvidenceIn(BaseModel):
    key: str
    value: float
    note: str | None = None


class ComboIn(BaseModel):
    gun: int
    lance: int
    hose_connector: int
    o_ring: int


class StepConfirmIn(BaseModel):
    checks: dict[str, bool]


# ------------------------------------------------------------------ 内部工具
def _machine_or_404(conn, machine_id: int) -> dict:
    m = db.row(conn, "SELECT * FROM machines WHERE id=?", (machine_id,))
    if not m:
        raise HTTPException(404, "机型不存在")
    return m


def _measurements(conn, machine_id: int) -> dict[str, float]:
    return {r["key"]: r["value"] for r in db.rows(
        conn, "SELECT key, value FROM evidence WHERE machine_id=?", (machine_id,))}


def _all_parts(conn) -> list[dict]:
    return db.rows(conn, "SELECT * FROM parts ORDER BY part_type, code")


def _valid_combos(conn, machine: dict) -> tuple[list[dict], int]:
    return logic.enumerate_combos(
        _all_parts(conn), machine["rated_pressure_bar"], _measurements(conn, machine["id"]))


def _reset_combo_steps(conn, machine_id: int) -> list[str]:
    """仅重置依赖部件组合的步骤；泄压确认与组合无关，予以保留。"""
    reset = []
    for key in logic.COMBO_DEPENDENT_STEPS:
        cur = conn.execute(
            "UPDATE steps SET status='pending', checks_json='{}', updated_at=datetime('now') "
            "WHERE machine_id=? AND step_key=? AND status!='pending'",
            (machine_id, key))
        if cur.rowcount:
            reset.append(key)
    return reset


def _invalidate(conn, machine: dict) -> dict:
    """证据变化后：仅使不再成立的选定组合失效，并级联重置相关步骤。"""
    combos, _ = _valid_combos(conn, machine)
    valid_keys = {c["key"] for c in combos}
    sel = db.row(conn, "SELECT * FROM selections WHERE machine_id=?", (machine["id"],))
    out = {"selection_cleared": False, "steps_reset": []}
    if sel and sel["combo_key"] not in valid_keys:
        conn.execute("DELETE FROM selections WHERE machine_id=?", (machine["id"],))
        out["selection_cleared"] = True
        out["steps_reset"] = _reset_combo_steps(conn, machine["id"])
    return out


def _analysis_payload(conn, machine_id: int, invalidated: dict | None = None) -> dict:
    machine = _machine_or_404(conn, machine_id)
    measurements = _measurements(conn, machine_id)
    parts = _all_parts(conn)
    combos, rejected = logic.enumerate_combos(
        parts, machine["rated_pressure_bar"], measurements)
    contradictions, table_note = logic.find_contradictions(machine, measurements)
    sel = db.row(conn, "SELECT * FROM selections WHERE machine_id=?", (machine_id,))
    selection = None
    if sel:
        ids = json.loads(sel["part_ids"])
        pmap = {p["id"]: p for p in parts}
        selection = {"combo_key": sel["combo_key"],
                     "parts": {slot: pmap.get(pid) for slot, pid in ids.items()}}
    return {
        "machine": machine,
        "evidence": db.rows(
            conn, "SELECT * FROM evidence WHERE machine_id=? ORDER BY key", (machine_id,)),
        "measurements": measurements,
        "combos": combos,
        "rejected_count": rejected,
        "contradictions": contradictions,
        "table_note": table_note,
        "missing_evidence": logic.missing_evidence(combos, measurements, parts),
        "next_measurement": logic.suggest_next_measurement(combos, measurements, parts),
        "selection": selection,
        "invalidated": invalidated,
    }


def _steps_payload(conn, machine_id: int) -> list[dict]:
    saved = {r["step_key"]: r for r in db.rows(
        conn, "SELECT * FROM steps WHERE machine_id=?", (machine_id,))}
    has_selection = db.row(
        conn, "SELECT machine_id FROM selections WHERE machine_id=?",
        (machine_id,)) is not None
    out, prev_ok = [], True
    for spec in logic.STEPS:
        r = saved.get(spec["key"])
        status = r["status"] if r else "pending"
        locked_reason = None
        if not prev_ok:
            locked_reason = "前序步骤未确认"
        if spec["key"] in logic.COMBO_DEPENDENT_STEPS and not has_selection:
            locked_reason = "尚未选定部件组合"
        out.append({
            "key": spec["key"], "title": spec["title"], "desc": spec["desc"],
            "check_defs": spec["checks"],
            "status": status,
            "values": json.loads(r["checks_json"]) if r else {},
            "locked_reason": locked_reason,
        })
        if status != "confirmed":
            prev_ok = False
    return out


def _combo_parts_or_400(conn, body: ComboIn) -> dict[str, dict]:
    ids = {"gun": body.gun, "lance": body.lance,
           "hose_connector": body.hose_connector, "o_ring": body.o_ring}
    pmap = {p["id"]: p for p in _all_parts(conn)}
    out = {}
    for slot, pid in ids.items():
        p = pmap.get(pid)
        if not p:
            raise HTTPException(400, f"部件不存在：id={pid}")
        if p["part_type"] != slot:
            raise HTTPException(400, f"{p['code']} 是 {p['part_type']}，不能装入 {slot} 槽位")
        out[slot] = p
    return out


# ------------------------------------------------------------------ 元数据与部件
@app.get("/api/meta")
def meta():
    return {
        "measurement_keys": logic.MEASUREMENT_KEYS,
        "steps": logic.STEPS,
        "model_table": [
            {"model_name": k[0], "revision_code": k[1], **v}
            for k, v in logic.MODEL_TABLE.items()
        ],
    }


@app.get("/api/parts")
def list_parts():
    with db.connect() as conn:
        return _all_parts(conn)


# ------------------------------------------------------------------ 机型登记
@app.post("/api/machines", status_code=201)
def create_machine(body: MachineIn):
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO machines (model_name, revision_code, rated_pressure_bar) VALUES (?,?,?)",
            (body.model_name.strip(), body.revision_code.strip(), body.rated_pressure_bar))
        return db.row(conn, "SELECT * FROM machines WHERE id=?", (cur.lastrowid,))


@app.get("/api/machines")
def list_machines():
    with db.connect() as conn:
        ms = db.rows(conn, "SELECT * FROM machines ORDER BY id DESC")
        for m in ms:
            m["has_selection"] = db.row(
                conn, "SELECT machine_id FROM selections WHERE machine_id=?",
                (m["id"],)) is not None
        return ms


# ------------------------------------------------------------------ 实测证据
@app.post("/api/machines/{machine_id}/evidence")
def add_evidence(machine_id: int, body: EvidenceIn):
    if body.key not in logic.MEASUREMENT_KEYS:
        raise HTTPException(400, f"未知测量项：{body.key}")
    with db.connect() as conn:
        machine = _machine_or_404(conn, machine_id)
        conn.execute(
            "INSERT INTO evidence (machine_id, kind, key, value, note) VALUES (?,?,?,?,?) "
            "ON CONFLICT(machine_id, key) DO UPDATE SET value=excluded.value, "
            "note=excluded.note, created_at=datetime('now')",
            (machine_id, "measurement", body.key, body.value, body.note))
        invalidated = _invalidate(conn, machine)  # 证据变化 → 仅相关组合/步骤失效
        return _analysis_payload(conn, machine_id, invalidated)


@app.delete("/api/machines/{machine_id}/evidence/{key}")
def delete_evidence(machine_id: int, key: str):
    with db.connect() as conn:
        machine = _machine_or_404(conn, machine_id)
        conn.execute("DELETE FROM evidence WHERE machine_id=? AND key=?", (machine_id, key))
        invalidated = _invalidate(conn, machine)
        return _analysis_payload(conn, machine_id, invalidated)


# ------------------------------------------------------------------ 分析
@app.get("/api/machines/{machine_id}/analysis")
def analysis(machine_id: int):
    with db.connect() as conn:
        return _analysis_payload(conn, machine_id)


@app.post("/api/machines/{machine_id}/validate-combo")
def validate_combo(machine_id: int, body: ComboIn):
    """爆炸图拖放后的即时校验，不产生任何选定。"""
    with db.connect() as conn:
        machine = _machine_or_404(conn, machine_id)
        parts = _combo_parts_or_400(conn, body)
        return logic.evaluate_combo(
            parts["gun"], parts["lance"], parts["hose_connector"], parts["o_ring"],
            machine["rated_pressure_bar"], _measurements(conn, machine_id))


# ------------------------------------------------------------------ 选定组合
@app.put("/api/machines/{machine_id}/selection")
def set_selection(machine_id: int, body: ComboIn):
    with db.connect() as conn:
        machine = _machine_or_404(conn, machine_id)
        parts = _combo_parts_or_400(conn, body)
        result = logic.evaluate_combo(
            parts["gun"], parts["lance"], parts["hose_connector"], parts["o_ring"],
            machine["rated_pressure_bar"], _measurements(conn, machine_id))
        if not result["ok"]:
            raise HTTPException(409, {"detail": "组合未通过校验，不能选定", "issues": result["issues"]})
        old = db.row(conn, "SELECT * FROM selections WHERE machine_id=?", (machine_id,))
        steps_reset: list[str] = []
        if not (old and old["combo_key"] == result["key"]):
            # 组合变化 → 仅重置依赖组合的步骤
            steps_reset = _reset_combo_steps(conn, machine_id)
        conn.execute(
            "INSERT INTO selections (machine_id, combo_key, part_ids) VALUES (?,?,?) "
            "ON CONFLICT(machine_id) DO UPDATE SET combo_key=excluded.combo_key, "
            "part_ids=excluded.part_ids, created_at=datetime('now')",
            (machine_id, result["key"], json.dumps(result["part_ids"])))
        payload = _analysis_payload(conn, machine_id)
        payload["steps_reset"] = steps_reset
        return payload


@app.delete("/api/machines/{machine_id}/selection")
def clear_selection(machine_id: int):
    with db.connect() as conn:
        _machine_or_404(conn, machine_id)
        conn.execute("DELETE FROM selections WHERE machine_id=?", (machine_id,))
        return {"steps_reset": _reset_combo_steps(conn, machine_id)}


# ------------------------------------------------------------------ 复装步骤
@app.get("/api/machines/{machine_id}/steps")
def get_steps(machine_id: int):
    with db.connect() as conn:
        _machine_or_404(conn, machine_id)
        return _steps_payload(conn, machine_id)


@app.post("/api/machines/{machine_id}/steps/{step_key}/confirm")
def confirm_step(machine_id: int, step_key: str, body: StepConfirmIn):
    spec = logic.STEP_DEF.get(step_key)
    if not spec:
        raise HTTPException(404, "未知步骤")
    with db.connect() as conn:
        _machine_or_404(conn, machine_id)
        steps = _steps_payload(conn, machine_id)
        cur = next(s for s in steps if s["key"] == step_key)
        if cur["locked_reason"]:
            raise HTTPException(409, f"步骤被锁定：{cur['locked_reason']}")
        if cur["status"] == "confirmed":
            raise HTTPException(409, "步骤已确认，如需修改请先撤回")

        failures = [c["label"] for c in spec["checks"]
                    if c["kind"] == "failure" and body.checks.get(c["id"])]
        missing = [c["label"] for c in spec["checks"]
                   if c["kind"] == "require_true" and not body.checks.get(c["id"])]
        if failures:
            status = "failed"  # 卡口未到底 / 密封圈挤出 / 接缝渗水等 → 阻止推进
        elif missing:
            raise HTTPException(400, "以下确认项未完成：" + "；".join(missing))
        else:
            status = "confirmed"
        conn.execute(
            "INSERT INTO steps (machine_id, step_key, status, checks_json) VALUES (?,?,?,?) "
            "ON CONFLICT(machine_id, step_key) DO UPDATE SET status=excluded.status, "
            "checks_json=excluded.checks_json, updated_at=datetime('now')",
            (machine_id, step_key, status, json.dumps(body.checks)))
        return _steps_payload(conn, machine_id)


@app.post("/api/machines/{machine_id}/steps/{step_key}/revoke")
def revoke_step(machine_id: int, step_key: str):
    """撤回误确认：该步及之后所有步骤回到待办。"""
    if step_key not in logic.STEP_DEF:
        raise HTTPException(404, "未知步骤")
    with db.connect() as conn:
        _machine_or_404(conn, machine_id)
        idx = logic.STEP_KEYS.index(step_key)
        for key in logic.STEP_KEYS[idx:]:
            conn.execute(
                "UPDATE steps SET status='pending', checks_json='{}', "
                "updated_at=datetime('now') WHERE machine_id=? AND step_key=?",
                (machine_id, key))
        return _steps_payload(conn, machine_id)


# ------------------------------------------------------------------ 前端静态文件（若已构建）
_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
