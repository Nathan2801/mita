
# Mita - Personal Task Manager.

Mita is a simple terminal program to manage tasks.

> [!NOTE]
> This is a personal usage project and can contains some flaws, the development
> happens over time as much as I use this tool.

## Requirements

* Python 3.13 (could work in older versions, but was not tested).

## Install

```bash
git clone https://github.com/nathan2801/mita
python mita/mita.py
```

## Usage

> [!TIP]
> For easy access you could simply add a alias to your shell profile.

Getting help.
```bash
python mita.py
```

Adding a task.
```bash
python mita.py add -d 'foo'
```

Adding a task with hidden tags. Currently tags are simply part of the task
description which are hidden when listing without `-v/--verbose` flag.
```bash
python mita.py add -d 'foo // #tag1,#tag2'
```

Listing tasks.
```bash
python mita.py list 
```

Listing tasks with their IDs and tags.
```bash
python mita.py list -v
```

Listing tasks with a pattern.
```bash
python mita.py list -p 'fo'
```

Set a task as done.
```bash
python mita.py done -p 'fo'
```

Remove tasks with a pattern.
```bash
python mita.py remove -p 'fo'
```

Remove all tasks that are marked as done, `-s/--status` is used to filter
tasks based on their status, `todo` and `done` are the only possible values.
```bash
python mita.py remove -s done
```

Remove all tasks, `-m/--multiple` flag should be setted when a pattern
matches multiple tasks (avoid mistakes).
```bash
python mita.py remove -p '*' -m
```

Remove task with a ID.
```bash
python mita.py remove -i 1786144913
```

## Command Output Format

Most commands provides a simple output format to simplify the interface with
shells, except by the `list` subcommand which has a human-oriented interface.

| command | output |
| -       | -      |
| add     | id     |
| done    | id(s)  |
| todo    | id(s)  |
| remove  | id(s)  |
| file    | path   |
| local   | path   |

Here are some example of how to use `mita` along side with bash.

```bash
# Add a task
id=$(mita add -d 'Buy cookies')
echo "Task added id: $id"

# Remove a task by id (when multiple return each task id in one line)
id=$(mita done -i $id)
echo "Task removed id: $id"

# Remove all tasks and echo their ids
ids=$(mita rm -m -p '*')
echo "$ids" | xargs -L1 echo "Removed task id:"

# Read current tasks file (json format)
path=$(mita file)
cat $path

# Create local tasks file and read it (json format)
path=$(mita local)
cat $path
```
