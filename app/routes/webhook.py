import hashlib
import hmac
import json
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.services.pipeline import ReviewPipeline

router = APIRouter(prefix="/webhook", tags=["webhook"])


def verify_signature(payload: bytes, signature: str) -> bool:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        return True  # Skip in dev if no secret set
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
):
    payload_bytes = await request.body()

    if not verify_signature(payload_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    payload = json.loads(payload_bytes)
    action = payload.get("action", "")

    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "action": action}

    pr = payload["pull_request"]
    repo = payload["repository"]["full_name"]

    pr_data = {
        "repo": repo,
        "pr_number": pr["number"],
        "pr_title": pr["title"],
        "pr_body": pr.get("body", ""),
        "base_sha": pr["base"]["sha"],
        "head_sha": pr["head"]["sha"],
        "author": pr["user"]["login"],
        "action": action,
    }

    store = request.app.state.store
    pipeline = ReviewPipeline(store=store)
    background_tasks.add_task(pipeline.run, pr_data)

    return {"status": "accepted", "pr": pr["number"], "repo": repo}
