# 云岫茶坊 AI 茶叶销售系统

一个以茶叶零售为业务场景的智能商城。系统覆盖茶品浏览、购物车、订单物流、售后服务、AI 选茶和 RAG 知识问答；后端已统一为同步 Flask 执行模型。

## 核心能力

- 茶品商城：按茶类、价格、产地与风味标签筛选商品
- AI 选茶顾问：结合自饮/礼赠场景、预算、香型和口感进行推荐与对比
- RAG 问答：使用 FAISS 商品知识库回答茶品、冲泡、保存等问题
- 交易链路：购物车、下单、支付、订单物流、退款与工单
- 多轮 Agent：保留原有意图识别、工具调用、上下文记忆和工作流编排
- Business Pack：业务提示词、插件清单、意图规则和能力开关集中配置

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Element Plus |
| Web 后端 | Flask、Waitress、Flask-CORS |
| 数据层 | SQLAlchemy、MySQL、Redis |
| AI 编排 | LangChain、LangGraph、Business Pack Runtime |
| RAG | FAISS、BM25、Embedding、混合检索与重排序 |
| 测试 | Pytest、Flask Test Client |

## AI 链路

茶叶主题改造只替换业务数据、提示词和展示语义，核心链路保持不变：

```text
用户请求
  -> Flask Chat / Gateway API
  -> RuntimeFactory(tea-retail)
  -> 上下文与会话状态
  -> 意图识别
  -> Function Calling / Topic Advisor Agent / RAG
  -> 业务工作流节点
  -> 保存上下文
  -> 流式或普通响应
```

主要工作流包括：普通问答、茶品咨询、AI 推荐、购买流程、订单查询、售后流程、工单和文档分析。

## 业务包

默认业务包是 `tea-retail`：

- 配置文件：`backend/config/businesses/tea-retail.yaml`
- 品牌：云岫茶坊
- 默认系统名：云岫茶坊 AI 茶叶销售系统
- 默认知识集合：`tea_products`、`brewing_guides`、`product_catalog`

为了不破坏既有 Agent 调用协议，以下内部工具名继续保留，但对外语义已经切换为茶叶销售：

| 兼容工具名 | 当前业务含义 |
| --- | --- |
| `search_projects` | 搜索茶叶商品 |
| `get_project_detail` | 查看单款茶品详情 |
| `compare_projects` | 对比多款茶品 |
| `check_tech_stack_match` | 匹配顾客的香型、口感与茶类偏好 |

同理，数据库字段 `tech_stack` 现在承载“产地、香型、工艺、风味标签”，`difficulty` 承载口感浓度：

- `easy`：清新鲜爽
- `medium`：醇香回甘
- `hard`：浓醇耐泡

## 演示数据

默认目录包含 6 个茶类和 8 款茶品：

- 绿茶：西湖龙井、洞庭碧螺春
- 红茶：武夷金骏眉
- 乌龙茶：武夷山大红袍、安溪铁观音
- 白茶：福鼎白牡丹
- 普洱茶：新会陈皮普洱熟茶
- 花茶：横州茉莉银针

旧演示数据库可执行安全迁移：

```powershell
cd backend
.\venv\Scripts\python.exe migrate_tea_catalog.py
```

迁移脚本仅匹配预置的旧演示商品标题，不会批量改写用户自行创建的商品；无商品引用的旧演示分类会被清理。

## 快速启动

确保 MySQL、Redis、后端虚拟环境和前端依赖已经就绪，然后在项目根目录运行：

```powershell
.\start.bat
```

默认地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- 路由清单：`http://localhost:8000/api/docs`

也可以分别启动：

```powershell
cd backend
.\venv\Scripts\python.exe main.py

cd frontend
npm run dev
```

## 测试与构建

后端全量测试：

```powershell
cd backend
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\venv\Scripts\python.exe -m pytest tests -q
```

前端生产构建：

```powershell
cd frontend
npm run build
```

## 主要目录

```text
backend/
  flask_api/                     # Flask 业务接口
  web/                           # 应用工厂、HTTP 与同步执行基础设施
  ai_module/
    core/                        # 编排、状态、节点与工作流
    infrastructure/plugins/      # 工具插件
  config/businesses/tea-retail.yaml
  services/                      # 商品、订单、RAG 等领域服务
  migrate_tea_catalog.py
frontend/
  src/views/                     # 商城与客服页面
  src/components/                # 公共布局和商品组件
```

## 架构边界与后续方向

当前已经完成同步 Flask 迁移和茶叶业务落地，但仍可继续增强：

- 将兼容字段逐步升级为通用商品属性模型
- 增加真实库存、批次、规格、产年与保质期字段
- 为 RAG 增加茶类知识、冲泡指南和质量评测集
- 完善权限、审计、限流、可观测性和多租户隔离
- 对前端大体积 chunk 继续做代码分包

## 安全提示

- 不要提交真实 API Key、数据库密码或支付密钥
- 通过 `.env` 管理本地配置，并为测试、开发、生产使用不同配置
- 正式部署前补齐工具权限校验、操作审计与接口限流