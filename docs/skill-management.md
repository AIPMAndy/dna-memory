# 共享 Skill 管理

DNA Memory 将“长期记忆”和“行为 Skill”分开治理：

- `knowledge_root/managed_memory_dir` 是验证后结论的 Markdown 真源。
- `skill_root` 是共享 Skill 真源，推荐 `~/.agents/skills`。
- `platform_skill_roots` 是 Codex、Claude Code、Hermes 的加载目录。
- `skill_registry` 只声明 DNA Memory 有权分发的共享 Skill。
- 注册表外的目录属于平台专属或未管理内容，不会被删除或覆盖。

## 注册表

```json
{
  "skills": {
    "dna-memory-loop": {
      "targets": ["codex", "claude", "hermes"]
    }
  }
}
```

推荐将仓库内的 `skills/dna-memory-loop` 放入共享真源。它统一三端行为：

1. 依赖历史的任务开始前，以独立关键词召回。
2. 只有真正使用的召回结果才提交反馈。
3. 只有验证后的长期结论才写回。
4. 记忆服务故障不阻塞主任务。
5. 不把完整 transcript、凭证或大型工具输出写入记忆。

## 命令

```bash
python3 dna.py skills inventory --json
python3 dna.py skills doctor --json
python3 dna.py skills sync --json
python3 dna.py skills sync --apply --json
```

`sync` 默认 dry-run。`--apply` 只为缺失目标创建符号链接，不会覆盖现有目录。

| 状态 | 含义 | 自动操作 |
|---|---|---|
| `shared` | 正确指向共享真源 | 无 |
| `platform` | 注册表外的平台专属 Skill | 保留 |
| `shadowed` | 内容相同但不是链接 | 仅报告 |
| `conflict` | 同名内容不同 | 阻断 |
| `broken_link` | 链接目标不存在 | 仅报告 |

## 候选提案

客户端不能直接调用 `memory_remember` 时，可在最终消息中输出：

```text
DNA_MEMORY_PROPOSAL {"type":"decision","summary":"verified reusable conclusion","confidence":"high","importance":0.8}
```

每个会话最多 3 条，每条不超过 800 字符。提案不是长期记忆；daily 维护仍会
执行类型、敏感信息、容量和去重检查。普通 Claude Desktop 云端聊天没有稳定
本地正文来源时，应使用显式 MCP 写回，不能假设后台自动捕获。

## 回滚

只删除客户端目录中的受管符号链接，不要删除 `skill_root` 真源。运行
`skills doctor` 确认没有断链或冲突。未知 Skill 始终保留。
