# F51. ⭐⭐⭐ 403 解开了 —— 病因是**那份拉回来的 metadata**，不是 notebook，也不是权限

**日期**：2026-10-07
**结论**：**克隆重型公开 notebook 现在可行。** 之前那个空的 403，来自**就地修改从内核拉回来的
`kernel-metadata.json`**，而不是 notebook 内容、不是尺寸、不是依赖、不是权限。

---

## 1. 决定性实验（每一步都排除了一个假设）

| 试验 | 结果 | 排除了什么 |
|---|---|---|
| 用**无意义内容撑大的 notebook**：50 / 150 / 300 / **600 KB** | **全部 PUSH OK** | ❌ **尺寸** |
| 同一本 duck18，**前 1 / 4 / 8 / 16 / 50 个 cell** | **全部 PUSH OK**（含**全部 50 个 cell**） | ❌ **notebook 内容** |
| 全部 cell + **13 个真实 dataset_sources**，**全新 id/标题 + 干净最小元数据** | **PUSH OK** | ❌ 依赖 |
| 同上 **再加 2 个 model_sources** | **PUSH OK** | ❌ 模型引用 |

⇒ **同一本 notebook、同样的依赖，用一份【新写的】最小 metadata 就能推。**

## 2. 病因

**`kernels_push` 读取的是本地 `kernel-metadata.json`。** 之前我一直**就地改**那份**从 `kaggle kernels pull -m`
拉回来的**副本 —— 它带着原作者的字段，其中最可疑的是：

```
"docker_image": "gcr.io/kaggle-private-byod/python@sha256:57e612b484cf..."
```

**`kaggle-private-byod` 是别人的私有 BYOD 镜像**，我们无权引用 ⇒ 服务器返回**空 body 的 403**。
（另有一个字段 `id_no`、`current_version_number` 之类也是拉回来的产物，不该带回去。）

**正确做法（写死）**：克隆公开 notebook 时，
**不要改拉回来的 metadata —— 写一份全新的**，只含：
`id / title / code_file / language / kernel_type / is_private / enable_* / keywords /
dataset_sources / kernel_sources / competition_sources / model_sources / (machine_shape)`。

⚠️ **注意代价**：**新 metadata 里没有那个私有 BYOD 镜像**。若那本 notebook 真的依赖它的环境，
**行为可能与原作者不同** —— 这一条**未验证**，必须在实跑时看日志确认，不能假设。

## 3. 顺带学到的第二条

**"Maximum batch GPU session count of 2 reached."** —— GPU 并发上限是 **2**，
而我为排查 403 留下的探针内核**还占着位**，于是正式克隆那一次**没能建出来**
（`versionNumber: null`、`ref: ""`）。
⇒ **排查用的小内核要立刻收尾**，否则它们会挡住真正要建的东西。这与 RSNA 那边 `A160` 记的
「`kernel-tpu-3dsmoke` 占着 TPU 并发位」是**同一个坑的 GPU 版本**。

## 4. 这条为什么重要

F45 普查的结论是：**所有拿到分的公开配方都声明 `NvidiaRtxPro6000` 并用 NVFP4 / FP8**，
而 F49 已实测**我们能通过 API 拿到 sm_120**。**唯一剩下的障碍就是"把那些配方拿进来"**——
现在它通了。

⇒ **从 24.53 往 40–55 档走的路上，最后一个已知障碍被移除。**
⚠️ 但"能克隆"≠"能拿分"：ARC 的分取决于时间预算内玩到哪一步，而**克隆件与原件是否行为一致未验证**。
