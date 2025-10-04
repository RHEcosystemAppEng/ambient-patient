# Ambient Healthcare Agent for Patients
## Overview

## Table of Contents
- [Key Features](#key-features)
- [Target Audience](#target-audience)
- [Technical Diagram](#technical-diagram)
- [Software Components](#software-components)
- [Hardware Requirements](#hardware-requirements)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Deployment Options](#deployment-options)
- [Customization](#customization)
- [License](#license)
- [Security Considerations](#security-considerations)

## Key Features
- **Patient Intake Agent**: An agent follows a system prompt script to guide a patient through the intake process at a clinic.
- **Other agent examples**: Additional examples of an appointment making agent, medication information agent, and a full agent that combines the 3 specialized agents.
- **NeMo Guardrails**: utilizing NVIDIA NeMo Guardrails for added safety to the agent's interactions with the patients.
- **Interaction via Voice or Chatbot**: voice interactions powered by NVIDIA Riva ASR and TTS  orchestrated by NVIDIA ACE Controller SDK. A text-based chatbot is also available as a Gradio UI.


## Target Audience
- Developers: This developer example serves as a reference architecture for teams to create their own healthcare agents that interact with patients.
## Technical Diagram
![](./ace-controller-voice-interface/assets/AmbientPatient.png)
## Software Components
The Ambient Patient developer example provides the following software components:

- **Agents**: Implemented in LangGraph, these agents provide an example implementation of utilizing LLMs with tool calling capabilities, creating tools for various healthcare purposes, utilizing the system prompt of the agent to guide agent behavior, and optionally adding guardrails to the LLM. We will mainly focus on the patient intake agent, but there are three other agents available as well. Please see [agent/](./agent/) for more details. The agents are implemented in the graph_*.py files in [agent/graph_definitions/](./agent/graph_definitions). 

- **NeMo Guardrails**: 

- **Voice UI Frontend**: The voice UI powered by the **NVIDIA ACE Controller SDK** utilizes WebRTC for connection. In the technical diagram, this includes the Web Client component, ACE Controller component, and the RIVA ASR and TTS NIMs. Please see [ace-controller-voice-interface/](./ace-controller-voice-interface/) for more details.

- **FastAPI Server**: The agents are served to the voice UI via a FastAPI server. Please see [agent/](./agent/chain_server/) for more details.

The Ambient Patient developer example has the following software dependencies:
- [NVIDIA NeMo Guardrails](https://developer.nvidia.com/nemo-guardrails)
- [NVIDIA ACE Controller SDK](https://github.com/NVIDIA/ace-controller/tree/develop)
- [NVIDIA RIVA](https://www.nvidia.com/en-us/ai-data-science/products/riva/) for automatic speech recognition and text to speech capabilities in the voice UI. 
- [NVIDIA NIM](https://developer.nvidia.com/nim) for powering the agent LLM, NeMo Guardrails LLM, and RIVA ASR and TTS.
    - [meta/llama-3.3-70b-instruct](https://build.nvidia.com/meta/llama-3_3-70b-instruct)
    - [nvidia/llama-3.1-nemoguard-8b-content-safety](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-content-safety)
    - [nvidia/llama-3.1-nemoguard-8b-topic-control](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-topic-control)
    - [nvidia/magpie-tts-multilingual](https://build.nvidia.com/nvidia/magpie-tts-multilingual)
    - [nvidia/parakeet-ctc-1.1b-asr](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr)

## Hardware Requirements

### Scenario 1:  For running with hosted NVIDIA NIM Microservices

This blueprint can be run entirely with hosted NVIDIA NIM Microservices without local NIM deployments. See [https://build.nvidia.com/](https://build.nvidia.com/) for details on each NIM. For this case, no GPU is required.

While it can be run without local NIM deployments, we recommend deploying the RIVA ASR and TTS NIMs locally. For this case, please see the modelcards linked below for the GPU requirement.

### Scenario 2: For running all services locally 

Use | Service(s)| Recommended GPU* 
--- | --- | --- 
[RIVA ASR NIM](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard) | `nvidia/parakeet-ctc-1_1b-asr` |  1 x various options including L40, A100, and more (see [modelcard]((https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard)))
[RIVA TTS NIM](https://build.nvidia.com/nvidia/magpie-tts-multilingual/modelcard) | `nvidia/magpie-tts-multilingual` | 1 x various options including L40, A100, and more (see [modelcard]((https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard))) 
Instruct Model for Agentic Orchestration | `llama-3.3-70b-instruct` | 2 x H100 80GB <br /> or <br />4 x A100 80GB
[NemoGuard Content Safety Model](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-content-safety/modelcard) (Optional for Enabling NeMo Guardrails) | `nvidia/llama-3_1-nemoguard-8b-content-safety` | 1x options including A100, H100, L40S, A6000
[NemoGuard Topic Control Model](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-topic-control/modelcard) (Optional for Enabling NeMo Guardrails) | `nvidia/llama-3_1-nemoguard-8b-topic-control` | 1x options including A100, H100, L40S, A6000
**Total** | Entire Ambient Healthcare Agent for Patients  | 8 x A100 80GB <br /> or other combinations of the above

*For details on optimized configurations for LLMs, please see the documentation [Supported Models for NVIDIA NIM for LLMs](https://docs.nvidia.com/nim/large-language-models/latest/supported-models.html).

## Getting Started
### Prerequisites
- NVIDIA AI Enterprise developer licence required to local host NVIDIA NIM Microservices.
- [NVIDIA API Key](https://build.nvidia.com/) for access to hosted NVIDIA NIM Microservices on the public NVIDIA AI Endpoints.
- [NGC API Key](https://docs.nvidia.com/ngc/latest/ngc-private-registry-user-guide.html#ngc-api-keys) for NGC container download and resources.

### Deployment Options
- [Deploy via Docker Compose using public NVIDIA AI Endpoints for NIMs](./docs/docker-compose-deploy-using-public-endpoints.md)
- [Deploy via Docker Compose using self hosted NIMs](./docs/docker-compose-deploy-using-self-hosted-nims.md)

## Customization

## License

## Security Considerations