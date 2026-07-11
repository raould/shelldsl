# TODO

When using this VM project to create portable Python code, there will be iterations necessary to make edits until the code runs successfully cross-version.

## The Nested Loop

A potential loop looks like this:

1. 1st stage
    1. Agent runs VM script to run checkers on target files.
    2. Agent reads all emitted errors.
    3. Agent applies changes to the target files under analysis in order to resolve the errors.
    4. Repeat from 1.1 until there are no reported errors.

2. 2nd stage
    1. Agent uses VM script to run target files on all Python verisons supported by VM/docker/Dockerfile.py*.
    2. Agent reads all emitted errors.
    3. Agent applies changes to the target files under analysis in order to resolve the errors.
    4. Agent runs 1st stage loop on all target files until there are no errors reported by the checkers.
    5. Repeat from 2.1 until there are no reported errors.
