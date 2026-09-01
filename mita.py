""" Mita - A simple Task manager.
"""
import os
import sys
import time
import json

TODO = "todo"
DONE = "done"

# When this is False we raise any exception as an usual python exception,
# otherwise we only print a user-friendly error message. Can be setted with
# -b/--debug flag.
catch_exception = True

class Unreachable(Exception):
    """ Debug error only that should never raise for the user.
    """
    def __init__(self, reason="", *args, **kwargs):
        self.reason = reason
        super().__init__(*args, **kwargs)

    def __str__(self):
        if self.reason == "":
            return "no reason provided"
        return f"{self.reason}"

class MissingSubcommand(Exception):
    """ Error when missing subcommand.
    """
    def __str__(self):
        return "missing subcommand"

class UnknownSubcommand(Exception):
    """ Error when a subcommand is not known.
    """
    def __init__(self, subcommand, *args, **kwargs):
        self.subcommand = subcommand
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"unknown subcommand: {self.subcommand}"

class MissingRequiredFlag(Exception):
    """ Error when missing a subcommand required flag.
    """
    def __init__(self, flag, *args, **kwargs):
        self.flag = flag
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"missing required flag: {self.flag["short"]}/{self.flag["long"]}"

class MissingOneOfRequiredFlags(Exception):
    """ Error Error when one of the required flags is missing.
    """
    def __init__(self, flags=[], *args, **kwargs):
        self.flags = flags
        super().__init__(*args, **kwargs)

    def __str__(self):
        to_line = lambda flag: f"{flag["short"]}/{flag["long"]}"
        flags_line = ", ".join(map(to_line, self.flags))
        return "missing one of the required flags: " + flags_line

class MultipleTasksFound(Exception):
    """ Error when multiple flag is not set and multiple tasks are filtered for
        certain operation.
    """
    def __str__(self):
        return "multiple tasks found, perhaps you want set -m/--multiple flag"

def shift(xs):
    """ Returns the first and remaining itens of a list.
    """
    match xs:
        case []:
            return None, []
        case [x, *rest]:
            return x, rest

def printx(*args, **kwargs):
    """ Extended print to handle terminal colors.

        >> printx("foo", color="green")
        >> printx("bar", color="yellow", end="")
    """  
    colors = {
        "black": 30, "red":     31,
        "green": 32, "yellow":  33,
        "blue":  34, "magenta": 35,
        "cyan":  36, "white":   37,
        "reset": 39,
    }

    color = kwargs.get("color", None)
    if color:
        del kwargs["color"] # make sure we don't pass it to builtin print.
    if color and color not in colors:
        raise Exception(f"invalid color: {color}")

    if color:
        co = colors[color]
        print(f"\033[{co}m", end="")
    print(*args, **kwargs)
    if color:
        re = colors["reset"]
        print(f"\033[{re}m", end="")

def loginfo(*args, **kwargs):
    """ Log an information.
    """
    printx("INFO: ", end="", color="yellow")
    printx(*args, **kwargs)

def logerror(*args, **kwargs):
    """ Log an error.
    """
    printx("ERROR: ", end="", color="red")
    printx(*args, **kwargs)

def flag(name, short, require_value=False, help=""):
    """ Returns a flag.
    """
    return {
        "name": name,
        "help": help,
        "long": "--" + name,
        "short": short,
        # Whether or not it requires a value.
        "require_value": require_value,
    }

def subcommand(name, help, required_flags=[], required_flags_or=[]):
    """ Returns a subcommand.
    """
    return name, {
        "name": name,
        "help": help,
        # Required flags.
        "required_flags": required_flags,
        # Required flags but allows flag A or flag B.
        "required_flags_or": required_flags_or,
    }

def program(name):
    """ Returns a terminal program.
    """
    return {
        "name": name,
        "opts": {},
        "flags": [],
        "subcommands": {},
    }

def program_add_flag(prg, *args, **kwargs):
    """ Add a program flag.
    """
    prg["flags"].append(flag(*args, **kwargs))

def program_find_flag(prg, flagname):
    """ Returns the flag information from a flag name.
    """
    for flag in prg["flags"]:
        if flag["name"] == flagname:
            return flag
    return None

def program_add_subcommand(prg, *args, **kwargs):
    """ Add a program subcommand.
    """
    name, subcmd = subcommand(*args, **kwargs)
    prg["subcommands"][name] = subcmd

def program_get_subcommand_information(prg):
    """ Returns the subcommand information from the subcommand option.
    """
    return prg["subcommands"][prg["opts"]["subcommand"]]

def program_set_default_options(prg):
    """ Set default program options values.
    """
    for flag in prg["flags"]:
        name = flag["name"]
        value = None if flag["require_value"] else False
        prg["opts"][name] = value

def program_set_subcommand(prg, args):
    """ Set program subcommand option.
    """
    cmdname, args = shift(args)
    if cmdname == None:
        raise MissingSubcommand()
    if cmdname not in prg["subcommands"]:
        raise UnknownSubcommand(cmdname)
    prg["opts"]["subcommand"] = cmdname
    return args

def program_parse_flags(prg, args):
    """ Parses remaining arguments as flags.
    """
    while len(args) > 0:
        found = None
        flag, args = shift(args)

        for itflag in prg["flags"]:
            if itflag["short"] == flag or itflag["long"] == flag:
                found = itflag

        if found == None:
            raise Exception(f"invalid flag: {flag}")

        name = found["name"]
        if found["require_value"]:
            if len(args) < 1:
                raise Exception(f"required value for flag: {flag}")
            prg["opts"][name], args = shift(args)
        else:
            prg["opts"][name] = True
    return args

def program_check_required_flags(prg):
    """ Check subcommand required flags.
    """
    opts = prg["opts"]
    flags = prg["flags"]
    subcmd = program_get_subcommand_information(prg)

    for flagname in subcmd["required_flags"]:
        if opts[flagname] == None:
            flag = program_find_flag(prg, flagname)
            raise MissingRequiredFlag(flag)

    for flags in subcmd["required_flags_or"]:
        has_some = False
        for flagname in flags:
            if opts[flagname] != None:
                has_some = True
                break
        if has_some == False:
            find_flag = lambda name: program_find_flag(prg, name)
            required_flags = list(map(find_flag, flags))
            raise MissingOneOfRequiredFlags(required_flags)

def program_parse_arguments(prg, args):
    """ Parse arguments into program and returns remaining arguments.
    """
    _, args = shift(args) # ignore program name.
    program_set_default_options(prg)
    args = program_set_subcommand(prg, args)
    args = program_parse_flags(prg, args)
    program_check_required_flags(prg)
    return args

def program_flags_lines(prg):
    """ Returns a list of lines containing usage-like flag options.
    """
    lines = ["FLAGS:"]
    for flag in prg["flags"]:
        indent = " " * 4
        long = flag["long"]
        short = flag["short"]
        space = " " * (20 - len(short) - len(long) - 2) # minus 2 because '/' between short and long flags.
        help = flag["help"]
        lines.append(f"{indent}{long}/{short}{space}{help}")
    return lines

def program_subcommand_lines(prg):
    """ Returns a list of lines containing usage-like subcommand options.
    """
    lines = ["SUBCOMMANDS:"]
    for subcmd in prg["subcommands"].values():
        indent = " " * 4
        name = subcmd["name"]
        help = subcmd["help"]
        space = " " * (20 - len(name) - 1)
        lines.append(f"{indent}{name}{space}{help}")
    return lines

def program_usage_string(prg):
    """ Returns the program usage message.
    """
    return "\n".join([
        "usage: mita [SUBCOMMAND] [FLAGS]",
        *program_subcommand_lines(prg),
        *program_flags_lines(prg),
    ])

def mita_program():
    """ Create mita default program.
    """
    prg = program("mita")
    # subcommands.
    program_add_subcommand(prg, "add", "Add a task",
                           required_flags=["desc"])
    program_add_subcommand(prg, "list", "Lists tasks")
    program_add_subcommand(prg, "remove", "Remove a task",
                           required_flags_or=[["id", "pattern", "status"]])
    program_add_subcommand(prg, "done", "Mark task(s) as done",
                           required_flags_or=[["id", "pattern", "status"]])
    program_add_subcommand(prg, "todo", "Mark task(s) as todo",
                           required_flags_or=[["id", "pattern", "status"]])
    program_add_subcommand(prg, "file", "Print current tasks file")
    program_add_subcommand(prg, "local", "Create local tasks file")
    # flags.
    program_add_flag(prg, "id", "-i", True,
                     "Select task by ID")
    program_add_flag(prg, "desc", "-d", True,
                     "Define task description")
    program_add_flag(prg, "status", "-s", True,
                     "Filter by task status: done|todo")
    program_add_flag(prg, "pattern", "-p", True,
                     "Search pattern for tasks")
    program_add_flag(prg, "multiple", "-m", False,
                     "Allow operate on multiple tasks")
    program_add_flag(prg, "no-color", "-n", False,
                     "Disable terminal colors output")
    program_add_flag(prg, "verbose", "-v", False,
                     "Print extra tasks information")
    program_add_flag(prg, "debug", "-b", False,
                     "Debug prints and python errors")
    return prg

def mita_diretory():
    """ Returns mita directory path.
    """
    path = os.getcwd()
    if os.path.exists(os.path.join(path, "tasks.json")):
        return path

    user = os.path.expanduser("~")
    return os.path.join(user, ".mita")

def mita_create_directory():
    """ Create mita directory if not exists.
    """
    try:
        os.mkdir(mita_diretory())
        return True
    except:
        return False

def mita_tasks_file():
    """ Returns the tasks file path.
    """
    mitadir = mita_diretory()
    return os.path.join(mitadir, "tasks.json")

def mita_create_tasks_file():
    """ Create mita tasks file if not exists.
    """
    mitafpath = mita_tasks_file()
    if not os.path.exists(mitafpath):
        with open(mitafpath, "w") as file: 
            file.write("{}")
            return True
    return False

def mita_task(desc, id=0):
    """ Returns the task id and the task value.
    """
    if id == 0:
        id = int(time.time())
    return id, {
        "id": id,
        "desc": desc or "",
        "status": TODO,
    }

def mita_filter(tasks, opts):
    """ Filter tasks based on options.

        It takes all tasks, tries to filter them by pattern, it tries to
        filter them by status, and then return filtered tasks.

        Star '*' is accept as a pattern but leaving it empty has the same effect,
        I did not thought of it before...
    """
    if opts["id"]:
        id = opts["id"]
        if id in tasks:
            task = tasks[id]
            yield (id, task, )
        return

    tasks = tasks.items()

    match opts["pattern"]:
        case "*":
            pass
        case None:
            pass
        case pattern:
            def filter_by_pattern(id_task):
                _, task = id_task
                u_pattern = pattern.upper()
                u_desc = task["desc"].upper()
                return u_pattern in u_desc
            tasks = filter(filter_by_pattern, tasks)

    match opts["status"]:
        case "todo":
            def filter_by_todo(id_task):
                _, task = id_task
                return task["status"] == TODO
            tasks = filter(filter_by_todo, tasks)
        case "done":
            def filter_by_done(id_task):
                _, task = id_task
                return task["status"] == DONE
            tasks = filter(filter_by_done, tasks)
        case None:
            pass

    for id, task in tasks:
        yield (id, task, )
    return

def mita_add(tasks, opts):
    """ Add a task to tasks.
    """
    id, task = mita_task(opts["desc"])
    tasks[id] = task 
    loginfo("task added successfully")

def mita_remove(tasks, opts):
    """ Remove a task from tasks.
    """
    filtered_tasks = list(mita_filter(tasks, opts))
    match filtered_tasks:
        case []:
            raise MultipleTasksFound()
        case [(id, _)]:
            printx("Removed tasks:")
            mita_print(tasks[id], id, opts)
            del tasks[id]
        case _:
            if opts["multiple"] == False:
                raise MultipleTasksFound()
            printx("Removed tasks:")
            for id, _ in filtered_tasks:
                mita_print(tasks[id], id, opts)
                del tasks[id]

def mita_list(tasks, opts):
    """ List tasks in tasks.

        It uses {mita_filter} so you can easily filter things by using the
        pattern or status flags.
    """
    todo_task_count = 0
    done_task_count = 0

    total_tasks = len(tasks.keys())
    filtered_tasks = list(mita_filter(tasks, opts))

    for _, task in filtered_tasks:
        if task["status"] == TODO:
            todo_task_count += 1
        elif task["status"] == DONE:
            done_task_count += 1
        else:
            raise Exception("unreachable")

    printx(f"Listing {len(filtered_tasks)} of {total_tasks} tasks", end="")
    printx(f", {done_task_count} ", end="")

    color = None if opts["no-color"] else "green"
    printx("done", color=color, end="")

    printx(f", {todo_task_count} ", end="")

    color = None if opts["no-color"] else "yellow"
    printx("todo", color=color)

    for id, task in filtered_tasks:
        mita_print(task, id if opts["verbose"] else None, opts)

def mita_set_status(tasks, opts, status):
    """ Set status of filtered tasks.
    """
    filtered_tasks = list(mita_filter(tasks, opts))

    def set_status(id, task):
        task["status"] = status
        printx("Task ", end="")
        color = None if opts["no-color"] else "blue"
        printx(f"#{id}", color="blue", end="")
        printx(f" set to {status}")

    match filtered_tasks:
        case []:
            raise Exception("task not found")
        case [(id, task)]:
            set_status(id, task)
        case _:
            if opts["multiple"] == False:
                raise MultipleTasksFound()
            for id, task in filtered_tasks:
                set_status(id, task)

def mita_done(tasks, opts):
    """ Set filtered tasks as done.
    """
    return mita_set_status(tasks, opts, DONE)

def mita_todo(tasks, opts):
    """ Set filtered tasks as todo.
    """
    return mita_set_status(tasks, opts, TODO)

def mita_print(task, id=None, opts={}):
    """ Print a inline formatted task.

        Comments and task ID are omitted if {opts["verbose"]} is False.
    """
    if id is not None:
        color = None if opts["no-color"] else "blue"
        printx(f"#{id}:", color=color, end="")

    if task["status"] == DONE:
        color = None if opts["no-color"] else "green"
        printx("done: ", color=color, end="")
    elif task["status"] == TODO:
        color = None if opts["no-color"] else "yellow"
        printx("todo: ", color=color, end="")
    else:
        raise Exception("unreachable")

    desc, *rest = task["desc"].split("//") # remove comments

    if opts["verbose"]:
        printx(desc, end="")
        color = None if opts["no-color"] else "blue"
        printx("//", color=color, end="")
        for whatever in rest:
            color = None if opts["no-color"] else "blue"
            printx(whatever, color=color, end="")
        printx()
        return

    printx(desc.strip()) # simply prints description

def mita_load_tasks(filepath):
    """ Load the default mita task file.
    """
    try:
        with open(filepath, "r") as file:
            return json.load(file)
    except:
        return {}

def mita_save_tasks(tasks, filepath):
    """ Save tasks into the default mita task file.
    """
    with open(filepath, "w") as file:
        json.dump(tasks, file, indent=2)

def mita_process(prg, tasks):
    """ Main mita process.
    """
    opts = prg["opts"]
    match opts["subcommand"]:
        case "add":
            mita_add(tasks, opts)
        case "list":
            mita_list(tasks, opts)
        case "done":
            mita_done(tasks, opts)
        case "todo":
            mita_todo(tasks, opts)
        case "remove":
            mita_remove(tasks, opts)
        case "file":
            printx(mita_tasks_file())
        case "local":
            path = os.getcwd()
            filepath = os.path.join(path, "tasks.json")

            if not os.path.exists(filepath):
                with open(filepath, "w") as file:
                    json.dump({}, file, indent=2)

            printx(filepath)
        case _:
            raise Exception("unreachable") # subcommand is checked at mita_opts

def main(args):
    prg = mita_program()
    try:
        _ = program_parse_arguments(prg, args)

        if prg["opts"]["debug"] == True:
            global catch_exception
            catch_exception = False
            printx("DEBUG:", color="cyan")
            printx(json.dumps(opts, indent=4))

        created = mita_create_directory()
        if created:
            loginfo(f"mita directory created at {mita_diretory()}")

        created = mita_create_tasks_file()
        if created:
            loginfo(f"mita tasks file created at {mita_tasks_file()}")

        file = mita_tasks_file()
        tasks = mita_load_tasks(file)

        mita_process(prg, tasks)
        mita_save_tasks(tasks, file)
    except Exception as e:
        if not catch_exception:
            raise e

        logerror(e)
        printx(program_usage_string(prg))

if __name__ == "__main__":
    exit(main(sys.argv))
