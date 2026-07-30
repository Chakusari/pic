import asyncio
import logging
import requests
# غیرفعال کردن هشدارهای SSL برای تضمین کارکرد روی تمامی سرورها
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

from telegram import InlineQueryResultPhoto, InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import Application, CommandHandler, InlineQueryHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات تلگرام شما
TOKEN = "8903097399:AAG0CpaLRx9G_5ynP0QjsN8dmVIxC3YwrQI"

# لیست کلیدهای Serper شما با ساختار چرخشی و پشتیبان هوشمند
SERPER_KEYS = [
    "d81c9714877640c38873df19b68e15b5cf684f93",
    "be1ff9212ccb724f8c2ef6480a685db8c1660811",
    "bc47ac50500fd03138cd35af124536d0d359af52"
]


def fetch_google_images(query: str) -> tuple[list, str]:
    """
    جستجوی تصویر در گوگل با استفاده از چرخش هوشمند کلیدها بر پایه وب‌سرویس Serper
    """
    url = "https://google.serper.dev/images"
    payload = {
        "q": query,
        "num": 50  # درخواست حداکثر ۵۰ عکس
    }
    
    last_status = "CONNECTION_ERROR"
    
    for api_key in SERPER_KEYS:
        if not api_key:
            continue
            
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        try:
            # نمایش انتهای کلید برای تشخیص کلید در حال استفاده در ترمینال
            logger.info(f"Attempting search with API Key ending in: ...{api_key[-4:]}")
            response = requests.post(url, headers=headers, json=payload, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                images = data.get("images", [])
                results = []
                
                for item in images:
                    img_url = item.get("imageUrl")
                    thumb_url = item.get("thumbnailUrl") or img_url
                    
                    if img_url:
                        results.append({
                            "img_url": img_url,
                            "thumb_url": thumb_url
                        })
                
                if results:
                    return results, "SUCCESS"
                else:
                    # اتصال موفق بود اما گوگل واقعاً عکسی برای این واژه پیدا نکرد
                    return [], "NO_RESULTS"
                    
            elif response.status_code in [401, 403, 429]:
                # ۴۲۹ نشان‌دهنده اتمام محدودیت درخواست (Rate Limit) آن کلید است
                logger.warning(f"Key ...{api_key[-4:]} exhausted/unauthorized. Switching to next key...")
                last_status = "API_KEY_ERROR"
            else:
                logger.warning(f"Key ...{api_key[-4:]} failed with status {response.status_code}. Trying next...")
                last_status = "HTTP_ERROR"
                
        except Exception as e:
            logger.error(f"Network error with key ...{api_key[-4:]}: {e}")
            last_status = "CONNECTION_ERROR"
            
    # در صورتی که تمام کلیدها تست شدند و با شکست مواجه شدند، آخرین وضعیت خطا برگردانده می‌شود
    return [], last_status


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("The bot is running")


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query.strip()
    if not query:
        return

    # دریافت تصاویر گوگل با سیستم چرخشی چندکلیدی
    search_results, status = await asyncio.to_thread(fetch_google_images, query)
    
    inline_results = []
    
    if status == "SUCCESS" and search_results:
        for idx, item in enumerate(search_results):
            inline_results.append(
                InlineQueryResultPhoto(
                    id=str(idx),
                    photo_url=item["img_url"],
                    thumbnail_url=item["thumb_url"]
                )
            )
            
    elif status == "NO_RESULTS":
        inline_results.append(
            InlineQueryResultArticle(
                id="no_photos_found",
                title="نتیجه‌ای یافت نشد",
                description="گوگل برای این کلمه تصویری پیدا نکرد. کلمات دیگری را امتحان کنید.",
                input_message_content=InputTextMessageContent(
                    f"🔍 جستجوی عبارت «{query}» در گوگل نتیجه‌ای نداشت."
                )
            )
        )
    else:
        # در صورتی که تمام کلیدها از کار افتاده باشند این خطا چاپ می‌شود
        inline_results.append(
            InlineQueryResultArticle(
                id="serper_technical_error",
                title="خطای فنی در ارتباط با گوگل",
                description="اتصال سرور قطع است یا تمامی کلیدهای جستجو منقضی شده‌اند.",
                input_message_content=InputTextMessageContent(
                    "⚠️ در حال حاضر امکان دریافت اطلاعات از گوگل وجود ندارد. لطفاً اعتبار پنل کاربری کلیدهای خود را در Serper.dev بررسی کنید."
                )
            )
        )
    
    # ارسال نتایج به تلگرام با زمان کش ۲۴ ساعته جهت ذخیره توکن‌ها
    await update.inline_query.answer(inline_results, cache_time=86400)


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    logger.info("Bot started. Exclusively searching Google Images via Serper with multi-key rotation...")
    application.run_polling()


if __name__ == "__main__":
    main()
