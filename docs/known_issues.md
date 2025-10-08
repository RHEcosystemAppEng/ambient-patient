# Known Issues
## RIVA TTS NIM
The TTS model `nvcr.io/nim/nvidia/magpie-tts-multilingual:1.3.0` has a known expected behavior. 

If deploying on a GPU device that doesn't have a prebuilt model profile, the deployed container will be building the model profile. During the build, the status of the docker container can show as "unhealthy" after a few minutes of showing "health: starting". When you see that "unhealthy" status, use `docker logs voice-agents-webrtc-riva-tts-magpie-1` to inspect the docker logs. If you see many message in the docker logs like below:

```
2025-09-26 21:06:16.292024375 [W:onnxruntime:, constant_folding.cc:269 ApplyImpl] Could not find a CPU kernel and hence can't constant fold Reciprocal node 'Reciprocal_4677'
```

That is expected behavior and it will continue the model profile build when possible, even when the container status shows "unhealthy". When you see docker logs like this do not restart the NIM deployment, please wait, and the "unhealthy" status should turn "healthy" once the model profile is built. It could take between 40 minutes to an hour.

The following GPU devices have prebuilt model profiles so you won't need to wait for the build process once you start the container, and the status of the container should show as "healthy" within a few minutes.

You could find the gpu_device of your GPU by looking at the beginning of the docker logs. Please note that not all GPUs of the same name will have the same gpu_device ids (for example not all A100s are exactly the same GPU).
```
- Compatible with system:
    - 676f29e8f80935a721ad27969acf4d92db44a377b72f601ba3302ab85771894c - ampereplus:disabled|batch_size:32|gpu:a100|gpu_device:20b2|model_type:prebuilt|name:magpie-tts-multilingual
    - 9a8ba11ff97fe7583beba2b1f5bb7238ce00d94e6fbbc5f8bee0575b8f66ffb3 - ampereplus:disabled|batch_size:64|gpu:a100|gpu_device:20b2|model_type:prebuilt|name:magpie-tts-multilingual
    - a78701bae30226ed228389eaace4e23e2b77aa2fdbc83ecbc70fcfe94e74085e - ampereplus:disabled|batch_size:8|gpu:a100|gpu_device:20b2|model_type:prebuilt|name:magpie-tts-multilingual
- Incompatible with system:
    - 262a309a35479be09707f4532ef44d6463ea0f8fae019558546cbe8550f407d4 - batch_size:32|model_type:rmir|name:magpie-tts-multilingual
    - 3263ca3ecc33ca903f66f401a05aa904f385d61f30636cfeba6d1f8751a0ddf9 - ampereplus:disabled|batch_size:32|gpu:h100|gpu_device:2330|model_type:prebuilt|name:magpie-tts-multilingual
    - 48afefb5babbc2666d0c07e302f9e2faf3940542fddc1ca9d77a2cfbe87025f1 - ampereplus:disabled|batch_size:8|gpu:h100|gpu_device:2330|model_type:prebuilt|name:magpie-tts-multilingual
    - 92aaefc8f69a291643720528095a91d9b1068c259117fb5f9f37d4565c2aaee0 - ampereplus:disabled|batch_size:8|gpu:l40s|gpu_device:26b9|model_type:prebuilt|name:magpie-tts-multilingual
    - a162605329dc80e7d685b8e2f8e913adf9d6b218442702042832749e8398e2fa - ampereplus:disabled|batch_size:32|gpu:l40s|gpu_device:26b9|model_type:prebuilt|name:magpie-tts-multilingual
    - c22515e8861affad674375ea30c5461e305e04f2bf57b5f53282b19226197b71 - ampereplus:disabled|batch_size:64|gpu:h100|gpu_device:2330|model_type:prebuilt|name:magpie-tts-multilingual
    - c4e0bf4f014c1c43d12db362e6ed79de40ec0b8315a57e0a77795dc186d52afb - batch_size:8|model_type:rmir|name:magpie-tts-multilingual
    - f2f1b5ab392f8432ef226ace90cc1349c52727b12abc89b3898485121c58be6a - batch_size:64|model_type:rmir|name:magpie-tts-multilingual
    - f3e0f3c8c376bd5c57c484ea01e60842d6960e13284a0e68d61ce306e03fb0f7 - ampereplus:disabled|batch_size:64|gpu:l40s|gpu_device:26b9|model_type:prebuilt|name:magpie-tts-multilingual
```

You can view available prebuilt profiles from above with
```
docker run -it --rm --name riva-dev  --runtime=nvidia      -e NVIDIA_VISIBLE_DEVICES=0         --shm-size=8GB       -e NGC_API_KEY       -e NIM_HTTP_API_PORT=9000       -e NIM_GRPC_API_PORT=50051 -p 9000:9000 -p 50051:50051 -p 8000:8000 --entrypoint nim_list_model_profiles nvcr.io/nim/nvidia/magpie-tts-multilingual:1.3.0
```