# async-smile

A program designed to stress test a web server by overloading it with traffic, simulating a DOS (denial of service). This program is provided for educational purposes only, use at your own risk.

## How to run your self
For this introduction, we're going to assume you're running on windows.

Before starting, make sure you have python 3.6 or above installed. You can check this by running (on windows) `py --version`.

1. First, you're going to want to download the code as a [zip file](https://github.com/EEKIM10/async-smile/archive/refs/heads/master.zip)
2. Then, extract the file. We are going to assume you've extracted it to your downloads folder.
3. You're then going to open up a terminal. Press the windows key on your keyboard, then type "cmd". Once the window pops up, run `cd Downloads\async-smile-master`.
4. Run `py async-smile.py --install`, and wait for it to finish.
5. Run `py async-smile.py` (with no arguments), and fill in the interactive prompts (for example, the first one asks for a URL - type that in, then hit enter).
6. The program will guide you from there.

If you want to stop the program before it finishes naturally, press `control` and `c` at the same time. If the program does not stop within 30 seconds, keep pressing them.

## Running the test server
If you want to test the power of this tool, you can start your own HTTP server to count the number of requests being sent. Think of it like a volt meter for your requests.

**Warning:** This is more advanced, and also requires python3.10 be installed.

1. Run `py -m pip install uvicorn[standard] fastapi matplotlib`
2. Run `py counter_server.py`. There is now, assuming everything went okay, a web page running on `http://localhost:8000/docs`

### Running a test
You're going to need to have two things:

* A browser open at [the plot generator](http://localhost:8000/docs#/default/generate_plot_plot_get)
* A terminal ready to run the async-smile.py file

Once those're ready, do the following:

1. Run `py async-smile.py`
2. Put `http://localhost:8000/` as the URL
3. Put however many threads in you want (the more the merrier, 2048 can reach about 22.2k requests in 30 seconds)
4. Put a number between 5 and 60 into the max time (you don't want it going on forever)
5. Wait until the program finishes
6. Switch to your browser, click "try it out", and press "execute"
7. You should get a nice graph with details on it.

Terminate the server the same way you'd terminate the async-smile program.

### Example of use:
Operating system: Debian 11
Terminal: bash
Network connection: local (n/a)

* URL: `http://localhost:8000/`
* Threads: 2048
* Max time: 30 seconds
![Output](/index.png)
