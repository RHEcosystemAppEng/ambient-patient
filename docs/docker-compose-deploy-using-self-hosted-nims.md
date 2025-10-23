# Deployment Using Self Hosted NIMs

We will bring up the services in this developer example via docker compose.

## Prerequisites
### 1. Set up NGC Login
```sh
docker login nvcr.io
Username: $oauthtoken
Password: < your private NGC key here >
```
You should see `Login Succeeded`.


### 2. Set up Environment Variables Part 1 - for Agent Backend
Read through this section [1. Edit the vars.env file to set environment variables](https://github.com/NVIDIA-AI-Blueprints/ambient-patient/tree/main/agent#1-edit-the-varsenv-file-to-set-environment-variables) in the agent/README to configure each of the environment variables needed in [agent/vars.env](../agent/vars.env) for bringing up the agent backend.
- Add your `NVIDIA_API_KEY` and `NGC_API_KEY`
- Since we are going to self host the agent LLM NIM, set both of the AGENT_LLM_BASE_URL and AGENT_LLM_MODEL differently:
    ```sh
    AGENT_LLM_BASE_URL="http://agent-instruct-llm:8000/v1"
    AGENT_LLM_MODEL="meta/llama-3.3-70b-instruct"
    ```
- If you intend to utilize the NemoGuard NIMs for Nemo Guardrails around your agent LLM, set 
    ```sh
    NEMO_GUARDRAILS_CONFIG_PATH=nmgr-config-store/patient-intake-nemoguard-self-hosted-nim
    ```
    Note the differences in base_url and model_name in the config.yml files for directories `patient-intake-nemoguard-self-hosted-nim` and `patient-intake-nemoguard`.

> It is required to set your environment variables before proceeding.

### 3. Set up Environment Variables Part 2 - for the ace-controller Voice UI

Follow this section [Setup API Keys and Configure Service Settings](https://github.com/NVIDIA-AI-Blueprints/ambient-patient/tree/main/ace-controller-voice-interface#setup-api-keys-and-configure-service-settings) in the ace-controller-voice-interface/README and set the variables in [`ace-controller-voice-interface/ace_controller.env`](../ace-controller-voice-interface/ace_controller.env).

- Add your `NVIDIA_API_KEY` and `NGC_API_KEY`
- Since we're self hosting the RIVA ASR and TTS NIMs and not using the public endpoints, change the default   `CONFIG_PATH` to 

    ```sh
    CONFIG_PATH=./configs/config_riva_self_hosting.yaml
    ```
> It is required to set your environment variables before proceeding.

### 4. Set up Networking 
**Note before proceeding!** When deploying on cloud providers such as Brev, a Turn server is needed. A Turn server is needed for WebRTC connections when clients are behind NATs or firewalls that prevent direct peer-to-peer communication. Please see the [Turn Server](./turn-server.md) documentation on setting one up before proceeding.

## Deployment Steps


### 1. Deploy Agent LLM NIM Locally
For this notebook, we assume we will always be at the root of the ambient-patient repository.
```sh
 # make sure you're in the ambient-patient directory
 cd ambient-patient
```
First set the GPU IDs for the Agent LLM NIM.
```sh
# if on A100s
export AGENT_LLM_GPU_ID=0,1,2,3
```
Next bring up the agent LLM NIM:
```sh
docker compose -f agent/docker-compose.yaml up -d agent-instruct-llm
```

Run the following command that refreshes every 2 seconds in a seperate terminal tab to view the container that we have just brought up
```sh
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"'
```
You should see the name `agent-instruct-lm` in the result:
```sh
NAMES                IMAGE                                            STATUS
agent-instruct-llm   nvcr.io/nim/meta/llama-3.3-70b-instruct:1.8.5   Up About a minute (health: starting)
```
Note: after the image is pulled, it should take less than 20 minutes for the status of the container to change from starting to healthy. You can continue to the next steps 3 and 4 while the status is health: starting.

### 2. Deploy NemoGuard NIMs Locally

If you would like to utilize the NemoGuard NIMs for guardrailing your agent LLM with content safety and topic control, and you have set `NEMO_GUARDRAILS_CONFIG_PATH=nmgr-config-store/patient-intake-nemoguard-self-hosted-nim` in your vars.env file, first set the GPU IDs for the NemoGuard NIMs.
```sh
# if on A100s
export NEMOGUARD_CONTENT_SAFETY_LLM_GPU_ID=4
export NEMOGUARD_TOPIC_CONTRIL_LLM_GPU_ID=5
```
Next bring up the two NemoGuard NIMs deployment:
```sh
docker compose -f agent/docker-compose.yaml up -d nemoguard-content-safety-llm nemoguard-topic-control-llm 
```
You should see the new names `nemoguard-content-safety-llm` and `nemoguard-topic-control-llm` in the result:
```sh
NAMES                          IMAGE                                                            STATUS
nemoguard-content-safety-llm              nvcr.io/nim/nvidia/llama-3.1-nemoguard-8b-content-safety:1.10.1   Up 7 minutes (healthy)
nemoguard-topic-control-llm               nvcr.io/nim/nvidia/llama-3.1-nemoguard-8b-topic-control:1.10.1    Up 7 minutes (healthy)
...
```
Note: after the images are pulled, it should take about 5 minutes for the status of the containers to change from starting to healthy. You can continue to the next step 4 while the status is health: starting.

### 3. Deploy Agent Backend App Server

 We will be bringing up the `app-server` service in [agent/docker-compose.yaml](../agent/docker-compose.yaml)

 Double check that your environment variables are set correctly according to 
 [1. Set Environment Variables for Agent Backend](../agent#1-edit-the-varsenv-file-to-set-environment-variables), then bring up the app-server service:
 ```sh
 docker compose -f agent/docker-compose.yaml up --build app-server
 # or to detach from docker logs add -d:
 docker compose -f agent/docker-compose.yaml up --build -d app-server
 ```
The build should take a few minutes. Note that after building the image for the first time, for bringing up this service again, if nothing in the source files changes and you don't need to rebuild the image, you could remove `--build` from the command:

```sh
docker compose -f agent/docker-compose.yaml up -d app-server
```

After the build finishes, you should see the new name `app-server-healthcare-assistant` in the results:
```
NAMES                             IMAGE                                                            STATUS
app-server-healthcare-assistant   app-server-healthcare-assistant:latest                           Up 14 seconds
...
```



### 4. Deploy RIVA NIMS
Set the GPU IDs for the RIVA NIMs.
```sh
# if on A100s, the RIVA NIMs could share one A100 or be deployed seperately
export RIVA_ASR_NIM_GPU_ID=6
export RIVA_TTS_NIM_GPU_ID=7
```
Bring up the RIVA NIMs. 

Since you are self deploying the RIVA NIMs, please see the [Known Issues](./known_issues.md) documentation on the RIVA TTS NIM known issue.

```sh
docker compose --profile riva-nims-local -f ace-controller-voice-interface/docker-compose.yml up -d
```
You should see the additional names `voice-agents-webrtc-riva-tts-magpie-1` and `voice-agents-webrtc-riva-asr-parakeet-1` in the result:
```sh
NAMES                                     IMAGE                                                            STATUS
voice-agents-webrtc-riva-tts-magpie-1     nvcr.io/nim/nvidia/magpie-tts-multilingual:1.3.0                 Up 6 minutes (healthy)
voice-agents-webrtc-riva-asr-parakeet-1   nvcr.io/nim/nvidia/parakeet-1-1b-ctc-en-us:1.3.0                 Up 6 minutes (healthy)
...
```
Note: after the images are pulled, it should take about 6 minutes for the status of the containers to change from starting to healthy.

### 5. Deploy Voice UI Powered by ace-controller

```bash
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up --build
# or to detach from docker logs add -d:
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up --build -d
```
The build should take a few minutes. Remove `--build` from the command if you haven't change any sources files and are bringing up the services again:
```sh
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up -d
```
You should see additional names `voice-agents-webrtc-ui-app` and `voice-agents-webrtc-python-app` in the results, for example:

```sh
NAMES                                     IMAGE                                                            STATUS
voice-agents-webrtc-ui-app-1              voice-agents-webrtc-ui-app                                       Up 2 minutes
voice-agents-webrtc-python-app-1          voice-agents-webrtc-python-app                                   Up 2 minutes (healthy)
...
```
After the services are up, it should take less than a minute for the status to be healthy.

Now you should see all the services as listed below:
NAMES                  |            IMAGE                       |             STATUS
--- | --- | ---
voice-agents-webrtc-python-app-1       |   voice-agents-webrtc-python-app                                |    Up 6 minutes (healthy)
voice-agents-webrtc-ui-app-1           |   voice-agents-webrtc-ui-app                                    |    Up 6 minutes
turn-server                            |   instrumentisto/coturn                                         |    Up 10 minutes
voice-agents-webrtc-riva-tts-magpie-1  |   nvcr.io/nim/nvidia/magpie-tts-multilingual:1.3.0               |   Up 25 minutes (healthy)
voice-agents-webrtc-riva-asr-parakeet-1  | nvcr.io/nim/nvidia/parakeet-1-1b-ctc-en-us:1.3.0               |   Up 25 minutes (healthy)
app-server-healthcare-assistant         |  app-server-healthcare-assistant:latest                           | Up 39 minutes
nemoguard-content-safety-llm            |  nvcr.io/nim/nvidia/llama-3.1-nemoguard-8b-content-safety:1.10.1  | Up 50 minutes (healthy)
nemoguard-topic-control-llm             |  nvcr.io/nim/nvidia/llama-3.1-nemoguard-8b-topic-control:1.10.1    |Up 50 minutes (healthy)
agent-instruct-llm                      |  nvcr.io/nim/meta/llama-3.3-70b-instruct:1.8.5                 |  Up 59 minutes (healthy)

If any of them is not up and running and has stopped, please investigate the docker logs of the container to see the issue.


### 6. Go to the Voice UI in your Web Browser
First, to enable microphone access in Chrome, go to `chrome://flags/`, enable "Insecure origins treated as secure", add `http://<machine-ip>:4400` to the list, and restart Chrome.

Next, go to `http://<machine-ip>:4400` in your browser to visit the voice UI. Upon loading, the page should look like the following:
![](../ace-controller-voice-interface/assets/ui_at_start.png)

Click Start, and click the Unmute button before starting your conversation.

If you have added your LangSmith key in the agent/vars.env file, you can view the agent backend traces in LangGraph at [smith.langchain.com](smith.langchain.com) under the “healthcare-agent-project” for observability.

### Troubleshooting
#### Permission Issue
If you're getting an error `Cannot read properties of undefined (reading 'getUserMedia')`, that means you have not enabled microphone access in Chrome. Go to `chrome://flags/`, enable "Insecure origins treated as secure", add `http://<machine-ip>:4400` to the list, and restart Chrome.

![](../docs/images/webpage_permission_error.png)

#### Timeout Issue
If you're getting a timeout issue where the button shows `Connecting...` and then "WebRTC connection failed", double check all the steps in the document. It's likely due to incorrect configurations.

![](../docs/images/webrtc_connection_failed.png)

After setting the correct configurations, make sure to **close the browser tab**, and open a new browser tab to access the application. If that doesn't seem to work, clear your browser cache and open the link again.

#### Other Issues
Please view the docker logs of the containers if you encounter other issues.


### 7. Bring down services

```sh
docker compose -f agent/docker-compose.yaml down
docker compose -f ace-controller-voice-interface/docker-compose.yml down
# if you just want to stop the RIVA NIMs
docker compose --profile riva-nims-local -f ace-controller-voice-interface/docker-compose.yml down
docker volume remove voice-agents-webrtc_nim_cache voice-agents-webrtc_riva_data
```