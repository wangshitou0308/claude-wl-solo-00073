"""部件库种子数据。brand/appearance 仅用于展示，判定逻辑绝不读取。"""
from .db import connect

PARTS = [
    # code, name, type, in_type, in_gender, out_type, out_gender,
    # thread_core, quick, bayonet_ear, spigot_depth, insert_len, groove_cross,
    # oring_cross, min_pressure, brand, appearance
    ("GUN-A", "喷枪 A（M22进 / M22出）", "gun", "m22", "female", "m22", "male",
     14.8, None, None, 9.5, 9.0, 2.62, None, 250, "凯驰兼容件", "黑色枪身黄扳机"),
    ("GUN-B", "喷枪 B（快插进 / 快插出）", "gun", "quick", "female", "quick", "male",
     None, 12.0, None, 12.5, 12.0, 2.62, None, 200, "无牌散装", "蓝色握把"),
    ("GUN-C", "喷枪 C（M22进 / 卡口出）", "gun", "m22", "female", "bayonet", "male",
     15.0, None, 12.2, 9.5, 14.0, 3.1, None, 160, "凯驰兼容件", "黑色枪身黑扳机"),
    ("GUN-D", "喷枪 D（M22进 / M22出·低压）", "gun", "m22", "female", "m22", "male",
     14.8, None, None, 9.5, 8.5, 2.4, None, 120, "无牌散装", "灰色枪身"),

    ("LAN-1", "延长杆 1（M22母口）", "lance", "m22", "female", None, None,
     14.8, None, None, 9.5, None, None, None, 250, "凯驰兼容件", "不锈钢杆"),
    ("LAN-2", "延长杆 2（快插母口）", "lance", "quick", "female", None, None,
     None, 12.0, None, 12.5, None, None, None, 200, "无牌散装", "镀锌杆"),
    ("LAN-3", "延长杆 3（卡口母口）", "lance", "bayonet", "female", None, None,
     None, None, 12.2, 14.5, None, None, None, 160, "凯驰兼容件", "黑色塑套杆"),
    ("LAN-4", "延长杆 4（M22母口·偏大）", "lance", "m22", "female", None, None,
     15.2, None, None, 8.0, None, None, None, 180, "无牌散装", "不锈钢杆有划痕"),

    ("HOS-1", "软管接头 1（M22公）", "hose_connector", None, None, "m22", "male",
     14.8, None, None, None, 9.0, None, None, 250, "凯驰兼容件", "黄铜本色"),
    ("HOS-2", "软管接头 2（快插公）", "hose_connector", None, None, "quick", "male",
     None, 11.9, None, None, 12.0, None, None, 200, "无牌散装", "镀镍"),
    ("HOS-3", "软管接头 3（M22公·低压）", "hose_connector", None, None, "m22", "male",
     15.1, None, None, None, 9.5, None, None, 150, "无牌散装", "黄铜带绿锈"),
    ("HOS-4", "软管接头 4（卡口公）", "hose_connector", None, None, "bayonet", "male",
     None, None, 12.0, None, 13.0, None, None, 140, "凯驰兼容件", "黑色塑料"),

    ("ORI-1", "密封圈 1（截面2.62）", "o_ring", None, None, None, None,
     None, None, None, None, None, None, 2.62, 250, "无牌散装", "黑色丁腈"),
    ("ORI-2", "密封圈 2（截面3.10）", "o_ring", None, None, None, None,
     None, None, None, None, None, None, 3.10, 200, "无牌散装", "黑色丁腈"),
    ("ORI-3", "密封圈 3（截面2.40）", "o_ring", None, None, None, None,
     None, None, None, None, None, None, 2.40, 150, "无牌散装", "棕色氟胶"),
    ("ORI-4", "密封圈 4（截面2.62·低压）", "o_ring", None, None, None, None,
     None, None, None, None, None, None, 2.62, 120, "无牌散装", "黑色丁腈发硬"),
]


def seed_parts() -> None:
    with connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM parts").fetchone()["c"]
        if n:
            return
        conn.executemany(
            """INSERT INTO parts
               (code, name, part_type, in_type, in_gender, out_type, out_gender,
                thread_core_mm, quick_mm, bayonet_ear_mm, spigot_depth_mm,
                insert_length_mm, groove_cross_mm, oring_cross_mm,
                min_pressure_bar, brand, appearance)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            PARTS,
        )
