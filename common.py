import json
import logging
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).parent
SCREENS_FILE = HERE / "figma_screens.json"
JOB_ID_MAPPING_FILE = HERE / "job_id_mapping.json"
FIGMA_DIR = HERE / "static"
OCR_RESULTS_FILE = HERE / "ocr_results.json"


TEST_CASE_MAPPING = {
    "TR-click_tests": "core click R test",
    "TR-device_tests": "core device R test",
    "TT-click_tests": "core click test",
    "TT-device_tests": "core device test",
}


def get_ocr_results() -> dict[str, dict[str, int]]:
    if not OCR_RESULTS_FILE.exists():
        return {}
    with open(OCR_RESULTS_FILE) as f:
        return json.load(f)


def get_screen_text_content() -> dict[str, list[dict[str, str]]]:
    with open(SCREENS_FILE) as f:
        return json.load(f)


def get_current_job_id_mapping() -> dict[str, str]:
    with open(JOB_ID_MAPPING_FILE) as f:
        return json.load(f)


def save_job_id_mapping(job_id_mapping: dict[str, str]) -> None:
    with open(JOB_ID_MAPPING_FILE, "w") as f:
        json.dump(job_id_mapping, f, indent=2)


def get_latest_test_report_url(test_name: str) -> str:
    test_job = get_job_from_test_case(test_name)
    job_id_mapping = get_current_job_id_mapping()
    job_id = job_id_mapping[test_job]
    test_in_url = f"{test_name}.html"
    quoted_test_url = quote(test_in_url)
    passed_tests_url = f"https://satoshilabs.gitlab.io/-/trezor/trezor-firmware/-/jobs/{job_id}/artifacts/test_ui_report/passed"
    return f"{passed_tests_url}/{quoted_test_url}"


def get_job_from_test_case(test_case: str) -> str:
    test_alias = "-".join(test_case.split("-")[:2])
    return TEST_CASE_MAPPING[test_alias]


def get_logger(name: str, log_file_path: str | Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_handler = logging.FileHandler(log_file_path)
    log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    return logger
