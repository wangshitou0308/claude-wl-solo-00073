"""判定逻辑：接口匹配、组合枚举、矛盾检测、下一处测量建议、步骤状态机。

原则：
- 只依据实测证据与部件尺寸/公母/止口/耐压判定；
- 品牌、外观绝不参与匹配，缺失证据不补齐；
- 证据变化仅使相关组合与依赖步骤失效。
"""

# ---------------------------------------------------------------- 测量项定义
MEASUREMENT_KEYS = {
    "m22_thread_core_mm": {"label": "M22 螺纹芯径 (mm)", "tol": 0.4},
    "quick_diameter_mm": {"label": "快插直径 (mm)", "tol": 0.3},
    "bayonet_ear_width_mm": {"label": "卡口耳宽 (mm)", "tol": 0.3},
    "oring_cross_section_mm": {"label": "密封圈截面 (mm)", "tol": 0.15},
    "spigot_depth_mm": {"label": "母端止口深度 (mm)", "tol": 0.5},
}

# 接口体系 -> 部件尺寸字段 / 对应测量项 / 公差
FAMILY_DIM_FIELD = {"m22": "thread_core_mm", "quick": "quick_mm", "bayonet": "bayonet_ear_mm"}
FAMILY_MEASURE_KEY = {"m22": "m22_thread_core_mm", "quick": "quick_diameter_mm", "bayonet": "bayonet_ear_width_mm"}
FAMILY_LABEL = {"m22": "M22 螺纹", "quick": "快插", "bayonet": "卡口"}

ORING_TOL = MEASUREMENT_KEYS["oring_cross_section_mm"]["tol"]
SPIGOT_TOL = MEASUREMENT_KEYS["spigot_depth_mm"]["tol"]

# ---------------------------------------------------------------- 内置型号表
# (型号, 修订码) -> 出厂接口规格。仅用于与实测比对列矛盾，绝不用于补齐缺失证据。
MODEL_TABLE = {
    ("K-200", "B"): {
        "rated_pressure_bar": 250,
        "m22_thread_core_mm": 14.8,
        "oring_cross_section_mm": 2.62,
    },
    ("K-150", "A"): {
        "rated_pressure_bar": 200,
        "quick_diameter_mm": 12.0,
        "oring_cross_section_mm": 2.62,
    },
    ("HD-9", "C"): {
        "rated_pressure_bar": 160,
        "bayonet_ear_width_mm": 12.2,
        "oring_cross_section_mm": 3.1,
    },
}

# ---------------------------------------------------------------- 复装步骤定义
# require_true: 必须全部勾选才能确认；failure: 一经报告即判定失败并阻止推进。
STEPS = [
    {
        "key": "confirm_depressurize",
        "title": "确认泄压",
        "desc": "复装前必须确认整机与管路无残余压力。",
        "checks": [
            {"id": "pump_off", "label": "主机已停机，电源/动力已断开", "kind": "require_true"},
            {"id": "trigger_released", "label": "已扣动喷枪扳机释放管路残压", "kind": "require_true"},
        ],
    },
    {
        "key": "install_oring",
        "title": "装密封圈",
        "desc": "将选定密封圈装入公端沟槽。",
        "checks": [
            {"id": "oring_seated", "label": "密封圈平整落入沟槽、无扭转", "kind": "require_true"},
            {"id": "oring_extruded", "label": "发现密封圈被挤出或切边", "kind": "failure"},
        ],
    },
    {
        "key": "connect_hose",
        "title": "连接软管",
        "desc": "软管接头接入喷枪进口。",
        "checks": [
            {"id": "hand_threaded", "label": "先用手将螺纹/快插对接到位，无错扣", "kind": "require_true"},
            {"id": "torque_done", "label": "按手感加拧 1/4 圈或听到快插落锁声", "kind": "require_true"},
        ],
    },
    {
        "key": "lock_lance",
        "title": "锁入枪杆",
        "desc": "延长杆推到底并旋转锁定。",
        "checks": [
            {"id": "rotation_locked", "label": "枪杆已推到底并完成旋转锁定", "kind": "require_true"},
            {"id": "bayonet_not_seated", "label": "发现卡口未到底（有旷量/露出台阶）", "kind": "failure"},
        ],
    },
    {
        "key": "cold_leak_check",
        "title": "冷水查漏",
        "desc": "通冷水 30 秒，观察各接缝。",
        "checks": [
            {"id": "dry_after_30s", "label": "30 秒内各接缝无渗水、无滴漏", "kind": "require_true"},
            {"id": "seam_leak", "label": "发现接缝渗水", "kind": "failure"},
        ],
    },
    {
        "key": "low_pressure_test",
        "title": "短时低压试喷",
        "desc": "低压短时试喷，确认喷雾稳定。",
        "checks": [
            {"id": "spray_stable", "label": "低压试喷 3~5 秒，喷雾稳定无抖动", "kind": "require_true"},
            {"id": "abnormal_noise", "label": "出现异响或压力波动", "kind": "failure"},
        ],
    },
]
STEP_KEYS = [s["key"] for s in STEPS]
STEP_DEF = {s["key"]: s for s in STEPS}

# 依赖部件组合（而非仅依赖整机）的步骤：组合失效时仅重置这些步骤。
COMBO_DEPENDENT_STEPS = [
    "install_oring",
    "connect_hose",
    "lock_lance",
    "cold_leak_check",
    "low_pressure_test",
]

SLOT_OF_TYPE = {"gun": "gun", "lance": "lance", "hose_connector": "hose_connector", "o_ring": "o_ring"}


# ---------------------------------------------------------------- 接口匹配
def _joint_issues(up: dict, down: dict, rated: float) -> list[str] | None:
    """上游出端 vs 下游入端。返回问题列表；接口体系不同返回 None（无法连接）。"""
    fam = up.get("out_type")
    if not fam or fam != down.get("in_type"):
        return None
    issues: list[str] = []
    if up.get("out_gender") == down.get("in_gender"):
        issues.append("公母端不匹配（两端同为%s）" % ("公" if up.get("out_gender") == "male" else "母"))

    field = FAMILY_DIM_FIELD[fam]
    tol = MEASUREMENT_KEYS[FAMILY_MEASURE_KEY[fam]]["tol"]
    du, dd = up.get(field), down.get(field)
    if du is None or dd is None:
        issues.append("部件档案缺少%s尺寸" % FAMILY_LABEL[fam])
    elif abs(du - dd) > tol:
        issues.append(f"{FAMILY_LABEL[fam]}尺寸超差：{du}mm vs {dd}mm（公差±{tol}）")

    male, female = (up, down) if up.get("out_gender") == "male" else (down, up)
    il, sd = male.get("insert_length_mm"), female.get("spigot_depth_mm")
    if il is not None and sd is not None and il > sd + 1e-9:
        issues.append(f"止口深度不足：公端插入 {il}mm > 母端止口 {sd}mm")

    for p in (up, down):
        if p["min_pressure_bar"] < rated:
            issues.append(f"{p['code']} 最低耐压 {p['min_pressure_bar']:.0f}bar < 额定 {rated:.0f}bar")
    return issues


def _oring_issues(gun: dict, lance: dict, oring: dict, rated: float) -> list[str]:
    """密封圈与枪-杆接口公端沟槽匹配。"""
    male = gun if gun.get("out_gender") == "male" else lance
    issues: list[str] = []
    groove = male.get("groove_cross_mm")
    cross = oring.get("oring_cross_mm")
    if groove is None:
        issues.append(f"接口公端 {male['code']} 无密封沟槽档案，无法核对密封圈")
    elif cross is None or abs(groove - cross) > ORING_TOL:
        issues.append(
            f"密封圈截面 {cross}mm 与 {male['code']} 沟槽 {groove}mm 不匹配（公差±{ORING_TOL}）"
        )
    if oring["min_pressure_bar"] < rated:
        issues.append(f"{oring['code']} 最低耐压 {oring['min_pressure_bar']:.0f}bar < 额定 {rated:.0f}bar")
    return issues


def _measurement_issues(parts: list[dict], oring: dict, measurements: dict[str, float]) -> list[str]:
    """实测证据过滤：凡已测尺寸，组合中相关部件必须落在公差内。未测则不过滤。"""
    issues: list[str] = []
    for p in parts:
        fams = {f for f in (p.get("in_type"), p.get("out_type")) if f}
        for fam in fams:
            key = FAMILY_MEASURE_KEY[fam]
            if key not in measurements:
                continue
            field = FAMILY_DIM_FIELD[fam]
            val = p.get(field)
            tol = MEASUREMENT_KEYS[key]["tol"]
            if val is None or abs(val - measurements[key]) > tol:
                issues.append(
                    f"{p['code']} 的{FAMILY_LABEL[fam]}尺寸 {val}mm 与实测 "
                    f"{measurements[key]}mm 超差（±{tol}）"
                )
        if p.get("in_gender") == "female" and "spigot_depth_mm" in measurements:
            sd = p.get("spigot_depth_mm")
            if sd is None or abs(sd - measurements["spigot_depth_mm"]) > SPIGOT_TOL:
                issues.append(
                    f"{p['code']} 止口深度 {sd}mm 与实测 {measurements['spigot_depth_mm']}mm "
                    f"超差（±{SPIGOT_TOL}）"
                )
    if "oring_cross_section_mm" in measurements:
        cross = oring.get("oring_cross_mm")
        if cross is None or abs(cross - measurements["oring_cross_section_mm"]) > ORING_TOL:
            issues.append(
                f"{oring['code']} 截面 {cross}mm 与实测 "
                f"{measurements['oring_cross_section_mm']}mm 超差（±{ORING_TOL}）"
            )
    return issues


# ---------------------------------------------------------------- 组合枚举
def evaluate_combo(gun: dict, lance: dict, hose: dict, oring: dict,
                   rated: float, measurements: dict[str, float]) -> dict:
    """评估一组候选部件，返回关节明细与问题列表。"""
    joints = []
    issues: list[str] = []

    j1 = _joint_issues(hose, gun, rated)
    joints.append({"name": "接口① 软管接头→喷枪", "ok": j1 == [], "issues": j1 or ["接口体系不一致，无法连接"] if j1 is None else j1})
    if j1 is None:
        issues.append("接口① 体系不一致")
    else:
        issues += [f"接口①：{i}" for i in j1]

    j2 = _joint_issues(gun, lance, rated)
    joints.append({"name": "接口② 喷枪→延长杆", "ok": j2 == [], "issues": j2 or ["接口体系不一致，无法连接"] if j2 is None else j2})
    if j2 is None:
        issues.append("接口② 体系不一致")
    else:
        issues += [f"接口②：{i}" for i in j2]

    oi = _oring_issues(gun, lance, oring, rated)
    joints.append({"name": "密封 枪-杆接口密封圈", "ok": oi == [], "issues": oi})
    issues += [f"密封：{i}" for i in oi]

    mi = _measurement_issues([gun, lance, hose], oring, measurements)
    joints.append({"name": "实测证据核对", "ok": mi == [], "issues": mi})
    issues += mi

    key = "|".join([gun["code"], lance["code"], hose["code"], oring["code"]])
    return {
        "key": key,
        "ok": issues == [],
        "issues": issues,
        "joints": joints,
        "part_ids": {"gun": gun["id"], "lance": lance["id"],
                     "hose_connector": hose["id"], "o_ring": oring["id"]},
        "parts": {"gun": gun, "lance": lance, "hose_connector": hose, "o_ring": oring},
    }


def enumerate_combos(parts: list[dict], rated: float, measurements: dict[str, float]) -> tuple[list[dict], int]:
    """枚举全部完整有效组合；返回 (有效组合, 被淘汰候选数)。"""
    by_type: dict[str, list[dict]] = {}
    for p in parts:
        by_type.setdefault(p["part_type"], []).append(p)
    guns = by_type.get("gun", [])
    lances = by_type.get("lance", [])
    hoses = by_type.get("hose_connector", [])
    orings = by_type.get("o_ring", [])

    valid: list[dict] = []
    rejected = 0
    for g in guns:
        for l in lances:
            for h in hoses:
                for o in orings:
                    c = evaluate_combo(g, l, h, o, rated, measurements)
                    if c["ok"]:
                        valid.append(c)
                    else:
                        rejected += 1
    return valid, rejected


# ---------------------------------------------------------------- 矛盾检测
def find_contradictions(machine: dict, measurements: dict[str, float]) -> tuple[list[dict], str | None]:
    """型号表 vs 实测。返回 (矛盾列表, 提示信息)。"""
    key = (machine["model_name"].strip().upper(), machine["revision_code"].strip().upper())
    spec = MODEL_TABLE.get(key)
    if spec is None:
        return [], "型号表中无此机型/修订码，全部判定仅依赖实测证据（不按外观或品牌补齐）。"
    out: list[dict] = []
    if abs(spec["rated_pressure_bar"] - machine["rated_pressure_bar"]) > 1e-6:
        out.append({
            "key": "rated_pressure_bar",
            "table": spec["rated_pressure_bar"],
            "measured": machine["rated_pressure_bar"],
            "message": f"登记额定压力 {machine['rated_pressure_bar']:.0f}bar 与型号表 "
                       f"{spec['rated_pressure_bar']:.0f}bar 不一致，请核对铭牌。",
        })
    for k, expected in spec.items():
        if k == "rated_pressure_bar" or k not in measurements:
            continue
        tol = MEASUREMENT_KEYS[k]["tol"]
        measured = measurements[k]
        if abs(expected - measured) > tol:
            out.append({
                "key": k,
                "table": expected,
                "measured": measured,
                "message": f"{MEASUREMENT_KEYS[k]['label']}：型号表 {expected}mm，"
                           f"实测 {measured}mm，超出公差 ±{tol}mm。",
            })
    return out, None


# ---------------------------------------------------------------- 下一处测量建议
def suggest_next_measurement(combos: list[dict], measurements: dict[str, float],
                             all_parts: list[dict]) -> dict | None:
    """多解时，挑选能把候选组合分得最开的未测项目。"""
    if len(combos) <= 1:
        return None

    def combo_dim_values(combo: dict, key: str) -> tuple:
        vals = []
        if key == "oring_cross_section_mm":
            v = combo["parts"]["o_ring"].get("oring_cross_mm")
            return (v,) if v is not None else ()
        if key == "spigot_depth_mm":
            for p in combo["parts"].values():
                if p.get("in_gender") == "female" and p.get("spigot_depth_mm") is not None:
                    vals.append(p["spigot_depth_mm"])
            return tuple(sorted(vals))
        fams = [f for f, k in FAMILY_MEASURE_KEY.items() if k == key]
        field = FAMILY_DIM_FIELD[fams[0]] if fams else None
        for p in combo["parts"].values():
            fam_set = {f for f in (p.get("in_type"), p.get("out_type")) if f}
            if any(f in fam_set for f in fams) and p.get(field) is not None:
                vals.append(p[field])
        return tuple(sorted(vals))

    best = None
    for key, meta in MEASUREMENT_KEYS.items():
        if key in measurements:
            continue
        buckets: dict[tuple, int] = {}
        for c in combos:
            sig = combo_dim_values(c, key)
            buckets[sig] = buckets.get(sig, 0) + 1
        n_buckets = len(buckets)
        if n_buckets <= 1:
            continue  # 该测量无法区分当前候选
        largest = max(buckets.values())
        score = (n_buckets, -largest)
        if best is None or score > best["score"]:
            best = {"key": key, "label": meta["label"], "score": score,
                    "buckets": n_buckets, "combos": len(combos)}
    if best is None:
        return None
    best["reason"] = (
        f"当前有 {best['combos']} 组候选无法区分；测量「{best['label']}」可将其分成 "
        f"{best['buckets']} 类，是最能缩小范围的下一处测量。"
    )
    best.pop("score", None)
    return best


def missing_evidence(combos: list[dict], measurements: dict[str, float],
                     all_parts: list[dict]) -> list[str]:
    """与当前候选相关但尚未测量的项目。缺失即缺失，不按外观/品牌补齐。"""
    source = combos if combos else [{"parts": {}} ]
    relevant: set[str] = set()
    if combos:
        for c in combos:
            for p in c["parts"].values():
                for f in (p.get("in_type"), p.get("out_type")):
                    if f:
                        relevant.add(FAMILY_MEASURE_KEY[f])
                if p.get("in_gender") == "female":
                    relevant.add("spigot_depth_mm")
            relevant.add("oring_cross_section_mm")
    else:
        for p in all_parts:
            for f in (p.get("in_type"), p.get("out_type")):
                if f:
                    relevant.add(FAMILY_MEASURE_KEY[f])
        relevant.update({"oring_cross_section_mm", "spigot_depth_mm"})
    return sorted(k for k in relevant if k not in measurements)
