// SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: BSD 2-Clause License
//
// Override for ambient-patient: upstream waits only on `iceGatheringState === "complete"`.
// With multiple STUN/TURN servers (Metered), some browsers keep `"gathering"` for a long time
// or never flip to `"complete"` while trickle candidates are still in flight. The standard
// end-of-candidates signal is `icecandidate` with `candidate === null` — resolve on that too.
// See: https://www.w3.org/TR/webrtc/#dom-rtcpeerconnectioniceevent

export default async function waitForICEGatheringComplete(
  pc: RTCPeerConnection,
  timeoutMs = 60000
): Promise<void> {
  if (pc.iceGatheringState === "complete") return;
  console.log(
    "Waiting for ICE gathering to complete. Current state:",
    pc.iceGatheringState
  );
  return new Promise((resolve) => {
    let settled = false;
    const done = (reason: string) => {
      if (settled) return;
      settled = true;
      cleanup();
      console.log("ICE gathering wait finished:", reason);
      resolve();
    };

    const checkState = () => {
      console.log("icegatheringstatechange:", pc.iceGatheringState);
      if (pc.iceGatheringState === "complete") {
        done("iceGatheringState=complete");
      }
    };

    const onIceCandidate = (event: RTCPeerConnectionIceEvent) => {
      if (event.candidate === null) {
        done("end-of-candidates (null)");
      }
    };

    const onTimeout = () => {
      console.warn(
        `ICE gathering timed out after ${timeoutMs} ms — proceeding with candidates gathered so far`
      );
      done("timeout");
    };

    const cleanup = () => {
      pc.removeEventListener("icegatheringstatechange", checkState);
      pc.removeEventListener("icecandidate", onIceCandidate);
      clearTimeout(timeoutId);
    };

    pc.addEventListener("icegatheringstatechange", checkState);
    pc.addEventListener("icecandidate", onIceCandidate);
    const timeoutId = setTimeout(onTimeout, timeoutMs);
    checkState();
  });
}
