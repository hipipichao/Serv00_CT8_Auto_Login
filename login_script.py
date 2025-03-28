import json
import asyncio
from pyppeteer import launch
from datetime import datetime, timedelta
import aiofiles
import random
import requests
import os

# 从环境变量中获取 Telegram Bot Token 和 Chat ID
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def format_to_iso(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')


async def delay_time(ms):
    await asyncio.sleep(ms / 1000)


# 全局浏览器实例
browser = None

# telegram消息
message = ""


async def login(username, password, panel):
    global browser

    page = None  # 确保 page 在任何情况下都被定义
    serviceName = 'CT8' if 'ct8' in panel else 'Serv00'  # 修改大小写
    try:
        if not browser:
            browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])

        page = await browser.newPage()
        url = f'https://{panel}/login/?next=/'
        await page.goto(url)

        username_input = await page.querySelector('#id_username')
        if username_input:
            await page.evaluate('''(input) => input.value = ""''', username_input)

        await page.type('#id_username', username)
        await page.type('#id_password', password)

        login_button = await page.querySelector('#submit')
        if login_button:
            await login_button.click()
        else:
            raise Exception('无法找到登录按钮')

        await page.waitForNavigation()

        is_logged_in = await page.evaluate('''() => {
            const logoutButton = document.querySelector('a[href="/logout/"]');
            return logoutButton !== null;
        }''')

        return is_logged_in

    except Exception as e:
        print(f'{serviceName}账号 {username} 登录时出现错误: {e}')
        return False

    finally:
        if page:
            await page.close()


async def shutdown_browser():
    global browser
    if browser:
        await browser.close()
        browser = None


async def main():
    global message

    try:
        async with aiofiles.open('accounts.json', mode='r', encoding='utf-8') as f:
            accounts_json = await f.read()
        accounts = json.loads(accounts_json)
    except Exception as e:
        print(f'读取 accounts.json 文件时出错: {e}')
        return

    # 添加报告头部
    message += "📊 *登录状态报告*\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n"

    for account in accounts:
        username = account['username']
        password = account['password']
        panel = account['panel']

        serviceName = 'CT8' if 'ct8' in panel else 'Serv00'  # 修改大小写
        is_logged_in = await login(username, password, panel)

        now_beijing = format_to_iso(datetime.utcnow() + timedelta(hours=8))
        status_icon = "✅" if is_logged_in else "❌"
        status_text = "登录成功" if is_logged_in else "登录失败"

        message += (
            f"🔹 *服务商*: `{serviceName}`\n"  # 保持变量引用
            f"👤 *账号*: `{username}`\n"
            f"🕒 *时间*: {now_beijing}\n"
            f"{status_icon} *状态*: _{status_text}_\n"
            "────────────────────\n"
        )

        delay = random.randint(1000, 8000)
        await delay_time(delay)

    # 添加报告尾部
    message += "\n🏁 *所有账号操作已完成*"
    await send_wx_message(message)
    print('所有账号登录完成！')
    print(message)
    await shutdown_browser()


async def get_token():
    url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=ww04276e7ac1b9fe59&corpsecret=pvp1-BUSpxgrz1iKIimRU4CPsGtk63-mUFuGqYb66WE'
    resp = requests.get(url)
    ACCESS_TOKEN = resp.json()['access_token']
    return ACCESS_TOKEN


async def send_wx_message(message):
    formatted_message = f"""
📨 *Serv00 & CT8 保号脚本运行报告*
━━━━━━━━━━━━━━━━━━━━
🕘 北京时间: `{format_to_iso(datetime.utcnow() + timedelta(hours=8))}`
🌐 UTC时间: `{format_to_iso(datetime.utcnow())}`
━━━━━━━━━━━━━━━━━━━━

{message}
"""
    ACCESS_TOKEN = get_token()
    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'.format(ACCESS_TOKEN)
    data = {
        "touser": "ZhaiYaChao",
        "msgtype": "text",
        "agentid": 1000004,
        "text": {
            "content": formatted_message
        },
        "safe": 0,
        "enable_id_trans": 0,
        "enable_duplicate_check": 0,
        "duplicate_check_interval": 1800
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code != 200:
            print(f"发送消息到企业微信失败: {response.text}")
    except Exception as e:
        print(f"发送消息到企业微信时出错: {e}")


if __name__ == '__main__':
    asyncio.run(main())
