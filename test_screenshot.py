"""
تست بات - اسکرین‌شات می‌گیره و توی تلگرام می‌فرسته
"""

import asyncio
import requests
from playwright.async_api import async_playwright

# ─── اینجا رو پر کن ───
TELEGRAM_BOT_TOKEN = "8612775892:AAEyEN7eoW_RH6Sl_-IklTotVfuw5R3VDw8"
TELEGRAM_CHAT_ID   = "8924939591"
# ──────────────────────

async def send_photo(path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(path, "rb") as f:
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": f})
    print("تلگرام:", r.status_code, r.text[:100])

async def send_text(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

async def test():
    print("شروع تست...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-ES",
        )
        page = await context.new_page()

        # مرحله ۱ - صفحه اول
        print("مرحله ۱: باز کردن سایت...")
        await page.goto("https://icp.administracionelectronica.gob.es/icpplus/", timeout=30000)
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/step1.png")
        await send_photo("/tmp/step1.png", "مرحله ۱: صفحه اول سایت")

        # محتوای صفحه برای دیباگ
        content = await page.content()
        selects = await page.query_selector_all("select")
        print(f"تعداد dropdown: {len(selects)}")
        await send_text(f"تعداد dropdown در صفحه اول: {len(selects)}")

        # مرحله ۲ - انتخاب Barcelona
        print("مرحله ۲: انتخاب Barcelona...")
        try:
            # پیدا کردن همه option ها
            options = await page.evaluate("""
                () => {
                    const selects = document.querySelectorAll('select');
                    let result = [];
                    selects.forEach((sel, i) => {
                        let opts = [];
                        sel.querySelectorAll('option').forEach(o => opts.push(o.text));
                        result.push({index: i, id: sel.id, name: sel.name, options: opts.slice(0,10)});
                    });
                    return result;
                }
            """)
            await send_text(f"dropdown ها:\n{str(options)[:500]}")
            
            # انتخاب Barcelona
            selected = False
            for sel_info in options:
                for opt in sel_info['options']:
                    if 'barcelona' in opt.lower() or 'Barcelona' in opt:
                        sel_id = sel_info['id'] or sel_info['name']
                        if sel_id:
                            await page.select_option(f"#{sel_id}" if sel_info['id'] else f"[name='{sel_info['name']}']", label=opt)
                        else:
                            await page.select_option(f"select:nth-child({sel_info['index']+1})", label=opt)
                        selected = True
                        await send_text(f"✅ Barcelona انتخاب شد: {opt}")
                        break
                if selected:
                    break
                    
            if not selected:
                await send_text("❌ Barcelona پیدا نشد در dropdown")
                
        except Exception as e:
            await send_text(f"❌ خطا در مرحله ۲: {str(e)[:200]}")

        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/step2.png")
        await send_photo("/tmp/step2.png", "مرحله ۲: بعد از انتخاب استان")

        # مرحله ۳ - کلیک Aceptar
        print("مرحله ۳: کلیک Aceptar...")
        try:
            btns = await page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('input[type=submit], button');
                    return Array.from(btns).map(b => ({text: b.value || b.textContent, id: b.id}));
                }
            """)
            await send_text(f"دکمه‌ها: {str(btns)[:300]}")
            
            await page.click("input[type='submit']")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
        except Exception as e:
            await send_text(f"❌ خطا در کلیک Aceptar: {str(e)[:200]}")

        await page.screenshot(path="/tmp/step3.png")
        await send_photo("/tmp/step3.png", "مرحله ۳: بعد از Aceptar اول")

        # مرحله ۴ - انتخاب نوع خدمت
        print("مرحله ۴: انتخاب نوع خدمت...")
        try:
            options2 = await page.evaluate("""
                () => {
                    const selects = document.querySelectorAll('select');
                    let result = [];
                    selects.forEach((sel, i) => {
                        let opts = [];
                        sel.querySelectorAll('option').forEach(o => opts.push(o.text));
                        result.push({index: i, id: sel.id, name: sel.name, options: opts});
                    });
                    return result;
                }
            """)
            await send_text(f"dropdown های مرحله ۴:\n{str(options2)[:800]}")
        except Exception as e:
            await send_text(f"❌ خطا در مرحله ۴: {str(e)[:200]}")

        await browser.close()
        await send_text("✅ تست تموم شد!")
        print("تست تموم شد!")

asyncio.run(test())
