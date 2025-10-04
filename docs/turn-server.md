### Coturn server

A TURN server is needed for WebRTC connections when clients are behind NATs or firewalls that prevent direct peer-to-peer communication. The TURN server acts as a relay to ensure connectivity in restrictive network environments.

> Note: This is needed for deployment on Brev. 

If on Brev, before proceeding further, make sure the instance provider type you're on enables exposing TCP/UDP Ports. This is required for the Turn server. If this section is not enabled, please change to another instance provider and start a new Brev instance.

![](./images/tcp_udp.png)

Before bringing up the applications in `ace-controller-voice-interface`, follow the steps in this section to utilize a Turn server.

#### Step 1: Run the Turn server docker container
```sh
# get this machin'es public ip
export HOST_IP_EXTERNAL=$(curl -s ifconfig.me)
# see the ip
echo $HOST_IP_EXTERNAL
# bring up a coturn server
docker run -d --name turn-server --network=host instrumentisto/coturn -n --verbose --log-file=stdout --external-ip=$HOST_IP_EXTERNAL --listening-ip=0.0.0.0 --lt-cred-mech --fingerprint --user=admin:admin --no-multicast-peers --realm=tokkio.realm.org --min-port=51000 --max-port=51010
```
#### Step 2: Modify ace-controller app configuration
Next, modify the `.env` file and `config.ts` file under `ace-controller-voice-interface`. The `config.ts` file will be utilized in the docker build process for the ui-app container from the webrtc_ui example.
```sh
# check the content of the existing ace-controller-voice-interface/.env
cat ace-controller-voice-interface/.env
# add three relevant env vars to ace-controller-voice-interface/.env
echo -e "\nTURN_USERNAME=admin\nTURN_PASSWORD=admin\nTURN_SERVER_URL=turn:$HOST_IP_EXTERNAL:3478" >> ace-controller-voice-interface/.env
# check the modified content of the existing ace-controller-voice-interface/.env
cat ace-controller-voice-interface/.env
```
```sh
# next check the content of the existing config.ts file
cat ace-controller-voice-interface/config.ts
# replace the ice server definition in config.ts
sed -i "s/export const RTC_CONFIG = {};/export const RTC_CONFIG: ConstructorParameters<typeof RTCPeerConnection>[0] = {\n    iceServers: [\n      {\n        urls: \"turn:$HOST_IP_EXTERNAL:3478\",\n        username: \"admin\",\n        credential: \"admin\",\n      },\n    ],\n  };/" ace-controller-voice-interface/config.ts
# next check the modified content of the existing config.ts file
cat ace-controller-voice-interface/config.ts
```

#### Step 3: Expose ports on your cloud provider instance

On the cloud provider instance, make sure the following ports are exposed:
- 4400
- 7860
- 3478
- 51000-51010 (this is from the range specified by the Turn server docker run command)

If on Brev, expose the ports using the `TCP/UDP Ports` section in your web console's `Access` tab.
![](./images/expose_ports.png)

In the end your section should look like this:
![](./images/all_ports_exposed.png)

#### Step 4: (re)start the ace-controller app
(re)start the ace-controller profile:
```sh
# if you have already spun up the ace-controller profile in ace-controller-voice-interface/docker-compose.yml, 
# first bring it down:
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml down
```

```sh
# the rebuild is needed, specifing --build 
docker compose --profile ace-controller -f ace-controller-voice-interface/docker-compose.yml up --build -d
```

#### Step 5: Go to the Voice UI in your Web Browser
First, to enable microphone access in Chrome, go to `chrome://flags/`, enable "Insecure origins treated as secure", add `http://<machine-ip>:4400` to the list, and restart Chrome.

Next, go to `http://<machine-ip>:4400` in your browser to visit the voice UI. Upon loading, the page should look like the following:
![](../ace-controller-voice-interface/assets/ui_at_start.png)


#### Troubleshooting 
##### Permission Issue
If you're getting an error `Cannot read properties of undefined (reading 'getUserMedia')`, that means you have not enabled microphone access in Chrome. Go to `chrome://flags/`, enable "Insecure origins treated as secure", add `http://<machine-ip>:4400` to the list, and restart Chrome.

![](./images/webpage_permission_error.png)

##### Timeout Issue
If you're getting a timeout issue where the button shows `Connecting...` and then "WebRTC connection failed", double check all the steps in the document. It's likely due to incorrect configurations.

![](./images/webrtc_connection_failed.png)

After setting the correct configurations, make sure to **close the browser tab**, and open a new browser tab to access the application. If that doesn't seem to work, clear your browser cache and open the link again.