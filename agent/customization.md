# Customization of the Healthcare Agents

## Table of Contents
- [Agent LLM](#agent-llm)
    - [LLM Model](#llm-model)
    - [LLM NIM Hosting Options](#llm-nim-hosting-options)
- [Agent Choice](#agent-choice)
    - [Example Agents](#example-agents)
    - [Switching to a Different Agent in Voice UI](#switching-to-a-different-agent-in-voice-ui)
    - [Create Your Own Agent](#create-your-own-agent)
- [Agent System Prompt](#agent-system-prompt)
- [Agent Tools](#agent-tools)
- [NeMo Guardrails Usage](#nemo-guardrails-usage)
    - [Example 1 patient-intake-basic-input](#1-patient-intake-basic-input)
    - [Example 2 patient-intake-input-output](#2-patient-intake-input-output)
    - [Example 3 patient-intake-nemoguard](#3-patient-intake-nemoguard)
    - [Example 4 patient-intake-nemoguard-self-hosted-nim](#4-patient-intake-nemoguard-self-hosted-nim)
    - [Example 5 patient-intake-nemoguard-response-customization](#5-patient-intake-nemoguard-response-customization)
    - [Customize the configuration for your use case](#6-customize-the-configuration-for-your-use-case)

## Agent LLM

### LLM Model
You can experiment with other LLMs available on build.nvidia.com by changing the `AGENT_LLM_MODEL` values in [vars.env](./vars.env), for passing into `ChatNVIDIA` in the Python files in the directory [`graph_definitions/`](./graph_definitions/).

As seen in [graph definitions](./graph_definitions/):
```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA
assistant_llm = ChatNVIDIA(model=llm_model, ...)
```

### LLM NIM Hosting Options
If instead of calling NVIDIA AI Endpoints with an API key, you would like to host your own LLM NIM instance, you could utilize the `agent-instruct-llm` service in the [docker-compose.yaml](./docker-compose.yaml) file. 

If you'd like to host the LLM NIM on a seperate server, please refer to the [Docker tab of the LLM NIM](https://build.nvidia.com/meta/llama-3_1-70b-instruct?snippet_tab=Docker) on how to host, and changed the `AGENT_LLM_BASE_URL` parameter in [vars.env](./vars.env) to [point to your own instance](https://python.langchain.com/docs/integrations/chat/nvidia_ai_endpoints/#working-with-nvidia-nims) when specifying `ChatNVIDIA` in the Python files in the directory [`graph_definitions/`](./graph_definitions/). For the hardware configuration of self hosting the LLM, please refer to the [documentation for LLM support matrix](https://docs.nvidia.com/nim/large-language-models/latest/support-matrix.html).


## Agent Choice
### Example Agents 
We have created 4 example agents in this directory:
- [Patient intake agent](./graph_definitions/graph_patient_intake_only.py): follows the system prompt for a list of info fields to gather the patient intake info, and when ready, utilizes a tool to save the patient intake info. The json files will be saved to the directory `./app_output_files`.
- [Appointment making agent](./graph_definitions/graph_appointment_making_only.py): helps look up available appointment times in sqlite based on the intended appointment type and dates, and write the user's intended booking time into sqlite. The example sqlite file containing available appointment times is located at [./sample_db/test_db.sqlite](./sample_db/test_db.sqlite) The temporarily modified sqlite fille will be in directory `.sample_db/test_db_tmp_copy.sqlite`.

- [Medication lookup agent](./graph_definitions/graph_medication_lookup_only.py): able to retrieve the date of birth and current medications of a patient given the patient id, and helps look up medication instructions.

- [Multi assistant full agent](./graph_definitions/graph.py): combines all 3 agents above, with one main orchestrating assistant and 3 specialized assistants.

### Switching to a Different Agent in Voice UI

The ambient-patient repo serves the patient intake agent in [agent/](../agent/graph_definitions/graph_patient_intake_only.py) in the FastAPI app server, which connects to the ACE Controller's RIVA ASR and TTS NIMs as well as the voice UI. To use a different agent in the voice interaction, for example the appointment making agent, you need to update the Docker Compose configuration. Follow these steps:

- In the `docker-compose.yml` file, find the `app-server` service section.
- Modify the entrypoint portion to call the appointment agent for example: 

  ```yaml
  entrypoint: python3 chain_server/chain_server.py --assistant appointment --port 8081
  ```
  See [README](./README.md) on the available agents, as well as [details on the FastAPI app server](./README.md#details-on-the-fastapi-app-server).

### Create Your Own Agent
To customize for your own agentic LLM in LangGraph with your own tools, the [LangGraph tutorial on customer support](https://langchain-ai.github.io/langgraph/tutorials/customer-support/customer-support/) is helpful, where you'll find detailed explanations and steps of creating tools and agentic LLM in LangGraph. Afterwards, you can create your own file similar to the graph files in [`graph_definitions/`](./graph_definitions/) which can connect to the simple text Gradio UI, or can be imported by the [FastAPI server](./chain_server/chain_server.py).

## Agent System Prompt

Please refer to the system prompt examples in [graph_definitions/system_prompts/](./graph_definitions/system_prompts/) for how we can use a system prompt to guide the agent in its behavior interacting with the user. 


## Agent Tools

Please refer to the tools defined in [graph_definitions/graph_patient_intake_only.py](./graph_definitions/graph_patient_intake_only.py), [graph_definitions/graph_appointment_making_only.py](./graph_definitions/graph_appointment_making_only.py), [graph_definitions/graph_medication_lookup_only.py](./graph_definitions/graph_medication_lookup_only.py), [graph.py](./graph_definitions/graph.py) as examples. The introductory [LangGraph tutorial](https://langchain-ai.github.io/langgraph/tutorials/get-started/2-add-tools/#2-configure-your-environment) on tool use could be helpful as well. 

## NeMo Guardrails Usage
[NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/latest/index.html) enables developers building LLM-based applications to easily add programmable guardrails between the application code and the LLM. 

We enable the optional use of NeMo Guardrails in this healthcare agent for patients repo, and have created the following example configurations inside the `nmgr-config-store` directory. For the official documentation on the NeMo Guardrails configuration, please see https://docs.nvidia.com/nemo/guardrails/latest/user-guides/configuration-guide/index.html.

### 1. `patient-intake-basic-input`
In this directory, we have the simplest guardrail around the user input. `config.yml` defines the llm to use in guardrails and a single flow for the input: `self check input`. `prompts.yml` defines the llm prompt for the flow `self check input` that will be passed into the guardrails llm specified in `config.yml`.

This example utilizes the public NVIDIA AI Endpoints for inference for the LLMs enabling NeMo Guardrails.

### 2. `patient-intake-input-output`
Adding on top of `patient-intake-basic-input`, in this directory we add the output rails as well in `config.yml` and `prompts.yml`, with more comprehensive prompts for both input and output in the patient intake scenario. Additionally, in the file `config.co`, we override the default response messages when guardrails needs to block the input / output.

This example utilizes the public NVIDIA AI Endpoints for inference for the LLMs enabling NeMo Guardrails.

### 3. `patient-intake-nemoguard`
So far, we have been utilizing generic LLMs in the guardrails. Next, we can look into utilizing the [NVIDIA NemoGuard](https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html#nvidia-models) content safety and topic safety models. 

This example utilizes the public NVIDIA AI Endpoints for inference for the LLMs enabling NeMo Guardrails.

### 4. `patient-intake-nemoguard-self-hosted-nim`
This example has the same content as the `patient-intake-nemoguard` example, but instead of utilizing the public NVIDIA AI Endpoints, it assumes self hosting of the NemoGuard NIMs enabling NeMo Guardrails. The only difference between this config example and `patient-intake-nemoguard` is in the `models:` section in `config.yml`.

### 5. `patient-intake-nemoguard-response-customization` 
The `config.co` file defines logic to handle the different unsafe categories returned by the [output parser](https://github.com/NVIDIA-NeMo/Guardrails/blob/develop/nemoguardrails/llm/output_parsers.py) that parses the raw model outputs. We are able to have different customized response messages for different unsafe categories, such as "I'm afraid I won't be able to answer that for privacy reasons.", "I'm afraid I won't be able to give medical advice or diagnosis.". The helper function in `actions.py` is utilized in `config.co`, and you can define your own Python helper functions when needed, by defining them within the config directory without needing to change anything in the NeMo Guardrails SDK.


### 6. Customize the configuration for your use case

If you're exploring the other agents such as the appointment making agent or medication lookup agent, please create your own configuration for these agents as the examples are meant for the patient intake scenario.


There are many more options for configuring guardrails. Please visit https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html. There are options for fact checking, hallucination detection, community models and libraries, using the NemoGuard jailbreaking model, etc.