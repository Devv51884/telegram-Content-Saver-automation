from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.request
from features.plan_manager import get_payment_config


def generate_paytm_checksum(body_dict: dict, merchant_key: str) -> str:
    body_str = json.dumps(body_dict, separators=(",", ":"))
    h = hmac.new(merchant_key.encode("utf-8"), body_str.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(h.digest()).decode("utf-8")


def check_paytm_order_status(order_id: str, mid: str = "", key: str = "") -> tuple[bool, str, dict]:
    cfg = get_payment_config()
    mid = (mid or cfg.get("paytm_mid") or "").strip()
    key = (key or cfg.get("paytm_key") or "").strip()

    if not mid or not key:
        return False, "NO_PAYTM_CONFIG", {}

    body = {
        "mid": mid,
        "orderId": str(order_id).strip(),
    }
    signature = generate_paytm_checksum(body, key)
    payload = {
        "body": body,
        "head": {
            "signature": signature,
        },
    }

    url = "https://securegw.paytm.in/v3/order/status"
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            body_res = data.get("body", {})
            result_info = body_res.get("resultInfo", {})
            result_status = str(result_info.get("resultStatus", "")).upper()
            txn_amount = float(body_res.get("txnAmount", 0) or 0)

            if result_status == "TXN_SUCCESS":
                return True, "TXN_SUCCESS", body_res
            elif result_status in {"PENDING", "TXN_INIT"}:
                return False, "PENDING", body_res
            else:
                return False, result_status or "TXN_FAILURE", body_res
    except Exception as exc:
        return False, f"ERROR: {exc}", {}
