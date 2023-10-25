from __future__ import annotations

from contextlib import contextmanager
from itertools import zip_longest
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from common import (
    FIGMA_DIR,
    MODEL_DIR_MAPPING,
    MODEL_FILE_MAPPING,
    get_latest_test_report_url,
    get_logger,
    get_ocr_results,
    get_screen_text_content,
)

HERE = Path(__file__).parent

log_file_path = HERE / "app.log"
logger = get_logger(__name__, log_file_path)

app = FastAPI()

app.mount("/static", StaticFiles(directory=FIGMA_DIR.name), name=FIGMA_DIR.name)

templates = Jinja2Templates(directory="templates")


def get_subdirs_names(dir: Path) -> list[str]:
    """Get a list of subdirectories."""
    return sorted([x.name for x in dir.iterdir() if x.is_dir()])


def get_dir_file_count(dir: Path) -> int:
    """Get a number of files in a directory."""
    return len([x for x in dir.iterdir() if x.is_file()])


def get_relevant_screens(
    model: str,
    filter_flow: str | None = None,
    filter_text: str | None = None,
) -> list[dict[str, Any]]:
    file = MODEL_FILE_MAPPING.get(model)
    if not file:
        raise HTTPException(status_code=404, detail="Model not found")

    screens_content = get_screen_text_content(file)
    image_data: list[dict[str, Any]] = []

    ocr_results = get_ocr_results()

    for flow_name, flow_data in screens_content.items():
        if filter_flow and flow_name != filter_flow:
            continue  # filter by flow
        for index, screen_info in enumerate(flow_data, start=1):
            description = screen_info["description"]
            if filter_text and filter_text.lower() not in description.lower():
                continue  # filter by text
            comment = screen_info.get("comment", "")
            img_name = f"{flow_name}{index}"
            img_src = f"/static/{model}/{flow_name}/{img_name}.png"
            ocr_result = ocr_results.get(flow_name, {}).get(img_name, 0)
            ocr_result_str = f"{ocr_result} %"
            ocr_failed = ocr_result < 20
            if screen_info.get("ok_to_fail_ocr", False):
                ocr_result_str = f"{ocr_result_str} (OK to fail)"
                ocr_failed = False

            test = screen_info["test"]
            screen_id = screen_info["screen_id"]
            test_link = get_latest_test_report_url(test)
            test_link = f"{test_link}#{screen_id}"

            image_data.append(
                {
                    "test_link": test_link,
                    "name": img_name,
                    "compare_index": screen_info.get("compare_index"),
                    "src": img_src,
                    "description": description,
                    "comment": comment,
                    "ocr_result_str": ocr_result_str,
                    "ocr_failed": ocr_failed,
                }
            )

    return image_data


def get_unique_tests_and_links(model: str, flow_name: str) -> dict[str, str]:
    file = MODEL_FILE_MAPPING.get(model)
    if not file:
        raise HTTPException(status_code=404, detail="Model not found")
    screens_content = get_screen_text_content(file)
    flow_data: list[dict[str, str]] = screens_content[flow_name]
    return {
        screen_info["test"]: get_latest_test_report_url(screen_info["test"])
        for screen_info in flow_data
    }


@contextmanager
def catch_log_raise_exception():
    try:
        yield
    except Exception as e:
        logger.exception(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    with catch_log_raise_exception():
        logger.info("Root")

        models = list(MODEL_DIR_MAPPING.keys())
        return templates.TemplateResponse(  # type: ignore
            "index.html",
            {"request": request, "models": models},
        )


@app.get("/model/{model}", response_class=HTMLResponse)
def model(model: str, request: Request):
    with catch_log_raise_exception():
        logger.info(f"Model: {model}")

        model_infos: dict[str, list[tuple[str, int]]] = {}
        dir = MODEL_DIR_MAPPING.get(model)
        if not dir:
            raise HTTPException(status_code=404, detail="Model not found")
        subdirs = get_subdirs_names(dir)
        subdirs_and_filecounts: list[tuple[str, int]] = [
            (subdir, get_dir_file_count(dir / subdir)) for subdir in subdirs
        ]
        model_infos[model] = subdirs_and_filecounts
        return templates.TemplateResponse(  # type: ignore
            "model_menu.html",
            {"request": request, "model_infos": model_infos},
        )


@app.get("/all_screens/{model}", response_class=HTMLResponse)
def all_screens(model: str, request: Request):
    with catch_log_raise_exception():
        logger.info("All screens")
        image_data = get_relevant_screens(model)
        return templates.TemplateResponse(  # type: ignore
            "all_screens.html",
            {
                "request": request,
                "image_data": image_data,
            },
        )


@app.get("/flow/{model}/{flow_name}", response_class=HTMLResponse)
def read_subdir(model: str, flow_name: str, request: Request):
    with catch_log_raise_exception():
        logger.info(f"Flow: {flow_name}, model: {model}")
        dir = MODEL_DIR_MAPPING.get(model)
        if not dir:
            raise HTTPException(status_code=404, detail="Model not found")
        if flow_name not in get_subdirs_names(dir):
            raise HTTPException(status_code=404, detail="Directory not found")

        image_data = get_relevant_screens(model, filter_flow=flow_name)
        unique_tests_and_links = get_unique_tests_and_links(model, flow_name)

        return templates.TemplateResponse(  # type: ignore
            "flow.html",
            {
                "request": request,
                "flow_name": flow_name,
                "image_data": image_data,
                "unique_tests_and_links": unique_tests_and_links,
            },
        )


@app.get("/compare/{flow_name}", response_class=HTMLResponse)
def compare_subdir(flow_name: str, request: Request):
    with catch_log_raise_exception():
        logger.info(f"Compare, Flow: {flow_name}")
        all_model_image_data: dict[str, list[dict[str, Any]]] = {}

        biggest_compare_index = 0
        for model, dir in MODEL_DIR_MAPPING.items():
            if flow_name not in get_subdirs_names(dir):
                continue

            image_data = get_relevant_screens(model, filter_flow=flow_name)
            for obj in image_data:
                biggest_compare_index = max(
                    biggest_compare_index, obj.get("compare_index", 0)
                )
            all_model_image_data[model] = image_data

        zipped_image_data: list[tuple[Any | None]] = []

        for i in range(biggest_compare_index):
            index_dict: dict[str, list[Any | None]] = {}
            for model, model_values in all_model_image_data.items():
                model_list = [
                    obj for obj in model_values if obj.get("compare_index") == i
                ]
                index_dict[model] = model_list

            longest_value = max(len(val) for val in index_dict.values())
            for model_values in index_dict.values():
                len_diff = longest_value - len(model_values)
                if len_diff > 0:
                    model_values.extend([None] * len_diff)

            for el in zip_longest(*index_dict.values()):
                zipped_image_data.append(el)

        return templates.TemplateResponse(  # type: ignore
            "compare_flow.html",
            {
                "request": request,
                "flow_name": flow_name,
                "image_data": zipped_image_data,
            },
        )


@app.get("/compare", response_class=HTMLResponse)
def compare_menu(request: Request):
    with catch_log_raise_exception():
        logger.info(f"Compare")
        all_model_flows: dict[str, set[str]] = {}

        def find_common_elements(sets: list[set[str]]) -> set[str]:
            result: set[str] = set()
            for i, set1 in enumerate(sets):
                for j, set2 in enumerate(sets):
                    if i != j:
                        result.update(set1.intersection(set2))
            return result

        for model, dir in MODEL_DIR_MAPPING.items():
            model_flows = get_subdirs_names(dir)
            all_model_flows[model] = set(model_flows)

        common_flows = find_common_elements(list(all_model_flows.values()))

        return templates.TemplateResponse(  # type: ignore
            "compare_menu.html",
            {
                "request": request,
                "flows": sorted(common_flows),
            },
        )


@app.get("/text")
def text_search(request: Request, text: str = ""):
    with catch_log_raise_exception():
        logger.info(f"Text search: {text}")
        image_data: list[dict[str, Any]] = []
        for model in MODEL_DIR_MAPPING:
            model_data = get_relevant_screens(model, filter_text=text) if text else []
            image_data.extend(model_data)
        return templates.TemplateResponse(  # type: ignore
            "text_search.html",
            {
                "request": request,
                "text": text,
                "image_data": image_data,
            },
        )
