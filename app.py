from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from common import (
    FIGMA_DIR,
    get_latest_test_report_url,
    get_logger,
    get_screen_text_content,
)

HERE = Path(__file__).parent

log_file_path = HERE / "app.log"
logger = get_logger(__name__, log_file_path)

app = FastAPI()

app.mount("/static", StaticFiles(directory=FIGMA_DIR.name), name=FIGMA_DIR.name)

templates = Jinja2Templates(directory="templates")


def get_subdirs_names() -> list[str]:
    """Get a list of subdirectories."""
    return sorted([x.name for x in FIGMA_DIR.iterdir() if x.is_dir()])


def get_dir_file_count(dir: Path) -> int:
    """Get a number of files in a directory."""
    return len([x for x in dir.iterdir() if x.is_file()])


@contextmanager
def catch_log_raise_exception():
    try:
        yield
    except Exception as e:
        logger.exception(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    with catch_log_raise_exception():
        logger.info("Root")
        subdirs = get_subdirs_names()
        subdirs_and_filecounts: list[tuple[str, int]] = [
            (subdir, get_dir_file_count(FIGMA_DIR / subdir)) for subdir in subdirs
        ]
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "subdirs_and_filecounts": subdirs_and_filecounts},
        )


@app.get("/flow/{flow_name}", response_class=HTMLResponse)
def read_subdir(flow_name: str, request: Request):
    with catch_log_raise_exception():
        logger.info(f"Flow: {flow_name}")
        if flow_name not in get_subdirs_names():
            raise HTTPException(status_code=404, detail="Directory not found")

        screens_content = get_screen_text_content()
        flow_data: list[dict[str, str]] = screens_content[flow_name]
        image_data: list[dict[str, str]] = []

        for index, screen_info in enumerate(flow_data, start=1):
            img_name = f"{flow_name}{index}"
            img_src = f"/static/{flow_name}/{img_name}.png"
            description = screen_info["description"]
            image_data.append(
                {
                    "name": img_name,
                    "src": img_src,
                    "description": description,
                }
            )

        unique_tests_and_links: dict[str, str] = {
            screen_info["test"]: get_latest_test_report_url(screen_info["test"])
            for screen_info in flow_data
        }

        return templates.TemplateResponse(
            "subdir.html",
            {
                "request": request,
                "flow_name": flow_name,
                "image_data": image_data,
                "unique_tests_and_links": unique_tests_and_links,
            },
        )


@app.get("/text")
def text_search(request: Request, text: str = ""):
    with catch_log_raise_exception():
        logger.info(f"Text search: {text}")
        if not text:
            image_data = []
        else:
            screens_content = get_screen_text_content()
            image_data: list[dict[str, str]] = []

            for flow_name, flow_data in screens_content.items():
                for index, screen_info in enumerate(flow_data, start=1):
                    img_name = f"{flow_name}{index}"
                    img_src = f"/static/{flow_name}/{img_name}.png"
                    description = screen_info["description"]
                    if text.lower() in description.lower():
                        image_data.append(
                            {
                                "name": img_name,
                                "src": img_src,
                                "description": description,
                            }
                        )

        return templates.TemplateResponse(
            "text_search.html",
            {
                "request": request,
                "text": text,
                "image_data": image_data,
            },
        )
