# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Agent service """
# pylint: disable=consider-using-dict-items,consider-iterating-dictionary,unused-argument,broad-exception-raised,broad-exception-caught

import re
import ast
from typing import List, Tuple, Dict

from langchain.agents import AgentExecutor
from common.models import User, UserChat, UserPlan, PlanStep
from common.models.agent import AgentCapability
from common.models.batch_job import BatchJobModel, JobStatus
from common.models.llm import CHAT_AI
from common.utils.http_exceptions import BadRequest
from common.utils.logging_handler import Logger
from config import get_agent_config
from services.agents.agents import BaseAgent
from services.agents.db_agent import run_db_agent
from services.agents.utils import agent_executor_arun_with_logs

Logger = Logger.get_logger(__file__)


def batch_execute_plan(request_body: Dict, job: BatchJobModel) -> Dict:
  # TODO
  pass


def get_agent_config_by_name(agent_name: str) -> dict:
  if agent_name in get_agent_config():
    return get_agent_config()[agent_name]
  return {}


def get_model_garden_agent_config() -> dict:
  planning_agents = \
      BaseAgent.get_agents_by_capability(AgentCapability.PLAN.value)
  return planning_agents


def get_plan_agent_config() -> dict:
  planning_agents = \
      BaseAgent.get_agents_by_capability(AgentCapability.PLAN.value)
  return planning_agents


def get_task_agent_config() -> dict:
  task_agents = \
      BaseAgent.get_agents_by_capability(AgentCapability.TASK.value)
  return task_agents


def get_all_agents() -> dict:
  """
  Return config dict for available agents
  """
  agent_config = get_agent_config()
  agent_config.update(get_plan_agent_config())
  return agent_config

async def batch_run_agent(request_body: Dict, job: BatchJobModel) -> Dict:
  # execute routing agent
  prompt = request_body["prompt"]
  agent_name = request_body["agent_name"]
  user_id = request_body["user_id"]
  chat_id = request_body["user_chat_id"]
  db_result_limit = request_body.get("db_result_limit", None)
  dataset = request_body.get("dataset", None)

  user = User.find_by_id(user_id)
  user_chat = UserChat.find_by_id(chat_id)
  user_chat.update_history(custom_entry={
    "batch_job": {
      "job_id": job.id,
      "job_name": job.name,
    },
  })
  user_chat.save(merge=True)

  agent_params = {}
  agent_params["db_result_limit"] = db_result_limit
  agent_params["user_email"] = user.email
  agent_params["dataset"] = dataset

  response_data, _ = await run_agent(
      agent_name, prompt, user_chat, agent_params)

  job.message = f"Successfully ran agent: {agent_name}"
  job.result_data = response_data
  job.status = JobStatus.JOB_STATUS_SUCCEEDED.value
  job.save()


async def run_agent(agent_name: str,
                    prompt: str,
                    user_chat: UserChat = None,
                    agent_params: dict = None) -> Tuple[str, str]:
  """
  Run an agent on user input

  Args:
      agent_name(str): Agent name
      prompt(str): the user input prompt
      user_chat(UserChat): previous chat for context
      agent_params(dict): dict of additional agent run params

  Returns:
      output(str): the output of the agent on the user input
      agent_logs(str): agent log stream
  """
  if agent_params is None:
    agent_params = {}
  chat_history = []
  if user_chat:
    chat_history = user_chat.history
  Logger.info(f"Running {agent_name} agent "
              f"with prompt=[{prompt}] and "
              f"chat_history=[{chat_history}]"
              f"agent_params=[{agent_params}]")

  llm_service_agent = BaseAgent.get_llm_service_agent(agent_name)

  agent_logs = ""
  output = ""
  agent_response = None
  response_data = {}
  chat_history_entry = {}

  if AgentCapability.DATABASE in llm_service_agent.capabilities():
    # handle database agent runs
    llm_type = llm_service_agent.llm_type
    dataset = agent_params.get("dataset", None)
    user_email = agent_params.get("user_email", None)
    db_result_limit = agent_params.get("db_result_limit", None)
    output, agent_logs = \
        await run_db_agent(prompt, llm_type=llm_type,
                           dataset=dataset, user_email=user_email,
                           db_result_limit=db_result_limit)
    if output.get("resources", None):
      chat_history_entry["resources"] = output.get("resources")
    if output.get("db_result", None):
      chat_history_entry["db_result"] = output.get("db_result")
    agent_response = output.get(f"{CHAT_AI}", None)
  else:
    tools = llm_service_agent.get_tools()
    tools_str = ", ".join(tool.name for tool in tools)

    Logger.info(f"Available tools=[{tools_str}]")
    langchain_agent = llm_service_agent.load_langchain_agent()

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=langchain_agent, tools=tools)

    chat_history = chat_history or []
    agent_inputs = {
      "input": prompt,
      "chat_history": chat_history
    }

    Logger.info("Running agent executor.... ")
    output, agent_logs = await agent_executor_arun_with_logs(
        agent_executor, agent_inputs)
    agent_response = output

  chat_history_entry["agent_logs"] = agent_logs or None
  response_data["content"] = output

  # add agent's thought process to response
  if agent_logs:
    response_data["agent_logs"] = agent_logs

  Logger.info(f"Chat data=[{response_data}]")

  # update chat data in response
  if user_chat:
    user_chat.update_history(response=agent_response,
                             custom_entry=chat_history_entry)
    chat_data = user_chat.get_fields(reformat_datetime=True)
    chat_data["id"] = user_chat.id
    response_data["chat"] = chat_data

  Logger.info(f"Agent {agent_name} generated"
              f" chat_history=[{chat_history_entry}]"
              f" output=[{response_data}] logs [{agent_logs}]")
  return response_data, agent_logs


async def agent_plan(agent_name: str,
                     prompt: str,
                     user_id: str,
                     chat_history: List = None) -> Tuple[str, UserPlan]:
  """
  Run an agent on user input to generate a plan

  Args:
      agent_name(str): Agent name
      prompt(str): the user input prompt
      chat_history(List): any previous chat history for context

  Returns:
      output(str): the output of the agent on the user input
      user_plan(str): user plan object created from agent plan
  """
  Logger.info(f"Starting with plan for "
              f"agent_name=[{agent_name}], "
              f"prompt=[{prompt}], user_id=[{user_id}], "
              f"chat_history=[{chat_history}]")
  planning_agents = get_plan_agent_config()
  if not agent_name in planning_agents.keys():
    raise BadRequest(f"{agent_name} is not a planning agent.")

  output = await run_agent(agent_name, prompt, chat_history)

  task_response = parse_agent_response("Plan:", output)
  raw_plan_steps = parse_action_output("Plan:", output)

  # create user plan

  user_plan = UserPlan(
      user_id=user_id,
      task_prompt=prompt,
      task_response=task_response,
      agent_name=agent_name)
  user_plan.save()

  # create PlanStep models
  plan_steps = [
      PlanStep(user_id=user_id,
               plan_id=user_plan.id,
               description=step_description,
               agent_name=agent_name)
      for step_description in raw_plan_steps]
  plan_step_ids = []
  for step in plan_steps:
    step.save()
    plan_step_ids.append(step.id)

  # save plan steps
  user_plan.plan_steps = plan_step_ids
  user_plan.update()

  Logger.info(f"Created steps using plan_agent_name=[{agent_name}] "
              f"raw_plan_steps={raw_plan_steps}")
  return output, user_plan


def parse_agent_response(header: str, text: str) -> str:
  """
  Parse agent response prior to action header
  """
  header_index = text.find(header)
  if header_index != -1:
    return text[:header_index]
  else:
    return text


def parse_action_output(header: str, text: str) -> List[str]:
  """
  Parse plans or routes from agent output, as delimited by a header.
  """
  Logger.info(f"Parsing agent output: {header}, {text}")

  # Regex pattern to match the steps after '<header>'
  # We are using the re.DOTALL flag to match across newlines and
  # re.MULTILINE to treat each line as a separate string
  steps_regex = re.compile(
      r"^\s*[\d#]+\..+?(?=\n\s*\d+|\Z)", re.MULTILINE | re.DOTALL)

  # Find the part of the text after header
  plan_part = re.split(header, text, flags=re.IGNORECASE)[-1]

  # Find all the steps within the '<header>' part
  steps = steps_regex.findall(plan_part)

  # strip whitespace
  steps = [step.strip() for step in steps]

  return steps


def parse_plan_step(text: str) -> dict:
  step_regex = re.compile(
      r"[\d|#]+\.\s.*\[(.*)\]\s?(.*)", re.DOTALL)
  matches = step_regex.findall(text)
  return matches


def parse_agent_execution_result(text):
  match_iter = re.finditer(
    r"(Action:|Observation:|Thought:|> Finished chain)", text)
  indices = [m.start(0) for m in match_iter]
  indices = [0] + indices + [len(text)]

  i = 0
  part_list = []
  while i < len(indices) - 1:
    pos_start = indices[i]
    pos_end = indices[i + 1]
    part_text = text[pos_start:pos_end]
    part_list.append(parse_agent_execution_chain(part_text))
    i += 1

  return part_list


def parse_agent_execution_chain(text):
  match = re.match(r"(Action|Observation|Thought):((.|\n)*)", text)
  if not match:
    return {
        "text_content": text,
    }

  part_type = match[1]
  part_dict = {
      "type": part_type
  }

  try:
    json_match = re.match(r"[\s\n]*```((.|\n)*)[\s\n]*```", match[2])
    if json_match:
      json_dict = ast.literal_eval(json_match[1].strip())
    else:
      json_dict = ast.literal_eval(match[2].strip())
    part_dict["json_content"] = json_dict

  except Exception:
    text_content = match[2]
    if text_content[:2] == "> ":
      text_content = text_content[2:]
    part_dict["text_content"] = match[2]

  return part_dict


async def agent_execute_plan(
        agent_name: str, user_plan: UserPlan = None) -> str:
  """
  Execute a given plan_steps.
  """
  Logger.info(f"Running {agent_name} agent "
              f"user_plan=[{user_plan}]")
  llm_service_agent = BaseAgent.get_llm_service_agent(agent_name)
  langchain_agent = llm_service_agent.load_langchain_agent()

  tools = llm_service_agent.get_tools()
  tools_str = ", ".join(tool.name for tool in tools)

  Logger.info(f"Available tools=[{tools_str}]")

  agent_executor = AgentExecutor.from_agent_and_tools(
    agent=langchain_agent,
    tools=tools,
    verbose=True)

  task_prompt = user_plan.task_prompt
  task_response = user_plan.task_response
  prompt = "Execute the plan provided below. "
  prompt += \
      f"The plan was created by an AI Planning Assistant." \
      f"The original task request by the human user was \"{task_prompt}\".\n" \
      f"The response of the planning agent was \"{task_response}\", \n" \
      f"followed by the plan listed below.\n" \
      f"Plan: \n"

  plan_steps = []
  for step in user_plan.plan_steps:
    description = PlanStep.find_by_id(step).description
    plan_steps.append(description)
  plan_steps_string = " ".join(plan_steps)
  agent_prompt = prompt + plan_steps_string
  agent_inputs = {
    "input": agent_prompt
  }
  Logger.info(f"Running agent executor.... input:{agent_prompt} ")

  # collect print-output to the string.
  output, agent_logs = await agent_executor_arun_with_logs(
      agent_executor, agent_inputs)

  Logger.info(f"Agent {agent_name} generated"
              f" output=[{output}]")

  agent_logs = parse_agent_execution_result(agent_logs)
  Logger.info(f"agent_logs: \n{agent_logs}")

  return output, agent_logs
