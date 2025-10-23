# Agentic Healthcare Front Desk

![](./images/architecture_diagram.png)

An agentic healthcare front desk can assist patients and the healthcare professionals in various scanarios: it can assist with the new patient intake process, going over each of the fields in a new patient form with the patients; it can assist with the appointment scheduling process, looking up available appointments and booking them for patients after conversing with the patient to find out their needs; it can help look up the patient's medications and general information on the medications, and more.

The front desk assistant contains agentic LLM NIM with tools calling capabilities implemented in the LangGraph framework.

Follow along this repository to see how you can create your own Healthcare front desk agent.

We will offer two options for interacting with the agentic healthcare front desk: with a text-based Gradio UI or with a voice-based web interface powered by [NVIDIA ace-controller](https://github.com/NVIDIA/ace-controller).


> [!NOTE]  
> If you're utilizing the NVIDIA AI Endpoints for the LLM, which is the default for this repo, latency can vary depending on the traffic to the endpoints. 



## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Run Instructions](#run-instructions)
4. [Customization](#customization)
5. [Details on the FastAPI App Server](#details-on-the-fastapi-app-server)


## Introduction
In this directory, we demonstrate the following:
* A customer care agent in Langgraph that has three specialist assistants: patient intake, medication assistance, and appointment making, with corresponding tools.
* A customer care agent in Langgraph for patient intake only. 
* A customer care agent in Langgraph for appointment making only.
* A customer care agent in Langgraph for medication lookup only.
* A Gradio based UI that allows us to use voice or typing in text to converse with any of the four agents.
* A FastAPI server that serves the agent graph.

The agentic tool calling capability in each of the customer care assistants is powered by LLM NIMs - NVIDIA Inference Microservices. With the agentic capability, you can write your own tools to be utilized by LLMs.

More details on the four example agents:
- [Patient intake agent](./graph_definitions/graph_patient_intake_only.py): follows the system prompt for a list of info fields to gather the patient intake info, and when ready, utilizes a tool to save the patient intake info. The json files will be saved to the directory `./app_output_files`.
- [Appointment making agent](./graph_definitions/graph_appointment_making_only.py): helps look up available appointment times in sqlite based on the intended appointment type and dates, and write the user's intended booking time into sqlite. The example sqlite file containing available appointment times is located at [./sample_db/test_db.sqlite](./sample_db/test_db.sqlite) The temporarily modified sqlite fille will be in directory `.sample_db/test_db_tmp_copy.sqlite`.

- [Medication lookup agent](./graph_definitions/graph_medication_lookup_only.py): able to retrieve the date of birth and current medications of a patient given the patient id, and helps look up medication instructions.

- [Multi assistant full agent](./graph_definitions/graph.py): combines all 3 agents above, with one main orchestrating assistant and 3 specialized assistants.

## Prerequisites
### Hardware 
There are no GPU requirements if you choose to utilize the public NVIDIA AI Endpoints for the NIMs.

For self hosting the NIMs for the agent LLM as well as optionally NeMo Guardrails, please refer to the [Hardware Requirements section of the Ambient Patient README](../README.md#hardware-requirements) on the GPU requirements for each NIM.

### API Keys
- NVIDIA AI Enterprise developer licence required to local host NVIDIA NIM Microservices.
- [NVIDIA API Key](https://build.nvidia.com/) for access to hosted NVIDIA NIM Microservices on the public NVIDIA AI Endpoints. See [NVIDIA API Keys](../docs/api_keys.md#nvidia-api-key) for detailed steps.
- [NGC API Key](https://docs.nvidia.com/ngc/latest/ngc-private-registry-user-guide.html#ngc-api-keys) for NGC container download and resources.


### Software

- Linux operating systems (Ubuntu 22.04 or later recommended)
- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)



## Run Instructions

As illustrated in the diagrams in the beginning, in this repo, we could run two types of applications, one is a FastAPI server that connects to the voice UI powered by ACE Controller, the other one is a simple text-based Gradio UI for the healthcare agent. 

To run the first type with the voice UI, please refer to the instruction in the [ambient-patient/README](../README.md#deployment-options). Read more on the FastAPI server in the [Details on the FastAPI App Server](#details-on-the-fastapi-app-server) section.

To run the second type with a text-based Gradio UI for easy experimentation, please continue reading this section. 

Now we will be going over how to bring up the agents with a text chatbot in Gradio. 


### 1. Edit the [vars.env](./vars.env) file to set environment variables
It is required to configure each one of these environment variables before proceeding to run the applications.
| Environment Variable | Description | Required/Optional |
|---|---|---|
| `NVIDIA_API_KEY` | Please enter your own. This is to access the hosted models on the public NVIDIA AI Endpoints. See [NVIDIA API Keys](../docs/api_keys.md#nvidia-api-key) for generating one.| Required |
| `NGC_API_KEY` | Please enter your own. This is to pull the relevant NIMs, docker images, and resources from NGC. See [NGC doc](https://docs.nvidia.com/ngc/latest/ngc-private-registry-user-guide.html#ngc-api-keys) on generating one. | Required |
| `TAVILY_API_KEY` | The Tavily key is only required if you want to run the full graph or the medication lookup graph. Get your API Key from the [Tavily website](https://app.tavily.com/). This is used in the tool named `medication_instruction_search_tool` in [`graph.py`](./graph_definitions/graph.py) or [`graph_medication_lookup_only.py`](./graph_definitions/graph_medication_lookup_only.py). </br> If you are not running these two applications, leave the Tavily key empty. | Optional |
|`AGENT_LLM_BASE_URL` | `AGENT_LLM_BASE_URL` is set to the default value of `"https://integrate.api.nvidia.com/v1"`, which points to the public NVIDIA AI Endpoints. If intending to self host the NIM by spinning up the `agent-instruct-llm` service in docker compose, set to `http://agent-instruct-llm:8050/v1`. This environment variable is used in the `ChatNVIDIA` API for defining the LLM to be used. | Required|
| `AGENT_LLM_MODEL`| This is set to the default value of `"meta/llama-3.3-70b-instruct"`. This environment variable is used in the `ChatNVIDIA` API for defining the LLM to be used. You can get a list of models that are known to support tool calling with, `tool_models = [model for model in ChatNVIDIA.get_available_models() if model.supports_tools]` | Required|
|`LOG_LEVEL` | `LOG_LEVEL` indicates the level of logging intended. If set to `WARNING`, we will only see the most essential human and agent message logs. If set to `INFO` or `DEBUG`, we will see details logs of human and agent messages, as well as details logs of NeMo Guardrails. | Required |
|`NEMO_GUARDRAILS_CONFIG_PATH` | If `NEMO_GUARDRAILS_CONFIG_PATH` is not set or left empty, that implies the agent(s) will not be utilizing NeMo Guardrails. If you would like to utilize NeMo Guardrails for safeguarding your application, you can point to the path where your config files are. We provide a few examples for the patient intake scenario under the directory [nmgr-config-store](./nmgr-config-store/). `nmgr-config-store/patient-intake-basic-input`, `nmgr-config-store/patient-intake-input-output` and `nmgr-config-store/patient-intake-nemoguard` utilize public NVIDIA AI Endpoint for the LLMs used for guardrails; `nmgr-config-store/patient-intake-nemoguard-self-hosted-nim` assumes local self hosted NemoGuard NIMs. </br> If you're exploring the other agents such as the appointment making agent or medication lookup agent, please create your own configuration for these agents, as the examples are only meant for the patient intake scenario.| Optional|
| LangSmith configuration: `LANGSMITH_TRACING`, `LANGSMITH_ENDPOINT`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT`| These four environment variables are entirely optional. They enable us to view the LangGraph application tracing in [Langsmith](https://smith.langchain.com/). If you would like to utilize LangSmith, please configure them for your own account. </br> Otherwise, feel free to remove them or leave them empty. | Optional
|`TIMEZONE` | This is utilized in the patient intake agent or full agent, for saving the patient info to a json file with a timestamp in the filename. Change the default value of "America/Los_Angeles" if you would like the timestamp to be in another timezone. | Required. </br> Suggest to keep the default value unless there's a need to modify. |
|`APP_OUTPUT_DIR` | This is utilized in the patient intake agent or full agent, for specifying the directory where the patient info will be saved to a json file. This directory will be created when the tool is called. If you change from the default value of "app_output_files", please also change in the [docker-compose.yaml](./docker-compose.yaml) volume mounting options for each service.| Required. </br> Suggest to keep the default value unless there's a need to modify.|


### 2. Running the simple text Gradio UI
To spin up a simple Gradio based web UI that allows us to converse with one of the agents via a chatbot, run one of the following services. Before running the services, please first read through the following info in `Automatic Reloading of Gradio UI Applications` and `Agent Memory Management`.

#### Automatic Reloading of Gradio UI Applications
During development, it's often that we will need to reiterate on the system prompt, guardrails configuration, and environment variables for controlling application settings. For the purposes of quick iterations, we have enabled reloading of the uvicorn applications that are run inside the `patient-intake-ui`, `appointment-making-ui`, `full-agent-ui`, and `medication-lookup-ui` containers so we won't need to docker compose down and docker compose up again during these reiterations. The directories listed below are watched so that if any file of the types `"*.env", "*.txt", "*.co", "*.yml", "*.py"` changes within these directories/files, excluding any `__pycache__` directories, the Gradio UI applications restarts after the web browser tab is closed. 
```sh
graph_definitions/
nmgr-config-store/
utils/
vars.env
```

After you have done `docker compose up <container name>`, during your development, after changing a file in the directories above, you will need to **close** the web browser tab, and **open a new tab** to let the application reload, which takes about 10 seconds. Simply refreshing the browser tab will **not enable** the app reload.

#### Agent Memory Management
The agents has a persistent memory throughout the interaction with the user, utilizing `langgraph.checkpoint.memory.MemorySaver`, and will have a memory reset erasing all messages if any of the phrases "restart", "start over", "a new session" is mentioned by the user in the conversation. 

If in the Gradio chatbot, the memory also starts fresh when the button "Clear Chat Memory" is clicked if you launched the Gradio chatbot UI by spinning up any of the `*-ui` containers, or when the application automatically reloads due to a file change.


##### 2.1 The patient intake agent 
Run the patient intake only agent.

```sh
# build and run the container, add -d for detaching from logs
docker compose up --build patient-intake-ui
# docker compose up --build -d patient-intake-ui
```
See [automatic reloading of Gradio UI application](#automatic-reloading-of-gradio-ui-applications) for how the app reloads after file changes.

Next, find the application by going to `http://<your-machine-ip>:7861/patient-intake` in your browser.


Note this will be running on port 7861 by default. If you need to run on a different port, modify the [`docker-compose.yaml`](./docker-compose.yaml) file's `patient-intake-ui` section and replace all mentions of 7861 with your own port number.



[Launch the web UI](#25-launch-the-web-ui) on your Chrome browser, you should see this interface:
![](./images/example_ui.png)

To bring down the patient intake UI:
```sh
docker compose down patient-intake-ui
```


##### 2.2 The appointment making agent 
Run the appointment making only agent.
```sh
# build and run the container, add -d for detaching from logs
docker compose up --build appointment-making-ui
# docker compose up --build -d appointment-making-ui
```

See [automatic reloading of Gradio UI application](#automatic-reloading-of-gradio-ui-applications) for how the app reloads after file changes.

Next, find the application by going to `http://<your-machine-ip>:7861/appointment-making` in your browser.

Note this will be running on port 7861 by default. If you need to run on a different port, modify the [`docker-compose.yaml`](./docker-compose.yaml) file's `appointment-making-ui` section and replace all mentions of 7861 with your own port number.

[Launch the web UI](#25-launch-the-web-ui) on your Chrome browser, you should see the same web interface as above.

To bring down the appointment making UI:
```sh
docker compose down appointment-making-ui
```

##### 2.3 The full agent 
Run the full agent comprising of three specialist agents.
```sh
# build and run the container, add -d for detaching from logs
docker compose up --build full-agent-ui
# docker compose up --build -d full-agent-ui
```

See [automatic reloading of Gradio UI application](#automatic-reloading-of-gradio-ui-applications) for how the app reloads after file changes.

Next, find the application by going to `http://<your-machine-ip>:7861/full-assistant` in your browser.


Note this will be running on port 7861 by default. If you need to run on a different port, modify the [`docker-compose.yaml`](./docker-compose.yaml) file's `full-agent-ui` section and replace all mentions of 7861 with your own port number.

[Launch the web UI](#25-launch-the-web-ui) on your Chrome browser, you should see the same web interface as above.

To bring down the full agent UI:
```sh
docker compose down full-agent-ui
```

##### 2.4 The medication lookup agent 
Run the medication lookup only agent.


```sh
# build and run the container, add -d for detaching from logs
docker compose up --build medication-lookup-ui
# docker compose up --build -d medication-lookup-ui
```

See [automatic reloading of Gradio UI application](#automatic-reloading-of-gradio-ui-applications) for how the app reloads after file changes.

Next, find the application by going to `http://<your-machine-ip>:7861/medication-lookup` in your browser.


Note this will be running on port 7861 by default. If you need to run on a different port, modify the [`docker-compose.yaml`](./docker-compose.yaml) file's `medication-lookup-ui` section and replace all mentions of 7861 with your own port number.


To bring down the medication lookup UI:
```sh
docker compose down medication-lookup-ui
```



## Customization
Please refer to [customization.md](./customization.md) on how to customize your agent, LLM, system prompt, tools, and NeMo Guardrails configurations.

## Details on the FastAPI App Server
### Serving Via FastAPI

In [ambient-patients](../), the FastAPI server is used for connecting to the voice UI powered by NVIDIA ACE Controller and RIVA speech NIMs.

We can serve any one of the agents via a FastAPI server for connection to any other compatible services. 


### Automatic Reloading of FastAPI Application
During development, it's often that we will need to reiterate on the python files, system prompt, guardrails configuration, and environment variables for controlling application settings. For the purposes of quick iterations, we have enabled reloading of the uvicorn applications for the `app-server` so we won't need to docker compose down and docker compose up again during these reiterations. The directories listed below are watched so that if any file of the types `"*.env", "*.txt", "*.co", "*.yml", "*.py"` changes within these directories/files, excluding any `__pycache__` directories, the FastAPI server application restarts. 
```sh
graph_definitions/
chain_server/
nmgr-config-store/
vars.env
```

### Launch the FastAPI Server
First go to the [docker-compose.yaml](./docker-compose.yaml) file, the command for the `app-server` service: `python3 chain_server/chain_server.py --assistant intake --port 8081` indicates the patient intake agent will be utilized in the FastAPI server. You can choose to specify any one of the four available options for `--assistant`: "intake", "appointment", "medication", or "full". 

Then bring up the app-server container:
```sh
# build and run the container, add -d for detaching from logs
docker compose up --build app-server
# docker compose up --build -d app-server
```

When you're ready to bring it down:
```
docker compose down app-server
```