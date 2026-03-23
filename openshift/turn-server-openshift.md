# TURN, WebRTC, and Metered on OpenShift

This document supplements [`docs/turn-server.md`](../docs/turn-server.md), which covers coturn, Brev, and local Docker Compose. **For deploying the voice stack on OpenShift with this fork**, read this file.

## Layout: base tree vs overlay

- **`ace-controller-voice-interface/`** — upstream-style NVIDIA blueprint files (e.g. stock `config.ts`, shorter `Dockerfile-webrtc-ui`).
- **`openshift/override/ace-controller-voice-interface/`** — fork customizations (Metered, `/api` routes, pipeline ICE, hooks, patches).
- **`openshift/build-images.sh`** merges base + overlay (overlay wins on path conflicts) before `oc start-build`. **Cluster images use the merged result**, not the stock files alone.

WebRTC needs **TURN on both sides**: the Python peer (`pipeline-patient.py` in the overlay) and the **browser** (via `RTC_CONFIG` in overlay `config.ts`).

## 1. TURN service

Run coturn or another TURN service reachable from both the cluster and user browsers. Expose UDP **3478** (and your relay port range, e.g. **51000–51010**).

## 2. Helm deploy and environment

Configure the same TURN URL and credentials the browser will use (see `openshift/ambient-patient/values.yaml` under `aceControllerPipeline`):

- `turnServerUrl` — e.g. `turn:turn.example.com:3478`
- `turnUsername` / `turnPassword`

**`openshift/deploy-app.sh`** reads **`TURN_SERVER_URL`**, **`TURN_USERNAME`**, **`TURN_PASSWORD`** from the **current shell environment** (it does not read files by itself). Either export them, or load your usual file then deploy:

```bash
export TURN_SERVER_URL='turn:turn.example.com:3478'
export TURN_USERNAME='...'
export TURN_PASSWORD='...'
./openshift/deploy-app.sh
```

```bash
set -a && source ace-controller-voice-interface/ace_controller.env && set +a && ./openshift/deploy-app.sh
```

These map to `TURN_SERVER_URL`, `TURN_USERNAME`, `TURN_PASSWORD` on the ace-controller-pipeline pod. Verify with:

`oc exec deploy/<release>-ace-controller-pipeline -n "$NAMESPACE" -- env | grep '^TURN_'`

**Optional:** create **`openshift/turn-overrides.yaml`** — merged by `deploy-app.sh` if present (gitignored; do not commit secrets).

## 3. Rebuild the voice UI image

Match Vite build args so the **browser** embeds the same TURN in `RTC_CONFIG` when needed:

```bash
export VITE_TURN_URLS='turn:turn.example.com:3478'
export VITE_TURN_USERNAME='...'
export VITE_TURN_PASSWORD='...'
./openshift/build-images.sh ace-controller-ui
oc rollout restart deployment -l app.kubernetes.io/component=ui-app -n "${NAMESPACE:-ambient-patient}"
```

The UI Dockerfile is **`openshift/override/ace-controller-voice-interface/Dockerfile-webrtc-ui`** (merged into the build context). It passes **`VITE_*`** into `npm run build`.

## 4. Firewall / NetworkPolicy

Allow **UDP** from clients to the TURN relay ports and from pods to TURN.

## Routes and WebSocket

The OpenShift Route for **`/api/ws`** sets long WebSocket timeouts (`haproxy.router.openshift.io/timeout-tunnel`). The overlay pipeline enables optional WebSocket ping settings where applicable for idle proxies.

The UI Docker build runs **`patch-webrtc-vite.cjs`** under **`openshift/override/ace-controller-voice-interface/`** so `vite.config.ts` gets **`build.target: "esnext"`** — required because **`config.ts` uses top-level await** to load **`/api/ice_config`**. If you build the webrtc UI outside the OpenShift image build, run `node patch-webrtc-vite.cjs` in a merged tree with the same layout `build-images.sh` produces, or set the same `build.target` in Vite.

The upstream **`waitForICEGatheringComplete`** only watches **`iceGatheringState === "complete"`**. With **TURN**, some browsers stay in **`gathering`** for a long time; completion is also signaled by an **`icecandidate`** event with **`candidate === null`**. This fork **overrides** `waitForICEGatheringComplete.ts` to resolve on **either** signal, with a **60 s** safety timeout.

### Python peer (aioice) and Metered

The browser loads ICE from **`GET /api/ice_config`** (Metered REST). The pipeline’s **Python** WebRTC stack (aioice) must use the **same** ephemeral credentials as the browser’s `RTCPeerConnection`. A **second** Metered REST call when the WebSocket opens can return **different** short-lived usernames/passwords, which often surfaces as **STUN 401** / **CHANNEL_BIND** errors in aioice even though ICE may still connect intermittently.

This fork’s **webrtc UI** sends **`iceServers`** on the first **`/api/ws`** message (same array the page used for the offer). The pipeline **prefers** that payload and falls back to Metered REST or static **`TURN_*`**. For the **Python** peer only, entries are merged by `(username, credential)`, non-TURN URLs are dropped, then **one** UDP **`turn:`** URL per group is chosen when possible — aioice often returns STUN **401** on **`CHANNEL_BIND`** if it is given many Metered endpoints at once (mixed UDP/TLS).

Rebuild the **ace-controller-ui** image after changing **`openshift/override/ace-controller-voice-interface/hooks/use-pipecat-webrtc.ts`** or **`Dockerfile-webrtc-ui`**.

**aioice still logs STUN 401 on `CHANNEL_BIND`:** try, on the **pipeline** pod only:

- `PIPELINE_AIOICE_PREFER=tls` — use `turns:` / TCP if UDP to Metered is blocked.
- `PIPELINE_AIOICE_MAX_TURN_GROUPS=1` (default) — only the first TURN credential group (Metered sometimes returns several).
- `PIPELINE_ICE_USE_STATIC_ONLY=true` — ignore Metered REST for the **Python** peer and use static **`TURN_*`**. The browser can still use **`/api/ice_config`**. Use when Metered ephemeral REST and aioice do not agree.

### Metered REST API (API key server-side)

Do **not** embed your Metered API key in the browser bundle. The pipeline exposes **`GET /ice_config`**, which proxies to Metered using **`METERED_TURN_API_KEY`** (and optional **`METERED_CREDENTIALS_URL`**, default `https://fax.metered.live/api/v1/turn/credentials`). Set these via Helm (`aceControllerPipeline.meteredTurnApiKey`) or **`openshift/deploy-app.sh`** with **`METERED_TURN_API_KEY`**.

The response is always `{ "iceServers": [ ... ] }`.

**UI build:** by default the Dockerfile sets **`VITE_ICE_FROM_PIPELINE=true`**, which bakes in a **top-level await** in `config.ts` so `RTC_CONFIG` is filled from **`/api/ice_config`** before the app runs. Pass **`VITE_ICE_FROM_PIPELINE=false`** at build time to use only static **`VITE_TURN_*`**. If both pipeline ICE and static TURN are unavailable, the browser may only gather **`typ host`** candidates (see DevTools) and ICE will fail across NAT.

Alternatively, bake static Metered URLs with **`VITE_TURN_URLS`** + username/password at build time.

### Troubleshooting: DevTools shows only `host` ICE candidates

That means **no STUN reflexive (`srflx`) and no TURN relay** were used. Fix: ensure **`METERED_TURN_API_KEY`** on the pipeline and a UI build with default pipeline ICE (or full **`VITE_TURN_*`** if you set **`VITE_ICE_FROM_PIPELINE=false`**), then hard-refresh the page.
