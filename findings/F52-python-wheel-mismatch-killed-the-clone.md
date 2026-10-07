# F52. 高阶 clone 死了 —— 死因是 cp312 的轮子装进 Python 3.13，不是显存、不是数据、不是模型

**日期**：2026-10-07
**结论**：`ppxl16/arc-agi-3-duck-18-1gc`（`machine_shape: NvidiaRtxPro6000`）**排队 6.75 小时后 ERROR**，
**启动前奏第 3.7 秒就崩了，模型一行都没跑。** 直接原因是它的 `unpack_sglang` 阶段要装一个
**cp312** 的 `zstandard` 轮子，而 Pro 6000 环境的 Python 是 **3.13.15** ⇒ pip 拒绝 ⇒ 该阶段中止
⇒ `/tmp/sgl/sgl-site/` 从未被创建 ⇒ 紧接着的 cell 读它时报 `FileNotFoundError`。

**这不是硬件问题，也不是竞赛侧问题。** GPU 拿到的正是我们要的那块。

---

## 1. 完整因果链（逐行来自日志，不是推断）

```
[ 3.2s] PATHS {'sglang_runtime': '/kaggle/input/sglang-penny-build-qwen/sglang-penny-runtime', ...}
[ 3.7s] PHASE_START unpack_sglang
[ 4.0s] PHASE_ERROR unpack_sglang
        ERROR: zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
               is not a supported wheel on this platform.
        subprocess.CalledProcessError:
          ['/usr/bin/python3','-m','pip','install','--quiet','--no-index','--no-deps',
           '--target','/tmp/zst','/kaggle/input/sglang-penny-build-qwen/sglang-penny-r...<whl>']
[23.5s] SETUP_OK False CUDA_HOME /tmp/cuda-root/usr/local/cuda-13.0
[36.0s] FileNotFoundError: [Errno 2] No such file or directory:
        '/tmp/sgl/sgl-site/sglang/srt/mem_cache/kv_cache_configurator.py'
        (cell line 122:  _kvc_src = _KVC.read_text().replace("\r\n", "\n"))
```

⇒ **`unpack_sglang` 失败是根因；`FileNotFoundError` 只是它的下游症状。**
那个 cell 自己的注释写着：*"~1.5 GB and runs 13 requests. **Both anchors must match exactly once
or the boot raises.**"* —— 而它连文件都没等到。

---

## 2. 同时被证实的（先前只是判断，现在是实测）

| 项 | 实测值 | 意义 |
|---|---|---|
| GPU | `NVIDIA RTX PRO 6000 Blackwell Server Edition, 580.178.04, 97887 MiB` | **F48/F49 得到再次确认**：API 用 `machine_shape: NvidiaRtxPro6000` 真的拿到 Pro 6000 / ~98 GB |
| 主机 | `MemTotal 176.9 GiB`、`nproc 48`、`python 3.13.15` | 大内存、48 核；**Python 3.13 就是这次死因的那一半** |
| T4 断言 | `accelerator_guard: PASSED (no T4 assertion in the log)` | 这个 clone 没有 T4 硬断言（与 RSNA 那边相反） |
| 硬上限 | `V1462_HARD_CAP armed 10800s`（=3 h） | 这次运行自带 3 小时上限 |
| 提交意图 | `taaf.kaggle: TRUE_SUBMISSION=False` | **这次是非提交运行**，所以 400/有效提交状态不因此改变 |

---

## 3. 为什么它排队 6.75 小时

轮询记录（15 分钟一次）：`11:22:48 QUEUED` → …… → `17:53:16 QUEUED` → `18:08:17 ERROR`。
**即：Pro 6000 的空闲窗口极稀缺**，拿到之后因为一个轮子 tag 在 4 秒内死掉 ——
**这是本次最贵的浪费形态**（排队成本 6.75 h，执行成本 4 s）。

---

## 4. 处置选项（未选择，留给下一次决定）

1. **换到 Python 3.12 的运行环境**再跑这个 clone —— 最小改动，但需要确认订阅里哪个 accelerator/runtime 组合提供 3.12。
2. **重建 `sglang-penny-runtime` 资产**，把 `zstandard` 等轮子换成 **cp313** —— 动的是资产，但一次修好、以后所有 Pro 6000 运行都受益。
3. **在 boot 前加显式的版本断言**：拿到 GPU 后**先比 `python -V` 与轮子的 `cpXY` 标签，不匹配就立刻响亮退出**，而不是让它在 36 秒后以一个看起来像"缺文件"的错误收场。
   ⇒ **推荐先做 3**：它把这个坑从"4 秒死 + 6.75 小时排队"变成"0 秒死 + 一句可读的话"，而且不依赖任何外部条件。

⚠️ **不要把这次 ERROR 记成"Pro 6000 路线不可行"。** 硬件拿到了、T4 断言过了、
死因是一个纯软件版本不匹配。这与 **F48/F49/F50** 的结论并不冲突。

---

## 5. 复现

```bash
kaggle kernels logs ppxl16/arc-agi-3-duck-18-1gc          # 91 行 JSON 流
python work/hunt_sgl_boot.py                              # D:\kaggle\arc\work\ 下，按 sgl/SITE//tmp 过滤
```
产物：`D:\kaggle\arc\state\arc_clone_result.json`（读数器写的）、`state/klog_raw.json`（原始日志）。
