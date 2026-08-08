
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

* Getting help.
```bash
python mita.py
```

* Adding a task.
```bash
python mita.py add -d 'foo'
```

* Adding a task with hidden tags. Currently tags are simply part of the task
description which are hidden when listing without `-v/--verbose` flag.
```bash
python mita.py add -d 'foo // #tag1,#tag2'
```

* Listing tasks.
```bash
python mita.py list 
```

* Listing tasks with their IDs and tags.
```bash
python mita.py list -v
```

* Listing tasks with a pattern.
```bash
python mita.py list -p 'fo'
```

* Set a task as done.
```bash
python mita.py done -p 'fo'
```

* Remove tasks with a pattern.
```bash
python mita.py remove -p 'fo'
```

* Remove all tasks that are marked as done, `-s/--status` is used to filter
tasks based on their status, `todo|done` are the only possible values.
```bash
python mita.py remove -s done
```

* Remove all tasks, `-m/--multiple` flag should be setted when a pattern
matches multiple tasks (avoid mistakes).
```bash
python mita.py remove -p '*' -m
```

* Remove task with a ID.
```bash
python mita.py remove -i 1786144913
```

