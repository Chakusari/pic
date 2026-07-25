import asyncio
import logging
import requests
# غیرفعال کردن هشدارهای SSL برای سازگاری کامل با همه‌ی سرورها
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

# کلید اختصاصی فعال‌شده‌ی شما در سیستم Serper
SERPER_KEY = "d81c9714877640c38873df19b68e15b5cf684f93"


def fetch_google_images(query: str) -> tuple[list, str]:
    """
    جستجوی تصویر در گوگل با استفاده از وب‌سرویس Serper
    """
    url = "https://google.serper.dev/images"
    payload = {
        "q": query,
        "num": 50  # درخواست حداکثر ۵۰ عکس
    }
    
    headers = {
        "X-API-KEY": SERPER_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Searching Google Images for: '{query}'")
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
                # اتصال موفق بود ولی گوگل عکسی برای این کلمه پیدا نکرد
                return [], "NO_RESULTS"
                
        elif response.status_code in [403, 401]:
            logger.error("Serper API Key is invalid or expired.")
            return [], "API_KEY_ERROR"
        else:
            logger.error(f"Google Serper returned HTTP code: {response.status_code}")
            return [], "HTTP_ERROR"
            
    except Exception as e:
        logger.error(f"Network or Connection error: {e}")
        return [], "CONNECTION_ERROR"


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("The bot is running")


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query.strip()
    if not query:
        return

    # دریافت نتایج از گوگل به همراه وضعیت پاسخ
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
        # نمایش پیام راهنما در صورتی که واقعاً عکسی در گوگل یافت نشد
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
        # نمایش پیام خطا در صورت بروز مشکلات مربوط به کلید یا شبکه
        inline_results.append(
            InlineQueryResultArticle(
                id="serper_technical_error",
                title="خطای موقت در ارتباط با گوگل",
                description="اتصال سرور قطع است یا اعتبار کلید جستجو به اتمام رسیده است.",
                input_message_content=InputTextMessageContent(
                    "⚠️ در حال حاضر امکان دریافت اطلاعات از گوگل وجود ندارد. لطفاً اعتبار پنل Serper.dev خود را بررسی کنید."
                )
            )
        )
    
    # ارسال نتایج به تلگرام با قابلیت لود تا ۵۰ عکس
    await update.inline_query.answer(inline_results, cache_time=86400)


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    logger.info("Bot started. Exclusively searching Google Images via Serper...")
    application.run_polling()


if __name__ == "__main__":
    main()