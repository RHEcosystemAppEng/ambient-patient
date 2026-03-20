// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/// <reference types="vite/client" />

/**
 * ICE config for the browser's RTCPeerConnection.
 *
 * **Default:** load ICE from ``/api/ice_config`` (pipeline + Metered). Set ``VITE_ICE_FROM_PIPELINE=false``
 * at build time to skip that and use only static ``VITE_TURN_*`` / default STUN.
 *
 * See docs/turn-server.md
 */

function buildStaticIceServers(): RTCIceServer[] {
  const turnUrls = (import.meta.env.VITE_TURN_URLS as string | undefined)?.trim();
  const turnUser = (import.meta.env.VITE_TURN_USERNAME as string | undefined)?.trim() ?? "";
  const turnCred = (import.meta.env.VITE_TURN_PASSWORD as string | undefined)?.trim() ?? "";

  const iceServers: RTCIceServer[] = [
    { urls: "stun:stun.l.google.com:19302" },
  ];

  if (turnUrls) {
    for (const u of turnUrls.split(",")) {
      const urls = u.trim();
      if (!urls) continue;
      const lower = urls.toLowerCase();
      const isStun = lower.startsWith("stun:") || lower.startsWith("stuns:");
      if (isStun) {
        iceServers.push({ urls });
      } else {
        iceServers.push({
          urls,
          username: turnUser,
          credential: turnCred,
        });
      }
    }
  }
  return iceServers;
}

async function buildRtcConfig(): Promise<ConstructorParameters<typeof RTCPeerConnection>[0]> {
  const usePipeline = import.meta.env.VITE_ICE_FROM_PIPELINE !== "false";
  if (usePipeline) {
    try {
      const base = `${window.location.protocol}//${window.location.host}`;
      const r = await fetch(`${base}/api/ice_config`);
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}`);
      }
      const data = (await r.json()) as ConstructorParameters<typeof RTCPeerConnection>[0];
      console.info("[ambient-patient] ICE loaded from /api/ice_config (Metered via pipeline)");
      return data;
    } catch (e) {
      console.error("[ambient-patient] /api/ice_config failed, using static ICE from env", e);
    }
  }
  return { iceServers: buildStaticIceServers() };
}

/** Resolved at module load (top-level await). Must include relay servers for cross-NAT WebRTC. */
export const RTC_CONFIG: ConstructorParameters<typeof RTCPeerConnection>[0] =
  await buildRtcConfig();

const host = window.location.hostname;
const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const httpProtocol = window.location.protocol;

// Use the /api path via the OpenShift route
export const RTC_OFFER_URL = `${protocol}://${host}/api/ws`;
export const POLL_PROMPT_URL = `${httpProtocol}//${host}/api/get_prompt`;

/** Same-origin proxy for Metered (see pipeline ``GET /ice_config``). */
export const ICE_CONFIG_URL = `${httpProtocol}//${host}/api/ice_config`;

/** Same as the fetch inside ``buildRtcConfig`` — for tests or manual DevTools use. */
export async function fetchRtcConfigFromPipeline(): Promise<
  ConstructorParameters<typeof RTCPeerConnection>[0]
> {
  const r = await fetch(ICE_CONFIG_URL);
  if (!r.ok) {
    throw new Error(`ice_config HTTP ${r.status}`);
  }
  return (await r.json()) as ConstructorParameters<typeof RTCPeerConnection>[0];
}

// Set to true to use dynamic prompt mode, false for default mode
export const DYNAMIC_PROMPT = false;
