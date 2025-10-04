from dotenv import load_dotenv
import os

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.medication import Medication
from fhirclient.models.medicationrequest import MedicationRequest


from langchain_community.tools.tavily_search import TavilySearchResults

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import ToolMessage
from langchain_core.runnables.graph import MermaidDrawMethod

from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START

import sys 
from typing import Annotated
from typing_extensions import TypedDict

import argparse
import logging

from nemoguardrails import RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails

from fastapi import FastAPI
import gradio as gr
import uvicorn


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from utils.ui import launch_demo_ui
from utils.logging import get_logging
from graph_definitions.utils_graph import add_messages_with_reset

#################
### variables ###
#################
patient_id = '14867dba-fb11-4df3-9829-8e8e081b39e6' # test patient id from looking through https://launch.smarthealthit.org/
save_graph_to_png = True
env_var_file = "/env_vars/vars.env"

def load_env_variables():
    """Load environment variables from vars.env file and return configuration"""
    #########################
    ### get env variables ###
    #########################
    load_dotenv(env_var_file, override=True)  # This line brings all environment variables from vars.env into os.environ

    assert os.environ['NVIDIA_API_KEY'] is not None, "Make sure you have your NVIDIA_API_KEY exported as a environment variable!"
    assert os.environ['TAVILY_API_KEY'] is not None, "Make sure you have your TAVILY_API_KEY exported as a environment variable!"
    nvidia_api_key = os.getenv("NVIDIA_API_KEY", None)

    assert os.environ['AGENT_LLM_MODEL'] is not None, "Make sure you have your AGENT_LLM_MODEL exported as a environment variable!"
    llm_model = os.getenv("AGENT_LLM_MODEL", None)

    assert os.environ['AGENT_LLM_BASE_URL'] is not None, "Make sure you have your AGENT_LLM_BASE_URL exported as a environment variable!"
    base_url = os.getenv("AGENT_LLM_BASE_URL", None)

    nemo_guardrails_config_path = os.getenv("NEMO_GUARDRAILS_CONFIG_PATH", None)

    tavily_api_key = os.getenv("TAVILY_API_KEY", None)

    return {
        'nvidia_api_key': nvidia_api_key,
        'llm_model': llm_model,
        'base_url': base_url,
        'nemo_guardrails_config_path': nemo_guardrails_config_path,
        'tavily_api_key': tavily_api_key
    }

# enable logging
logger = get_logging(__name__)

########################
### Define the tools ###
########################

settings = {
    'app_id': 'my_web_app',
    'api_base': 'https://r4.smarthealthit.org'
}

smart = client.FHIRClient(settings=settings)

@tool
def get_patient_dob() -> str:
    """Retrieve the patient's date of birth."""
    patient = Patient.read(patient_id, smart.server)
    return patient.birthDate.isostring

@tool
def get_patient_medications() -> list:
    """Retrieve the patient's list of medications."""
    def _med_name(med):
        if med.coding:
            name = next((coding.display for coding in med.coding if coding.system == 'http://www.nlm.nih.gov/research/umls/rxnorm'), None)
            if name:
                return name
        if med.text and med.text:
            return med.text
        return "Unnamed Medication(TM)"
  
    def _get_medication_by_ref(ref, smart):
        med_id = ref.split("/")[1]
        return Medication.read(med_id, smart.server).code
    
    def _get_med_name(prescription, client=None):
        if prescription.medicationCodeableConcept is not None:
            med = prescription.medicationCodeableConcept
            return _med_name(med)
        elif prescription.medicationReference is not None and client is not None:
            med = _get_medication_by_ref(prescription.medicationReference.reference, client)
            return _med_name(med)
        else:
            return 'Error: medication not found'
    
    # test patient id from looking through https://launch.smarthealthit.org/
    bundle = MedicationRequest.where({'patient': patient_id}).perform(smart.server)
    prescriptions = [be.resource for be in bundle.entry] if bundle is not None and bundle.entry is not None else None
  
    return [_get_med_name(p, smart) for p in prescriptions]


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

def create_medication_lookup_graph():
    """Create and return a fresh instance of the medication lookup graph"""
    # Reload environment variables from vars.env
    env_config = load_env_variables()
    
    # Create fresh LLM instance with reloaded config
    assistant_llm = ChatNVIDIA(
        model=env_config['llm_model'], 
        base_url=env_config['base_url']
    )
    
    # Create fresh TavilySearchResults with reloaded API key
    medication_instruction_search_tool = TavilySearchResults(
        description="Search online for instructions related the patient's requested medication. Do not use to give medical advice."
    )
    
    # Recreate medication lookup runnable with fresh LLM
    system_prompt_path = os.path.join(SCRIPT_DIR, "system_prompts", "medication_lookup_system_prompt.txt")
    with open(system_prompt_path, 'r') as file:
        prompt = file.read()

    medication_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt),
            ("placeholder", "{messages}"),
        ]
    )
    medication_tools = [get_patient_medications, get_patient_dob, medication_instruction_search_tool]

    if env_config['nemo_guardrails_config_path'] is not None and env_config['nemo_guardrails_config_path'] != "":
        try:
            # a path for the guardrails config files is provided in the environment variables
            rails_config_path = os.path.join("/app", env_config['nemo_guardrails_config_path'])
            # load the guardrails config files
            config = RailsConfig.from_path(rails_config_path)
            # create the guardrails runnable
            guardrails = RunnableRails(config=config, passthrough=True)
            # create the medication runnable with the guardrails
            medication_runnable = medication_prompt | ( guardrails | assistant_llm.bind_tools(medication_tools) )
            logger.warning(f"Guardrails config files loaded from path {env_config['nemo_guardrails_config_path']}")
        except Exception as ex:
            logger.error(f"Error loading guardrails config files from path {env_config['nemo_guardrails_config_path']}: {ex}")
            logger.error("NeMo Guardrails will not be used. Standing up the medication lookup agent without guardrails.")
            medication_runnable = medication_prompt | assistant_llm.bind_tools(medication_tools) 
    else:
        # no path for the guardrails config files is provided in the environment variables so we don't use guardrails
        logger.warning("Standing up the medication lookup agent without NeMo Guardrails.")
        medication_runnable = medication_prompt | assistant_llm.bind_tools(medication_tools)

    # Create a fresh StateGraph builder
    builder = StateGraph(State)
    
    # Define nodes: these do the work
    builder.add_node("medication_assistant", Assistant(medication_runnable))
    builder.add_node("tools", create_tool_node_with_fallback(medication_tools))
    
    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "medication_assistant")
    builder.add_conditional_edges(
        "medication_assistant",
        tools_condition,
    )
    builder.add_edge("tools", "medication_assistant")
    
    # The checkpointer lets the graph persist its state
    # this is a complete memory for the entire graph.
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    logger.info("Medication lookup graph built successfully")
    return graph

# Create initial graph instance for backwards compatibility
medication_lookup_graph = create_medication_lookup_graph()


if save_graph_to_png:
    try:
        save_image_path = "/graph_images/appgraph_medication_lookup.png"
        with open(save_image_path, "wb") as png:
            png.write(medication_lookup_graph.get_graph(xray=True).draw_mermaid_png(draw_method=MermaidDrawMethod.API))
            logger.info(f"Graph PNG saved to {save_image_path}")
    except Exception as ex:
        logger.error(f"Error saving graph to PNG: {ex}")



demo = launch_demo_ui(medication_lookup_graph)


app = FastAPI()
@app.get("/")
def app_main():
    return {"message": "This is your main app"}
app = gr.mount_gradio_app(app, demo, path="/medication-lookup")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860,
                        help = "Specify the port number for the simple Gradio UI to run at.")
                            
    args = parser.parse_args()
    server_port = args.port
    
    uvicorn.run("graph_medication_lookup_only:app", 
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