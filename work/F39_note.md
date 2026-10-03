
### 39.1 State at 2026-09-30 11:45Z

* Kernel **version 4** of `ppxl16/arc-prize-2026-arc-agi-3-starter` is built, pushed CPU-only
  (`enable_gpu: false`, push returned **no error field**) and is **COMPLETE**. It carries
  `agents/goose_nolevel_cpu.py`.
* ⚠️ **The submission was REFUSED with HTTP 400** — the competition allows **one submission per day**,
  and today's slot went to `56705048`. The next slot opens at **00:00Z**. So v4 is *ready*, not sent.
* ⚠️ When submitting, do **not** rebuild the notebook: `build_notebook.py` **re-syncs `enable_gpu=True`**
  into the metadata (observed in this session), which would hit the exhausted GPU quota. Either set it
  back to `False` after any rebuild, or submit `kernel_version=4` exactly as pushed.
