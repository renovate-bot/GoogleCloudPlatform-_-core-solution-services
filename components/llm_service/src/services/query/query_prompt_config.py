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
Query prompt templates
"""

from langchain.prompts import PromptTemplate

prompt_template = """
You are a helpful and truthful AI Assistant.
Use the following pieces of context and the chat history to answer the question at the end.
Do not answer anything other than the final question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context:
{context}

Chat History:
{chat_history}

Question: {question}
Helpful Answer:"""

QUESTION_PROMPT = PromptTemplate(
    template=prompt_template, input_variables=[
        "context", "chat_history", "question"
    ]
)

llama2_prompt_template = """
[INST]<<SYS>>You are a helpful and truthful AI search assistant for NASA.
Only respond to the final Human input at the end.
Use the following pieces of context to answer the question at the end.
If the answer is not in the context provided,
just say that you don't know, don't try to make up an answer.<</SYS>>

{context}

{chat_history}

Human input: {question}[/INST]"""

LLAMA2_QUESTION_PROMPT = PromptTemplate(
    template=llama2_prompt_template, input_variables=[
        "context", "chat_history", "question"
    ]
)

summary_template = """
Summarize the following text in three sentences or less:
{original_text}
"""

SUMMARY_PROMPT = PromptTemplate(
    template=summary_template, input_variables=["original_text"]
)
