<div align="center">

# 🚗 车优 (EV-Compass)

### 你的私人新能源购车财务与战略顾问

</div>

***

## 📖 项目简介 (Overview)

### 痛点背景

新能源汽车市场迭代极快，新车型层出不穷，价格战此起彼伏。消费者面临：

- **选择困难症**：同价位车型多达数十款，参数配置眼花缭乱
- **"刚买就背刺"风险**：新车刚提，换代降价消息就来
- **财务决策盲区**：只看首付，忽视 TCO（总拥有成本）

### 核心价值

**车优 (EV-Compass) 不是一个简单的问答机器人**，而是一个具备"深度决策框架"的 AI 智能体：

- 🧠 **智能追问**：基于 Slot Filling 技术，"缺啥问啥"，精准把握用户需求
- 🛡️ **防冲动消费**：内置财务诊断逻辑，客观劝退不合理需求
- 📊 **TCO 核算**：计算总拥有成本，而非仅仅关注购车价格
- 🔍 **实时信息**：对接 Tavily 搜索，获取最新车市动态和优惠信息

***

## ✨ 核心亮点 (Key Features)

### 🧠 深度决策图谱

基于 **LangGraph** 构建的 ReAct (Reason + Act) 状态机工作流：

```
START → reasoning → [tool_node → reasoning]* → END
```

- **动态槽位提取 (Slot Filling)**：自动识别并追踪预算、收入、用车场景、充电条件等关键信息
- **多轮记忆**：通过 Redis Checkpointer 实现会话状态持久化，支持断点续聊
- **智能追问**：缺失关键信息时，温和引导用户补充，而非盲目推荐

### ⚡ 全链路流式响应 (SSE)

彻底打通三层 SSE 流式链路，实现丝滑的打字机输出体验：

```
FastAPI (StreamingResponse)
    ↓ SSE
Spring Boot (WebClient → SseEmitter)
    ↓ SSE
Vue3 (fetchEventSource)
    ↓ 实时渲染
用户界面
```

**技术细节**：

- FastAPI 使用 `StreamingResponse` + `async generator` 产出 SSE 事件
- Spring Boot 通过 `WebClient` 订阅 Python 服务，使用 `SseEmitter` 转发前端
- Vue3 使用 `@microsoft/fetch-event-source` 处理 SSE，配合 AbortController 支持请求取消

### 🛠 动态工具调用 (Tool Calling)

无缝对接 **阿里云 Qwen-Plus** 模型，支持 Agent 主动调用外部工具：

| 工具名称                        | 功能描述      | 使用场景           |
| --------------------------- | --------- | -------------- |
| `tavily_search_car_news`    | 搜索汽车新闻资讯  | 新车发布、换代消息、行业动态 |
| `tavily_search_car_price`   | 搜索价格和优惠   | 报价查询、促销活动、落地价  |
| `tavily_search_car_reviews` | 搜索评测口碑    | 专业评测、车主反馈、优缺点  |
| `search_car_reviews_rag`    | RAG 知识库检索 | 车评库语义搜索        |

**知识缓存机制**：工具调用结果自动缓存至 Milvus，避免重复请求，提升响应速度。

### 📊 严苛的财务诊断

内置购车 TCO（总拥有成本）核算逻辑：

- 基于用户收入客观劝退不合理需求
- 计算保险、充电/加油、保养、折旧等隐性成本
- 提供"买得起 vs 养得起"的双重评估

***

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue3)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ ChatConsole │  │ Pinia Store │  │ fetchEventSource (SSE)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backend (Spring Boot 3.2)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Controller  │  │   Service   │  │   WebClient (WebFlux)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │   Mapper    │  │    MySQL    │                               │
│  └─────────────┘  └─────────────┘                               │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Service (FastAPI)                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    LangGraph ReAct Loop                  │   │
│  │  ┌───────────┐    ┌───────────┐    ┌───────────────┐   │   │
│  │  │ Reasoning │ ←→ │  Tool     │ ←→ │   Qwen-Plus   │   │   │
│  │  │   Node    │    │   Node    │    │   (LLM)       │   │   │
│  │  └───────────┘    └───────────┘    └───────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Tavily    │  │   Milvus    │  │    Redis Checkpointer   │ │
│  │   Search    │  │    RAG      │  │    (State Persist)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

***

## 🛠 技术栈 (Tech Stack)

### 前端 (Frontend)

| 技术                                                                           | 版本   | 用途                |
| ---------------------------------------------------------------------------- | ---- | ----------------- |
| [Vue 3](https://vuejs.org/)                                                  | 3.4  | 渐进式 JavaScript 框架 |
| [Element Plus](https://element-plus.org/)                                    | 2.6  | Vue 3 组件库         |
| [Pinia](https://pinia.vuejs.org/)                                            | 2.1  | 状态管理              |
| [Vue Router](https://router.vuejs.org/)                                      | 4.3  | 路由管理              |
| [Vite](https://vitejs.dev/)                                                  | 5.2  | 构建工具              |
| [marked](https://marked.js.org/)                                             | 17.0 | Markdown 解析       |
| [@microsoft/fetch-event-source](https://github.com/Azure/fetch-event-source) | 2.0  | SSE 客户端           |

### 中台 (Java Backend)

| 技术                                                                                   | 版本  | 用途          |
| ------------------------------------------------------------------------------------ | --- | ----------- |
| [Spring Boot](https://spring.io/)                                                    | 3.2 | 应用框架        |
| [Spring WebFlux](https://docs.spring.io/spring-framework/reference/web/webflux.html) | -   | 响应式 Web 客户端 |
| [MyBatis-Plus](https://baomidou.com/)                                                | 3.5 | ORM 框架      |
| [MySQL](https://www.mysql.com/)                                                      | 8.0 | 关系型数据库      |
| [Hutool](https://hutool.cn/)                                                         | 5.8 | Java 工具库    |
| [Lombok](https://projectlombok.org/)                                                 | -   | 代码简化        |

### 后台 (Agent Service)

| 技术                                                     | 版本    | 用途            |
| ------------------------------------------------------ | ----- | ------------- |
| [FastAPI](https://fastapi.tiangolo.com/)               | 0.109 | Python Web 框架 |
| [LangGraph](https://langchain-ai.github.io/langgraph/) | -     | Agent 编排框架    |
| [LangChain](https://python.langchain.com/)             | -     | LLM 应用框架      |
| [LlamaIndex](https://www.llamaindex.ai/)               | -     | RAG 框架        |
| [Qwen-Plus](https://tongyi.aliyun.com/)                | -     | 阿里云千问大模型      |
| [Milvus](https://milvus.io/)                           | -     | 向量数据库         |
| [Tavily](https://tavily.com/)                          | -     | AI 搜索 API     |
| [Redis](https://redis.io/)                             | -     | 状态持久化         |

***

## 🚀 快速开始 (Getting Started)

### 环境要求

| 组件      | 版本要求      |
| ------- | --------- |
| JDK     | 21+       |
| Node.js | 18+       |
| Python  | 3.10+     |
| MySQL   | 8.0+      |
| Redis   | 7.0+ (可选) |
| Milvus  | 2.3+ (可选) |

### 1️⃣ 克隆项目

```bash
git clone https://github.com/your-username/ev-compass.git
cd ev-compass
```

### 2️⃣ 配置环境变量

#### Python Agent 配置

```bash
cd chece-agent

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Keys
```

**关键配置项**：

```bash
# 阿里云百炼 API Key (必填)
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# Tavily 搜索 API Key (必填)
TAVILY_API_KEY=your_tavily_api_key_here

# Redis 连接 (可选，用于状态持久化)
REDIS_URL=redis://localhost:6379/0
```

> 💡 **获取 API Keys**：
>
> - 阿里云百炼：<https://bailian.console.aliyun.com>
> - Tavily：<https://tavily.com>

#### Java Backend 配置

编辑 `java-backend/cp-bk/src/main/resources/application.yml`：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/car_policy?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai
    username: root
    password: your_mysql_password

agent:
  service:
    url: http://localhost:8000  # Python Agent 服务地址
```

### 3️⃣ 启动服务

#### 启动 Python Agent 服务

```bash
cd chece-agent

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问 <http://localhost:8000/docs> 查看 API 文档。

#### 启动 Java 后端服务

```bash
cd java-backend/cp-bk

# 使用 Maven 启动
./mvnw spring-boot:run

# 或者在 IDE 中运行 CpBkApplication.java
```

服务启动后访问 <http://localhost:8080。>

#### 启动 Vue 前端

```bash
cd vue

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 <http://localhost:5173> 即可体验完整应用。

### 4️⃣ 数据库初始化

创建 MySQL 数据库并执行建表脚本：

```sql
CREATE DATABASE IF NOT EXISTS car_policy DEFAULT CHARACTER SET utf8mb4;

USE car_policy;

-- 建表脚本位于 java-backend/cp-bk/src/main/resources/db/schema.sql
```

***

## 📸 界面预览 (Screenshots)

### 智能对话界面

!\[Chat Interface]\(./screenshots/chat-interface.png null)
*基于 SSE 的流式输出，打字机效果，支持 Markdown 渲染*

### 工具调用可视化

!\[Tool Calling]\(./screenshots/tool-calling.png null)
*实时展示 Agent 的工具调用过程*

> 📝 **提示**：请将实际运行截图放置于 `screenshots/` 目录下。

***

## 📁 项目结构

```
ev-compass/
├── vue/                          # 前端项目
│   ├── src/
│   │   ├── api/                  # API 接口封装
│   │   ├── components/           # 公共组件
│   │   ├── layouts/              # 布局组件
│   │   ├── router/               # 路由配置
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── styles/               # 全局样式
│   │   ├── utils/                # 工具函数
│   │   └── views/                # 页面组件
│   ├── package.json
│   └── vite.config.js
│
├── java-backend/                 # Java 后端
│   └── cp-bk/
│       ├── src/main/java/com/chece/api/
│       │   ├── controller/       # 控制器层
│       │   ├── service/          # 服务层
│       │   ├── mapper/           # 数据访问层
│       │   ├── entity/           # 实体类
│       │   ├── dto/              # 数据传输对象
│       │   ├── config/           # 配置类
│       │   └── common/           # 公共组件
│       ├── src/main/resources/
│       │   ├── application.yml   # 配置文件
│       │   └── db/               # 数据库脚本
│       └── pom.xml
│
├── chece-agent/                  # Python Agent 服务
│   ├── app/
│   │   ├── agent/                # LangGraph 工作流
│   │   │   ├── graph.py          # ReAct 循环定义
│   │   │   └── state.py          # 状态定义
│   │   ├── api/                  # FastAPI 路由
│   │   ├── tools/                # 工具封装
│   │   ├── rag/                  # RAG 模块
│   │   ├── core/                 # 核心配置
│   │   └── main.py               # 应用入口
│   ├── requirements.txt
│   └── .env.example
│
└── README.md
```

***

## 🔮 路线图 (Roadmap)

- [ ] 多轮对话上下文优化
- [ ] 车型对比功能
- [ ] 用户画像建模
- [ ] 购车时机预测
- [ ] 微信小程序端
- [ ] Docker 一键部署

***

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star 支持一下！**

Made with ❤️ by \[Your Name]

</div>
