from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

HERE = Path(__file__).parent

log_file_path = HERE / "app.log"
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(log_file_path)
log_formatter = logging.Formatter("%(asctime)s %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

screens_file = HERE / "figma_screens.json"

app = FastAPI()

static_dir = "static"
app.mount("/static", StaticFiles(directory=static_dir), name=static_dir)

# Assuming you put your templates in a "templates" directory
templates = Jinja2Templates(directory="templates")


def get_subdirs_names() -> list[str]:
    """Get a list of subdirectories."""
    dir_path = HERE / static_dir
    return sorted([x.name for x in dir_path.iterdir() if x.is_dir()])


def get_dir_file_count(dir: Path) -> int:
    """Get a number of files in a directory."""
    return len([x for x in dir.iterdir() if x.is_file()])


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    logger.info("root")
    subdirs = get_subdirs_names()
    subdirs_and_filecounts: list[tuple[str, int]] = [
        (subdir, get_dir_file_count(HERE / static_dir / subdir)) for subdir in subdirs
    ]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "subdirs_and_filecounts": subdirs_and_filecounts},
    )


@app.get("/flow/{flow_name}", response_class=HTMLResponse)
def read_subdir(flow_name: str, request: Request):
    logger.info(f"flow {flow_name}")
    if flow_name not in get_subdirs_names():
        raise HTTPException(status_code=404, detail="Directory not found")

    screens_content = json.loads(screens_file.read_text())
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

    unique_tests: set[str] = {screen_info["test"] for screen_info in flow_data}

    return templates.TemplateResponse(
        "subdir.html",
        {
            "request": request,
            "flow_name": flow_name,
            "image_data": image_data,
            "unique_tests": unique_tests,
        },
    )
