# AgentRadar Agent 评测

## 评测目标

固定评测用于尽早发现需求解析、候选过滤和证据化研究的回归。数据位于 `backend/evaluation/agent_cases.json`，目前包含计划书指定的五类需求：

1. 适合初学者的 LangGraph 项目；
2. 具备长期记忆能力的 Agent；
3. FastAPI 与 LangGraph 项目；
4. Agent Evaluation 项目；
5. 适合简历改造的多 Agent 系统。

另外提供一个工程完整的 Agent 仓库和一个简单聊天套壳仓库。README、目录树和依赖内容全部固定在评测集内，不依赖 GitHub 网络状态。

## 运行方式

```bash
cd backend
.venv/bin/python -m app.evaluation evaluation/agent_cases.json
.venv/bin/python -m app.evaluation evaluation/agent_cases.json --format markdown
```

第一条输出适合机器读取的 JSON，第二条输出适合文档或面试展示的 Markdown。CI 会执行同一套评测，并由单元测试检查最低质量阈值。

## V1.0.0 基线

| 指标 | 结果 | 口径 |
|---|---:|---|
| 条件字段准确率 | 100.00% | 5 条需求的 7 个结构化字段逐项比较 |
| 搜索查询有效率 | 100.00% | 每个计划有 3 至 5 条查询且包含安全限定条件 |
| 排除词查询泄漏率 | 0.00% | 排除技术未再次进入 GitHub 查询 |
| Agent 能力识别准确率 | 100.00% | 2 个研究样本的 8 项能力逐项比较 |
| 套壳风险判断准确率 | 100.00% | 完整工程与简单聊天套壳均分类正确 |
| 错误项目过滤召回率 | 100.00% | fork、归档、无 README、过旧、忽略和重复项目均被过滤 |
| 首位推荐准确率 | 100.00% | 目标需求下完整 Agent 工程排在首位 |
| 不存在文件路径幻觉率 | 0.00% | 所有阅读路径都来自固定真实目录树 |
| 证据来源覆盖率 | 100.00% | README、目录、依赖、Release 和 Issue 来源均有记录 |

离线基线的模型调用数和外部工具调用数都为 0，因此运行稳定、无费用，也适合在 CI 中阻止确定性规则回归。

## 结果边界

这套基线不替代联网质量评测。GitHub 搜索召回率、真实仓库推荐相关度、API 成功率、限流影响、平均执行时间和模型费用必须在配置 GitHub Token 与模型服务后单独采样。V1 将离线基线作为合并门槛，把联网指标作为发布前人工验收，避免网络波动导致 CI 随机失败。
