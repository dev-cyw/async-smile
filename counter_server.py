import asyncio
import copy
import datetime
import os
import pathlib
import time

from fastapi import FastAPI, Request, Query, HTTPException
from uvicorn import run
from os import urandom
from fastapi.responses import FileResponse
import matplotlib.pyplot as mpl


app = FastAPI()
app.state.requests = 0
app.state.history = []
app.state.response_history = []
app.state.task = None


async def count_requests():
    last_count = 0
    while True:
        start = copy.copy(app.state.requests)
        await asyncio.sleep(1.0)
        end = copy.copy(app.state.requests)
        count = end - start

        # Add to history, only if history[0] is not zero and history[-1] is not zero.
        try:
            if count == 0:
                if app.state.history[0] != 0 and app.state.history[-1] != 0:
                    app.state.history.append(count)
            else:
                app.state.history.append(count)
        except IndexError:
            app.state.history.append(count)

        if end == start or count == last_count:
            continue
        else:
            last_count = count
        print("[%s] Requests Per Second: %s" % (datetime.datetime.now().strftime("%X"), count))


@app.on_event("startup")
async def startup():
    app.state.task = asyncio.create_task(count_requests())


@app.middleware("http")
async def middleware(request: Request, call_next):
    if len(request.url.path) > 1:
        return await call_next(request)
    start = time.time_ns()
    response = await call_next(request)
    end = time.time_ns()
    app.state.response_history.append(round(end - start))
    return response


@app.get("/")
def get_root(response: bool = False):
    app.state.requests += 1
    if response:
        return {"requests": app.state.requests, "random_bytes": urandom(69).hex()}
    return {}


@app.post("/reset")
def reset_counter(to: int = 0):
    app.state.requests = to
    return "ok"


@app.get("/plot")
def generate_plot(obj: str = Query("rps", regex=r"^(rps|latency)$")):
    match obj:
        case "rps":
            mpl.plot(range(len(app.state.history)), app.state.history)
            mpl.title("Requests received per second (RPS)")
            mpl.xlabel("Time since first request (seconds)")
            mpl.ylabel("Requests Per Second")
            mpl.grid(True)
            mpl.savefig("./plot.png")
            mpl.close()
        case "latency":
            mpl.plot(range(len(app.state.response_history)), [round(x / 1e+6) for x in app.state.response_history])
            mpl.title("Response time per request")
            mpl.xlabel("Request number")
            # mpl.ylabel("Response Time (µs)")
            mpl.ylabel("Response Time (ms)")
            mpl.grid(True)
            mpl.savefig("./plot.png")
            mpl.close()
        case _:
            raise HTTPException(status_code=400, detail="Invalid plot type")
    return FileResponse("./plot.png")


@app.on_event("shutdown")
async def shutdown():
    app.state.task.cancel()
    try:
        app.state.task.result()
    except (asyncio.CancelledError, asyncio.TimeoutError, asyncio.InvalidStateError):
        pass
    p = pathlib.Path("./plot.png")
    if p.exists():
        os.remove(p)


if __name__ == "__main__":
    run(app, port=8000, access_log=False)
