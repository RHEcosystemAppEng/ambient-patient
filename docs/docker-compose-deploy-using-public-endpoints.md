# Deployment Using Public NVIDIA AI Endpoints
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

Since we are utilizing the public NVIDIA AI Endpoints for experiencing the developer example for the first time, leave the default values for:
- `AGENT_LLM_BASE_URL="https://integrate.api.nvidia.com/v1"`
- If you would like NemoGuard NIMs enabled: `NEMO_GUARDRAILS_CONFIG_PATH=nmgr-config-store/patient-intake-nemoguard`

> It is required to set your environment variables before proceeding.

### 3. Set up Environment Variables Part 2 - for the ace-controller Voice UI

Next we will be working on services defined in the [`ace-controller-voice-interface`](../ace-controller-voice-interface/) directory. Follow this section [Setup API Keys and Configure Service Settings](https://github.com/NVIDIA-AI-Blueprints/ambient-patient/tree/main/ace-controller-voice-interface#setup-api-keys-and-configure-service-settings) in the ace-controller-voice-interface/README and set the variables in  [`ace-controller-voice-interface/ace_controller.env`](../ace-controller-voice-interface/ace_controller.env).

- Add your `NVIDIA_API_KEY` and `NGC_API_KEY`
- Since we're utilizing the public NVIDIA AI Endpoints, we should keep the default `CONFIG_PATH`:
    ```sh
    CONFIG_PATH=./configs/config_riva_public_endpoints.yaml
    ```
> It is required to set your environment variables before proceeding.

### 4. Set up Networking 

**Note before proceeding!** When deploying on cloud providers such as Brev, a Turn server is needed. A Turn server is needed for WebRTC connections when clients are behind NATs or firewalls that prevent direct peer-to-peer communication. Please see the [Turn Server](./turn-server.md) documentation on setting one up before proceeding.

## Deployment Steps
We will bring up the services in this developer example via docker compose.

### 1. Deploy Agent Backend App Server


 For this notebook, we assume we will always be at the root of the ambient-patient repository.
 ```sh
 # navigate to ambient-patient
 cd ambient-patient
 ```
  We will be bringing up the `app-server` service in [agent/docker-compose.yaml](../agent/docker-compose.yaml)
 ```sh
 docker compose -f agent/docker-compose.yaml up --build app-server
 # or to detach from docker logs add -d:
 docker compose -f agent/docker-compose.yaml up --build -d app-server
 ```
The build should take a few minutes. Note that after building the image for the first time, for bringing up this service again, if nothing in the source files changes and you don't need to rebuild the image, you could remove `--build` from the command:

```sh
docker compose -f agent/docker-compose.yaml up -d app-server
```

Run the following command that refreshes every 2 seconds in a seperate terminal tab to view the container that we have just brought up
```sh
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"'
```
You should see a name `app-server-healthcare-assistant` in the results, for example:
```
NAMES                             IMAGE                                    STATUS
app-server-healthcare-assistant   app-server-healthcare-assistant:latest   Up 18 seconds
```


### 2. Deploy Voice UI Powered by ace-controller

```bash
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up --build
# or to detach from docker logs add -d:
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up --build -d
```
The build should take a few minutes. Remove `--build` from the command if you haven't change any sources files and are bringing up the services again:
```sh
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up -d
```
You should see the new names `voice-agents-webrtc-ui-app-1` and `voice-agents-webrtc-python-app-1` in the docker ps results, for example:

```sh
NAMES                              IMAGE                                    STATUS
voice-agents-webrtc-ui-app-1       voice-agents-webrtc-ui-app               Up About a minute
voice-agents-webrtc-python-app-1   voice-agents-webrtc-python-app           Up About a minute (healthy)
app-server-healthcare-assistant    app-server-healthcare-assistant:latest   Up 5 minutes
```
### 3. Go to the Voice UI in your Web Browser
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

### 4. Bring down the services
Bring down the app server that serves the agent
```sh
docker compose -f agent/docker-compose.yaml down app-server
```
Bring down the ace-controller web UI
```sh
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml down
```
