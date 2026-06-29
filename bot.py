"""
==============================================
  BOT چک کردن نوبت هuellas TIE - بارسلونا
==============================================
ساخته شده برای: تلگرام + ویندوز
"""

import asyncio
import random
import time
from datetime import datetime
from playwright.async_api import async_playwright
import requests
import json
import os

# ─────────────────────────────────────────
#   تنظیمات - اینجا رو پر کن
# ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8612775892:AAEyEN7eoW_RH6Sl_-IklTotVfuw5R3VDw8"
TELEGRAM_CHAT_ID   = "8924939591"

CHECK_INTERVAL_MINUTES = 5   # هر چند دقیقه چک کنه (پیشنهاد: 5)

# استان و دفاتر مورد نظر
PROVINCE = "Barcelona"

# لیست دفاتری که چک می‌کنه (می‌تونی بیشتر اضافه کنی)
OFFICES = [
    "Barcelona - C/Murcia",
    "Barcelona - Rambla Guipúscoa",
    "Barcelona - Zona Franca",
    "Barcelona - Sant Martí",
    "Badalona",
    "Sabadell",
    "Terrassa",
    "Santa Coloma de Gramenet",
]

# URL سایت دولتی
ICPPLUS_URL = "https://icp.administracionelectronica.gob.es/icpplus/"

# ─────────────────────────────────────────
#   ارسال پیام تلگرام
# ─────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print(f"[TELEGRAM] پیام ارسال شد ✓")
        else:
            print(f"[TELEGRAM ERROR] {r.text}")
    except Exception as e:
        print(f"[TELEGRAM EXCEPTION] {e}")


# ─────────────────────────────────────────
#   چک کردن نوبت
# ─────────────────────────────────────────
async def check_appointment():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] در حال چک کردن سایت...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="es-ES",
        )

        page = await context.new_page()

        # غیرفعال کردن webdriver flag
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        found_slots = []

        try:
            # مرحله ۱: ورود به سایت
            await page.goto(ICPPLUS_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(random.uniform(1.5, 3))

            # مرحله ۲: انتخاب استان Barcelona
            await page.select_option("select#form", label=PROVINCE)
            await asyncio.sleep(random.uniform(1, 2))

            # کلیک دکمه Aceptar
            await page.click("input[value='Aceptar']")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # مرحله ۳: انتخاب نوع خدمت - تومای هوئلاس
            tramite_options = [
                "POLICÍA-TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)",
                "POLICÍA - TOMA DE HUELLAS",
                "Toma de huellas",
            ]

            selected = False
            for tramite in tramite_options:
                try:
                    await page.select_option("select#tramiteGrupo\\[0\\]", label=tramite)
                    selected = True
                    break
                except:
                    pass

            if not selected:
                # سعی کن با partial text انتخاب کنی
                options = await page.query_selector_all("select option")
                for opt in options:
                    text = await opt.inner_text()
                    if "HUELLAS" in text.upper() or "HUELLA" in text.upper():
                        value = await opt.get_attribute("value")
                        await page.select_option("select", value=value)
                        selected = True
                        break

            if not selected:
                print("[WARN] نتونست نوع خدمت رو انتخاب کنه - ساختار سایت تغییر کرده")
                await browser.close()
                return False

            await asyncio.sleep(random.uniform(1, 2))
            await page.click("input[value='Aceptar']")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # مرحله ۴: چک کردن هر دفتر
            for office in OFFICES:
                try:
                    await page.select_option("select#sede", label=office)
                    await asyncio.sleep(random.uniform(0.8, 1.5))
                    await page.click("input[value='Aceptar']")
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(random.uniform(1, 2))

                    # چک کردن پیام "no hay citas"
                    content = await page.content()
                    content_upper = content.upper()

                    no_appointment_phrases = [
                        "NO HAY CITAS DISPONIBLES",
                        "NO EXISTEN CITAS DISPONIBLES",
                        "EN ESTE MOMENTO NO HAY",
                    ]

                    has_no_cita = any(phrase in content_upper for phrase in no_appointment_phrases)

                    if not has_no_cita:
                        # احتمالاً نوبت هست!
                        print(f"[!!!] نوبت پیدا شد در: {office}")
                        found_slots.append(office)

                    else:
                        print(f"[ ] {office}: نوبت نداره")

                    # برگشتن به صفحه قبل
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(random.uniform(1, 1.5))

                except Exception as e:
                    print(f"[ERR] {office}: {e}")
                    continue

        except Exception as e:
            print(f"[MAIN ERROR] {e}")

        await browser.close()

        if found_slots:
            msg = (
                "🚨 <b>نوبت پیدا شد!</b> 🚨\n\n"
                f"📍 <b>دفاتر با نوبت خالی:</b>\n"
                + "\n".join(f"  ✅ {o}" for o in found_slots)
                + f"\n\n⏰ زمان: {datetime.now().strftime('%H:%M:%S')}"
                + "\n\n🔗 <a href='https://icp.administracionelectronica.gob.es/icpplus/'>برو ثبت کن!</a>"
            )
            send_telegram(msg)
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] هیچ نوبتی پیدا نشد.")
            return False


# ─────────────────────────────────────────
#   حلقه اصلی
# ─────────────────────────────────────────
async def main():
    print("=" * 50)
    print("  بات چک نوبت هuellas TIE بارسلونا")
    print("=" * 50)

    # تست تلگرام
    send_telegram(
        "✅ <b>بات شروع به کار کرد</b>\n"
        f"هر {CHECK_INTERVAL_MINUTES} دقیقه یه‌بار چک می‌کنه.\n"
        "وقتی نوبت پیدا بشه بهت خبر می‌دم! 🔔"
    )

    check_count = 0
    while True:
        check_count += 1
        print(f"\n─── چک شماره {check_count} ───")

        try:
            found = await check_appointment()
            if found:
                # اگه نوبت پیدا شد، ۳۰ ثانیه صبر کن بعد ادامه بده
                await asyncio.sleep(30)
        except Exception as e:
            print(f"[LOOP ERROR] {e}")

        # هر ۵۰ چک یه پیام وضعیت بفرست (نشون می‌ده بات هنوز کار می‌کنه)
        if check_count % 50 == 0:
            send_telegram(
                f"💙 بات هنوز فعاله\n"
                f"تعداد چک: {check_count}\n"
                f"آخرین چک: {datetime.now().strftime('%H:%M')}"
            )

        # صبر بین هر چک
        interval = CHECK_INTERVAL_MINUTES * 60
        # کمی random اضافه می‌کنه تا طبیعی‌تر بنظر برسه
        jitter = random.uniform(-30, 30)
        await asyncio.sleep(interval + jitter)


if __name__ == "__main__":
    asyncio.run(main())
