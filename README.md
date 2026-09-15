# 高压清洗机枪杆接头复装判定台

面向社区工具共享点的复装辅助台：志愿者清洗多台高压清洗机后，喷枪、延长杆、
软管接头、密封圈混放。本工具只依据**实测证据**与部件档案判定可复装组合，
不按外观或品牌补齐缺失数据。

## 功能

- **机型登记**：整机型号 + 修订码 + 额定压力；内置型号表仅用于与实测比对并列矛盾。
- **实测录入**：M22 螺纹芯径、快插直径、卡口耳宽、密封圈截面、止口深度。
- **组合枚举**：按接口尺寸、公母端、止口深度与各段最低耐压枚举完整组合；
  型号表与实测冲突时列出矛盾；缺失证据不补齐；多解时建议最能区分候选的下一处测量。
- **爆炸图拖放**：SVG 爆炸图中把候选部件拖入槽位，校验后采用组合。
- **复装步骤**：确认泄压 → 装密封圈 → 连接软管 → 锁入枪杆 → 冷水查漏 → 短时低压试喷；
  卡口未到底 / 密封圈挤出 / 接缝渗水即阻止推进；误确认可撤回；
  证据变化仅使相关组合与依赖步骤失效。

## 运行（本机原生）

后端（Python 3.11+，依赖已装于 `backend/.venv`）：

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --port 8000
```

前端（开发模式，代理 /api 到 8000）：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

或直接由后端托管已构建前端：`npm run build` 后访问 http://localhost:8000 。

首次启动自动建库（`backend/washer.db`）并播种部件库与复装步骤定义。

## 目录

```
backend/app/
  main.py    FastAPI 路由：机型/证据/分析/组合/步骤
  logic.py   接口匹配、组合枚举、矛盾检测、下一处测量建议、步骤状态机
  db.py      SQLite 建库与访问
  seed.py    部件库种子（品牌/外观仅展示，不参与判定）
frontend/src/
  App.tsx                    页面编排
  components/MachinePanel    机型登记
  components/EvidencePanel   实测录入
  components/AnalysisPanel   矛盾/缺失证据/候选组合
  components/ExplodedView    SVG 爆炸图拖放
  components/StepsPanel      复装步骤向导
```

## 判定原则

1. 只依据实测证据与部件档案（接口尺寸、公母端、止口深度、最低耐压）。
2. 品牌、外观绝不参与匹配；缺失证据保持未知并提示测量位置。
3. 证据变化时，仅失效受影响的组合与依赖组合的步骤，其余进度保留。
