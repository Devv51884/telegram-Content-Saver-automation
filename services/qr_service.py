from __future__ import annotations

import os
import urllib.parse
import urllib.request

from config import TEMP_DIR
from features.plan_manager import get_payment_config


def build_upi_uri(upi_id: str, payee_name: str, amount: int | float, order_id: str) -> str:
    params = {
        "pa": str(upi_id).strip(),
        "pn": str(payee_name).strip(),
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tr": str(order_id).strip(),
        "tn": f"Plan {order_id}",
    }
    return f"upi://pay?{urllib.parse.urlencode(params)}"


def generate_qr_image(upi_uri: str, order_id: str) -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    qr_path = os.path.join(TEMP_DIR, f"qr_{order_id}.png")

    try:
        import qrcode
        from PIL import Image

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)
        return qr_path
    except Exception:
        pass

    # Online API fallback (requires no local qrcode/PIL packages)
    try:
        encoded_data = urllib.parse.quote(upi_uri)
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_data}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response, open(qr_path, "wb") as f:
            f.write(response.read())
        return qr_path
    except Exception:
        return ""


def create_order_qr(order: dict) -> tuple[str, str, dict]:
    cfg = get_payment_config()
    upi_id = cfg.get("upi_id") or "nope728@ptyes"
    payee_name = cfg.get("payee_name") or "Code Devil Premium"
    amount = float(order.get("amount", 99))
    order_id = str(order.get("order_id", ""))

    upi_uri = build_upi_uri(upi_id, payee_name, amount, order_id)

    custom_qr_path = cfg.get("custom_qr_path")
    custom_qr_file_id = cfg.get("custom_qr_file_id")

    if custom_qr_path and os.path.exists(custom_qr_path):
        qr_file_path = custom_qr_path
    elif custom_qr_file_id:
        qr_file_path = custom_qr_file_id
    else:
        qr_file_path = generate_qr_image(upi_uri, order_id)

    deep_links = {
        "upi": upi_uri,
        "gpay": upi_uri,
        "phonepe": upi_uri.replace("upi://pay", "phonepe://pay"),
        "paytm": upi_uri.replace("upi://pay", "paytmmp://pay"),
    }

    return qr_file_path, upi_uri, deep_links
