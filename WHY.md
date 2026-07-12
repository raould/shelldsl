The Two Problems Problem

license: public domain CC0

Why moving from Bash to Python is a trap door, not a ladder

There's an old joke: "I had a problem, so I used \[tool\]. Now I have two problems." Moving from Bash to Python is exactly this. You had one problem — your shell script can't parse JSON, or you need a hash map, or your text munging is getting gnarly. So you reach for Python. Now you have two problems: the original problem, and Python's entire dependency/versioning/packaging ecosystem sitting underneath you.

But the real question isn't "Bash or Python." The real question is: why did you leave Bash in the first place? And the answer reveals a deeper tension that neither a shell DSL nor a Python migration cleanly solves.

⸻

Part 1: The real reason you leave Bash

It's not about HTTP. It's not about syntax. It's about data.

The surface-level complaint is always ergonomic: "I hate quoting rules," "subprocess is ugly," "I need error handling." But the fundamental reason people leave shell scripting is that shell data is flat text, and real problems have structure.

A shell pipeline is a stream of bytes. Usually lines. Sometimes tab-separated fields. The entire computational model is:

produce bytes | transform bytes | consume bytes

This works beautifully when your problem fits that shape. grep, awk, sed, sort, uniq, cut, wc — these are all line-oriented tools operating on byte streams. They compose perfectly because they agree on a universal interchange format: newlines and fields.

But the moment your data has nesting, types, relationships, or schema, you're fighting the model. Consider what happens when you curl a JSON API in Bash:

curl \-s https://api.example.com/users | jq '.\[\] | select(.active) | .email'

This works. But now try: "get all active users, look up their most recent order, compute the total revenue by region, and flag any region where revenue dropped more than 10% from last month." In Bash, you're now juggling temporary files, parsing JSON with jq into flat text, re-parsing that text, doing arithmetic with bc or awk, and building up associative arrays with fragile key-encoding hacks.

You didn't leave Bash because curl was hard. You left because your data stopped being lines.

The format gap

Shell tools communicate through three formats, all limited:

Plain text lines. Great for logs, file lists, simple records. Falls apart with any field that might contain spaces, newlines, or special characters. There's no quoting standard — CSV sort of tries, TSV avoids the problem by banning tabs, and most tools just pray that filenames don't have newlines in them.

Flat delimited fields. cut \-d: \-f1 /etc/passwd works because /etc/passwd has a known, stable, simple schema. But this breaks the moment a field contains the delimiter, or the schema has optional fields, or you need nested records.

JSON (via jq). This is the modern escape hatch: jq gives you structured queries over nested data. But jq is its own language, with its own learning curve, and the result still comes back as text that you have to re-parse downstream. You're writing programs in two languages (Bash \+ jq), threading data between them as serialized strings.

The deeper truth: pipes are a universal interface, but text is a lowest-common-denominator format. You get composability at the cost of structure. The moment you need to carry structure across a pipe boundary, you're serializing and deserializing by hand.

This is the actual inflection point. Not "my script is getting long" or "I need better error handling." It's: my data has shape, and my tools can't see it.

What "real datatypes" actually buy you

When you move to Python (or any language with real data structures), you get:

Named fields. user.email instead of echo "$line" | cut \-d, \-f3 and hoping field 3 is still email after someone added a column.

Nesting. A user has orders. An order has items. An item has a price. This is trivial in Python. In Bash, you're encoding it as user\_123\_order\_456\_item\_789\_price in variable names or temp files.

Type safety (loose as it is in Python). An integer is an integer. A list is a list. You don't accidentally sort numbers lexicographically or split a string on a space that was part of the data.

Composition through function calls. Returning structured data from a function is trivial. In Bash, a function can only "return" by printing to stdout (text again) or setting global variables.

In-memory joins and aggregations. Grouping, filtering, mapping, reducing — these are natural operations on collections. In Bash, every one of them is an awk program or a loop with string manipulation.

This is the gravity that pulls people toward Python. And it's legitimate. The pull isn't a failure of understanding — it's a recognition that some problems are fundamentally about structured data, and line-oriented tools are the wrong abstraction.

⸻

Part 2: The trap door

So you move to Python. Now you can parse JSON into dicts, build objects, use real control flow, handle errors with exceptions, and compose functions that pass structured data around. Your data problem is solved.

But you've acquired a new problem: the platform under you is moving.

Your Bash script from 2009 that calls curl, jq, grep, and awk? It still runs. It will run in 2030\.

Your Python script from 2009? It's Python 2\. It uses urllib2, which doesn't exist anymore. It uses print as a statement. It uses has\_key() on dicts. It assumes strings are bytes. It might use optparse (deprecated in favor of argparse). It installs dependencies with easy\_install into the system Python. It is, in every practical sense, dead code that requires archaeology to revive.

This is the two-problems problem. You solved your data structure problem by stepping onto a platform that:

* Broke backward compatibility in a major version transition  
* Evolves its standard library continuously  
* Depends on an ecosystem of third-party packages, each on its own release schedule  
* Has a packaging and environment story that has changed repeatedly (setuptools, pip, virtualenv, pipenv, poetry, conda, pdm, uv)  
* Adds new syntax regularly (f-strings, walrus operator, pattern matching, exception groups)

You traded a stable platform with weak data handling for a powerful platform with a moving floor.

⸻

Part 3: A minimal shell DSL — meeting in the middle

Given the tension above, what would it look like to get both stability and structure? The idea is: stay as close to shell semantics as possible (invoke external tools, use pipes, respect exit codes) but do it from inside Python, where you have real data types waiting to receive the results.

Here's a sketch of what a minimal, frozen shell DSL in Python might look like.

The core primitive: cmd

from shelldsl import cmd

\# Just run something. Like typing it in a terminal.

cmd("ls \-la /etc")

\# Capture output as text.

result \= cmd("git status \--porcelain").text

\# Check success.

if cmd("make \-j4").ok:

    cmd("make install")

\# Exit code explicitly available.

code \= cmd("grep \-q root /etc/passwd").code

No subprocess.Popen. No shell=True vs shell=False confusion. No shlex.split. The string is a command, it runs, you get back a result object with .text, .ok, .code, .lines.

Pipes: shell-style composition

\# Pipe between commands, just like shell.

result \= cmd("dmesg") | cmd("grep usb") | cmd("tail \-20")

\# The result is the final command's output.

for line in result.lines:

    print(line)

This is syntactic sugar over actual OS pipes. The DSL handles the plumbing. Each command is a real process. No Python buffering surprises.

The key insight: use curl, not requests

\# Don't do this (fragile, version-dependent, ecosystem-coupled):

import requests

r \= requests.get("https://api.example.com/users")

data \= r.json()

\# Do this instead (stable, external, curl hasn't changed in 20 years):

data \= cmd("curl \-s https://api.example.com/users").json()

The .json() method on the result object is where the shell world meets the Python world. The HTTP call happens in curl — stable, external, well-tested, version-independent. The parse happens in Python — where structured data actually belongs.

This is the crucial boundary: external tools for I/O, Python for data.

Variables and interpolation

url \= "https://api.example.com/users"

token \= os.environ\["API\_TOKEN"\]

\# Safe interpolation — arguments are escaped, not word-split.

data \= cmd("curl \-s \-H", f"Authorization: Bearer {token}", url).json()

\# Or explicit list form for full control.

data \= cmd(\["curl", "-s", "-H", f"Authorization: Bearer {token}", url\]).json()

Environment management

from shelldsl import cmd, Env

\# Inherit current env, override specific vars.

env \= Env(CC="clang", CFLAGS="-O2 \-Wall")

cmd("make \-j4", env=env)

\# Chain environments.

build\_env \= Env.current().with\_(CC="clang", DEBUG="1")

cmd("./configure && make", env=build\_env)

The bridge: where text becomes structure

This is where the DSL earns its keep. The whole point of being in Python is to cross the format gap — to take the flat text that shell tools produce and give it shape.

\# CSV output → Python dicts

rows \= cmd("cat sales.csv").csv(header=True)

\# rows \= \[{"region": "west", "revenue": "142000", ...}, ...\]

\# JSON output → Python objects  

users \= cmd("curl \-s https://api.example.com/users").json()

\# users \= \[{"id": 1, "name": "Alice", "active": True}, ...\]

\# Line-oriented output → filtered list

pids \= \[int(line.split()\[1\]) for line in cmd("ps aux").lines if "nginx" in line\]

\# Tab-separated → named tuples

records \= cmd("cut \-f1,3,5 data.tsv").tsv(columns=\["name", "age", "score"\])

\# Key-value output (like env, git config, etc.)

config \= cmd("git config \--list").kv(sep="=")

\# config \= {"user.name": "Alice", "user.email": "alice@example.com", ...}

This is the pattern: the left side of the bridge is shell (stable, external, text). The right side is Python (structured, typed, manipulable). The DSL is the bridge.

What the DSL deliberately does NOT include

The stability of this approach depends on what you leave out.

No HTTP library. Use curl. 

No file-watching library. Use inotifywait or fswatch.

No process management library. Use systemctl or supervisorctl. 

No argument parsing framework. Use getopt or keep it simple. 

No async runtime. If you need concurrency, use xargs \-P or parallel. 

No dependency on any third-party Python package.

The DSL is a bridge between OS-level tools (frozen, stable, external) and Python data structures (powerful, typed, composable). It is not a framework. It has no plugins. It does not evolve.

⸻

Part 4: The honest tension

There's a catch, and it would be dishonest not to name it.

The shell DSL works beautifully when your workflow is: invoke tools, capture output, parse it, make decisions, invoke more tools. This covers a huge amount of real-world scripting: deployment automation, log analysis, system administration, CI/CD pipelines, data pipeline orchestration.

But it doesn't cover everything. Some problems are fundamentally compute problems, not orchestration problems. If you're doing numerical work, text analysis, machine learning, web serving, or building applications, you need Python-native libraries. You need numpy, pandas, flask, sqlalchemy. You need the ecosystem. And the ecosystem is where the instability lives.

The honest framing is that there are two distinct activities that people conflate:

Scripting — orchestrating tools, moving data between systems, automating workflows. For this, the shell DSL approach is ideal. Stay external. Stay stable. Use Python only for data structure and control flow.

Programming — building applications, implementing algorithms, processing data computationally. For this, you need the full language and its ecosystem. Accept the maintenance cost.

The mistake is using the programming stack for scripting tasks. You don't need requests \+ json \+ a virtual environment \+ requirements.txt to hit an API endpoint and check a field in the response. You need curl and a JSON parser.

The other mistake is using the scripting stack for programming tasks. You don't want to cmd("python3 \-c 'import numpy; ...'") your way through a matrix multiplication. That's just Bash with extra steps.

The shell DSL gives you a clean place to stand for the scripting case, without falling through the trap door into Python's dependency world. For the programming case, you walk through that door knowingly, accepting the cost.

⸻

Summary: the decision framework

Stay in Bash when your data is lines and your job is plumbing.

Use the shell DSL when your data starts to have structure but your job is still orchestration — calling tools, parsing results, making decisions, calling more tools. You get Python's data types without Python's ecosystem fragility.

Go full Python when your job is computation — when you need to transform, model, analyze, or serve data using algorithms that don't exist as CLI tools. Accept the dependency cost. Pin your versions. Maintain your environment.

The inflection point isn't about script length or complexity. It's about the shape of your data and whether your job is orchestrating tools or implementing logic. The shell DSL exists for the large middle ground where people currently fall through the trap door unnecessarily.

