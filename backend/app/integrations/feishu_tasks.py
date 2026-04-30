import json
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib import error, request


DEFAULT_BASE_URL = "https://open.feishu.cn"


def get_feishu_config() -> Dict[str, Any]:
    return {
        "base_url": os.environ.get("FEISHU_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "app_id": os.environ.get("FEISHU_APP_ID", "").strip(),
        "app_secret": os.environ.get("FEISHU_APP_SECRET", "").strip(),
        "task_origin_name": os.environ.get("FEISHU_TASK_ORIGIN_NAME", "AI Meeting Minutes Assistant").strip(),
        "task_origin_url": os.environ.get("FEISHU_TASK_ORIGIN_URL", "http://localhost:8080").strip(),
        "default_open_id": os.environ.get("FEISHU_DEFAULT_OPEN_ID", "").strip(),
        "default_collaborator_ids": os.environ.get("FEISHU_DEFAULT_COLLABORATOR_IDS", "").strip(),
        "default_follower_ids": os.environ.get("FEISHU_DEFAULT_FOLLOWER_IDS", "").strip(),
    }


def is_feishu_configured() -> bool:
    config = get_feishu_config()
    return bool(
        config["app_id"]
        and config["app_secret"]
        and config["app_id"] != "your_feishu_app_id_here"
        and config["app_secret"] != "your_feishu_app_secret_here"
    )


def _post_json(url: str, payload: Dict[str, Any], bearer_token: Optional[str] = None) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Feishu API request failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to connect to Feishu Open Platform: {exc.reason}") from exc


def _normalize_user_record(raw_user: Dict[str, Any]) -> Dict[str, str]:
    return {
        "open_id": raw_user.get("user_id", ""),
        "name": raw_user.get("name", ""),
        "email": raw_user.get("email", ""),
        "mobile": raw_user.get("mobile", ""),
    }


def get_tenant_access_token() -> str:
    config = get_feishu_config()
    if not is_feishu_configured():
        raise RuntimeError("Feishu sync is not configured. Add FEISHU_APP_ID and FEISHU_APP_SECRET.")

    response = _post_json(
        f"{config['base_url']}/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": config["app_id"], "app_secret": config["app_secret"]},
    )

    if response.get("code") != 0 or not response.get("tenant_access_token"):
        raise RuntimeError(
            f"Failed to obtain Feishu tenant access token: {response.get('msg') or response}"
        )
    return response["tenant_access_token"]


def resolve_feishu_open_ids(
    emails: Optional[List[str]] = None,
    mobiles: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    normalized_emails = [item.strip() for item in (emails or []) if item and item.strip()]
    normalized_mobiles = [item.strip() for item in (mobiles or []) if item and item.strip()]

    if not normalized_emails and not normalized_mobiles:
        raise RuntimeError("Provide at least one email or mobile number to resolve Feishu open_id.")

    tenant_access_token = get_tenant_access_token()
    config = get_feishu_config()
    payload: Dict[str, Any] = {}
    if normalized_emails:
        payload["emails"] = normalized_emails
    if normalized_mobiles:
        payload["mobiles"] = normalized_mobiles

    response = _post_json(
        f"{config['base_url']}/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id",
        payload,
        bearer_token=tenant_access_token,
    )

    if response.get("code") != 0:
        raise RuntimeError(
            f"Failed to resolve Feishu open_id: {response.get('msg') or response}"
        )

    user_list = ((response.get("data") or {}).get("user_list")) or []
    return [_normalize_user_record(user) for user in user_list]


def parse_deadline_to_due(deadline: str) -> Optional[Dict[str, Any]]:
    text = (deadline or "").strip()
    if not text or text.lower() in {"none", "n/a", "na", "unassigned", "tbd"}:
        return None

    candidates = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    parsed: Optional[datetime] = None
    for fmt in candidates:
        try:
            parsed = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                return None

    timestamp = int(parsed.timestamp())
    return {"time": str(timestamp), "timezone": "Asia/Shanghai", "is_all_day": True}


def parse_id_list(raw_value: str) -> List[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_default_task_member_ids(config: Dict[str, Any]) -> Dict[str, List[str]]:
    default_open_id = config.get("default_open_id", "")
    collaborator_ids = parse_id_list(config.get("default_collaborator_ids", ""))
    follower_ids = parse_id_list(config.get("default_follower_ids", ""))

    if default_open_id:
        if default_open_id not in collaborator_ids:
            collaborator_ids.append(default_open_id)
        if default_open_id not in follower_ids:
            follower_ids.append(default_open_id)

    return {
        "collaborator_ids": collaborator_ids,
        "follower_ids": follower_ids,
    }


def build_task_payload(action_item: Dict[str, Any], meeting: Dict[str, Any]) -> Dict[str, Any]:
    config = get_feishu_config()
    task = (action_item.get("task") or "").strip()
    assignee = (action_item.get("assignee") or "Unassigned").strip()
    deadline = (action_item.get("deadline") or "None").strip()

    lines = [
        f"Meeting: {meeting.get('filename', 'Unknown meeting')}",
        f"Template: {meeting.get('template', 'general')}",
        f"Owner: {assignee}",
        f"Deadline: {deadline}",
    ]

    payload: Dict[str, Any] = {
        "summary": task[:256],
        "description": "\n".join(lines),
        "origin": {
            "platform_i18n_name": json.dumps(
                {
                    "zh_cn": config["task_origin_name"],
                    "en_us": config["task_origin_name"],
                },
                ensure_ascii=False,
            ),
            "href": {
                "url": config["task_origin_url"],
                "title": meeting.get("filename", task[:64] or "Meeting Action Item"),
            },
        },
    }

    member_ids = get_default_task_member_ids(config)
    if member_ids["collaborator_ids"]:
        payload["collaborator_ids"] = member_ids["collaborator_ids"]
    if member_ids["follower_ids"]:
        payload["follower_ids"] = member_ids["follower_ids"]

    due = parse_deadline_to_due(deadline)
    if due is not None:
        payload["due"] = due

    return payload


def create_feishu_task(action_item: Dict[str, Any], meeting: Dict[str, Any], tenant_access_token: str) -> Dict[str, Any]:
    config = get_feishu_config()
    payload = build_task_payload(action_item, meeting)
    response = _post_json(
        f"{config['base_url']}/open-apis/task/v1/tasks?user_id_type=open_id",
        payload,
        bearer_token=tenant_access_token,
    )

    if response.get("code") != 0:
        raise RuntimeError(
            f"Failed to create Feishu task: {response.get('msg') or response}"
        )

    task_info = (response.get("data") or {}).get("task") or {}
    return {
        "task_id": task_info.get("id", ""),
        "summary": task_info.get("summary", payload["summary"]),
        "due_time": ((task_info.get("due") or {}).get("time")) if task_info.get("due") else "",
    }


def sync_meeting_action_items_to_feishu(meeting: Dict[str, Any]) -> Dict[str, Any]:
    items = meeting.get("action_items") or []
    valid_items = [item for item in items if (item.get("task") or "").strip()]

    if not valid_items:
        raise RuntimeError("No action items are available to sync for this meeting.")

    tenant_access_token = get_tenant_access_token()
    created_tasks: List[Dict[str, Any]] = []

    for item in valid_items:
        created_tasks.append(create_feishu_task(item, meeting, tenant_access_token))

    return {
        "synced_count": len(created_tasks),
        "created_tasks": created_tasks,
    }
