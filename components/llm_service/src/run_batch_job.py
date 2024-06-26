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

# pylint: disable = broad-except,unused-import
"""Entry point for batch job"""
import json
import asyncio
from absl import flags, app
from common.utils.config import (JOB_TYPE_QUERY_ENGINE_BUILD,
                                 JOB_TYPE_QUERY_EXECUTE,
                                 JOB_TYPE_AGENT_RUN,
                                 JOB_TYPE_AGENT_PLAN_EXECUTE,
                                 JOB_TYPE_ROUTING_AGENT)
from common.utils.logging_handler import Logger
from common.utils.kf_job_app import kube_delete_job
from common.models.batch_job import BatchJobModel, JobStatus
from services.query.query_service import (batch_build_query_engine,
                                          batch_query_generate)
from services.agents.routing_agent import batch_run_dispatch
from services.agents.agent_service import (batch_run_agent,
                                           batch_execute_plan)
from config import JOB_NAMESPACE

# pylint: disable=broad-exception-raised

Logger = Logger.get_logger(__file__)
FLAGS = flags.FLAGS
flags.DEFINE_string("container_name", "",
                    "Name of the container in which job is running")
flags.mark_flag_as_required("container_name")


def main(argv):
  """Entry point method for batch job"""
  try:
    del argv  # Unused.
    job = BatchJobModel.find_by_uuid(FLAGS.container_name)
    job.status = "active"
    job.update()
    request_body = json.loads(job.input_data)
    if job.type == JOB_TYPE_QUERY_ENGINE_BUILD:
      _ = asyncio.get_event_loop().run_until_complete(
      batch_build_query_engine(request_body, job))
    elif job.type ==  JOB_TYPE_QUERY_EXECUTE:
      _ = asyncio.get_event_loop().run_until_complete(
        batch_query_generate(request_body, job))
    elif job.type == JOB_TYPE_AGENT_RUN:
      _ = asyncio.get_event_loop().run_until_complete(
      batch_run_agent(request_body, job))
    elif job.type == JOB_TYPE_AGENT_PLAN_EXECUTE:
      _ = asyncio.get_event_loop().run_until_complete(
      batch_execute_plan(request_body, job))
    elif job.type == JOB_TYPE_ROUTING_AGENT:
      _ = asyncio.get_event_loop().run_until_complete(
        batch_run_dispatch(request_body, job))
    else:
      raise Exception("Invalid job type")

    job.status = JobStatus.JOB_STATUS_SUCCEEDED.value
    job.update()
    if JOB_NAMESPACE == "default":
      kube_delete_job(FLAGS.container_name, JOB_NAMESPACE)

  except Exception as e:
    Logger.info(f"Job failed. Error: {e}")
    job = BatchJobModel.find_by_uuid(FLAGS.container_name)
    job.status = "failed"
    job.errors = {"error_message": str(e)}
    job.update()
    Logger.info(f"Namespace: {JOB_NAMESPACE}")
    raise e


if __name__ == "__main__":
  Logger.info("run_batch_job file for llm-service was triggered")
  app.run(main)
