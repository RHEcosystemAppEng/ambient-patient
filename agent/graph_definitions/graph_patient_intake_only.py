# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from dotenv import load_dotenv
import os

from langchain_nvidia_ai_endpoints import ChatNVIDIA


import datetime
from zoneinfo import ZoneInfo



from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import ToolMessage


from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START

import sys 
from typing import Annotated
from typing_extensions import TypedDict

import argparse
import logging

from pydantic import Field

from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails

from fastapi import FastAPI
import gradio as gr
import uvicorn
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from utils.ui import launch_demo_ui
from utils.logging import get_logging
from graph_definitions.utils_graph import add_messages_with_reset

#################
### variables ###
#################
save_graph_to_png = True

env_var_file = "/env_vars/vars.env"

def load_env_variables():
    """Load environment variables from vars.env file and return configuration"""
    #########################
    ### get env variables ###
    #########################
    load_dotenv(env_var_file, override=True)  # This line brings all environment variables from vars.env into os.environ

    assert os.environ['NVIDIA_API_KEY'] is not None, "Make sure you have your NVIDIA_API_KEY exported as a environment variable!"
    nvidia_api_key = os.getenv("NVIDIA_API_KEY", None)

    assert os.environ['AGENT_LLM_MODEL'] is not None, "Make sure you have your AGENT_LLM_MODEL exported as a environment variable!"
    llm_model = os.getenv("AGENT_LLM_MODEL", None)

    assert os.environ['AGENT_LLM_BASE_URL'] is not None, "Make sure you have your AGENT_LLM_BASE_URL exported as a environment variable!"
    base_url = os.getenv("AGENT_LLM_BASE_URL", None)

    nemo_guardrails_config_path = os.getenv("NEMO_GUARDRAILS_CONFIG_PATH", None)

    return {
        'nvidia_api_key': nvidia_api_key,
        'llm_model': llm_model,
        'base_url': base_url,
        'nemo_guardrails_config_path': nemo_guardrails_config_path
    }
# enable logging
logger = get_logging(__name__)

########################
### Define the tools ###
########################
# In this tool we illustrate how you can define 
# the different data fields that are needed for 
# patient intake and the agentic llm will gather each field. 
# Here we are only printing each of the fields for illustration
# of the tool, however in your own use case, you would likely want 
# to make API calls to transmit the gathered data fields back
# to your own database.
@tool
def print_gathered_patient_info(
    patient_name: str = Field(description="Name of the patient"),
    patient_dob: datetime.date = Field(description="Date of birth of the patient"),
    current_medication: list[str] = Field(description="Current list of medications the patient is taking"),
    allergies_medication: list[str] = Field(description="Medication allergies of the patient"),
    current_symptoms: str = Field(description="Current symptoms of the patient"),
    current_symptoms_duration: str = Field(description="Duration of the current symptoms in days, weeks, or months"),
    pharmacy_location: str = Field(description="Location of the pharmacy")
) -> str:
    """This function prints out and transmits the gathered information for each patient intake field:
     patient_name is the patient name,
     patient_dob is the patient date of birth,
     current_medications is a list of current medications for the patient,
     allergies_medication is a list of allergies in medication for the patient,
     current_symptoms is a description of the current symptoms for the patient,
     current_symptoms_duration is the time duration of current symptoms,
     pharmacy_location is the patient pharmacy location. """
    
    # Process the input fields and generate output
    output_message = f"""Here's a summary from the patient intake agent:
    
    Patient Name: {patient_name}
    Patient Date of Birth: {patient_dob}
    Current Medication: {current_medication}
    Allergies Medication: {allergies_medication}
    Current Symptoms: {current_symptoms}
    Current Symptoms Duration: {current_symptoms_duration}
    Pharmacy Location: {pharmacy_location}

    The intake is now complete.
    """

    json_data = {
        "patient_name": patient_name,
        "patient_dob": patient_dob,
        "current_medication": current_medication,
        "allergies_medication": allergies_medication,
        "current_symptoms": current_symptoms,
        "current_symptoms_duration": current_symptoms_duration,
        "pharmacy_location": pharmacy_location
    }

    output_dir = os.path.join("/app", os.getenv("APP_OUTPUT_DIR", "app_output_files"), "patient_intake_agent")
    os.makedirs(output_dir, exist_ok=True) 
    
    timezone_name = os.getenv("TIMEZONE", "America/Los_Angeles")
    timezone = ZoneInfo(timezone_name)
    output_file_name = "output_{}.json".format(datetime.datetime.now(timezone).strftime("%Y-%m-%d-%H-%M-%S"))
    def date_serializer(obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()  
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    try:
        with open(os.path.join(output_dir,output_file_name), "w") as f:
            json.dump(json_data, f, default=date_serializer)
    except Exception as e:
        logger.error(f"Error writing to output json file from patient intake agent: {e}")

    return output_message


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages_with_reset]

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state, config)

            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}
    

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def create_intake_graph():
    """Create and return a fresh instance of the intake graph"""
    # Reload environment variables from vars.env
    env_config = load_env_variables()
    
    # Create fresh LLM instance with reloaded config
    assistant_llm = ChatNVIDIA(
        model=env_config['llm_model'], 
        base_url=env_config['base_url']
    )
    
    # Recreate patient intake runnable with fresh LLM and guardrails config
    system_prompt_path = os.path.join(SCRIPT_DIR, "system_prompts", "patient_intake_system_prompt.txt")
    with open(system_prompt_path, 'r') as file:
        prompt = file.read()

    patient_intake_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt),
            ("placeholder", "{messages}"),
        ]
    )
    patient_intake_tools = [print_gathered_patient_info]

    if env_config['nemo_guardrails_config_path'] is not None and env_config['nemo_guardrails_config_path'] != "":
        try:
            # a path for the guardrails config files is provided in the environment variables
            rails_config_path = os.path.join("/app", env_config['nemo_guardrails_config_path'])
            # load the guardrails config files
            config = RailsConfig.from_path(rails_config_path)
            # create the guardrails runnable
            guardrails = RunnableRails(config=config, passthrough=True)
            # create the patient intake runnable with the guardrails
            patient_intake_runnable = patient_intake_prompt | ( guardrails | assistant_llm.bind_tools(patient_intake_tools) )
            logger.warning(f"Guardrails config files loaded from path {env_config['nemo_guardrails_config_path']}")
        except Exception as ex:
            logger.error(f"Error loading guardrails config files from path {env_config['nemo_guardrails_config_path']}: {ex}")
            logger.error("NeMo Guardrails will not be used. Standing up the patient intake agent without guardrails.")
            patient_intake_runnable = patient_intake_prompt | assistant_llm.bind_tools(patient_intake_tools) 
    else:
        # no path for the guardrails config files is provided in the environment variables so we don't use guardrails
        logger.warning("Standing up the patient intake agent without NeMo Guardrails.")
        patient_intake_runnable = patient_intake_prompt | assistant_llm.bind_tools(patient_intake_tools) 

    # Create a fresh StateGraph builder
    builder = StateGraph(State)
    
    # Define nodes: these do the work
    builder.add_node("patient_intake_assistant", Assistant(patient_intake_runnable))
    builder.add_node("tools", create_tool_node_with_fallback(patient_intake_tools))
    
    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "patient_intake_assistant")
    builder.add_conditional_edges(
        "patient_intake_assistant",
        tools_condition,
    )
    builder.add_edge("tools", "patient_intake_assistant")
    
    # The checkpointer lets the graph persist its state
    # this is a complete memory for the entire graph.
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    logger.info("Graph built successfully")
    return graph

# Create initial graph instance for backwards compatibility
intake_graph = create_intake_graph()


if save_graph_to_png:
    try:
        save_image_path = "/graph_images/appgraph_patient_intake.png"
        with open(save_image_path, "wb") as png:
            png.write(intake_graph.get_graph(xray=True).draw_mermaid_png())
            logger.info(f"Graph PNG saved to {save_image_path}")
    except Exception as ex:
        logger.error(f"Error saving graph to PNG: {ex}")


demo = launch_demo_ui(intake_graph)

app = FastAPI()
@app.get("/")
def app_main():
    return {"message": "This is your main app"}
app = gr.mount_gradio_app(app, demo, path="/patient-intake")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7861,
                        help = "Specify the port number for the simple Gradio UI to run at.")
                            
    args = parser.parse_args()
    server_port = args.port

    
    uvicorn.run("graph_patient_intake_only:app", 
                host="0.0.0.0", 
                port=server_port, 
                reload=True, 
                reload_includes=["*.env", "*.txt", "*.co", "*.yml", "*.py"],
                reload_excludes=["**/__pycache__/**"],
                reload_dirs=[
                    "/app/graph_definitions",
                    "/app/nmgr-config-store",
                    "/app/utils",
                    "/env_vars"

                ])