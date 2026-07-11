# The Two Problems Problem

## Why moving from Bash to Python is a trap door, not a ladder

There's an old joke: "I had a problem, so I used [tool]. Now I have two problems." Moving from Bash to Python is exactly this. You had one problem — your shell script can't parse JSON, or you need a hash map, or your text munging is getting gnarly. So you reach for Python. Now you have two problems: the original problem, and Python's entire dependency/versioning/packaging ecosystem sitting underneath you.

But the real question isn't "Bash or Python." The real question is: **why did you leave Bash in the first place?** And the answer reveals a deeper tension that neither a shell DSL nor a Python migration cleanly solves.

---

## Part 1: The real reason you leave Bash

### It's not about HTTP. It's not about syntax. It's about data.

The surface-level complaint is always ergonomic: "I hate quoting rules," "subprocess is ugly," "I need error handling." But the fundamental reason people leave shell scripting is that **shell data is flat text, and real problems have structure.**

A shell pipeline is a stream of bytes. Usually lines. Sometimes tab-separated fields. The entire computational model is:

```
produce bytes | transform bytes | consume bytes
```

This works beautifully when your problem fits that shape. `grep`, `awk`, `sed`, `sort`, `uniq`, `cut`, `wc` — these are all line-oriented tools operating on byte streams. They compose perfectly because they agree on a universal interchange format: newlines and fields.

But the moment your data has **nesting**, **types**, **relationships**, or **schema**, you're fighting the model. Consider what happens when you `curl` a JSON API in Bash:

```bash
curl -s https://api.example.com/users | jq '.[] | select(.active) | .email'
```

This works. But now try: "get all active users, look up their most recent order, compute the total revenue by region, and flag any region where revenue dropped more than 10% from last month." In Bash, you're now juggling temporary files, parsing JSON with `jq` into flat text, re-parsing that text, doing arithmetic with `bc` or `awk`, and building up associative arrays with fragile key-encoding hacks.

You didn't leave Bash because `curl` was hard. You left because **your data stopped being lines.**

### The format gap

Shell tools communicate through three formats, all limited:

**Plain text lines.** Great for logs, file lists, simple records. Falls apart with any field that might contain spaces, newlines, or special characters. There's no quoting standard — CSV sort of tries, TSV avoids the problem by banning tabs, and most tools just pray that filenames don't have newlines in them.

**Flat delimited fields.** `cut -d: -f1 /etc/passwd` works because `/etc/passwd` has a known, stable, simple schema. But this breaks the moment a field contains the delimiter, or the schema has optional fields, or you need nested records.

**JSON (via jq).** This is the modern escape hatch: `jq` gives you structured queries over nested data. But `jq` is its own language, with its own learning curve, and the result still comes back as text that you have to re-parse downstream. You're writing programs in two languages (Bash + jq), threading data between them as serialized strings.

The deeper truth: **pipes are a universal interface, but text is a lowest-common-denominator format.** You get composability at the cost of structure. The moment you need to carry structure across a pipe boundary, you're serializing and deserializing by hand.

This is the actual inflection point. Not "my script is getting long" or "I need better error handling." It's: **my data has shape, and my tools can't see it.**

### What "real datatypes" actually buy you

When you move to Python (or any language with real data structures), you get:

**Named fields.** `user.email` instead of `echo "$line" | cut -d, -f3` and hoping field 3 is still email after someone added a column.

**Nesting.** A user has orders. An order has items. An item has a price. This is trivial in Python. In Bash, you're encoding it as `user_123_order_456_item_789_price` in variable names or temp files.

**Type safety (loose as it is in Python).** An integer is an integer. A list is a list. You don't accidentally sort numbers lexicographically or split a string on a space that was part of the data.

**Composition through function calls.** Returning structured data from a function is trivial. In Bash, a function can only "return" by printing to stdout (text again) or setting global variables.

**In-memory joins and aggregations.** Grouping, filtering, mapping, reducing — these are natural operations on collections. In Bash, every one of them is an `awk` program or a loop with string manipulation.

This is the gravity that pulls people toward Python. And it's legitimate. The pull isn't a failure of understanding — it's a recognition that **some problems are fundamentally about structured data, and line-oriented tools are the wrong abstraction.**

---

## Part 2: The trap door

So you move to Python. Now you can parse JSON into dicts, build objects, use real control flow, handle errors with exceptions, and compose functions that pass structured data around. Your data problem is solved.

But you've acquired a new problem: **the platform under you is moving.**

Your Bash script from 2009 that calls `curl`, `jq`, `grep`, and `awk`? It still runs. It will run in 2030.

Your Python script from 2009? It's Python 2. It uses `urllib2`, which doesn't exist anymore. It uses `print` as a statement. It uses `has_key()` on dicts. It assumes strings are bytes. It might use `optparse` (deprecated in favor of `argparse`). It installs dependencies with `easy_install` into the system Python. It is, in every practical sense, dead code that requires archaeology to revive.

This is the two-problems problem. You solved your data structure problem by stepping onto a platform that:

- Broke backward compatibility in a major version transition
- Evolves its standard library continuously
- Depends on an ecosystem of third-party packages, each on its own release schedule
- Has a packaging and environment story that has changed repeatedly (`setuptools`, `pip`, `virtualenv`, `pipenv`, `poetry`, `conda`, `pdm`, `uv`)
- Adds new syntax regularly (f-strings, walrus operator, pattern matching, exception groups)

You traded a stable platform with weak data handling for a powerful platform with a moving floor.

---

## Part 3: A minimal shell DSL — meeting in the middle

Given the tension above, what would it look like to get **both** stability and structure? The idea is: stay as close to shell semantics as possible (invoke external tools, use pipes, respect exit codes) but do it from inside Python, where you have real data types waiting to receive the results.

Here's a sketch of what a minimal, frozen shell DSL in Python might look like.

### The core primitive: `cmd`

```python
from shelldsl import cmd

# Just run something. Like typing it in a terminal.
cmd("ls -la /etc")

# Capture output as text.
result = cmd("git status --porcelain").text

# Check success.
if cmd("make -j4").ok:
    cmd("make install")

# Exit code explicitly available.
code = cmd("grep -q root /etc/passwd").code
```

No `subprocess.Popen`. No `shell=True` vs `shell=False` confusion. No `shlex.split`. The string is a command, it runs, you get back a result object with `.text`, `.ok`, `.code`, `.lines`.

### Pipes: shell-style composition

```python
# Pipe between commands, just like shell.
result = cmd("dmesg") | cmd("grep usb") | cmd("tail -20")

# The result is the final command's output.
for line in result.lines:
    print(line)
```

This is syntactic sugar over actual OS pipes. The DSL handles the plumbing. Each command is a real process. No Python buffering surprises.

### The key insight: use curl, not requests

```python
# Don't do this (fragile, version-dependent, ecosystem-coupled):
import requests
r = requests.get("https://api.example.com/users")
data = r.json()

# Do this instead (stable, external, curl hasn't changed in 20 years):
data = cmd("curl -s https://api.example.com/users").json()
```

The `.json()` method on the result object is where the shell world meets the Python world. The HTTP call happens in `curl` — stable, external, well-tested, version-independent. The parse happens in Python — where structured data actually belongs.

This is the crucial boundary: **external tools for I/O, Python for data.**

### Variables and interpolation

```python
url = "https://api.example.com/users"
token = os.environ["API_TOKEN"]

# Safe interpolation — arguments are escaped, not word-split.
data = cmd("curl -s -H", f"Authorization: Bearer {token}", url).json()

# Or explicit list form for full control.
data = cmd(["curl", "-s", "-H", f"Authorization: Bearer {token}", url]).json()
```

### Environment management

```python
from shelldsl import cmd, Env

# Inherit current env, override specific vars.
env = Env(CC="clang", CFLAGS="-O2 -Wall")
cmd("make -j4", env=env)

# Chain environments.
build_env = Env.current().with_(CC="clang", DEBUG="1")
cmd("./configure && make", env=build_env)
```

### The bridge: where text becomes structure

This is where the DSL earns its keep. The whole point of being in Python is to cross the format gap — to take the flat text that shell tools produce and give it shape.

```python
# CSV output → Python dicts
rows = cmd("cat sales.csv").csv(header=True)
# rows = [{"region": "west", "revenue": "142000", ...}, ...]

# JSON output → Python objects  
users = cmd("curl -s https://api.example.com/users").json()
# users = [{"id": 1, "name": "Alice", "active": True}, ...]

# Line-oriented output → filtered list
pids = [int(line.split()[1]) for line in cmd("ps aux").lines if "nginx" in line]

# Tab-separated → named tuples
records = cmd("cut -f1,3,5 data.tsv").tsv(columns=["name", "age", "score"])

# Key-value output (like env, git config, etc.)
config = cmd("git config --list").kv(sep="=")
# config = {"user.name": "Alice", "user.email": "alice@example.com", ...}
```

This is the pattern: **the left side of the bridge is shell (stable, external, text). The right side is Python (structured, typed, manipulable). The DSL is the bridge.**

### What the DSL deliberately does NOT include

The stability of this approach depends on what you leave out.

No HTTP library. Use `curl`.
No file-watching library. Use `inotifywait` or `fswatch`.  
No process management library. Use `systemctl` or `supervisorctl`.
No argument parsing framework. Use `getopt` or keep it simple.
No async runtime. If you need concurrency, use `xargs -P` or `parallel`.
No dependency on any third-party Python package.

The DSL is a bridge between OS-level tools (frozen, stable, external) and Python data structures (powerful, typed, composable). It is not a framework. It has no plugins. It does not evolve.

---

## Part 4: The honest tension

There's a catch, and it would be dishonest not to name it.

The shell DSL works beautifully when your workflow is: **invoke tools, capture output, parse it, make decisions, invoke more tools.** This covers a huge amount of real-world scripting: deployment automation, log analysis, system administration, CI/CD pipelines, data pipeline orchestration.

But it doesn't cover everything. Some problems are fundamentally **compute problems**, not **orchestration problems.** If you're doing numerical work, text analysis, machine learning, web serving, or building applications, you need Python-native libraries. You need `numpy`, `pandas`, `flask`, `sqlalchemy`. You need the ecosystem. And the ecosystem is where the instability lives.

The honest framing is that there are two distinct activities that people conflate:

**Scripting** — orchestrating tools, moving data between systems, automating workflows. For this, the shell DSL approach is ideal. Stay external. Stay stable. Use Python only for data structure and control flow.

**Programming** — building applications, implementing algorithms, processing data computationally. For this, you need the full language and its ecosystem. Accept the maintenance cost.

The mistake is using the programming stack for scripting tasks. You don't need `requests` + `json` + a virtual environment + `requirements.txt` to hit an API endpoint and check a field in the response. You need `curl` and a JSON parser.

The other mistake is using the scripting stack for programming tasks. You don't want to `cmd("python3 -c 'import numpy; ...'")` your way through a matrix multiplication. That's just Bash with extra steps.

The shell DSL gives you a clean place to stand for the scripting case, without falling through the trap door into Python's dependency world. For the programming case, you walk through that door knowingly, accepting the cost.

---

## Part 5: Design lessons from the existing landscape

Several libraries and projects have attacked this exact problem. Rather than reviewing them, the question is: what design decisions did each one make, and which of those decisions should be stolen, adapted, or deliberately avoided by the DSL?

### From Plumbum: the environment is the hardest problem

Plumbum's most important contribution isn't its pipe syntax. It's the `local` object.

```python
from plumbum import local

# What will actually run? Plumbum tells you exactly.
local.cmd.ls          # LocalCommand(/bin/ls)
local["git"]          # LocalCommand(/usr/bin/git)
local.env["PATH"]     # the actual PATH, right now
local.cwd             # the actual working directory, right now
```

This solves a problem that every other library ignores and that causes real production failures: **when you write a Python script, you have no idea what environment it will run in.** Your interactive shell has a `.bashrc` that sets PATH, aliases, environment variables. A cron job has almost none of that. A Docker container has a different set. A CI runner has another. Another user on the same machine has their own. `systemd` services inherit yet a different environment. Your script worked on your laptop and broke in production because `/usr/local/bin` wasn't in PATH, or because `LANG` wasn't set, or because the working directory was `/` instead of your project root.

In Bash, this is somewhat visible — you can `echo $PATH` and `which git` and see what's going on. In Python, it's buried. `subprocess.run("git status", shell=True)` will use whatever shell the OS provides, with whatever PATH that shell inherits, and you'll get a cryptic "command not found" error with no indication of what PATH was searched.

Plumbum makes the environment a first-class, inspectable, modifiable object. You can ask "what would actually run if I typed `git`?" before running it. You can set a working directory with a context manager (`with local.cwd(path)`). You can snapshot and modify the environment explicitly.

**Design lesson for the DSL:** The environment must be explicit and inspectable, not implicit and inherited. The DSL needs:

```python
# See what will actually execute
cmd("git").which()          # "/usr/bin/git" or None

# See the current environment
cmd.env                     # the full environment dict
cmd.env["PATH"]             # the PATH that commands will search
cmd.cwd                     # the working directory for commands

# Modify it explicitly
with cmd.cd("/opt/project"):
    cmd("make")             # runs in /opt/project

with cmd.path_prepend("/opt/custom/bin"):
    cmd("my-tool")          # finds my-tool in /opt/custom/bin

# Or create an isolated context
ctx = cmd.context(
    cwd="/opt/project",
    env={"PATH": "/usr/bin:/bin", "HOME": "/root"},
)
ctx.run("make -j4")
```

Plumbum also does something the DSL should adopt: the `SshMachine` abstraction, where `remote["ls"]` gives you a command object that works identically to `local["ls"]` but runs over SSH. The same API, different machine. The DSL doesn't need SSH built in, but the *principle* — that a command context is an object you can swap — is right. You should be able to say "run these commands as if the environment were X" without mutating global state.

What Plumbum gets wrong, and what the DSL should avoid: the bracket syntax (`ls["-a"]`) is a Python-ism that doesn't read like either shell or natural English. The operator overloading (`& FG`, `< "file"`, `> "output"`) is clever but creates a private dialect. The DSL should use plain method calls and strings — boring, but readable by anyone who knows either shell or Python.

### From `sh`: the result model and the magic trap

`sh`'s result model is deceptively simple — calling a command returns a `RunningCommand` object that behaves like a string (its `__str__` returns stdout) but also carries `.exit_code`, `.stderr`, `.stdout`, and process state. This dual nature — "it's a string but also an object" — is actually a useful design pattern for the bridge problem.

```python
from sh import git
result = git("status", "--short")

# Use it as a string:
print(result)                    # prints stdout

# But also inspect it:
result.exit_code                 # 0
result.stderr                    # ""
```

The problem is that this string-like behavior hides the structure question. When the result *is* a string, there's no obvious moment where you're prompted to think "wait, I should parse this." You just use it as text, and your script works until the text format changes or contains unexpected characters.

**Design lesson for the DSL:** The result object should NOT behave like a string. It should be explicitly a result, and you should have to take a deliberate step to get data out of it. That step is the bridge:

```python
result = cmd("git status --porcelain")

# Not this (implicit string coercion):
print(result)              # should print something like <CmdResult 'git status --porcelain' code=0>

# But this (explicit extraction):
print(result.text)         # stdout as string
for line in result.lines:  # stdout split into lines
    ...
result.json()              # parse stdout as JSON
result.csv()               # parse stdout as CSV
result.ok                  # True if exit code == 0
result.code                # the exit code
```

The friction is intentional. Every time you write `.text` or `.lines` or `.json()`, you're making a decision about what format the output is in. That decision is the bridge moment — the point where unstructured bytes become structured data — and it should be visible in the code.

The other lesson from `sh` is about magic. `sh`'s `from sh import anything` works by installing a custom module finder that intercepts imports and creates command wrappers on the fly. This is the cleverest thing in the library, and also the most fragile. It breaks IDE autocompletion, confuses type checkers, and makes it impossible to know at a glance whether `from sh import foo` will work without actually running it. The 1.x to 2.x migration broke this mechanism in ways that required code changes.

**Design lesson for the DSL:** No import magic. Commands are created explicitly. This is more verbose but completely predictable:

```python
from shelldsl import cmd

# This always works. No magic, no PATH lookup at import time.
cmd("git status")

# If you want a reusable handle:
git = cmd.bind("git")
git("status")
git("log --oneline -10")
```

### From Xonsh: the bridge exists, and `$(@json ...)` is the key insight

Xonsh is the only project in the space that recognized the bridge as a first-class design problem. Its `$(@json ...)` operator takes the output of a command and parses it as JSON directly:

```
$(@json podman ps --format json)['ID']
```

That's not a shell command piped through `jq`. That's a shell command whose output is automatically deserialized into a Python dict, which you then index with `['ID']`. The data crosses from text to structure in one expression.

Xonsh also treats environment variables as typed Python objects — `$PATH` is a list, not a colon-delimited string, so you can `$PATH.append('/tmp')` instead of `export PATH=$PATH:/tmp`. This is the right idea: the environment isn't text, it's structure, and the shell should expose it as structure.

**Design lesson for the DSL:** Steal `$(@json ...)` as a method. Steal typed environment access. But do it in valid Python:

```python
# Xonsh's insight, in plain Python:
containers = cmd("podman ps --format json").json()
print(containers[0]["ID"])

# Typed environment access:
cmd.env.PATH                    # list, not colon-delimited string
cmd.env.PATH.append("/tmp")     # just works
cmd.env.PATH.prepend("/opt/bin")

# Not this:
path = os.environ["PATH"]       # colon-delimited string
parts = path.split(":")         # manual parsing
parts.append("/tmp")            # manual list ops
os.environ["PATH"] = ":".join(parts)  # manual serialization
```

What to avoid from Xonsh: the auto-detection between Python and shell modes. In Xonsh, `ls -l` runs as a shell command because `ls` and `l` aren't Python variables. But if you later `ls = 44` and `l = 2`, suddenly `ls -l` evaluates to `42`. This is an inherent ambiguity in a language that tries to be two things at once. The DSL avoids this entirely by being unambiguously Python: `cmd("ls -l")` is always a command invocation, `ls - l` is always Python arithmetic. No context-dependent parsing.

### From PipePy: lazy evaluation and the composition question

PipePy made an interesting design choice: commands are lazy by default. Constructing `ls("-l") | grep("py")` doesn't execute anything — it builds a pipeline object. Execution happens when you access the result. This means you can build up pipelines programmatically, pass them around, and execute them later.

```python
# PipePy's lazy construction:
pipeline = ls("-l") | grep("py") | wc("-l")
# Nothing has run yet.

result = pipeline.stdout  # NOW it runs.
```

This is a genuinely useful property for a DSL. It means pipelines are composable values — you can write functions that return pipelines, store pipelines in data structures, choose between pipelines based on conditions, and only execute at the point where you need the result.

**Design lesson for the DSL:** Consider a two-phase model. `cmd("ls -la")` creates a command spec. `.run()` or property access executes it. Pipelines are built by chaining specs:

```python
# Phase 1: build
pipeline = cmd("ps aux") | cmd("grep python") | cmd("wc -l")
# Nothing has executed.

# Phase 2: run
count = int(pipeline.text)
# Now it runs.

# This enables reusable pipeline templates:
def find_procs(name):
    return cmd("ps aux") | cmd(f"grep {name}") | cmd("grep -v grep")

python_procs = find_procs("python").lines
node_procs = find_procs("node").lines
```

PipePy also has a `source()` function that reads a shell file's environment effects — it runs the file in a bash subprocess, captures the resulting environment, and applies the differences to Python's `os.environ`. This is a pragmatic solution to a real problem: many projects have `.env` files, `activate` scripts, or shell-based configuration that sets environment variables. Python can't `source` these natively.

**Design lesson for the DSL:** Include a `source` primitive. This is table stakes for real-world use:

```python
# Absorb environment from a shell file:
cmd.source("./env.sh")                    # like running "source ./env.sh"
cmd.source("/opt/project/.env")
cmd.source("$HOME/.cargo/env")

# See what changed:
diff = cmd.source_preview("./env.sh")     # returns dict of added/changed vars
```

### The composite picture: what the DSL should steal

Assembling the lessons, the DSL's design isn't arbitrary — it's informed by what each predecessor got right and wrong:

**From Plumbum, steal:**
- Explicit environment model (`cmd.env`, `cmd.cwd`, `cmd.context(...)`)
- `which` / path resolution as a queryable operation
- The principle that command contexts are swappable objects
- Working-directory-as-context-manager

**From `sh`, steal:**
- The result object that carries stdout, stderr, and exit code together
- The single-file, zero-dependency distribution model

**Avoid from `sh`:**
- Import magic
- String-like result coercion (results should be explicitly results)
- Nesting-as-piping

**From Xonsh, steal:**
- `$(@json ...)` as `.json()` — output parsing as a first-class bridge operation
- Typed environment variables (PATH as a list, not a string)
- The recognition that the bridge is the central design problem

**Avoid from Xonsh:**
- New language / superset approach
- Auto-detection between modes
- Dependency on specific Python version ranges

**From PipePy, steal:**
- Lazy evaluation / two-phase (build, then run)
- `source()` for absorbing shell environment files
- Composable pipeline values

**Avoid from PipePy:**
- `overload_chars(locals())` and similar namespace injection magic

**From none of them, but needed:**
- `.json()`, `.csv()`, `.tsv()`, `.kv()` bridge methods on result objects
- A stability commitment — frozen API, no breaking changes, no new syntax
- Explicit non-goals: no SSH, no CLI toolkit, no color library, no framework ambitions

### The environment problem deserves special emphasis

The Plumbum lesson is worth expanding because the environment problem is more subtle than it first appears, and it bites harder than almost any other issue in practice.

When you type `git status` in your terminal, here's what actually happens: your shell reads `$PATH`, searches each directory in order, finds `/usr/bin/git`, and runs it. But the PATH was set by a chain of files — `/etc/environment`, then `/etc/profile`, then `~/.bashrc` or `~/.zshrc`, then maybe `~/.profile`, maybe `~/.bash_profile`, and any `source`d files along the way. Each one can modify PATH, set variables, define aliases, and alter the behavior of subsequent commands.

When you run `python3 myscript.py` from that same terminal, the script inherits that environment. But when the same script runs from cron, it gets a minimal environment — often just `/usr/bin:/bin`. When it runs from `systemd`, it gets whatever `Environment=` directives are in the unit file. When it runs in a Docker container, it gets whatever the Dockerfile's `ENV` directives set. When a colleague runs it on their machine, they get their PATH, their shell, their environment.

This means a Python script that calls external commands is implicitly coupled to the environment it runs in, but that coupling is invisible. There's no declaration, no check, no error message that says "this script requires `git` to be in PATH and `JAVA_HOME` to be set." The failures are silent and delayed: `FileNotFoundError: [Errno 2] No such file or directory: 'git'` at runtime, in production, on the machine where the environment is different.

The DSL should make this coupling explicit:

```python
# Declare what you need. Fail fast with clear messages.
cmd.require("git", "curl", "jq")
# → raises EnvironmentError("'jq' not found in PATH: /usr/bin:/bin")
#   before any command runs

# Or check more carefully:
cmd.require(
    "git >= 2.0",              # version check
    "python3",                 # existence check
    env=["API_TOKEN", "HOME"], # required env vars
)

# Snapshot the environment for reproducibility:
cmd.env.freeze("env.lock.json")
# → writes {"PATH": [...], "HOME": "...", "git": "/usr/bin/git", ...}

# Later, validate against it:
cmd.env.check("env.lock.json")
# → warns about differences
```

This isn't something any existing library does well. Plumbum lets you inspect the environment, but doesn't help you declare requirements. `sh` ignores the issue entirely. Xonsh inherits whatever the user's xonsh session has. The DSL should treat environment requirements the way Python treats import requirements — as declarations that can be checked, documented, and enforced.

---

## Summary: the decision framework

**Stay in Bash** when your data is lines and your job is plumbing.

**Use the shell DSL** when your data starts to have structure but your job is still orchestration — calling tools, parsing results, making decisions, calling more tools. You get Python's data types without Python's ecosystem fragility.

**Go full Python** when your job is computation — when you need to transform, model, analyze, or serve data using algorithms that don't exist as CLI tools. Accept the dependency cost. Pin your versions. Maintain your environment.

The inflection point isn't about script length or complexity. It's about the shape of your data and whether your job is orchestrating tools or implementing logic. The shell DSL exists for the large middle ground where people currently fall through the trap door unnecessarily.
