# Customization of the Healthcare Agents
## NeMo Guardrails Usage
[NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/latest/index.html) enables developers building LLM-based applications to easily add programmable guardrails between the application code and the LLM. 

We enable the optional use of NeMo Guardrails in this healthcare agent for patients repo, and have created the following example configurations inside the `nmgr-config-store` directory. For the official documentation on the NeMo Guardrails configuration, please see https://docs.nvidia.com/nemo/guardrails/latest/user-guides/configuration-guide/index.html.

### 1. `patient-intake-basic-input`
In this directory, we have the simplest guardrail around the user input. `config.yml` defines the llm to use in guardrails and a single flow for the input: `self check input`. `prompts.yml` defines the llm prompt for the flow `self check input` that will be passed into the guardrails llm specified in `config.yml`.

### 2. `patient-intake-input-output`
Adding on top of `patient-intake-basic-input`, in this directory we add the output rails as well in `config.yml` and `prompts.yml`, with more comprehensive prompts for both input and output in the patient intake scenario. Additionally, in the file `config.co`, we override the default response messages when guardrails needs to block the input / output.

### 3. `patient-intake-nemoguard`
So far, we have been utilizing generic LLMs in the guardrails. Next, we can look into utilizing the [NVIDIA NemoGuard](https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html#nvidia-models) content safety and topic safety models. 

### 4. Customize the configuration for your use case
There are many more options for configuring guardrails. Please visit https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html. There are options for fact checking, hallucination detection, community models and libraries, using the NemoGuard jailbreaking model, etc.