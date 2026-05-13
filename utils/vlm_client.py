import base64
from pathlib import Path
from openai import OpenAI

from config.settings import DASHSCOPE_API_KEY, VLM_MODEL
from config.prompts import build_all_table_rows_prompt, build_forced_table_prompt
from utils.json_utils import extract_json_from_text


def _image_to_data_url(image_path: Path) -> str:
    suffix = image_path.suffix.lower()

    if suffix == ".png":
        mime = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        mime = "image/png"

    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _get_client() -> OpenAI:
    if not DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY 为空，请填写 .env")

    return OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def _call_vlm(image_path: Path, prompt: str):
    client = _get_client()
    image_url = _image_to_data_url(image_path)

    resp = client.chat.completions.create(
        model=VLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        temperature=0,
    )

    content = resp.choices[0].message.content
    data = extract_json_from_text(content)

    if not isinstance(data, dict):
        data = {
            "page_image": image_path.name,
            "page_type": "other",
            "page_note": "VLM 返回内容不是合法 JSON dict",
            "tables": [],
        }

    data.setdefault("page_image", image_path.name)
    data.setdefault("page_type", "other")
    data.setdefault("tables", [])

    return data


def _count_rows(result) -> int:
    if not isinstance(result, dict):
        return 0

    total = 0

    for table in result.get("tables", []):
        if not isinstance(table, dict):
            continue

        rows = table.get("rows", [])

        if isinstance(rows, list):
            total += len(rows)

    return total


def extract_all_table_rows_from_image(image_path):
    image_path = Path(image_path)

    # 第一次：正常 Prompt
    result = _call_vlm(
        image_path=image_path,
        prompt=build_all_table_rows_prompt(image_path.name),
    )

    row_count = _count_rows(result)

    # 第二次：如果第一次没识别成表格，或者没有抽到任何 rows，强制重试
    if result.get("page_type") != "performance_data_table" or row_count == 0:
        retry_result = _call_vlm(
            image_path=image_path,
            prompt=build_forced_table_prompt(image_path.name),
        )

        retry_count = _count_rows(retry_result)

        if retry_count > row_count:
            retry_result["retry_used"] = True
            retry_result["retry_reason"] = "first_pass_no_rows_or_not_table"
            return retry_result

    result["retry_used"] = False
    return result