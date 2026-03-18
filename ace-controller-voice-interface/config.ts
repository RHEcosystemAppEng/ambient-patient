// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

export const RTC_CONFIG = {};

const host = window.location.hostname;
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const httpProtocol = window.location.protocol;

// Use the /api path via the OpenShift route
export const RTC_OFFER_URL = `${protocol}://${host}/api/ws`;
export const POLL_PROMPT_URL = `${httpProtocol}//${host}/api/get_prompt`;

// Set to true to use dynamic prompt mode, false for default mode
export const DYNAMIC_PROMPT = false;