#!/usr/bin/env python3
"""Run a target command in a Dockerized Python interpreter.

This is host-side orchestration. The mounted project supplies the source and
its tests; the image supplies the interpreter and operating system.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run a command in a Dockerized interpreter"
    )
    parser.add_argument("--image", default=None, help="Docker image tag")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build and run every VM/docker/Dockerfile.py* image",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild matrix images even when the image already exists",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project directory to mount; defaults to the current directory",
    )
    parser.add_argument(
        "--workdir",
        default="/workspace",
        help="Container working directory",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Mount the project read-only",
    )
    parser.add_argument(
        "--network-none",
        action="store_true",
        help="Disable container networking",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional Docker container name",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run in the container; prefix with --",
    )
    return parser


def repository_root():
    scripts = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(scripts))


def dockerfiles():
    root = repository_root()
    pattern = os.path.join(root, "VM", "docker", "Dockerfile.py*")
    return sorted(glob.glob(pattern))


def image_name(dockerfile):
    name = os.path.basename(dockerfile)
    return "shelldsl-%s" % name.replace("Dockerfile.", "").replace("_", "-")


def docker_arguments(options):
    project = options.project or os.getcwd()
    project = os.path.abspath(project)
    if not os.path.isdir(project):
        raise ValueError("project directory does not exist: %s" % project)
    container_command = list(options.command)
    if container_command and container_command[0] == "--":
        container_command = container_command[1:]
    if not container_command:
        raise ValueError("a container command is required after --")

    if not options.image:
        raise ValueError("--image is required unless --all is used")
    command = ["docker", "run", "--rm"]
    if options.name:
        command.extend(["--name", options.name])
    if options.network_none:
        command.extend(["--network", "none"])
    mount = project + ":" + options.workdir
    if options.read_only:
        mount = mount + ":ro"
    command.extend(["--volume", mount, "--workdir", options.workdir])
    command.append(options.image)
    command.extend(container_command)
    return command


def build_arguments(dockerfile, tag):
    return [
        "docker", "build", "--file", dockerfile,
        "--tag", tag, repository_root(),
    ]


def image_exists(tag):
    return subprocess.call(
        ["docker", "image", "inspect", tag],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) == 0


def run(options):
    if shutil.which("docker") is None:
        sys.stderr.write("error: docker executable was not found\n")
        return 2
    if options.all:
        files = dockerfiles()
        if not files:
            sys.stderr.write("error: no VM/docker/Dockerfile.py* files found\n")
            return 2
        result = 0
        for dockerfile in files:
            tag = image_name(dockerfile)
            if options.rebuild or not image_exists(tag):
                sys.stdout.write("==> building %s (%s)\n" % (tag, dockerfile))
                status = subprocess.call(build_arguments(dockerfile, tag))
                if status != 0:
                    result = status
                    continue
            else:
                sys.stdout.write("==> reusing %s\n" % tag)
            options.image = tag
            try:
                command = docker_arguments(options)
            except ValueError as error:
                sys.stderr.write("error: %s\n" % error)
                return 2
            sys.stdout.write("==> running %s\n" % tag)
            status = subprocess.call(command)
            if status != 0:
                result = status
        return result
    try:
        command = docker_arguments(options)
    except ValueError as error:
        sys.stderr.write("error: %s\n" % error)
        return 2
    return subprocess.call(command)


def main(arguments):
    parser = build_parser()
    options = parser.parse_args(arguments)
    return run(options)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
