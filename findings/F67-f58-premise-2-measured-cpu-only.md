# F67 — 2026-10-11 — F58 的前提 #2 **已实测：dist-packages 可写、`.pth` 真的执行**（而且没占 GPU 名额）

## 1. 怎么做到的：CPU 内核不占 GPU 名额

两个 GPU 名额被我们自己的内核占满（`arc-duck-taaf` RUNNING + `arc-vllm-probe` QUEUED），
`duck18-va` 推不进去。但 **A6 记过"纯 CPU 内核不占 GPU 槽"** —— 于是我把这个探针做成
`enable_gpu: false`、**零数据集**，结果**推送成功、几十秒内 COMPLETE**。

⇒ ⭐ **一条可复用的通道**：**当 GPU 名额是瓶颈时，把问题切成"不需要 GPU 的那一半"先用 CPU 内核跑掉。**
本次就是：F58 的两个前提里，**#2 不需要 GPU，#1（sgl-site 里有没有 numpy/）需要**。

（工具注意：`enable_internet: false` + 无数据集，脚本只用标准库。）

## 2. 逐字读数（`ppxl16/arc-pth-probe`，COMPLETE）

```
python      : 3.13.15
purelib     : /usr/local/lib/python3.13/dist-packages
site dirs   : ['/usr/local/lib/python3.13/dist-packages',
               '/usr/lib/python3/dist-packages',
               '/usr/lib/python3.13/dist-packages']

STEP 1  exists: True   os.access W: True
        actually wrote a file: YES -> .../zz_arc_probe_marker.txt
STEP 2  wrote .../zz_arc_probe.pth
        child: ARC_PROBE_PTH_RAN at index [6]
        CHILD_PATH ['', '/kaggle/lib/kagglegym', '/kaggle/lib',
                    '/kaggle/input/competitions/arc-prize-2026-arc-agi-3',
                    '/usr/lib/python313.zip', '/usr/lib/python3.13',
                    '/usr/lib/python3.13/lib-dynload',
                    '/usr/local/lib/python3.13/dist-packages',      <- 7
                    '/usr/lib/python3/dist-packages']
        .pth EXECUTED: YES
STEP 3  HAS numpy/ : /usr/local/lib/python3.13/dist-packages
                    /usr/lib/python3/dist-packages
```

## 3. 结论（三条）

1. ⭐ **前提 #2 成立**：`/usr/local/lib/python3.13/dist-packages` **可写**，且放在那里的 `.pth`
   **确实在新解释器里被执行**。⇒ **F58 §3 的修法有可落地的位置，不会静默失效。**
2. ⭐ **F58 没提到的一个事实**：**`/usr/lib/python3/dist-packages` 里也有 `numpy/`** ——
   那是 `site` 目录里的**第二个** numpy 源。F58 的修法只修剪"真的含 `numpy/` 的路径"并把目标插到 0，
   所以**它天然覆盖这一条**；但若将来有人把修法改成"只删 sgl-site"，就会漏掉它。**记下来。**
3. ⚠️ **仍然未知的只有一条**：**`/tmp/sgl/sgl-site`（4 GB 运行时）里到底有没有 `numpy/`** ——
   这条**必须有那套运行时才能测**，所以只能等 `duck18-va` 那一枪。

## 4. 对判读键（F66）的更新

F66 的表格里有一行是"**没有 `[arc_numpy_fix] pruned` ⇒ `.pth` 没执行**"。
**现在这一行的解释收窄了**：既然"可写 + 会执行"都已证实，那么**如果真的没看到 `pruned`**，
原因就不再是"装不上"，而更可能是：
* v5 的 `.pth` 写入代码**根本没走到**（即渲染/更早的关卡又坏了），或
* 它写到了**别的 site 目录**（本探针实测有 **三个** site 目录，`site.getsitepackages()` 的第一个
  才是 dist-packages —— 若 v5 用的是 `sysconfig.get_paths()['purelib']` 那也是它，但要**核对**）。

⚠️ ⇒ **`duck18-va` 跑起来后，第一件要确认的事**：日志里有没有 `pruned`；
**没有的话，先去核 v5 到底往哪个路径写**，而不是先怀疑"不可写"（这一条已经被排除）。

## 5. 本轮净产出

| # | 产出 |
|---|---|
| 1 | **F58 前提 #2 实测成立**（可写 + 会执行），且发现**第二个含 numpy 的 site 目录** |
| 2 | 建立并验证了**"CPU 内核不占 GPU 名额"这条通道**（名额满时仍能推进） |
| 3 | 把 F66 判读键里"没看到 pruned"的解释**收窄**（先核写入路径，别再怀疑权限） |
