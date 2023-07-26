from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urljoin
import re

import requests

from gitlab import get_branch_job_ids

HERE = Path(__file__).parent
screens_file = HERE / "figma_screens.json"
figma_dir = HERE / "static"

OVERWRITE = False


def get_job_from_test_case(test_case: str) -> str:
    mapping = {
        "TR-click_tests": "core click R test",
        "TR-device_tests": "core device R test",
        "TT-click_tests": "core click test",
        "TT-device_tests": "core device test",
    }
    test_alias = "-".join(test_case.split("-")[:2])
    return mapping[test_alias]


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
    job_name = get_job_from_test_case(test_case)

    job_id = jobs_id_mapping[job_name]

    test_in_url = f"{test_case}.html"

    quoted_test_url = quote(test_in_url)

    passed_tests_url = f"https://satoshilabs.gitlab.io/-/trezor/trezor-firmware/-/jobs/{job_id}/artifacts/test_ui_report/passed"
    url = f"{passed_tests_url}/{quoted_test_url}"

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
    img_dir = figma_dir / flow_name
    img_dir.mkdir(exist_ok=True)
    img_path = img_dir / img_name
    if img_path.exists() and not OVERWRITE:
        return
    img_bytes = get_image_content(img_url)
    img_path.write_bytes(img_bytes)


if __name__ == "__main__":
    branch = "grdddj/figma_mapping"
    jobs_id_mapping = get_branch_job_ids(branch)

    screens = json.loads(screens_file.read_text())
    for flow_name, flow_screens in screens.items():
        print(f"Getting screens for flow {flow_name}")
        for index, screen_info in enumerate(flow_screens, start=1):
            screen_name = f"{flow_name}{index}"
            test_case = screen_info["test"]
            screen_id = screen_info["screen_id"]
            print(f"Getting image {test_case}#{screen_id}")
            img_url = get_img_url_from_last_test(test_case, screen_id)
            download_img(flow_name, screen_name, img_url)
