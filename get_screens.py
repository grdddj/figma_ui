from __future__ import annotations

import re
import sys
from functools import lru_cache
from urllib.parse import urljoin

import requests

from common import (
    FIGMA_DIR,
    get_latest_test_report_url,
    get_screen_text_content,
    save_job_id_mapping,
)
from gitlab import get_branch_job_ids

OVERWRITE = False


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


def download_img(flow_name: str, screen_name: str, img_url: str) -> None:
    img_name = f"{screen_name}.png"
    img_dir = FIGMA_DIR / flow_name
    img_dir.mkdir(exist_ok=True)
    img_path = img_dir / img_name
    if img_path.exists() and not OVERWRITE:
        return
    img_bytes = get_image_content(img_url)
    img_path.write_bytes(img_bytes)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        OVERWRITE = True  # type: ignore

    branch = "master"

    jobs_id_mapping = get_branch_job_ids(branch)
    save_job_id_mapping(jobs_id_mapping)

    failed_to_download: list[str] = []

    for flow_name, flow_screens in get_screen_text_content().items():
        # if flow_name != "Recovery":
        #     continue
        print(f"Getting screens for flow {flow_name}")
        for index, screen_info in enumerate(flow_screens, start=1):
            if "missing" in screen_info:
                print(f"Skipping missing screen {screen_info['screen_id']}")
                continue
            screen_name = f"{flow_name}{index}"
            test_case = screen_info["test"]
            screen_id = screen_info["screen_id"]
            print(f"Getting image {test_case}#{screen_id}")
            try:
                img_url = get_img_url_from_last_test(test_case, screen_id)
                download_img(flow_name, screen_name, img_url)
            except Exception as e:
                print(f"Failed to download - {e}")
                failed_to_download.append(f"{flow_name}#{screen_name}: {e}")

    if failed_to_download:
        print("Failed to download:")
        for error in failed_to_download:
            print(error)
        sys.exit(1)
