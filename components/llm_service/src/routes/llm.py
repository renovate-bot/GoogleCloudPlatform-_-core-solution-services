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

# pylint: disable = broad-except

""" LLM endpoints """
from base64 import b64decode
from fastapi import APIRouter

from common.utils.logging_handler import Logger
from common.utils.errors import (PayloadTooLargeError)
from common.utils.http_exceptions import (InternalServerError, BadRequest)
from config import (PAYLOAD_FILE_SIZE,
                    ERROR_RESPONSES, get_model_config)
from schemas.llm_schema import (LLMGenerateModel,
                                LLMMultiGenerateModel,
                                LLMGetTypesResponse,
                                LLMGetEmbeddingTypesResponse,
                                LLMGenerateResponse,
                                LLMEmbeddingsResponse,
                                LLMMultiEmbeddingsResponse,
                                LLMEmbeddingsModel,
                                LLMMultiEmbeddingsModel)
from services.llm_generate import llm_generate, llm_generate_multi
from services.embeddings import get_embeddings, get_multi_embeddings
from utils.file_helper import validate_multi_vision_file_type

router = APIRouter(prefix="/llm", tags=["LLMs"], responses=ERROR_RESPONSES)

Logger = Logger.get_logger(__file__)

@router.get(
    "",
    name="Get all LLM types",
    response_model=LLMGetTypesResponse)
def get_llm_list():
  """
  Get available LLMs

  Returns:
      LLMGetTypesResponse
  """
  try:
    return {
      "success": True,
      "message": "Successfully retrieved llm types",
      "data": get_model_config().get_llm_types()
    }
  except Exception as e:
    raise InternalServerError(str(e)) from e


@router.get(
    "/embedding_types",
    name="Get supported embedding types",
    response_model=LLMGetEmbeddingTypesResponse)
def get_embedding_types():
  """
  Get supported embedding types

  Returns:
      LLMGetEmbeddingTypesResponse
  """
  try:
    return {
      "success": True,
      "message": "Successfully retrieved embedding types",
      "data": get_model_config().get_embedding_types()
    }
  except Exception as e:
    raise InternalServerError(str(e)) from e

@router.post(
    "/embedding",
    name="Generate embeddings from LLM",
    response_model=LLMEmbeddingsResponse)
async def generate_embeddings(embeddings_config: LLMEmbeddingsModel):
  """
  Generate embeddings with an LLM

  Args:
      embeddings_config: Input config dictionary,
        including text(str) and embedding_type(str) type for model

  Returns:
      LLMEmbeddingsResponse
  """
  embeddings_config_dict = {**embeddings_config.dict()}
  text = embeddings_config_dict.get("text")
  if text is None or text == "":
    return BadRequest("Missing or invalid payload parameters")

  if len(text) > PAYLOAD_FILE_SIZE:
    return PayloadTooLargeError(
      f"Text must be less than {PAYLOAD_FILE_SIZE}")

  embedding_type = embeddings_config_dict.get("embedding_type")

  try:
    _, embeddings = await get_embeddings(text, embedding_type)

    return {
        "success": True,
        "message": "Successfully generated embeddings",
        "data": embeddings
    }
  except Exception as e:
    raise InternalServerError(str(e)) from e

@router.post(
    "/embedding/multi",
    name="Generate multimodal embeddings from LLM",
    response_model=LLMMultiEmbeddingsResponse)
async def generate_embeddings_multi(embeddings_config: LLMMultiEmbeddingsModel):
  """
  Generate multimodal embeddings with an LLM

  Args:
      embeddings_config: Input config dictionary, user_file_b64(str),
        user_file_name(str), text(str), and embedding_type(str) type for model

  Returns:
      LLMMultiEmbeddingsResponse
  """
  embeddings_config_dict = {**embeddings_config.dict()}
  text = embeddings_config_dict.get("text")
  embedding_type = embeddings_config_dict.get("embedding_type")
  user_file_b64 = embeddings_config_dict.get("user_file_b64")
  user_file_name = embeddings_config_dict.get("user_file_name")

  if (user_file_b64 is None or user_file_b64 == "" or
    user_file_name is None or user_file_name == "" or
    text is None or text == ""):
    return BadRequest("Missing or invalid payload parameters")

  if len(text) > PAYLOAD_FILE_SIZE:
    return PayloadTooLargeError(
      f"Text must be less than {PAYLOAD_FILE_SIZE}")


  is_file_valid, user_file_extension = validate_multi_vision_file_type(
                                        user_file_name, user_file_b64)
  if not is_file_valid or user_file_extension.startswith("video"):
    return BadRequest("File type must be a supported image.")

  try:
    user_file_bytes = b64decode(user_file_b64)
    embeddings = \
        await get_multi_embeddings(text, user_file_bytes, embedding_type)

    return {
        "success": True,
        "message": "Successfully generated embeddings",
        "data": embeddings
    }
  except Exception as e:
    raise InternalServerError(str(e)) from e

@router.post(
    "/generate",
    name="Generate text from LLM",
    response_model=LLMGenerateResponse)
async def generate(gen_config: LLMGenerateModel):
  """
  Generate text with an LLM

  Args:
      gen_config: Input config dictionary,
        including prompt(str) and llm_type(str) type for model

  Returns:
      LLMGenerateResponse
  """
  genconfig_dict = {**gen_config.dict()}

  prompt = genconfig_dict.get("prompt")
  if prompt is None or prompt == "":
    return BadRequest("Missing or invalid payload parameters")

  if len(prompt) > PAYLOAD_FILE_SIZE:
    return PayloadTooLargeError(
      f"Prompt must be less than {PAYLOAD_FILE_SIZE}")

  llm_type = genconfig_dict.get("llm_type")

  try:
    result = await llm_generate(prompt, llm_type)

    return {
        "success": True,
        "message": "Successfully generated text",
        "content": result
    }
  except Exception as e:
    raise InternalServerError(str(e)) from e

@router.post(
    "/generate/multi",
    name="Generate text with a multimodal LLM",
    response_model=LLMGenerateResponse)
async def generate_multi(gen_config: LLMMultiGenerateModel):
  """
  Generate text with a multimodal LLM

  Args:
      gen_config: Input config dictionary,
        including user_file_b64(str), user_file_name(str),
        prompt(str), and llm_type(str) type for model

  Returns:
      LLMMultiGenerateResponse
  """
  genconfig_dict = {**gen_config.dict()}
  user_file_b64 = genconfig_dict.get("user_file_b64")
  user_file_name = genconfig_dict.get("user_file_name")
  prompt = genconfig_dict.get("prompt")
  llm_type = genconfig_dict.get("llm_type")

  if (user_file_b64 is None or user_file_b64 == "" or
    user_file_name is None or user_file_name == "" or
    prompt is None or prompt == ""):
    return BadRequest("Missing or invalid payload parameters")

  if len(prompt) > PAYLOAD_FILE_SIZE:
    return PayloadTooLargeError(
      f"Prompt must be less than {PAYLOAD_FILE_SIZE}")

  # Make sure that the user file is a valid image or video
  is_file_valid, user_file_extension = validate_multi_vision_file_type(
                                        user_file_name, user_file_b64)
  if not is_file_valid or not user_file_extension:
    return BadRequest("File type must be a supported image or video.")

  try:
    user_file_bytes = b64decode(user_file_b64)
    result = await llm_generate_multi(prompt, user_file_bytes,
                                    user_file_extension, llm_type)

    return {
        "success": True,
        "message": "Successfully generated text",
        "content": result
    }
  except Exception as e:
    raise InternalServerError(str(e)) from e
