# TREZOR UI SCREENS vs FIGMA SCREENS

This repository's goal is to provide a visual comparison between the real Trezor screens and their designs in Figma.

It uses screenshots from UI tests to get the latest state of the screens.

It consists of the `HTML` frontend and a `python` backend.

## Features

Frontend website gives easy access to the following features:
- see all the screens for a specific model
- see a specific flow for a specific model
- compare a specific flow between all models
- search for screens with a specific text in all models

## Data

The core data describing the flows are saved in model-specific `json` files - e.g. [figma_screens_tr.json](figma_screens_tr.json). They define from which test the screen comes from (`test`) and its index in that test (`screen_id`). The whole relevant screen text is defined in `description` field and `compare_index` allows for side-by-side comparisons of specific screens on different models.

Example of a screen definition:

```json
{
    "compare_index": 3,
    "description": "SKIP BACKUP || Are you sure you want to skip the backup? || <SKIP> <BACK UP>",
    "test": "TR-device_tests-reset_recovery-test_reset_backup.py::test_skip_backup_manual[BackupType.Bip39-backup_flow_bip39]",
    "screen_id": 11
}
```

## Architecture / development

App is a `fastapi` python server, which serves the `HTML` files in `templates` directory, together with all the screenshots in `static` directory.

Dependencies are installed by `pip install -r requirements.txt`.

During development, the most useful command to run is `make debug`, which will reload the server on every file change. The default port number the app is running on is `8078`. `make run` will then run the app in "production" mode, without reloading.

## Update process

The repository does not store any screens in `static`, they are gitignored and have to be generated.

Currently, the updates of the state happen via `get_screens.py` script. It will try connecting to Gitlab and get the latest screenshots from the UI tests, saving then into `static` directory.

`backup.sh` will move the current screens into `backup` folder, so the old state is also persisted before downloading new fresh screens.

`make update` combines these two steps together.

## Deployment

On the `linux` server, it should be enough just to install the dependencies in `requirements.txt` and run `sudo ./deploy_service.sh`. It will generate and start a service running `make run` in the background.

Possibly, for running without a service, there is `make start` target, which runs the app in the background as well using `nohup`.

## Possible improvements

- having a UI button (maybe password-protected) to trigger the update process at any given time
- showing some kind of diff between old and new screens after doing an update
- improve the OCR so it can be more relied upon
