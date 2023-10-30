from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin

import click
import requests

from common import (
    MODEL_DIR_MAPPING,
    MODEL_FILE_MAPPING,
    get_latest_test_report_url,
    get_screen_text_content,
    save_job_id_mapping,
)
from gitlab import get_branch_job_ids

OVERWRITE = False
DEBUG = False
DEFAULT_BRANCH = "main"


@lru_cache(maxsize=None)
def get_html_content(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def get_image_content(url: str) -> bytes:
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def get_img_url_from_last_test(test_case: str, id: str) -> str:
    url = get_latest_test_report_url(test_case)
    if DEBUG:
        print(f"Test URL: {url}")

    html = get_html_content(url)

    src_relative = find_img_source_by_id(html, id)
    src_absolute = urljoin(url, src_relative)

    return src_absolute


def find_img_source_by_id(html_text: str, img_id: str) -> str:
    pattern = rf'<img id="{img_id}" .*?src="(.*?)"'
    match = re.search(pattern, html_text)
    if match is None:
        raise ValueError(f"Image with id {img_id} not found")
    return match.group(1)


def download_img(dir: Path, flow_name: str, screen_name: str, img_url: str) -> None:
    img_name = f"{screen_name}.png"
    img_dir = dir / flow_name
    img_dir.mkdir(exist_ok=True)
    img_path = img_dir / img_name
    if img_path.exists() and not OVERWRITE:
        return
    img_bytes = get_image_content(img_url)
    img_path.write_bytes(img_bytes)


@click.command()
# fmt: off
@click.option("-d", "--debug", is_flag=True, help="Show debug logs")
@click.option("-u", "--update", is_flag=True, help="Do not download already existing images")
@click.option("-b", "--branch", default=DEFAULT_BRANCH, help="Which branch to use")
@click.option("-f", "--flows-to-update", multiple=True, help="Which flows to update")
@click.argument("model", type=click.Choice(list(MODEL_FILE_MAPPING.keys()), case_sensitive=False))
# fmt: on
def cli(debug: bool, update: bool, branch: str, model: str, flows_to_update: list[str]):
    global OVERWRITE, DEBUG

    OVERWRITE = not update  # type: ignore
    DEBUG = debug  # type: ignore

    click.echo(f"Using branch {branch} and model {model}")

    if flows_to_update:
        click.echo(f"Updating only flows {flows_to_update}")

    file = MODEL_FILE_MAPPING.get(model)
    if not file:
        raise ValueError(f"Model {model} not found")
    dir = MODEL_DIR_MAPPING.get(model)
    if not dir:
        raise ValueError(f"Model {model} not found")

    all_flows = get_screen_text_content(file)
    for flow_to_update in flows_to_update:
        if flow_to_update not in all_flows:
            raise ValueError(f"Flow {flow_to_update} not found")

    jobs_id_mapping = get_branch_job_ids(branch)
    save_job_id_mapping(jobs_id_mapping)

    failed_to_download: list[str] = []
    for flow_name, flow_screens in all_flows.items():
        if flows_to_update and flow_name not in flows_to_update:
            continue
        click.echo(f"Getting screens for flow {flow_name}")
        for index, screen_info in enumerate(flow_screens, start=1):
            if "missing" in screen_info:
                click.echo(f"Skipping missing screen {screen_info['screen_id']}")
                continue
            screen_name = f"{flow_name}{index}"
            test_case = screen_info["test"]
            screen_id = screen_info["screen_id"]
            click.echo(f"Getting image {test_case}#{screen_id}")
            try:
                img_url = get_img_url_from_last_test(test_case, screen_id)
                if DEBUG:
                    click.echo(f"Image URL: {img_url}")
                download_img(dir, flow_name, screen_name, img_url)
            except Exception as e:
                click.echo(f"Failed to download - {e}")
                failed_to_download.append(f"{flow_name}#{screen_name}: {e}")

    if failed_to_download:
        click.echo("Failed to download:")
        for error in failed_to_download:
            click.echo(error)
        sys.exit(1)


if __name__ == "__main__":
    cli()
