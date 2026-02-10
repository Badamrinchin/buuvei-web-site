from fastapi import FastAPI, Request, Form
from typing import List
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from google.oauth2.service_account import Credentials
import gspread

from datetime import datetime
import json
import re
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()

# Templates
templates = Jinja2Templates(directory="templates")

# Google Sheets config
SHEET_ID = "1NTZFZzRORut5i5apZRdT-sVmAaSj5e3u-pdIBJJkYTs"
SHEET_NAME = "Sheet1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

sheet = None
try:
    service_account_json = os.getenv("SERVICE_ACCOUNT_JSON", "").strip()
    service_account_file = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")
    if service_account_json:
        creds = Credentials.from_service_account_info(
            json.loads(service_account_json),
            scopes=SCOPES,
        )
    else:
        creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
except Exception as e:
    print(f"⚠️ Google Sheets not available: {e}")

last_submit = {}


def send_order_email(order_data):
    """Send email notification for new order"""
    try:
        # Gmail SMTP settings (use environment variables for credentials)
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = os.getenv("SENDER_EMAIL", "noreply@example.com")
        sender_password = os.getenv("SENDER_PASSWORD", "")
        
        if not sender_password:
            print("⚠️ Email not sent: SENDER_PASSWORD environment variable not set")
            return False
        
        recipient_email = "badamrinchin@gmail.com"
        
        # Create email message
        subject = "Шинэ захиалга ирлээ"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #4f46e5;">Шинэ захиалга ирлээ</h2>
                <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Утас</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('phone', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Төрөл</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('type', '')}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Хэмжээ</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('size', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Өнгө</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('color', '')}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Хээ</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('pattern', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Хээний өнгө</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('patternColor', '')}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Хүлээлгэн өгөх огноо</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('deliveryDate', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Хүргэлтийн төрөл</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('deliveryType', '')}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Хаяг</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('deliveryAddress', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Бүртгэсэн</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{order_data.get('registeredBy', '')}</td>
                    </tr>
                </table>
                <p style="margin-top: 20px; color: #666; font-size: 12px;">
                    Энэ имэйл автоматаар үүсэгдсэн болно.
                </p>
            </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print(f"✅ Email sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")
        return False


@app.get("/favicon.ico", response_class=Response)
def favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/register")
async def register(
    request: Request,
    phone: str = Form(...),
    category: str = Form(...),
    type: List[str] = Form([]),
    typeOther: List[str] = Form([]),
    size: List[str] = Form([]),
    sizeOther: List[str] = Form([]),
    color: List[str] = Form([]),
    colorOther: List[str] = Form([]),
    pattern: List[str] = Form([]),
    patternOther: List[str] = Form([]),
    patternColor: List[str] = Form([]),
    patternColorOther: List[str] = Form([]),
    quantity: List[str] = Form([]),
    deliveryDate: str = Form(""),
    registeredBy: str = Form(""),
    deliveryType: str = Form(""),
    deliveryAddress: str = Form(""),
    totalPayment: str = Form(""),
    advancePayment: str = Form(""),
    balancePayment: str = Form(""),
    paid: str = Form("")
):
    if not re.fullmatch(r"\d{8}", phone):
        return JSONResponse({"error": "Утас 8 оронтой байх ёстой"}, status_code=400)

    now = time.time()

    form = await request.form()

    def get_list(form_data, key: str, fallback: List[str]) -> List[str]:
        values = form_data.getlist(key)
        if not values:
            values = form_data.getlist(f"{key}[]")
        return values or fallback

    types_in = get_list(form, "type", type)
    type_others_in = get_list(form, "typeOther", typeOther)
    sizes_in = get_list(form, "size", size)
    size_others_in = get_list(form, "sizeOther", sizeOther)
    colors_in = get_list(form, "color", color)
    color_others_in = get_list(form, "colorOther", colorOther)
    patterns_in = get_list(form, "pattern", pattern)
    pattern_others_in = get_list(form, "patternOther", patternOther)
    pattern_colors_in = get_list(form, "patternColor", patternColor)
    pattern_color_others_in = get_list(form, "patternColorOther", patternColorOther)
    quantities_in = get_list(form, "quantity", quantity)

    def pick_value(options: List[str], others: List[str], index: int) -> str:
        option = options[index] if index < len(options) else ""
        other = others[index] if index < len(others) else ""
        return other if option == "Бусад" else option

    count = max(
        len(types_in),
        len(sizes_in),
        len(colors_in),
        len(patterns_in),
        len(pattern_colors_in),
        len(quantities_in),
        1,
    )

    types = [pick_value(types_in, type_others_in, i) for i in range(count)]
    sizes = [pick_value(sizes_in, size_others_in, i) for i in range(count)]
    colors = [pick_value(colors_in, color_others_in, i) for i in range(count)]
    patterns = [pick_value(patterns_in, pattern_others_in, i) for i in range(count)]
    pattern_colors = [pick_value(pattern_colors_in, pattern_color_others_in, i) for i in range(count)]
    quantities = [quantities_in[i] if i < len(quantities_in) else "1" for i in range(count)]

    def join_values(values: List[str]) -> str:
        return " | ".join([v for v in values if v])

    final_type = join_values(types)
    final_size = join_values(sizes)
    final_color = join_values(colors)
    final_pattern = join_values(patterns)
    final_pattern_color = join_values(pattern_colors)

    paid_value = "TRUE" if paid.lower() in ["true", "1", "yes", "тийм", "on"] else ""
    balance_final = "0" if paid_value else balancePayment

    signature = "|".join([
        phone,
        category,
        deliveryDate,
        registeredBy,
        deliveryType,
        deliveryAddress,
        ";".join(types),
        ";".join(sizes),
        ";".join(colors),
        ";".join(patterns),
        ";".join(pattern_colors),
        totalPayment,
        advancePayment,
        balance_final,
        paid_value,
    ])

    if signature in last_submit and now - last_submit[signature] < 2:
        return {"status": "ignored"}
    last_submit[signature] = now

    if not sheet:
        return JSONResponse({"error": "Google Sheets холболт алга байна"}, status_code=500)

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        for i in range(count):
            is_first = i == 0
            sheet.append_row([
                timestamp,
                phone,
                category,
                types[i] if i < len(types) else "",
                sizes[i] if i < len(sizes) else "",
                colors[i] if i < len(colors) else "",
                patterns[i] if i < len(patterns) else "",
                pattern_colors[i] if i < len(pattern_colors) else "",
                quantities[i] if i < len(quantities) else "1",
                deliveryDate,
                deliveryDate,  # Захиалгын хугацаа
                deliveryType,
                "",  # status
                totalPayment if is_first else "",
                advancePayment if is_first else "",
                balance_final if is_first else "",
                paid_value if is_first else "",
                deliveryAddress,
                registeredBy,
            ])

        # Send email notification if it's an order
        if category == "Захиалга":
            order_data = {
                "phone": phone,
                "type": final_type,
                "size": final_size,
                "color": final_color,
                "pattern": final_pattern,
                "patternColor": final_pattern_color,
                "deliveryDate": deliveryDate,
                "registeredBy": registeredBy,
                "deliveryType": deliveryType,
                "deliveryAddress": deliveryAddress,
            }
            send_order_email(order_data)

    except Exception as e:
        print(f"⚠️ Failed to write to sheet: {e}")
        return JSONResponse({"error": "Хүснэгт рүү бичиж чадсангүй"}, status_code=500)

    return {"status": "success"}


@app.get("/orders")
def get_orders():
    """Fetch all orders from Google Sheets"""
    try:
        if not sheet:
            return JSONResponse({"error": "Google Sheets not available"}, status_code=500)
        
        # Get all values from the sheet
        all_values = sheet.get_all_values()
        
        # Skip header row (if exists) and get only order data (category = "Захиалга")
        orders = []
        for i, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
            if len(row) >= 10:  # Ensure row has enough columns
                # Column mapping (newest): [timestamp, phone, category, type, size, color, pattern, patternColor, quantity, deliveryDate, orderDuration, deliveryType, status, total, advance, balance, paid, deliveryAddress, registeredBy]
                # Column mapping (new): [timestamp, phone, category, type, size, color, pattern, patternColor, quantity, deliveryDate, registeredBy, deliveryType, status, total, advance, balance, paid, deliveryAddress]
                # Column mapping (old): [timestamp, phone, category, type, size, color, pattern, patternColor, deliveryDate, registeredBy, deliveryType, status, total, advance, balance, paid]
                category = row[2] if len(row) > 2 else ""
                
                if category == "Захиалга":
                    has_quantity = len(row) >= 17
                    has_address = len(row) >= 18
                    has_registered_last = len(row) >= 19
                    idx = {
                        "timestamp": 0,
                        "phone": 1,
                        "category": 2,
                        "type": 3,
                        "size": 4,
                        "color": 5,
                        "pattern": 6,
                        "patternColor": 7,
                        "quantity": 8 if has_quantity else None,
                        "deliveryDate": 9 if has_quantity else 8,
                        "orderDuration": 10 if has_registered_last else None,
                        "registeredBy": 18 if has_registered_last else (10 if has_quantity else 9),
                        "deliveryType": 11 if has_quantity else 10,
                        "status": 12 if has_quantity else 11,
                        "total": 13 if has_quantity else 12,
                        "advance": 14 if has_quantity else 13,
                        "balance": 15 if has_quantity else 14,
                        "paid": 16 if has_quantity else 15,
                        "deliveryAddress": 17 if has_address else None,
                    }
                    orders.append({
                        "row": i,
                        "timestamp": row[idx["timestamp"]] if len(row) > idx["timestamp"] else "",
                        "phone": row[idx["phone"]] if len(row) > idx["phone"] else "",
                        "type": row[idx["type"]] if len(row) > idx["type"] else "",
                        "size": row[idx["size"]] if len(row) > idx["size"] else "",
                        "color": row[idx["color"]] if len(row) > idx["color"] else "",
                        "pattern": row[idx["pattern"]] if len(row) > idx["pattern"] else "",
                        "patternColor": row[idx["patternColor"]] if len(row) > idx["patternColor"] else "",
                        "quantity": row[idx["quantity"]] if idx["quantity"] is not None and len(row) > idx["quantity"] else "",
                        "registeredBy": row[idx["registeredBy"]] if len(row) > idx["registeredBy"] else "",
                        "deliveryDate": row[idx["orderDuration"]] if idx["orderDuration"] is not None and len(row) > idx["orderDuration"] else (row[idx["deliveryDate"]] if len(row) > idx["deliveryDate"] else ""),
                        "deliveryType": row[idx["deliveryType"]] if len(row) > idx["deliveryType"] else "",
                        "status": row[idx["status"]] if len(row) > idx["status"] else "",
                        "totalPayment": row[idx["total"]] if len(row) > idx["total"] else "",
                        "advancePayment": row[idx["advance"]] if len(row) > idx["advance"] else "",
                        "balancePayment": row[idx["balance"]] if len(row) > idx["balance"] else "",
                        "paid": row[idx["paid"]] if len(row) > idx["paid"] else "",
                        "deliveryAddress": row[idx["deliveryAddress"]] if idx["deliveryAddress"] is not None and len(row) > idx["deliveryAddress"] else "",
                    })
        
        return {"orders": orders}
    except Exception as e:
        print(f"⚠️ Error fetching orders: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/orders/{row}/status")
def update_order_status(row: int, status: str = Form(...)):
    """Update order status in Google Sheets"""
    try:
        if not sheet:
            return JSONResponse({"error": "Google Sheets not available"}, status_code=500)
        
        # Validate status
        valid_statuses = ["Хийгдэж байгаа", "Бэлэн болсон", "Авсан"]
        if status not in valid_statuses:
            return JSONResponse({"error": "Invalid status"}, status_code=400)
        
        # Update the status in column 13 (index 12) of the specified row
        sheet.update_cell(row, 13, status)
        
        return {"status": "success", "message": f"Row {row} updated with status: {status}"}
    except Exception as e:
        print(f"⚠️ Error updating status: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/orders/{row}/payment")
def update_order_payment(
    row: int,
    total: str = Form(""),
    advance: str = Form(""),
    balance: str = Form(""),
    paid: str = Form(""),
):
    """Update payment fields in Google Sheets"""
    try:
        if not sheet:
            return JSONResponse({"error": "Google Sheets not available"}, status_code=500)

        paid_value = "TRUE" if paid.lower() in ["true", "1", "yes", "тийм"] else ""

        # Columns (new): 14 total, 15 advance, 16 balance, 17 paid
        sheet.update_cell(row, 14, total)
        sheet.update_cell(row, 15, advance)
        sheet.update_cell(row, 16, balance)
        sheet.update_cell(row, 17, paid_value)

        return {"status": "success"}
    except Exception as e:
        print(f"⚠️ Error updating payment: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

