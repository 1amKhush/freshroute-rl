# Verification record

The user story is: choose a replay or live model in the browser, observe real routing decisions, inject a fault into an isolated simulator session, inspect the resulting outcome, and compare exact-state simulator branches.

| Boundary | Evidence |
| --- | --- |
| Python simulator and learning | 32 checks pass, including reward accounting, freshness/version invariants, seeded replay, temporal-difference updates, training/save/load, Gymnasium checker, observation bounds, complete frozen DQN replay through the API, and control-policy metadata separation. |
| Release model and evidence | All 14 frozen weights hashes verify; selected model and trace hashes verify; the current simulator exactly reproduces the saved DQN replay. |
| API and simulator | Seeded API decision records equal CLI records; sessions remain isolated; episode completion, invalid requests, fault injection, export integrity, and selected-decision counterfactuals pass. |
| Browser and actual API | Nine Playwright tests pass against the production build, including real DQN inference, outage injection, same-snapshot branch rendering, and cleanup when leaving during session creation. |
| Replay interaction | Displayed action/reward values match trace data; keyboard stepping, last-record stopping, reset, invalid-file rejection, and mobile width checks pass. |
| Accessibility | Automated WCAG A/AA rules report no violations in the tested replay and live/branch views. Manual screen-reader review remains a team check. |
| Production bundle | TypeScript and Vite production build pass; fonts and default replay assets are bundled locally. |
| Animated routing | Packet geometry follows the selected actual route. Successful and stale reads return data; timeout/offline reads have no return packet. Pause/resume, automatic replay interruption, rapid seeking, next-state exclusion, local motion disable, dynamic system reduced-motion changes, and mobile width checks pass. |
| Development mode | Representative packet/pause/return and preference-change browser tests also pass against Vite with React Strict Mode. |
| Clean checkout, original release | A separate Git archive of the original release installed all 31 Python packages from the hashed locks and all 77 npm packages from the lockfile, built the app, passed all 30 Python checks, and passed all four original browser checks against its own server on port 8001. Cached downloads were reused; project environments and build outputs were created afresh. |
| Clean frontend, motion extension | A fresh temporary frontend directory installed all 82 npm packages from the updated lockfile and completed TypeScript/Vite production build with the same output hashes as the working frontend. The Python implementation and model artifacts are unchanged by this extension. |
| Training revision provenance | Recomputed source fingerprints match Q-learning commit `14c0ede` and DQN training commit `4a755e6`. |

Tested runtime: Linux, Python 3.12.14, Node.js 24.21.0, Gymnasium 1.4.0, Stable-Baselines3 2.9.0, PyTorch 2.14.1+cpu, and NumPy 2.5.4. Exact dependency hashes are in the Python locks and npm lockfile. The original Q-learning artifact was produced with Python 3.12.3 at its recorded source revision.

The restricted execution sandbox stalled the API test client's local event-loop startup and denied esbuild's postinstall binary execution in the clean checkout. Both passed when rerun with the required local execution/socket permissions; the evidence above uses those successful runs. CodeRabbit was signed out, so external CodeRabbit review was not performed. Direct code inspection and executable checks were completed.

The motion extension uses Motion 14.6.0's mini entry point and includes its MIT notice in the built static assets. The isolated engine measures 3,349 bytes gzip; after the final browser fixes, total application JavaScript is 83.54 kB gzip and CSS is 9.33 kB gzip. See [measurement details and visual semantics](visualization.md). Updated screenshots were captured from the actual application. Automated accessibility checks cover the tested views; no frame-rate benchmark, low-end-device measurement, or narrated video is claimed.

## Final refactor verification

Before editing, all 30 existing Python checks and eight browser checks passed at `591c9b7`. After consolidating decision-record formatting, replay state changes, and validation expressions, 32 Python checks and all eight expanded browser checks pass. The added Python cases cover the complete 160-decision frozen DQN replay through the API and the absence of learned-agent metadata on control-policy records. Browser cases also exercise previous/filter navigation, malformed reward values and totals, invalid action values and outcome flags, and recovery by importing a valid trace.

At seed 110000, all 32 rollout combinations (two saved learners, four scenarios, and each learner plus three controls) produce identical canonical decision records and summary metrics before and after the refactor. All 71 files under `artifacts/` retain their original hashes. The default replay screenshot at a 1600-by-1100 viewport is byte-identical. No retraining, artifact replacement, dependency changes, or simulator/algorithm changes were required.

## Final browser fixes and submission packaging

Both reported UI failures were reproduced before the fix: an extra reward-term field crashed rendering, and navigating away during session creation left the server session alive. Trace validation now requires exactly the three defined reward components. Live sessions are owned independently of React rendering, and responses arriving after unmount are deleted without stepping the simulator.

All 32 Python checks and nine production browser checks pass. The malformed-trace and delayed-session-creation cases also pass against Vite in React Strict Mode. The two regression cases failed against the preceding build and pass after the fixes. No simulator, learner, model, or saved experiment data changed.

The two-page PDF and self-contained LaTeX source are included and linked from the README. Current snapshot IDs in the commit record resolve from a fresh clone; the original revision IDs remain provenance metadata. Both history helpers were exercised in a fresh single-branch clone without the original commit objects. The reconstruction helper preserves snapshot trees and original provenance, and the editor preserves the original branch, staged work, and untracked files. Training-source fingerprints were recomputed successfully from snapshots `14c0ede` and `4a755e6`.

## Re-run

```bash
.venv/bin/python -m unittest discover -s tests -v
node scripts/sync-demo.mjs
npm --prefix web run build
.venv/bin/python -m freshroute serve
```

With the server running in a separate terminal:

```bash
LAB_URL=http://127.0.0.1:8000 npm --prefix web run test:e2e
```

The saved study is a fixed-budget simulator experiment. Passing application checks does not establish a production database performance or consistency guarantee. Team attribution, instructor submission, and narrated presentation are not automated by these checks.
