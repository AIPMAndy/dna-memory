# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Markdown/Obsidian 长期真源与可重建 SQLite 索引
- Codex、Claude Code、Claude Desktop 和 Hermes 的统一 stdio MCP
- 有界原生会话指针、候选提案、召回反馈与价值指标
- 显式 `supersedes` 关系与原子回滚
- 跨客户端共享 Skill 清单、诊断和安全同步
- 通用 `dna-memory-loop` Skill
- CI 测试、编译和公开敏感信息扫描
- 跨会话精确去重：同类型且规范化摘要相同的 active 记忆只保留一条，并合并来源与客户端
- daily 维护的 `deduplicated` 指标，区分新认知结晶与重复候选

### Changed
- README、快速上手和客户端文档改为当前跨端用法
- 本机 profile、运行配置和记忆数据全部迁出 Git 仓库
- macOS 自动化标识和示例路径改为通用命名
- 旧 Claude 同步脚本不再包含固定用户或项目路径
- 自动提取过滤操作交接、计划性叙述和无主体发布话术，减少过程话术结晶

### Removed
- 私人 Skill、个人部署计划、真实 vault 名称和运行时记忆样例

## [2026-04-22] - 可用性优化

### 核心改进
- 识别并解决使用率低的根本问题：不是功能不够，而是使用门槛高
- 通过文档优化而非代码重构，保持向后兼容性
- 聚焦核心价值：让 AI Agent 真正用起来记忆系统

### 设计原则
- 优先让它能用，而不是追求完美
- 保持简单：3 个核心功能 > 30 个高级功能
- 降低门槛：快速上手 > 功能完整

---

**Project**: https://github.com/AIPMAndy/dna-memory
