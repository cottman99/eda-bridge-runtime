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
执行连续性和证据，而 ADS 与 AnsysEM Bridge 继续承载原生工程知识。

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

![ADS 与 HFSS 完整闭环中 Agent 编排和真实 Bridge 加 EDA 工作的时间占比](docs/assets/readme/runtime-complete-workflow-time.png)

最新验收测试覆盖的是完整用户旅程，而不是孤立 API：ADS 从空白工作区
搭建并仿真电路，导出 31 行有限数据，再全新打开可编辑 DDS 页面；HFSS
3D Layout 从空白工程搭建 3 层、2 端口模型，求解 5 个频点，再全新打开
原生 S 参数 Report。Codex 与 Pi 各自都只用一个 Runtime 计划完成闭环。

| 完整旅程 | Codex 总耗时 / Bridge + EDA | Pi 总耗时 / Bridge + EDA |
| --- | ---: | ---: |
| ADS 电路 → 数据 → DDS | 39.782 秒 / 5.438 秒 | 33.922 秒 / 5.140 秒 |
| HFSS 版图 → 求解 → Report | 242.657 秒 / 209.360 秒 | 229.328 秒 / 202.641 秒 |

以上是每个 Agent、每个 EDA 保留的一次功能性验收，不是统计速度排名。
它说明了真正的时间边界：ADS 工程操作只需数秒；长 HFSS 工作流主要由
求解本身主导。测试没有单独测量数据包级网络耗时，但未观察到占主导的
SSH 命令传递成本。

![Codex 与 Pi Agent 在六项受控 EDA 重复测试中的耗时](docs/assets/readme/codex-pi-bounded-tests.png)

图中是六项公开受控测试的中位耗时，每个 Agent、每项任务重复三次。
两者都走相同 Runtime 与 Bridge。Agent 占比较高的任务差异更明显；
AEDT 生命周期占主导的任务主要受 EDA 本身耗时限制。这是工程基线，
不是对 Agent 的普遍排名。完整方法、通过率和解释边界见
[测试总结](evals/BASELINE_2026-08-30_CODEX_PI_SUMMARY.md)。

目前的测试阶梯覆盖文档证据、精确幂等重试、ADS 与 AnsysEM 的类型化
操作、真实 Momentum 求解，以及一次跨 EDA 协作。脱敏后的真实主机
验收记录见 [Acceptance](docs/ACCEPTANCE.md)。

## 从一个 Agent 配置开始

在 Agent 所在的电脑安装 Runtime：

```console
python -m pip install "eda-bridge-runtime==0.1.0a32"
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
- 没有 Bridge 证据时，不宣称求解、产物或持久化修改成功。

## 下一步

- 在不改变用户对话方式的前提下接入更多厂商 Bridge；
- 让长任务恢复与证据查看更直观；
- 保留更多贯穿电路、版图、EM、仿真、提取和原生绘图的完整真实工程任务。

## 进一步了解

- [整体架构](docs/ARCHITECTURE.md)
- [Agent 主机、EDA 主机与同机部署](docs/DEPLOYMENT_ROLES.md)
- [MCP 与 Codex 集成](docs/MCP_AND_CODEX.md)
- [Pi Agent 试点](docs/PI_AGENT_PILOT.md)
- [验收证据](docs/ACCEPTANCE.md)
- [当前范围](docs/V0_1_SCOPE.md)

本项目仍是公开 Alpha。首次使用请从可丢弃工程开始，并先查看相应厂商
Bridge 的能力边界和证据说明。
