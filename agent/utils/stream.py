# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(level=log_level)

logger = logging.getLogger(__name__)

async def print_event_async_stream(graph, input_message, thread_config, max_length=1500):
    last_answer = ""
    full_log = ""
    async for event in graph.astream({"messages": [{"role": "user", "content": input_message}]}, thread_config, stream_mode="values"):
        try:
            logger.info("Event from graph stream has {} values".format(len(event.values())))
            for value in event.values():
                
                try:
                    if isinstance(value, list):
                        if len(value) == 0:
                            continue
                        value_messages = value[-1]
                        logger.info("Logging there are {} event values in the list.\n".format(len(value)))
                        logger.info("Logging the last event value in a list of event values: {}\n".format(value_messages))
                    else:
                        value_messages = value
                    
                    if hasattr(value_messages, 'pretty_repr'):
                        logger.warning("Agent event: \n\n {}\n".format(value_messages.pretty_repr()))
                        full_log += value_messages.pretty_repr() + "\n\n"
                    else:
                        logger.warning("Agent event: \n\n {}\n".format(str(value_messages)))
                        full_log += str(value_messages) + "\n\n"
                        continue
                    
                    if value_messages.type == "ai":
                        if value_messages.content == "" and value_messages.tool_calls:
                            # this is an AI message with tool calls
                            tool_name = value_messages.tool_calls[0]["name"].replace("_"," ").replace("-"," ")
                            last_answer += "Agent is making a tool call with the tool {}. \n".format(tool_name)
                        else:
                            # this is an AI message without tool calls
                            ret = value_messages.content
                            if len(ret) > max_length:
                                ret = ret[:max_length] + " ... (truncated)"
                            last_answer += ret + "\n"
                    elif value_messages.type == "tool":
                        # this is a tool call message
                        last_answer += "Tool call has finished. \n"
                    elif value_messages.type == "human":
                        pass
                except Exception as ex:
                    logger.exception("Agent response failed while iterating through values in event with exception: %s", ex)
                    return "Error encountered, please see Docker logs for more details", full_log
                    
        except Exception as ex:
            logger.exception("Agent response failed while iterating through events in graph.astream with exception: %s", ex)
            return "Error encountered, please see Docker logs for more details", full_log
            
    return last_answer, full_log