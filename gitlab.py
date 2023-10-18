"""
Helper functions for communication with Gitlab.

Allowing for interaction with the test results, e.g. with UI tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import requests

AnyDict = dict[Any, Any]

HERE = Path(__file__).parent

BRANCHES_API_TEMPLATE = "https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines.json?scope=branches&page={}"
GRAPHQL_API = "https://gitlab.com/api/graphql"


def _get_gitlab_branches(page: int) -> list[AnyDict]:
    return requests.get(BRANCHES_API_TEMPLATE.format(page)).json()["pipelines"]


def _get_branch_obj(branch_name: str) -> AnyDict:
    # Trying first 10 pages of branches
    for page in range(1, 11):
        branches = _get_gitlab_branches(page)
        for branch_obj in branches:
            if branch_obj["ref"]["name"] == branch_name:
                # TODO: make sure the tests have finished! We cannot use the incomplete pipeline
                return branch_obj
    raise ValueError(f"Branch {branch_name} not found")


def _get_pipeline_jobs_info(pipeline_iid: int) -> AnyDict:
    # Getting just the stuff we need - the job names and IDs
    graphql_query = """
query getJobsFromPipeline($projectPath: ID!, $iid: ID!) {
  project(fullPath: $projectPath) {
    pipeline(iid: $iid) {
      stages {
        nodes {
          groups {
            nodes {
              jobs {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
    """
    query = {
        "query": graphql_query,
        "variables": {
            "projectPath": "satoshilabs/trezor/trezor-firmware",
            "iid": pipeline_iid,
        },
    }
    return requests.post(GRAPHQL_API, json=query).json()


def _yield_pipeline_jobs(pipeline_iid: int) -> Iterator[AnyDict]:
    jobs_info = _get_pipeline_jobs_info(pipeline_iid)
    stages = jobs_info["data"]["project"]["pipeline"]["stages"]["nodes"]
    for stage in stages:
        nodes = stage["groups"]["nodes"]
        for node in nodes:
            jobs = node["jobs"]["nodes"]
            for job in jobs:
                yield job


def get_branch_job_ids(branch_name: str) -> dict[str, str]:
    branch_obj = _get_branch_obj(branch_name)
    pipeline_iid = branch_obj["iid"]
    res: dict[str, str] = {}
    for job in _yield_pipeline_jobs(pipeline_iid):
        job_id = job["id"].split("/")[-1]
        res[job["name"]] = job_id
    return res
