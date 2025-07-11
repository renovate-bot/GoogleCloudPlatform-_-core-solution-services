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
Models for LLM generation and chat
"""
from typing import List, Optional, TYPE_CHECKING
from fireo.fields import TextField, ListField, IDField
from common.models import BaseModel

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
  from common.models.llm_query import QueryEngine, QueryResult, QueryReference

# constants used as tags for chat history
CHAT_HUMAN = "HumanInput"
CHAT_AI = "AIOutput"
CHAT_FILE = "UploadedFile"
CHAT_FILE_URL = "FileURL"
CHAT_FILE_BASE64 = "FileContentsBase64"
CHAT_FILE_TYPE = "FileType"
CHAT_SOURCE = "Source"
CHAT_QUERY_RESULT = "QueryResult"
CHAT_QUERY_REFERENCES = "QueryReferences"
CHAT_QUERY_REFRENCE_READABLE = "ReadableQueryReference"

class UserChat(BaseModel):
  """
  UserChat ORM class
  """
  id = IDField()
  user_id = TextField(required=True)
  prompt = TextField(required=False, default="")
  title = TextField(required=False, default="")
  llm_type = TextField(required=False)
  agent_name = TextField(required=False)
  history = ListField(default=[])

  class Meta:
    ignore_none_field = False
    collection_name = BaseModel.DATABASE_PREFIX + "user_chats"

  @classmethod
  def find_by_user(cls,
                   user_id,
                   skip=0,
                   order_by="-created_time",
                   limit=1000):
    """
    Fetch all chats for user

    Args:
        user_id (str): User id
        skip (int, optional): number of chats to skip.
        order_by (str, optional): order list according to order_by field.
        limit (int, optional): limit till cohorts to be fetched.

    Returns:
        List[UserChat]: List of chats for user.

    """
    objects = cls.collection.filter(
        "user_id", "==", user_id).filter(
            "deleted_at_timestamp", "==",
            None).order(order_by).offset(skip).fetch(limit)
    return list(objects)

  @classmethod
  def get_history_entry(cls, prompt: str, response: str) -> List[dict]:
    """ Get history entry for query and response """
    entry = [{CHAT_HUMAN: prompt}, {CHAT_AI: response}]
    return entry

  def update_history(self,
                     prompt: str=None,
                     response: str=None,
                     custom_entry: dict=None,
                     query_engine: Optional["QueryEngine"]=None,
                     query_result: Optional["QueryResult"]=None,
                     query_references: Optional[List["QueryReference"]]=None,
                     query_refs_str: Optional[str]=None):
    """ Update history with query and response """

    if not self.history:
      self.history = []

    if prompt:
      self.history.append({CHAT_HUMAN: prompt})

    if response:
      self.history.append({CHAT_AI: response})

    if custom_entry:
      self.history.append(custom_entry)

    if query_engine:
      self.history.append({
        CHAT_SOURCE: {
          "id": query_engine.id,
          "name": query_engine.name,
          "type": query_engine.query_engine_type
        }
      })

    if query_result:
      self.history.append({CHAT_QUERY_RESULT: query_result.response})

    if all((x is not None) for x in
           (query_engine, query_references, query_refs_str)):
      reference_data = []
      for ref in query_references:
        ref_data = {
          "chunk_id": ref.chunk_id,
          "document_url": ref.document_url,
          "document_text": ref.document_text,
          "modality": ref.modality
        }
        if ref.chunk_url:
          ref_data["chunk_url"] = ref.chunk_url
        if ref.page is not None:
          ref_data["page"] = ref.page
        if ref.timestamp_start and ref.timestamp_stop:
          ref_data["timestamp_start"] = ref.timestamp_start
          ref_data["timestamp_stop"] = ref.timestamp_stop
        reference_data.append(ref_data)
      self.history.append({
        CHAT_SOURCE: {
          "id": query_engine.id,
          "name": query_engine.name,
          "type": query_engine.query_engine_type
        },
        CHAT_QUERY_REFERENCES: reference_data,
        CHAT_QUERY_REFRENCE_READABLE: query_refs_str
      })

    self.save(merge=True)

  @classmethod
  def is_human(cls, entry: dict) -> bool:
    return CHAT_HUMAN in entry.keys()

  @classmethod
  def is_ai(cls, entry: dict) -> bool:
    return CHAT_AI in entry.keys()

  @classmethod
  def is_file_bytes(cls, entry: dict) -> bool:
    return CHAT_FILE_BASE64 in entry

  @classmethod
  def is_file_uri(cls, entry: dict) -> bool:
    return CHAT_FILE_URL in entry

  @classmethod
  def is_source(cls, entry: dict) -> bool:
    return CHAT_SOURCE in entry

  @classmethod
  def is_query_result(cls, entry: dict) -> bool:
    return CHAT_QUERY_RESULT in entry

  @classmethod
  def is_query_references(cls, entry: dict) -> bool:
    return CHAT_QUERY_REFERENCES in entry

  @classmethod
  def is_full_query_response(cls, entry: dict) -> bool:
    return (CHAT_QUERY_REFERENCES in entry and
            CHAT_SOURCE in entry and
            CHAT_QUERY_REFRENCE_READABLE in entry)

  @classmethod
  def get_file_b64(cls, entry: dict) -> str:
    return entry[CHAT_FILE_BASE64]

  @classmethod
  def get_file_type(cls, entry: dict) -> str:
    return entry[CHAT_FILE_TYPE]

  @classmethod
  def get_file_uri(cls, entry: dict) -> str:
    return entry[CHAT_FILE_URL]

  @classmethod
  def get_source(cls, entry: dict) -> dict:
    return entry[CHAT_SOURCE]

  @classmethod
  def get_query_result(cls, entry: dict) -> str:
    return entry[CHAT_QUERY_RESULT]

  @classmethod
  def get_query_references(cls, entry: dict) -> List[dict]:
    return entry[CHAT_QUERY_REFERENCES]

  @classmethod
  def entry_content(cls, entry: dict) -> str:
    return list(entry.values())[0]

  @classmethod
  def convert_query_response_to_chat_entry(cls, entry: dict) -> str:
    if not cls.is_full_query_response(entry):
      return ""
    return (f"A search of the {entry[CHAT_SOURCE]['name']} Source produced "
              f"these references: {entry[CHAT_QUERY_REFRENCE_READABLE]}")

