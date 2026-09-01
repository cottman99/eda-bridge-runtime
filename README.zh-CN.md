# EDA Bridge Runtime

<p align="center">
  <img src="plugins/eda-bridge-runtime/assets/logo.png" width="150" alt="EDA Bridge Runtime logo">
</p>

<p align="center"><strong>自然地提出任务，稳定地到达正确的 EDA，并留下可恢复、可验证的结果。</strong></p>

<p align="center">
  <a href="README.md">English</a>
</p>

![一个工程请求到达本机或远程 EDA，并返回经过验证的结果](docs/assets/readme/runtime-engineer-workflow-v3.png)

## 一段对话可以到达真实、可编辑的 EDA 结果

用户只需要使用正常的工程语言。厂商 Bridge 负责 ADS 或 AEDT 操作，
Runtime 则让所选目标、操作动机、重试身份、长任务回执、时间和证据在
本机与 SSH 路径中保持一致。

| 可继续编辑的 ADS 结果 | 可继续编辑的 HFSS 结果 |
| --- | --- |
| ![公开验收中的原生 ADS Data Display](docs/assets/readme/ads-native-dds.png) | ![公开验收中的原生 AEDT S 参数 Report](docs/assets/readme/ansys-native-s-parameters.png) |

公开保留的完整任务已经证明：ADS 可从电路建立走到 31 行有限数据并重新
打开原生 DDS 页面；HFSS 可建立三层、双端口模型，求解五个频点并重新
打开原生 Report。Codex 和 Pi 都能各用一个可恢复 Runtime 计划完成任务。

| 可直接检查的模型状态 | 让执行可恢复的公共路径 |
| --- | --- |
| ![包含工程树、布局和叠层的原生 AEDT 模型窗口](docs/assets/readme/ansys-native-layout-stackup.png) | ![一条自然语言需求变成一个可恢复的 EDA 计划，并返回全新验证的证据](docs/assets/readme/runtime-user-flow.png) |

这些都是真实公开合成工程的应用窗口截图，不是效果图或 Python 重绘。
EDA Bridge Runtime 是厂商 Bridge 背后的公共、厂商无关执行路径：它保存
执行连续性和证据，而 ADS 与 AnsysEM Bridge 保留版本相关的运行时集成。

能力不再用 wrapper 数量衡量。Agent 结合准确 Context、版本匹配的官方文档
和随包提供的小型启动经验库，通过受控事务执行官方厂商代码。高频操作可以
保留为与经验资产绑定的编译快捷方式，用于省 token 和降低转写错误；快捷
方式既不是知识真相，也不是触达该能力的唯一通路。

## 它给工程师带来的变化

| 你想要…… | Runtime 负责保证…… |
| --- | --- |
| 只用自然语言，不自己拼 SSH 命令 | 自动复用已经选定的本机或远程连接。 |
| 断线后仍能继续长时间 EDA 任务 | 先记录任务再执行，之后可凭回执继续查看。 |
| 超时或重试时不重复修改工程 | 完全相同的请求返回原有运行结果，而不是盲目再执行。 |
| 知道系统做了什么、为什么做、花了多久 | 记录简短动机、可观察的 Agent 身份、阶段耗时、结果和证据引用。 |
| 在 Codex 与 Pi Agent 之间切换 | 两者使用相同的 Runtime 与厂商 Bridge 契约。 |
| 今天本机运行、明天改为远程运行 | 本机和 SSH 路径使用同一套协议和安全规则。 |

## 公开测试证明了什么

![ADS 与 AEDT 受监督实时编辑的观测耗时](docs/assets/readme/supervised-live-edit-latency.png)

工程师正在查看已打开的 EDA 时，小型受监督修改直接留在同一个图形进程中。
已验收的 ADS 与 AEDT 路径会应用类型化 Patch、立即回读对象；完全相同的重试
不会创建重复对象，也可以只回滚该 Patch，而不必隐式保存。

| 已验收实时操作 | ADS 2026 Update 2.1 | AEDT 2026 R1 |
| --- | ---: | ---: |
| 暖态修改 | 93–187 ms | 296–453 ms |
| 创建对象并回读 | 253 ms | 937 ms |
| 精确回放，重复对象为 0 | 3 ms | 12 ms |
| 仅回滚该 Patch | 21 ms | 204 ms |

这些是 2026-08-31 在可丢弃工程中得到的受控功能性观察，不是厂商性能排名。
ADS 的数据分别来自端到端暖态调用和对象操作的 Bridge 往返；AnsysEM 的数据
分别来自暖态实时调用和 Adapter 时间。Codex 与 Pi Agent 均通过创建、回放和
回滚合同。公开表述由[源数据与图表生成输入](evals/public-readme-data-v1.json)
约束，并可追溯到保留的验收证据。

### 完整旅程说明长任务的时间花在哪里

![ADS 与 HFSS 完整闭环中 Agent 编排和真实 Bridge 加 EDA 工作的时间占比](docs/assets/readme/runtime-complete-workflow-time.png)

最新验收测试覆盖的是完整用户旅程，而不是孤立 API：ADS 从空白工作区
搭建并仿真电路，导出 31 行有限数据，再全新打开可编辑 DDS 页面；HFSS
3D Layout 从空白工程搭建 3 层、2 端口模型，求解 5 个频点，再全新打开
原生 S 参数 Report。Codex 与 Pi 各自都只用一个 Runtime 计划完成闭环。

| 完整旅程 | Codex 总耗时 / Bridge + EDA | Pi 总耗时 / Bridge + EDA |
| --- | ---: | ---: |
| ADS 电路 → 数据 → 两页 DDS | 40.594 秒 / 5.157 秒 | 36.953 秒 / 5.157 秒 |
| HFSS 版图 → 求解 → Report | 242.657 秒 / 209.360 秒 | 229.328 秒 / 202.641 秒 |

以上是最终冻结于 2026-08-30 的公开基线：每个 Agent、每个 EDA 保留一次功能性验收，
不是统计速度排名。
它说明了真正的时间边界：ADS 工程操作只需数秒；长 HFSS 工作流主要由
求解本身主导。测试没有单独测量数据包级网络耗时，但未观察到占主导的
SSH 命令传递成本。

![Codex 与 Pi Agent 在六项受控 EDA 重复测试中的耗时](docs/assets/readme/codex-pi-bounded-tests.png)

图中是冻结于 2026-08-30 的六项公开受控测试中位耗时，每个 Agent、每项任务
重复三次。
两者都走相同 Runtime 与 Bridge。Agent 占比较高的任务差异更明显；
AEDT 生命周期占主导的任务主要受 EDA 本身耗时限制。这是工程基线，
不是对 Agent 的普遍排名。完整方法、通过率和解释边界见
[测试总结](evals/BASELINE_2026-08-30_CODEX_PI_SUMMARY.md)。

目前的测试阶梯覆盖文档证据、精确幂等重试、ADS 与 AnsysEM 的类型化
操作、真实 Momentum 求解，以及一次跨 EDA 协作。脱敏后的真实主机
验收记录见 [Acceptance](docs/ACCEPTANCE.md)。

另一组 2026-09-01 ADS 2027 对比，把当前 Runtime MCP + Runtime/ADS Skills
与官方 ADS MCP 分别交给两个 Agent，每个任务重复三次。Runtime 总体通过
22/24、知识任务通过 18/18；官方路径总体通过 18/24、执行任务通过 6/6。
Runtime 成功的受治理原生批处理中位数为 2.379 秒，但 Agent 使用路径明显
更重。方法与审计数据见
[ADS adapter 对比报告](https://github.com/cottman99/ads-agent-bridge/blob/main/docs/BENCHMARK_ADS2027_HEADLESS_AC.md)。

## 从一个 Agent 配置开始

在 Agent 所在的电脑安装 Runtime：

```console
python -m pip install "eda-bridge-runtime==0.1.0a37"
eda-runtime doctor
```

为你使用的 Agent 创建隔离配置：

```console
eda-runtime agent-profile codex install
eda-runtime agent-profile pi install --help
```

管理员只需一次性选择厂商 Skill 和连接。之后工程师启动生成的配置，
直接使用自然语言，不需要自己维护 SSH 命令、元信息文件或日志。

每台 EDA 主机安装对应的厂商 Bridge：

- [ADS Agent Bridge](https://github.com/cottman99/ads-agent-bridge)
- [AnsysEM Agent Bridge](https://github.com/cottman99/ansysem-agent-bridge)

Agent 与 EDA 同机时注册本机连接，分开时注册 SSH 连接。两种情况都经过
Runtime，因此审计、重试、目标选择和证据规则不会分裂成两套系统。

## 安全承诺

- 每个 Agent 操作都带一条简短动机。
- 修改操作必须有稳定身份，绝不盲目重复执行。
- SSH 断开不等于 EDA 长任务失败。
- Context 只包含定位信息和指纹，不包含凭据。
- 追加式日志保存指纹与受控元信息，不保存完整聊天或原始操作载荷。
- 厂商相关行为保留在各自 Bridge 中，不进入 Runtime 核心。
- 启动经验是带哈希的建议性包数据，Markdown 永不执行；缺失时不阻断受控
  原生执行。
- 没有 Bridge 证据时，不宣称求解、产物或持久化修改成功。

## 下一步

- 在不改变用户对话方式的前提下接入更多厂商 Bridge；
- 通过统一、受治理的原生执行与事务信封广泛调用版本匹配的官方 API，
  而不是把厂商 API 逐项重写成 Bridge wrapper；
- 让长任务恢复与证据查看更直观；
- 保留更多贯穿电路、版图、EM、仿真、提取和原生绘图的完整真实工程任务。

## 进一步了解

- [整体架构](docs/ARCHITECTURE.md)
- [不重写厂商 API 的能力扩展模型](docs/CAPABILITY_MODEL.md)
- [Agent 主机、EDA 主机与同机部署](docs/DEPLOYMENT_ROLES.md)
- [MCP 与 Codex 集成](docs/MCP_AND_CODEX.md)
- [Pi Agent 试点](docs/PI_AGENT_PILOT.md)
- [验收证据](docs/ACCEPTANCE.md)
- [当前范围](docs/V0_1_SCOPE.md)

本项目仍是公开 Alpha。首次使用请从可丢弃工程开始，并先查看相应厂商
Bridge 的能力边界和证据说明。
