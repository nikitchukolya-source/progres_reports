from __future__ import annotations

import os

import gspread
import requests
from google.oauth2.service_account import Credentials


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

TELEGRAM_CHAT_IDS = [
    int(x.strip())
    for x in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")
    if x.strip()
]

SPREADSHEET_ID = "1jjM4_Br-_mNtMsMYKSlybFmS8pvTwOhtWK7zz6rDt1g"
SHEET_NAME = "Summary"

GOOGLE_CREDENTIALS_FILE = "credentials.json"

EXCLUDED_MANAGERS = {
    "Ангеліна Молокова",
}


# ============================================================
# GOOGLE SHEETS
# ============================================================

def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]

    credentials = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes,
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    return spreadsheet.worksheet(SHEET_NAME)


# ============================================================
# ОТРИМАННЯ ДАТИ
# ============================================================

def get_report_date(sheet):
    """
    Читаємо дату з клітинки S2.
    """
    report_date = str(sheet.acell("S2").value or "").strip()

    return report_date or "дату не вказано"


# ============================================================
# ОТРИМАННЯ ДАНИХ
# ============================================================

def get_managers_data(sheet):
    """
    Читаємо колонки A:K.

    A = ім'я менеджера
    I = к-сть зусиль
    J = к-сть оферів
    K = к-сть підписок
    """

    rows = sheet.get("A2:K100")

    managers = []

    for row in rows:

        row = row + [""] * (11 - len(row))

        name = str(row[0]).strip()

        if not name:
            continue

        if name.lower().startswith("всього"):
            break

        # Не беремо стажерів
        if "стажер" in name.lower():
            continue

        # Не беремо тімліда
        if name in EXCLUDED_MANAGERS:
            continue

        efforts = str(row[8]).strip()
        offers = str(row[9]).strip()
        subscriptions = str(row[10]).strip()

        managers.append({
            "name": name,
            "efforts": efforts or "—",
            "offers": offers or "—",
            "subscriptions": subscriptions or "—",
        })

    return managers


# ============================================================
# ФОРМУВАННЯ TELEGRAM-ПОВІДОМЛЕННЯ
# ============================================================

def build_message(managers, report_date):
    lines = [
        f"📊 <b>Активність команди Ангеліни — {report_date}</b>",
        "",
        "<pre>",
        f"{'Команда Ангеліни':<21} {'Зус.':>5} {'Офери':>6} {'Підп.':>5}",
        "-" * 42,
    ]

    total_efforts = 0
    total_offers = 0
    total_subscriptions = 0

    for manager in managers:
        name = manager["name"][:21]

        efforts = manager["efforts"]
        offers = manager["offers"]
        subscriptions = manager["subscriptions"]

        try:
            total_efforts += int(
                str(efforts).replace(" ", "").replace("—", "0")
            )
        except ValueError:
            pass

        try:
            total_offers += int(
                str(offers).replace(" ", "").replace("—", "0")
            )
        except ValueError:
            pass

        try:
            total_subscriptions += int(
                str(subscriptions).replace(" ", "").replace("—", "0")
            )
        except ValueError:
            pass

        lines.append(
            f"{name:<21} "
            f"{efforts:>5} "
            f"{offers:>6} "
            f"{subscriptions:>5}"
        )

    lines.append("-" * 42)

    lines.append(
        f"{'ВСЬОГО':<21} "
        f"{total_efforts:>5} "
        f"{total_offers:>6} "
        f"{total_subscriptions:>5}"
    )

    lines.append("</pre>")

    return "\n".join(lines)


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram_message(chat_id, message):

    if not chat_id:
        return

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    response.raise_for_status()


# ============================================================
# MAIN
# ============================================================

def main():

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "Не задано TELEGRAM_BOT_TOKEN"
        )

    sheet = get_google_sheet()

    report_date = get_report_date(sheet)

    managers = get_managers_data(sheet)

    if not managers:
        raise RuntimeError(
            "Не знайдено даних менеджерів."
        )

    message = build_message(
        managers,
        report_date
    )

    for chat_id in TELEGRAM_CHAT_IDS:
        send_telegram_message(
            chat_id=chat_id,
            message=message,
        )

    print("Звіт успішно відправлено.")


if __name__ == "__main__":
    main()