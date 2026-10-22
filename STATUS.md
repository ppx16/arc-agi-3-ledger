# ARC Prize 2026 — ARC-AGI-3 — STATUS (2026-10-21)

> This supersedes `STATUS-2026-10-15.md`. The earlier statuses stay as history; this page is the current
> one screen. Numbers below are server readings, not notebook titles.

---

## 1. Standing

| | rank | score | subs |
|---|---|---|---|
| **us** | **827** | **29.34** | 16 |
| bronze (top 10 %) | 457 | **30.85** | — |
| silver (top 5 %) | 228 | 32.23 | — |
| gold | 10 | 43.94 | — |
| leader | 1 | 68.91 | 169 |

**Margin to bronze: −1.51 score, ≈ −370 places.** Deadline **2026-11-02 23:59Z** (12 days).

---

## 2. The mechanism, and why it changes the objective

The board records `max over all of a team's submissions` (F80). So the medal probability is

```
P(medal) = 1 - (1 - p)^n ,   p = P(one draw > cut)
```

**the right tail, not the mean** (F82). A lower-mean agent with a wider spread can be far more likely to
medal than a higher-mean, tighter one — the left tail costs nothing because only the maximum is kept.

## 3. Our distribution (13 draws)

`22.48 24.53 23.67 19.83 23.51 26.41 28.98 27.96 25.72 23.82 27.10 29.34 25.08`

mean **25.26**, sd **2.71**, max **29.34**. With the cut at 30.85: `p ≈ 2.0 %` per draw, so the **12
remaining draws give ≈ 21 %**.

Two of those draws are worth staring at together: **29.34 (10-20) and 25.08 (10-21)** — same kernel, same
environment, nothing changed. The spread is the sampling.

## 4. Every lever we can reach, and why each is closed

| Lever | Status |
|---|---|
| A stronger public agent | **Closed (F85).** Our harness patch and the best public fork's are both 498,799 characters and differ in exactly 11 of them — eight hyphens and three quotes, all inside prompt prose. Same agent; the 29.34 vs 32.60 gap is sampling. |
| A newer/leaner harness | **Closed (F85).** Same private BYOD image, same two Qwen model datasets, same RTX PRO 6000 as that fork; the "V6 persistent interpreter" it advertises is already in our copy (`persistent` ×30). |
| Sampling knobs (temperature 0.6 / top_p 0.95 / top_k 20 / seed −1) | **No evidence either way (F83).** Reachable — cell 4 sets environment variables before the analyzer module imports — but "hotter ⇒ fatter right tail" is exactly the kind of plausible-unverified story this project keeps falsifying, and a test costs a draw. |
| `n_passes` | **Closed (F84).** Set to 4 only in offline Save runs; forced to **1** under `TRUE_SUBMISSION`. Submissions are already single-pass, i.e. already at maximum variance. |
| Per-game improvements | **Closed for 12 days (F84).** The floor is stable (three games maxed every pass) and the gap is stable (four or five games score near zero every pass) — so the missing points are in games the agent never solves, which needs research, not a parameter. |
| More than one draw per day | **Impossible.** One per team per UTC day. |

**⇒ The remaining 12 draws are the remaining opportunity. Draw, do not change.**

## 5. The daily action (the entire plan)

```powershell
cd D:\kaggle\arc
kaggle competitions leaderboard -c arc-prize-2026-arc-agi-3 -d -p D:\kaggle\arc\state\lb
python work\recon.py
python work\submit_code.py ppxl16/arc-agi-3-m2-franzen-verbatim 1 "<why, in one paragraph>"
```

- Quota resets at **00:00Z**; one submission per UTC day.
- ⚠️ **The `1` in that command is the kernel VERSION, and it must stay `1`.** `submit_code.py` takes
  `<slug> <version> <message>` and sets `req.kernel_version` explicitly, so every draw we have made used the
  same pinned version — the code F85 inspected. Changing that number silently changes what is being drawn.
- ⚠️ The leaderboard must be downloaded into `arc\state\lb\` — `recon.py` reads the old file otherwise (A203).
- ⚠️ Identify ourselves by `TeamMemberUserNames` containing `ppxl16`; the team name `p pxl16` has a space
  in it, so a substring search for `ppxl` fails.
- **Do not miss a day.** Zero days of slack in 12.

## 6. What would actually change the plan

Not a notebook with a higher `bestPublicScore` — those are maxima over unknown numbers of runs (F81).
Only one thing would justify switching kernels: **evidence about a kernel's distribution**, i.e. several
draws of the same alternative under the same conditions. Until that exists, switching is a coin flip paid
for with the scarcest resource we have.
