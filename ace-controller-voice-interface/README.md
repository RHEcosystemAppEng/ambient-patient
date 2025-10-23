
# Agentic Patient Front Desk Assistant

<div align="center">
  <img src="./assets/AmbientPatient.png" alt="Image"/>
</div>
<div align="center">
  <img src="./assets/ambientpatient_patientintake_RivaE2E_newui_transcripts_gh.gif" alt="Animated GIF"/>
</div>

In this example, we showcase how to build a patient front desk voice agent pipeline using WebRTC with real-time transcripts. It uses Pipecat pipeline with FastAPI on the backend, and React on the frontend. This pipeline uses a WebRTC based SmallWebRTCTransport, Riva ASR and TTS models and an Agent service. An example recording of the agent interaction with audio can be found [here](./assets/agentic_front_desk_patient_intake.mp4).


## Prerequisites
### Hardware Requirements
For the hardware required when choosing to self deploy the RIVA ASR and TTS NIMs, please see the details on the RIVA NIMs in the [ambient-patient/README](../README.md#hardware-requirements).

### API Keys
- NVIDIA AI Enterprise developer licence required to local host NVIDIA NIM Microservices.
- [NVIDIA API Key](https://build.nvidia.com/) for access to hosted NVIDIA NIM Microservices on the public NVIDIA AI Endpoints. See [NVIDIA API Keys](../docs/api_keys.md#nvidia-api-key) for detailed steps.
- [NGC API Key](https://docs.nvidia.com/ngc/latest/ngc-private-registry-user-guide.html#ngc-api-keys) for NGC container download and resources.


### Software

- Linux operating systems (Ubuntu 22.04 or later recommended)
- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)



## Setup API keys and Configure Service Settings


Open the [ace_controller.env](./ace_controller.env) file, and configure the following environment variables:

| Environment Variable | Description | Required/Optional |
|---|---|---|
| `NGC_API_KEY` | Required for downloading RIVA ASR and TTS NIMs (containers on NGC) for self hosting. See [NGC doc](https://docs.nvidia.com/ngc/latest/ngc-private-registry-user-guide.html#ngc-api-keys) on generating one. | Required |
| `NVIDIA_API_KEY` | Required to access the NVIDIA API catalog public endpoints [build.nvidia.com](https://build.nvidia.com/) if utilizing public endpoints for the RIVA ASR AND TTS NIMs. See [NVIDIA API Keys](../docs/api_keys.md#nvidia-api-key) for generating one.| Required |
| `CONFIG_PATH`| Required configuration file for the speech pipeline. </br> Option 1: when utilizing the public NVIDIA AI Endpoints for the RIVA ASR and TTS NIMs, specify `CONFIG_PATH=./configs/config_riva_public_endpoints.yaml` </br>  Option 2: when self hosting the RIVA ASR NIM, specify `CONFIG_PATH=./configs/config_riva_self_hosting.yaml` </br> See [Bot Pipeline Customizations](#pipeline-customizations) for more info. | Required |
|`REQUEST_TIMEOUT` | Specifies the timeout threshold in seconds waiting for a response from the request to the agent backend | Required. </br> Suggest to leave as default. |
   
## Deploy Services

There are multiple service components in the agentic patient front desk assistant application, all of which are deployed through Docker Compose.

1. Riva Parakeet ASR Service (optional for local self hosting)
2. Riva Magpie TTS Service (optional for local self hosting)
3. Agentic Patient Front Desk Service
4. The Speech Service
5. The UI Service

Key components of the services are configured as environment variables in the `ace_controller.env` file and as configuration parameters under `configs/config_*.yaml` before deploying the application. 

### Bring up the RIVA ASR and TTS NIMs
If you decided to utilize the public endpoints for the RIVA ASR AND TTS NIMs, and have set `CONFIG_PATH=./configs/config_riva_public_endpoints.yaml` in your `ace_controller.env` file, skip this step. 

If you decided to self host the RIVA ASR AND TTS NIMs, and have set `CONFIG_PATH=./configs/config_riva_self_hosting.yaml` in your `ace_controller.env` file, stand up the RIVA NIMs now with the commands:
```bash
docker compose up -d riva-asr-parakeet
docker compose up -d riva-tts-magpie
```
Note: It could take up to 6 minutes for the status of the NIM containers to change from starting to healthy.

### Bring up the RIVA Speech Service and UI 

```bash
docker compose --profile ace-controller up --build -d 
```

Note: To enable microphone access in Chrome, go to `chrome://flags/`, enable "Insecure origins treated as secure", add `http://<machine-ip>:4400` to the list, and restart Chrome.



## Using Coturn Server

If you want to share widely or want to deploy on cloud platforms, you will need to setup coturn server. Follow instructions in section `5. Set up Coturn Server` in the [ace-controller/examples/voice_agent_webrtc](https://github.com/NVIDIA/ace-controller/tree/develop/examples/voice_agent_webrtc#steps-to-deploy-voice_agent_webrtc-application) README for modifications required for using coturn.

## Pipeline Customizations

### Configuring ASR and TTS Models

You may customize ASR (Automatic Speech Recognition) and TTS (Text-to-Speech) services by configuring the `config_*.yaml` files in [configs/](./configs/). 

The choice between the two .yaml files as-is allows you to switch between NIM public endpoints hosted models and locally deployed models:

- When `CONFIG_PATH=./configs/config_riva_public_endpoints.yaml` is specified, the yaml file as-is sets the following: 
  - `RivaASRService.server="grpc.nvcf.nvidia.com:443"`
  - `RivaASRService.function_id="1598d209-5e27-4d3c-8079-4751568b1081"`
  - `RivaTTSService.server="grpc.nvcf.nvidia.com:443"`
  - `RivaTTSService.function_id="877104f7-e885-42b9-8de8-f6e4c6303969"`

- When `CONFIG_PATH=./configs/config_riva_self_hosting.yaml` is specified, the yaml file as-is sets the following: 
  - `RivaASRService.server="riva-asr-parakeet:50052"`
  - `RivaASRService.model="parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer"`
  - `RivaTTSService.server="riva-tts-magpie:50051"`
  - `RivaTTSService.model="magpie_tts_ensemble-Magpie-Multilingual"`

For more details on configuration options, such as `language` options for ASR/TTS, `sample_rate` for ASR, `voice_id` options for TTS, refer to the [NIM NVIDIA Magpie](https://build.nvidia.com/nvidia/magpie-tts-multilingual), [NIM NVIDIA Parakeet](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/api) documentation.


You could change the ASR / TTS models to different ones if you'd like. Browse [build.nvidia.com](build.nvidia.com) for the available ASR/TTS NIMs. You could find the `function_id` for each model in the example requests under the `Try API` tab on build.nvidia.com, such as https://build.nvidia.com/nvidia/magpie-tts-multilingual/api.

### Adding Custom TTS IPA Dictionary
In [ipa.json](./ipa.json), you could add to the dictionary your custom word-pronounciation pairs in the International Phonetic Alphabet (IPA) standard.

### Speculative Speech
Speculative speech processing is a feature in the voice agent that reduces bot response latency by working directly on Riva ASR early interim user transcripts instead of waiting for final transcripts. This is only a feature of Riva ASR. In our application, we disable this feature by default because our healthcare agent backend in LangGraph retains memory of every interaction / request between the user and the agent. With speculative speech, there are two similar requests sent to the agent backend and two responses, one for the interim ASR transcript and one for the final ASR transcript, and getting a response for each request. With both of the interactions logged in the agent memory, there can be great confusion caused. If connected to a backend without memory saved for each request/response, speculative speech can reduce latency without causing any issues.

If you are customizing for an agentic system that is okay with getting one request for interim ASR transcript and one request for the final ASR request, such as a simple LLM backend, you could add `ENABLE_SPECULATIVE_SPEECH` environment variable and set as `true` in the `ace_controller.env` file to enable speculative speech processing.

See the [documentation](https://docs.nvidia.com/ace/ace-controller-microservice/1.0/user-guide.html#speculative-speech-processing) on Speculative Speech Processing for more details.

### Saving to Audio Files

By default, our application does not save any audio files from the user-agent interaction. If you would like to enable audio file saving, you could add the environment variable `DUMP_AUDIO_FILES` and set to `true` in the `ace_controller.env` file.