from __future__ import annotations

import os
import time
import uuid
import zipfile
from pathlib import Path

import requests

from app.core.config import Settings, get_settings


class MinerUClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _get_token(self) -> str:
        token = self._settings.models.mineru_api_key or os.getenv("MINERU_API_KEY", "")
        if not token:
            raise ValueError("MINERU_API_KEY is not configured.")
        return token

    def _upload_pdf(self, pdf_path: Path, data_id: str) -> dict[str, str]:
        response = requests.post(
            self._settings.mineru.upload_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._get_token()}",
            },
            json={
                "files": [{"name": pdf_path.name, "data_id": data_id}],
                "model_version": self._settings.mineru.model_version,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg", "MinerU upload url request failed."))

        batch_id = payload["data"]["batch_id"]
        upload_url = payload["data"]["file_urls"][0]
        with pdf_path.open("rb") as file_obj:
            put_response = requests.put(upload_url, data=file_obj, timeout=300)
        put_response.raise_for_status()
        return {"batch_id": batch_id, "data_id": data_id}

    def _wait_for_result(self, batch_id: str, data_id: str) -> str:
        start_time = time.time()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_token()}",
        }
        while time.time() - start_time < self._settings.mineru.max_wait_time:
            response = requests.get(
                self._settings.mineru.result_url_template.format(batch_id),
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(payload.get("msg", "MinerU result request failed."))
            for item in payload["data"]["extract_result"]:
                if item.get("data_id") != data_id:
                    continue
                state = item.get("state")
                if state == "done" and item.get("full_zip_url"):
                    return item["full_zip_url"]
                if state == "failed":
                    raise RuntimeError(item.get("err_msg", "MinerU parsing failed."))
            time.sleep(self._settings.mineru.poll_interval)
        raise TimeoutError("Timed out while waiting for MinerU results.")

    def _download_and_extract_zip(self, zip_url: str, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_zip = output_dir / "temp.zip"
        response = requests.get(zip_url, stream=True, timeout=300)
        response.raise_for_status()
        with temp_zip.open("wb") as file_obj:
            for chunk in response.iter_content(chunk_size=8192):
                file_obj.write(chunk)
        with zipfile.ZipFile(temp_zip, "r") as archive:
            archive.extractall(output_dir)
        temp_zip.unlink(missing_ok=True)

    def parse_pdf(self, pdf_path: Path, output_dir: Path) -> Path:
        data_id = uuid.uuid4().hex
        upload_info = self._upload_pdf(pdf_path=pdf_path, data_id=data_id)
        zip_url = self._wait_for_result(batch_id=upload_info["batch_id"], data_id=data_id)
        self._download_and_extract_zip(zip_url=zip_url, output_dir=output_dir)
        return output_dir
