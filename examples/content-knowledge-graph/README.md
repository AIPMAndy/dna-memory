# Content Knowledge Graph 🧠

**把散落的文稿变成可追溯、可审核、可重组的知识图谱。**

[简体中文](#30-秒运行) · [案例研究](../../docs/research/dontbesilent-knowledge-system.md) · [DNA Memory 主项目](../../README.md)

由 **AI 酋长 Andy** 独立开发，灵感来自公开的内容工程实践，但没有复制 dontbesilent 的源码、Skill、数据或受限制的文档。**本项目公开的是引擎、模拟示例和原创研究，不包含作者的私人知识库，也不包含 Andy 的私人数据。**

## 它解决什么问题

一篇文章写完，就躺在文件夹里。下一次创作又重新找问题、观点、案例和方案。把文件直接塞进大模型的上下文，也不能保证可追溯和可持续维护。

本项目提供一个 **Local-first** 流程：

~~~text
Markdown / TXT → 来源登记、哈希与排除敏感信息
              → 提取问题 QST / 概念 CON / 观点 OPI / 案例 CAS / 方案 SOL
              → 原文逐字证据 + 来源文件路径 + 行号
              → 人工审核 → 显式关系（回应/解释/证明/冲突）
              → 离线知识图谱 HTML + 选题装配稿
~~~

**零 Python 第三方依赖**，默认完全离线。只有用户明确选择 AI 提取模式，且提供 API 凭证并允许外传时，才会把文稿发送到 OpenAI-compatible API。

## 30 秒运行

需要 Python 3.10+。在仓库根目录执行：

~~~bash
cd examples/content-knowledge-graph

# 1. 使用仓库内的纯虚构样本，不需要联网或 API Key
python3 knowledge_graph.py ingest demo
python3 knowledge_graph.py extract
python3 knowledge_graph.py validate

# 2. 生成本地可打开的可视化和内容装配稿
python3 knowledge_graph.py graph
python3 knowledge_graph.py assemble --include-drafts

# 3. 打开 workspace/graph.html
# Windows: start workspace/graph.html
# macOS: open workspace/graph.html
# Linux: xdg-open workspace/graph.html
~~~

输出目录默认是当前目录下的 **workspace/**。其内容可能包含绝对源路径和私人知识信息，**不应提交 Git**。

## 导入自己的素材

~~~bash
python3 knowledge_graph.py --workspace ~/my-private-content-graph ingest ~/my-articles
python3 knowledge_graph.py --workspace ~/my-private-content-graph extract
python3 knowledge_graph.py --workspace ~/my-private-content-graph validate
~~~

默认的离线提取只识别文稿中的明确标记行。例如：

~~~text
问题：为什么内容阅读量高却没有咨询？
概念：曝光与高质量商机是不同的指标。
观点：用真实问题而非空泛热点筛选意向客户。
案例：这里应填入可验证的公开案例，未经授权不可使用客户信息。
方案：记录阅读、有效咨询、成交和真实交付结果。
~~~

这些标记便于构建 **可复现的基准测试**，并不代表工具已完成无标记文章的语义理解。无标记文章需要 AI 模式，或由人手工打标。

## AI 自动抽取（可选）

明确允许材料离开本机后再使用：

~~~bash
export OPENAI_API_KEY="your_key_here"
python3 knowledge_graph.py extract \
  --mode ai \
  --model gpt-4.1-mini \
  --allow-external-upload
~~~

支持使用 \`--base-url https://your-compatible-provider.example/v1\` 配合兼容 API。该调用会发送文稿正文（单篇最多前 12,000 字符），**需要真实的模型访问权限和可能产生 API 费用**。不要导入客户合同、个人聊天、秘钥或未授权文本。不要把 API Key 写入仓库或命令历史；请使用环境变量。

AI 产出的节点始终标记为 \`draft\`，并要求 \`quote\` 原文逐字存在，过滤掉没有原文证据的模型输出。**有原文引用不保证结论正确。**

## 人工审查和建立关系

先在 \`workspace/units.json\` 中找到节点 ID，逐一核实：

~~~bash
python3 knowledge_graph.py approve QST-xxxxxxxxxxxxxxxx
python3 knowledge_graph.py approve OPI-yyyyyyyyyyyyyyyy
python3 knowledge_graph.py link QST-xxxxxxxxxxxxxxxx 回应 OPI-yyyyyyyyyyyyyyyy \
  --evidence "核对原文后的关系说明"
python3 knowledge_graph.py validate
python3 knowledge_graph.py assemble
~~~

关系必须是经人工批准的活动节点，不能凭“两个节点都提过流量”就自动宣称二者存在因果关系。源文件发生变化后，旧节点会标记 stale，防止未经复核继续进入装配稿。

## 命令速查

| 命令 | 功能 |
|---|---|
| \`ingest <目录>\` | 注册 MD/TXT 来源，哈希检查和敏感文本排除 |
| \`extract\` | 默认从标记行提取草稿 |
| \`extract --mode ai --allow-external-upload\` | 用户授权后使用 API 提议节点 |
| \`approve <节点ID>\` | 人工确认某个节点 |
| \`link <源ID> <关系> <目标ID> --evidence "理由"\` | 添加有证据的显式关系 |
| \`validate\` | 检查证据来源、关系有效性与缺口 |
| \`search <关键词>\` | 在活动节点中检索 |
| \`graph\` | 输出离线 HTML 图谱 |
| \`assemble\` | 将已审批的内容节点组成写作材料草稿 |
| \`assemble --include-drafts\` | 测试环境下也包含草稿 |

## 已实现 / 尚未实现

**已实现：** 本地索引；源文件变化检测；五类知识节点；两种抽取方式；逐字证据和行号；审核状态；显式关系；来源校验；离线 HTML 图谱；可追溯装配稿。

**尚未实现：** PDF/DOCX/OCR 导入、百万节点可视化、自动语义关系审核、跨文档向量 RAG、分布式任务队列、浏览器拖拽上传、Obsidian 原生双链导出。请勿把此 MVP 宣传成已经复刻作者的千万字完整私有系统。

## 工程质量门槛

1. 原始资料默认不移动、不删除、不改写。
2. 先处理 3–5 篇代表性文稿；输出质量合格再扩容。
3. 每个节点拥有稳定 ID、原文证据、来源路径和行号。
4. 所有显式关系都要求已审批节点、人工证据和无悬空目标。
5. 敏感信息、密钥、客户资料不进入公开仓库。
6. 真实效果看复用率、错误率、创作效率、咨询转化，而不是节点总量。

## 参考研究与许可

详细研究请看 [dontbesilent 的内容工程与商业模式](../../docs/research/dontbesilent-knowledge-system.md)。这是独立实现，不包含其受限许可仓库的衍生复制；官方源项目及其许可证请直接访问 [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill)。

本目录代码遵循 DNA Memory 仓库的 **Apache-2.0** 许可证，第三方资料和被导入的用户内容不因此获得 Apache 授权。

**作者**：AI 酋长 Andy · [GitHub](https://github.com/AIPMAndy) · [个人网站](https://metaver.vip/)。
