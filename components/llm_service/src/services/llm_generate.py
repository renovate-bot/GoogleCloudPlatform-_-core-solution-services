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
"""
LLM Generation Service
"""
# pylint: disable=import-outside-toplevel,line-too-long
import time
from typing import Optional, List
import google.cloud.aiplatform
from vertexai.preview.language_models import (ChatModel, TextGenerationModel)
from vertexai.preview.generative_models import (
    GenerativeModel, Part, GenerationConfig, HarmCategory, HarmBlockThreshold)
from common.config import PROJECT_ID, REGION
from common.models import UserChat, UserQuery
from common.utils.errors import ResourceNotFoundException
from common.utils.http_exceptions import InternalServerError
from common.utils.logging_handler import Logger
from common.utils.request_handler import post_method
from common.utils.token_handler import UserCredentials
from config import (get_model_config, get_provider_models,
                    get_provider_value, get_provider_model_config,
                    get_model_config_value,
                    PROVIDER_VERTEX, PROVIDER_TRUSS,
                    PROVIDER_MODEL_GARDEN, PROVIDER_VLLM,
                    PROVIDER_LANGCHAIN, PROVIDER_LLM_SERVICE,
                    KEY_MODEL_ENDPOINT, KEY_MODEL_NAME,
                    KEY_MODEL_PARAMS, KEY_MODEL_CONTEXT_LENGTH,
                    DEFAULT_LLM_TYPE, DEFAULT_MULTIMODAL_LLM_TYPE)
from services.langchain_service import langchain_llm_generate
from utils.errors import ContextWindowExceededException

Logger = Logger.get_logger(__file__)

# A conservative characters-per-token constant, used to check
# whether prompt length exceeds context window size
CHARS_PER_TOKEN = 3

async def llm_generate(prompt: str, llm_type: str) -> str:
  """
  Generate text with an LLM given a prompt.
  Args:
    prompt: the text prompt to pass to the LLM
    llm_type: the type of LLM to use (default to openai)
  Returns:
    the text response: str
  """
  Logger.info(f"Generating text with an LLM given a prompt={prompt},"
              f" llm_type={llm_type}")
  # default to openai LLM
  if llm_type is None:
    llm_type = DEFAULT_LLM_TYPE

  try:
    start_time = time.time()

    # check whether the context length exceeds the limit for the model
    check_context_length(prompt, llm_type)

    # call the appropriate provider to generate the chat response
    # for Google models, prioritize native client over langchain
    chat_llm_types = get_model_config().get_chat_llm_types()
    if llm_type in get_provider_models(PROVIDER_LLM_SERVICE):
      is_chat = llm_type in chat_llm_types
      response = await llm_service_predict(prompt, is_chat, llm_type)
    elif llm_type in get_provider_models(PROVIDER_TRUSS):
      model_endpoint = get_provider_value(
          PROVIDER_TRUSS, KEY_MODEL_ENDPOINT, llm_type)
      response = await llm_truss_service_predict(
          llm_type, prompt, model_endpoint)
    elif llm_type in get_provider_models(PROVIDER_VLLM):
      model_endpoint = get_provider_value(
          PROVIDER_VLLM, KEY_MODEL_ENDPOINT, llm_type)
      response = await llm_vllm_service_predict(
          llm_type, prompt, model_endpoint)
    elif llm_type in get_provider_models(PROVIDER_MODEL_GARDEN):
      response = await model_garden_predict(prompt, llm_type)
    elif llm_type in get_provider_models(PROVIDER_VERTEX):
      google_llm = get_provider_value(
          PROVIDER_VERTEX, KEY_MODEL_NAME, llm_type)
      if google_llm is None:
        raise RuntimeError(
            f"Vertex model name not found for llm type {llm_type}")
      is_chat = llm_type in chat_llm_types
      is_multimodal = False
      response = await google_llm_predict(
        prompt, is_chat, is_multimodal, google_llm)
    elif llm_type in get_provider_models(PROVIDER_LANGCHAIN):
      response = await langchain_llm_generate(prompt, llm_type)
    else:
      raise ResourceNotFoundException(f"Cannot find llm type '{llm_type}'")

    process_time = round(time.time() - start_time)
    Logger.info(f"Received response in {process_time} seconds from "
                f"model with llm_type={llm_type}.")
    return response
  except Exception as e:
    raise InternalServerError(str(e)) from e

async def llm_generate_multimodal(prompt: str, llm_type: str, user_file_types: List[str],
                             user_file_bytes: bytes = None,
                             user_file_urls: List[str] = None) -> str:
  """
  Generate text with an LLM given a file and a prompt.
  Args:
    prompt: the text prompt to pass to the LLM
    user_file_bytes: bytes of the file provided by the user
    user_file_urls: list of URLs to include in context
    user_file_types: list of mime times for files to include in context
    llm_type: the type of LLM to use (default to gemini)
  Returns:
    the text response: str
  """
  Logger.info(f"Generating text with an LLM given a prompt={prompt},"
              f" user_file_bytes=bytes, llm_type={llm_type}")
  # default to Gemini multimodal LLM
  if llm_type is None:
    llm_type = DEFAULT_MULTIMODAL_LLM_TYPE

  try:
    start_time = time.time()

    # for Google models, prioritize native client over langchain
    chat_llm_types = get_model_config().get_chat_llm_types()
    multimodal_llm_types = get_model_config().get_multimodal_llm_types()
    if llm_type in get_provider_models(PROVIDER_VERTEX):
      google_llm = get_provider_value(
          PROVIDER_VERTEX, KEY_MODEL_NAME, llm_type)
      if google_llm is None:
        raise RuntimeError(
            f"Vertex model name not found for llm type {llm_type}")
      is_chat = llm_type in chat_llm_types
      is_multimodal = llm_type in multimodal_llm_types
      if not is_multimodal:
        raise RuntimeError(
            f"Vertex model {llm_type} needs to be multimodal")
      response = await google_llm_predict(prompt, is_chat, is_multimodal,
                            google_llm, None, user_file_bytes,
                            user_file_urls, user_file_types)
    else:
      raise ResourceNotFoundException(f"Cannot find llm type '{llm_type}'")

    process_time = round(time.time() - start_time)
    Logger.info(f"Received response in {process_time} seconds from "
                f"model with llm_type={llm_type}.")
    return response
  except Exception as e:
    raise InternalServerError(str(e)) from e

#SC240930: MAKE INPUT ARGS OPTIONAL: chat_file_type, chat_file_urls, chat_file_bytes
async def llm_chat(prompt: str, llm_type: str,
                   user_chat: Optional[UserChat] = None,
                   user_query: Optional[UserQuery] = None,
                   chat_file_types: List[str] = None,
                   chat_file_urls: List[str] = None,
                   chat_file_bytes: bytes = None) -> str:
  """
  Send a prompt to a chat model and return string response.
  Supports including a file in the chat context, either by URL or
  directly from file content.

  Args:
    prompt: the text prompt to pass to the LLM
    llm_type: the type of LLM to use
    user_chat (optional): a user chat to use for context
    user_query (optional): a user query to use for context
    chat_file_bytes (bytes): bytes of file to include in chat context
    chat_file_urls (List[str]): urls of files to include in chat context
    chat_file_type (str): mime type of file to include in chat context #SC241001
    chat_file_types (List[str]): mime types of files to include in chat context
  Returns:
    the text response: str
  """
  Logger.info(f"#SC240930: Just entered llm_chat")
  chat_file_bytes_log = chat_file_bytes[:10] if chat_file_bytes else None
  Logger.info(f"Generating chat with llm_type=[{llm_type}],"
              f" prompt=[{prompt}]"
              f" user_chat=[{user_chat}]"
              f" user_query=[{user_query}]"
              f" chat_file_bytes=[{chat_file_bytes_log}]"
              f" chat_file_urls=[{chat_file_urls}]"
              f" chat_file_type=[{chat_file_types}]")

  if llm_type not in get_model_config().get_chat_llm_types():
    raise ResourceNotFoundException(f"Cannot find chat llm type '{llm_type}'")

  # validate chat file params
  is_multimodal = False
  if chat_file_bytes is not None or chat_file_urls:
    if chat_file_bytes is not None and chat_file_urls:
      raise InternalServerError(
          "Must set only one of chat_file_bytes/chat_file_urls")
    if llm_type not in get_provider_models(PROVIDER_VERTEX):
      raise InternalServerError("Chat files only supported for Vertex")
    if chat_file_types is None:
      raise InternalServerError("Mime type must be passed for chat file")
    is_multimodal = True

  try:
    response = None

    # add chat history to prompt if necessary
    Logger.info(f"#SC240930: In llm_chat: {user_chat=}")
    Logger.info(f"#SC240930: In llm_chat: {user_query=}")
    if user_chat is not None or user_query is not None:
      Logger.info(f"#SC240930: About to enter get_context_prompt")
      context_prompt = get_context_prompt(
          user_chat=user_chat, user_query=user_query)
      # context_prompt includes only text (no images/video) from
      # user_chat.history and user_query.history
      Logger.info(f"#SC240930: Just exited get_context_prompt")
      Logger.info(f"#SC240930: In llm_chat: {context_prompt=}")
      Logger.info(f"#SC240930: In llm_chat: {prompt=}")
      prompt = context_prompt + "\n" + prompt
      Logger.info(f"#SC240930: In llm_chat: Updated {prompt=}")

    # check whether the context length exceeds the limit for the model
    Logger.info(f"#SC240930: About to enter check_context_length")
    check_context_length(prompt, llm_type)
    Logger.info(f"#SC240930: Just exited check_context_length")

    # call the appropriate provider to generate the chat response
    if llm_type in get_provider_models(PROVIDER_LLM_SERVICE):
      is_chat = True
      response = await llm_service_predict(
          prompt, is_chat, llm_type, user_chat)
    elif llm_type in get_provider_models(PROVIDER_TRUSS):
      model_endpoint = get_provider_value(
          PROVIDER_TRUSS, KEY_MODEL_ENDPOINT, llm_type)
      response = await llm_truss_service_predict(
          llm_type, prompt, model_endpoint)
    elif llm_type in get_provider_models(PROVIDER_VLLM):
      model_endpoint = get_provider_value(
          PROVIDER_VLLM, KEY_MODEL_ENDPOINT, llm_type)
      response = await llm_vllm_service_predict(
          llm_type, prompt, model_endpoint)
    elif llm_type in get_provider_models(PROVIDER_MODEL_GARDEN):
      response = await model_garden_predict(prompt, llm_type)
    elif llm_type in get_provider_models(PROVIDER_VERTEX):
      google_llm = get_provider_value(
          PROVIDER_VERTEX, KEY_MODEL_NAME, llm_type)
      if google_llm is None:
        raise RuntimeError(
            f"Vertex model name not found for llm type {llm_type}")
      is_chat = True
      Logger.info(f"#SC240930: About to enter google_llm_predict")
      response = await google_llm_predict(prompt, is_chat, is_multimodal,
                                          google_llm, user_chat,
                                          chat_file_bytes,
                                          chat_file_urls, chat_file_types)
      Logger.info(f"#SC240930: Just existed google_llm_predict")
    elif llm_type in get_provider_models(PROVIDER_LANGCHAIN):
      response = await langchain_llm_generate(prompt, llm_type, user_chat)
    Logger.info(f"#SC240930: About to exit llm_chat with NO exception")
    return response
  except Exception as e:
    import traceback
    Logger.error(traceback.print_exc())
    Logger.info(f"#SC240930: About to exit llm_chat WITH exception")
    raise InternalServerError(str(e)) from e

def get_context_prompt(user_chat=None,
                       user_query=None) -> str:
  """
  Get context prompt for chat based on previous chat or query history.

  Args:
    user_chat (optional): previous user chat
    user_query (optional): previous user query
  Returns:
    string context prompt
  """
  context_prompt = ""
  prompt_list = []
  if user_chat is not None:
    history = user_chat.history
    for entry in history:
      content = UserChat.entry_content(entry)
      if UserChat.is_human(entry):
        prompt_list.append(f"Human input: {content}")
      elif UserChat.is_ai(entry):
        prompt_list.append(f"AI response: {content}")
      # prompt_list includes only text from user_chat.history

  if user_query is not None:
    history = user_query.history
    for entry in history:
      content = UserQuery.entry_content(entry)
      if UserQuery.is_human(entry):
        prompt_list.append(f"Human input: {content}")
      elif UserQuery.is_ai(entry):
        prompt_list.append(f"AI response: {content}")
      # prompt_list includes only text from user_query.history

  Logger.info(f"#SC240930: In get_context_prompt: {prompt_list=}")
  Logger.info(f"#SC240930: In get_context_prompt: about to do the join on prompt_list, for which all elements should be strings")
  context_prompt = "\n\n".join(prompt_list)
  Logger.info(f"#SC240930: In get_context_prompt: just finished the join on prompt_list, for which all elements should be strings")
  Logger.info(f"#SC240930: In get_context_prompt: {context_prompt=}")

  Logger.info("f#SC240930: About to exit get_context_prompt")
  return context_prompt

def check_context_length(prompt, llm_type):
  """
  Check whether a prompt exceeds the maximum context length for
  a model.

  Raise an exception if max context length exceeded.
  """
  # check if prompt exceeds context window length for model
  # assume a constant relationship between tokens and chars
  # TODO: Recalculate max_context_length for text prompt,
  # subtracting out tokens used by non-text context (image, video, etc)
  token_length = len(prompt) / CHARS_PER_TOKEN
  max_context_length = get_model_config_value(llm_type,
                                              KEY_MODEL_CONTEXT_LENGTH,
                                              None)
  if max_context_length and token_length > max_context_length:
    msg = f"Token length {token_length} exceeds llm_type {llm_type} " + \
          f"Max context length {max_context_length}"
    Logger.error(msg)
    raise ContextWindowExceededException(msg)

async def llm_truss_service_predict(llm_type: str, prompt: str,
                                    model_endpoint: str,
                                    parameters: dict = None) -> str:
  """
  Send a prompt to an instance of the LLM service and return response.
  Args:
    llm_type:
    prompt: the text prompt to pass to the LLM
    model_endpoint: model endpoint ip to be used for prediction and port number
      (e.g: xx.xxx.xxx.xx:8080)
    parameters (optional):  parameters to be used for prediction
  Returns:
    the text response: str
  """
  if parameters is None:
    parameters = get_provider_value(
        PROVIDER_TRUSS, KEY_MODEL_PARAMS, llm_type)

  parameters.update({"prompt": f"'{prompt}'"})

  api_url = f"http://{model_endpoint}/v1/models/model:predict"
  Logger.info(f"Generating text using Truss Hosted Model "
              f"api_url=[{api_url}], prompt=[{prompt}], "
              f"parameters=[{parameters}.")

  resp = post_method(api_url, request_body=parameters)

  if resp.status_code != 200:
    raise InternalServerError(
      f"Error status {resp.status_code}: {str(resp)}")

  json_response = resp.json()

  Logger.info(f"Got LLM service response {json_response}")
  output = json_response["data"]["generated_text"]

  # if the prompt is repeated as part of the response, remove it
  output = output.replace(prompt, "").strip()
  # Llama 2 often adds quotes
  if output.startswith('"') or output.startswith("'"):
    output = output[1:]
  if output.endswith('"') or output.endswith("'"):
    output = output[:-1]

  return output

async def llm_vllm_service_predict(llm_type: str, prompt: str,
                                   model_endpoint: str,
                                   parameters: dict = None) -> str:
  """
  Send a prompt to an instance of the LLM service and return response.
  Args:
    llm_type:
    prompt: the text prompt to pass to the LLM
    model_endpoint: model endpoint ip to be used for prediction and port number
      (e.g: xx.xxx.xxx.xx:8080)
    parameters (optional):  parameters to be used for prediction
  Returns:
    the text response: str
  """
  if parameters is None:
    parameters = get_provider_value(
        PROVIDER_VLLM, KEY_MODEL_PARAMS, llm_type)

  parameters.update({"prompt": f"<start_of_turn>user\n{prompt}<end_of_turn>\n"})

  api_url = f"http://{model_endpoint}/generate"
  Logger.info(f"Generating text using vLLM Hosted Model "
              f"api_url=[{api_url}], prompt=[{prompt}], "
              f"parameters=[{parameters}.")

  resp = post_method(api_url, request_body=parameters)

  if resp.status_code != 200:
    raise InternalServerError(
      f"Error status {resp.status_code}: {str(resp)}")

  json_response = resp.json()

  Logger.info(f"Got LLM service response {json_response}")
  output = json_response["data"]["generated_text"]

  # if the prompt is repeated as part of the response, remove it
  output = output.replace(prompt, "")

  return output

async def llm_service_predict(prompt: str, is_chat: bool,
                              llm_type: str, user_chat=None,
                              auth_token: str = None) -> str:

  """
  Send a prompt to an instance of the LLM service and return response.

  Args:
    prompt: the text prompt to pass to the LLM
    is_chat: true if the model is a chat model
    llm_type: the type of LLM to use
    user_chat (optional): a user chat to use for context
    auth_token:

  Returns:
    the text response: str
  """
  llm_service_config = get_model_config().get_provider_config(
      PROVIDER_LLM_SERVICE, llm_type)
  if not auth_token:
    auth_client = UserCredentials(llm_service_config.get("user"),
                                  llm_service_config.get("password"))
    auth_token = auth_client.get_id_token()

  # start with base url of the LLM service we are calling
  api_url = llm_service_config.get(KEY_MODEL_ENDPOINT)

  if is_chat:
    if user_chat:
      path = "/chat/{user_chat.id}"
    else:
      path = "/chat"
  else:
    path = "/llm/generate"
  api_url = api_url + path

  request_body = {
    "prompt": prompt,
    "llm_type": llm_type
  }

  Logger.info(f"Sending LLM service request to {api_url}")
  resp = post_method(api_url,
                     request_body=request_body,
                     token=auth_token)

  if resp.status_code != 200:
    raise InternalServerError(
      f"Error status {resp.status_code}: {str(resp)}")

  json_response = resp.json()

  Logger.info(f"Got LLM service response {json_response}")
  output = json_response["content"]
  return output

async def model_garden_predict(prompt: str,
                               llm_type: str,
                               parameters: dict = None) -> str:
  """
  Generate text with a Model Garden model.
  Args:
    prompt: the text prompt to pass to the LLM
    llm_type:
    parameters (optional):  parameters to be used for prediction
  Returns:
    the prediction text.
  """
  aip_endpoint_name = get_provider_value(
      PROVIDER_MODEL_GARDEN, KEY_MODEL_ENDPOINT, llm_type)

  aip_endpoint = f"projects/{PROJECT_ID}/locations/" \
                 f"{REGION}/endpoints/{aip_endpoint_name}"
  Logger.info(f"Generating text using Model Garden "
              f"endpoint=[{aip_endpoint}], prompt=[{prompt}], "
              f"parameters=[{parameters}.")

  if parameters is None:
    parameters = get_provider_value(PROVIDER_MODEL_GARDEN,
                                    KEY_MODEL_PARAMS, llm_type)

  parameters.update({"prompt": f"'{prompt}'"})

  instances = [parameters, ]
  endpoint_without_peft = google.cloud.aiplatform.Endpoint(aip_endpoint)

  response = await endpoint_without_peft.predict_async(instances=instances)

  predictions_text = "\n".join(response.predictions)
  Logger.info(f"Received response from "
              f"{response.model_resource_name} version="
              f"[{response.model_version_id}] with {len(response.predictions)}"
              f" prediction(s) = [{predictions_text}] ")

  return predictions_text

#SC240930: Make user_file_bytes, user_file_urls, and user_file_types all Optional?
async def google_llm_predict(prompt: str, is_chat: bool, is_multimodal: bool,
                google_llm: str, user_chat=None,
                user_file_bytes: bytes=None,
                user_file_urls: List[str]=None,
                user_file_types: List[str]=None) -> str:
  """
  Generate text with a Google multimodal LLM given a prompt.
  Args:
    prompt: the text prompt to pass to the LLM
    is_chat: true if the model is a chat model
    is_multimodal: true if the model is a multimodal model
    google_llm: name of the vertex llm model
    user_chat: chat history
    user_file_bytes: the bytes of the file provided by the user
    user_file_urls: list of urls of files provided by the user
    user_file_types: list of mime types of the files provided by the user
  Returns:
    the text response.
  """
  Logger.info(f"#SC240930: Just entered google_llm_predict")
  user_file_bytes_log = user_file_bytes[:10] if user_file_bytes else None
  Logger.info(f"Generating text with a Google multimodal LLM:"
              f" prompt=[{prompt}], is_chat=[{is_chat}],"
              f" is_multimodal=[{is_multimodal}], google_llm=[{google_llm}],"
              f" user_file_bytes=[{user_file_bytes_log}],"
              f" user_file_urls=[{user_file_urls}],"
              f" user_file_type=[{user_file_types}].")

  # TODO: Consider images in chat
  prompt_list = []
  if user_chat is not None:
    history = user_chat.history
    for entry in history:
      content = UserChat.entry_content(entry)
      if UserChat.is_human(entry):
        prompt_list.append(f"Human input: {content}")
      elif UserChat.is_ai(entry):
        prompt_list.append(f"AI response: {content}")
      # prompt_list includes only text (no images/video)
      # from user_chat.history
  prompt_list.append(prompt)
  context_prompt = "\n\n".join(prompt_list)

  # Get model params. If params are set at the model level
  # use those else use global vertex params.
  parameters = {}
  provider_config = get_provider_model_config(PROVIDER_VERTEX)
  for _, model_config in provider_config.items():
    model_name = model_config.get(KEY_MODEL_NAME)
    if model_name == google_llm and KEY_MODEL_PARAMS in model_config:
      parameters = model_config.get(KEY_MODEL_PARAMS)
  else:
    parameters = get_provider_value(PROVIDER_VERTEX,
                                    KEY_MODEL_PARAMS)

  try:
    if is_chat:
      # gemini uses new "GenerativeModel" class and requires different params
      if "gemini" in google_llm:
        # TODO: fix safety settings
        safety_settings = {
             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        }
        chat_model = GenerativeModel(google_llm)
        if is_multimodal:
          user_file_parts = []
          if user_file_bytes is not None:
            user_file_parts = [Part.from_data(user_file_bytes,
                                              mime_type=user_file_types[0])]
            #SC241001: CHANGE INPUT ARG user_file_bytes to also be a list (of bytes), one for each uploaded file
          elif user_file_urls is not None:
            user_file_parts = [
              Part.from_uri(user_file_url, mime_type=user_file_type)
              for user_file_url, user_file_type in zip(user_file_urls, user_file_types)
            ]
          else:
            raise RuntimeError(
                "if is_multimodal one of user_file_bytes or user_file_urls must be set")
          context_list = [*user_file_parts, context_prompt]
          Logger.info(f"context list {context_list}")
          generation_config = GenerationConfig(**parameters)
          response = await chat_model.generate_content_async(context_list,
              generation_config=generation_config)
        else:
          chat = chat_model.start_chat()
          response = await chat.send_message_async(context_prompt,
              generation_config=parameters, safety_settings=safety_settings)
      else:
        chat_model = ChatModel.from_pretrained(google_llm)
        chat = chat_model.start_chat()
        response = await chat.send_message_async(context_prompt, **parameters)
    else:
      text_model = TextGenerationModel.from_pretrained(google_llm)
      response = await text_model.predict_async(
          context_prompt,
          **parameters,
      )
    Logger.info(f"#SC240930: About to exit google_llm_predict, with NO exception")

  except Exception as e:
    Logger.info(f"#SC240930: About to exit google_llm_predict, WITH exception")
    raise InternalServerError(str(e)) from e

  Logger.info(f"Received response from the Model [{response.text}]")
  response = response.text

  return response
