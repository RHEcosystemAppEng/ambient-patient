# Ambient Healthcare Agent for Patients
## Overview
An agentic healthcare front desk can assist patients and healthcare professional staff by reducing the burden of the patient intake process, structuring responses into documentation and thus allowing for more patient-clinical staff quality time. This developer example provides developers with a reference implementation of an voice agent powered by NVIDIA LLM NIM, NVIDIA RIVA ASR and TTS NIM, and NeMo Guardrails. It includes a demonstration of the agent's capabilities in a typical conversation between a patient and a healthcare clinical staff member.

## Table of Contents
- [Key Features](#key-features)
- [Target Audience](#target-audience)
- [Technical Diagram](#technical-diagram)
- [Software Components](#software-components)
- [Hardware Requirements](#hardware-requirements)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Deployment Options](#deployment-options)
- [Next Steps](#next-steps)
- [Customization](#customization)
- [License and Governing Terms](#license-and-governing-terms)
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

- **NeMo Guardrails**: Safeguards your agentic application and provides highly customizable configurations. Please see [NeMo Guardrails](https://developer.nvidia.com/nemo-guardrails) for more details.

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
#### Disk Space
The disk space required in this scenario is 302 GB.
#### GPU Requirement
Use | Service(s)| Recommended GPU* 
--- | --- | --- 
[RIVA ASR NIM](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard) | `nvidia/parakeet-ctc-1_1b-asr` |  1 x various options including L40, A100, and more (see [modelcard](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard))
[RIVA TTS NIM](https://build.nvidia.com/nvidia/magpie-tts-multilingual/modelcard) | `nvidia/magpie-tts-multilingual` | 1 x various options including L40, A100, and more (see [modelcard](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard))
[Instruct Model](https://build.nvidia.com/meta/llama-3_3-70b-instruct) for Agentic Orchestration | `llama-3.3-70b-instruct` | 2 x H100 80GB <br> or <br>4 x A100 80GB
[NemoGuard Content Safety Model](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-content-safety/modelcard) (Optional for Enabling NeMo Guardrails) | `nvidia/llama-3_1-nemoguard-8b-content-safety` | 1x options including A100, H100, L40S, A6000
[NemoGuard Topic Control Model](https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-topic-control/modelcard) (Optional for Enabling NeMo Guardrails) | `nvidia/llama-3_1-nemoguard-8b-topic-control` | 1x options including A100, H100, L40S, A6000
**Total** | Entire Ambient Healthcare Agent for Patients  | 8 x A100 80GB <br /> or other combinations of the above

*For details on optimized configurations for LLMs, please see the documentation [Supported Models for NVIDIA NIM for LLMs](https://docs.nvidia.com/nim/large-language-models/latest/supported-models.html).




## Getting Started
### Prerequisites
#### API Keys
- NVIDIA AI Enterprise developer licence required to local host NVIDIA NIM Microservices.
- [NVIDIA API Key](https://build.nvidia.com/) for access to hosted NVIDIA NIM Microservices on the public NVIDIA AI Endpoints. See [NVIDIA API Keys](./docs/api_keys.md#nvidia-api-key) for detailed steps.
- [NGC API Key](https://docs.nvidia.com/ngc/latest/ngc-private-registry-user-guide.html#ngc-api-keys) for NGC container download and resources.

#### Software

- Linux operating systems (Ubuntu 22.04 or later recommended)
- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Deployment Options
There are two options available for this Ambient Patient Developer Example, a full voice assistant interface, which we recommend to get started with, and a chatbot assistant interface, for development and testing.
#### Option A: Full Voice Assistant (Recommended)
This option deploys the complete voice-enabled patient intake application, powered by NVIDIA ace controller voice agent.
- [Deploy via Docker Compose using public NVIDIA AI Endpoints for NIMs](https://github.com/NVIDIA-AI-Blueprints/ambient-patient/blob/main/docs/docker-compose-deploy-using-public-endpoints.md). Follow this documentation for some initial quick exploration of the developer example. 
- [Deploy via Docker Compose using self hosted NIMs](https://github.com/NVIDIA-AI-Blueprints/ambient-patient/blob/main/docs/docker-compose-deploy-using-self-hosted-nims.md). Follow this documentation for production deployment.

#### Option B: Chatbot Assistant (For Development & Testing)

This option is designed for experimenting with the agent's implementation and customization using a simple text-based Gradio Chatbot, without needing to set up the full voice pipeline. For setting up the chatbot, please refer to section [2. Running the simple text Gradio UI]((https://github.com/NVIDIA-AI-Blueprints/ambient-patient/tree/main/agent#2-running-the-simple-text-gradio-ui)) in the agent/README.


## Next Steps
After experiencing the full voice assistant, and the chatbot assistant, the next steps are:
- See your LangGraph agent traces for observability in LangSmith under the “healthcare-agent-project” project, if you have set up your LangSmith API keys in [agent/vars.env](./agent/vars.env).
- View the content in the [agent/README](./agent/) as well as the [ace-controller-voice-interface/README](./ace-controller-voice-interface/).
- Customize your NeMo Guardrails configuration, your agent tools for connecting to your own APIs, and more. See the links in the next section [Customization](#customization).
- Create your own voice agent applications for your use cases.

## Customization

For customization on the RIVA ASR and TTS options, adding custom TTS IPA dictionary, and exploring other example agents other than the patient intake agent, please see the [Pipeline Customizations](./ace-controller-voice-interface/README.md#pipeline-customizations) section in the ace-controller-voice-interface/README.

For customization on the LLM model, NIM hosting options, agent, system prompt, tools definition, and NeMo Guardrails configurations, please see the document [agent/customization.md](./agent/customization.md).


## License and Governing Terms
GOVERNING TERMS: The API trial service is governed by the [NVIDIA API Trial Terms of Service](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf). The developer example software is governed by the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). Use of the NIM containers is governed by the [NVIDIA Software License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement) and [Product Specific Terms for NVIDIA AI Products](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products). Use of the ASR Parakeet CTC Riva 1.1b, Magpie TTS Multilingual, and Llama-3.3-70b-Instruct models is governed by the [NVIDIA Community Model License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-community-models-license/). Use of the Llama-3.1-Nemoguard-8b-Topic-Control, and Llama-3.1-Nemoguard-8b-Content-Safety models is governed by the [NVIDIA Open Model License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/). Use of the Ace-Controller software is governed by the [BSD 2-Clause License](https://github.com/NVIDIA/ace-controller/blob/develop-health/LICENSE). 

ADDITIONAL INFORMATION: For Llama-3.1-Nemoguard-8b-Topic-Control and Llama-3.1-Nemoguard-8b-Content-Safety, [Llama 3.1 Community License Agreement](https://www.llama.com/llama3_1/license/). For Llama-3.3-70b-Instruct, [Llama 3.3 Community License Agreement](https://www.llama.com/llama3_3/license/). Built with Llama.


## Security Considerations

- The Ambient Patient repository is shared as a reference and is provided "as is". The security in the production environment is the responsibility of the end users deploying it. When deploying in a production environment, please have security experts review any potential risks and threats; define the trust boundaries, implement logging and monitoring capabilities, secure the communication channels, integrate AuthN & AuthZ with appropriate access controls, keep the deployment up to date, ensure the containers/source code are secure and free of known vulnerabilities.
- A frontend that handles AuthN & AuthZ should be in place as missing AuthN & AuthZ could provide ungated access to customer models if directly exposed to e.g. the internet, resulting in either cost to the customer, resource exhaustion, or denial of service.
- The Ambient Patient repository doesn't require any privileged access to the system.
- The end users are responsible for ensuring the availability of their deployment.
- The end users are responsible for building the container images and keeping them up to date.
- The end users are responsible for ensuring that OSS packages used by the developer blueprint are current.
- The logs from the agent backend and UI frontend containers are printed to standard out. They can include input prompts and output completions for development purposes. The end users are advised to handle logging securely and avoid information leakage for production use cases.
- The agent backend and UI frontend containers may interact with local files for development purposes. The end users are advised to customize all file saving and uploading logic securely and avoid information leakage for production use cases.