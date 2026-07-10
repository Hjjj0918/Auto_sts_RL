# Changelog

---

## [Unreleased]

### Added
- 迷你 STS 环境 `src/mini_sts_env.py`：4D 状态空间，4 离散动作，继承 gym.Env
- PPO 训练脚本 `src/train_ppo.py`：单核训练，EvalCallback 自动保存最优模型
- MaskablePPO 训练脚本 `src/train_masked_ppo.py`：基于 sb3-contrib 的动作掩码训练
- 多进程并行训练脚本 `src/train_ppo_parallel.py`（SubprocVecEnv，Windows 兼容）
- TCP 桥接脚本 `src/tcp_bridge.py`：连接 Communication Mod（stdin/stdout）与 RL 客户端
- 测试套件 `tests/`：环境冒烟测试、训练模型回放、TCP 通信测试
- Communication Mod 配置文件模板（位于 `%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`）

### Changed
- 项目目录重构：核心代码移入 `src/`，测试代码移入 `tests/`
- 所有脚本统一 `sys.path` 修正，支持从任意目录运行

### Fixed
- Windows 多进程 spawn 模式兼容（`if __name__ == "__main__"` 守卫）
- PyTorch CUDA 版本安装路径冲突
- Communication Mod TCP 协议误解修正（实际为 stdin/stdout 纯文本协议）

---

## [0.1.0] - 2026-07-08

### Added
- 项目初始化，MIT 许可证
- 环境验证脚本 `verify_env.py`
- `.gitignore`、`README.md`、`CHANGELOG.md`
