""" Mita - A simple Task manager.
"""
import os
import sys
import time
import json

TODO = "todo"
DONE = "done"

# Defines whether printx() should print colored output or not.
no_color = False

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

    color = None
    if no_color == False:
        color = kwargs.get("color")
        if color:
            assert color in colors, f"invalid color: {color}"

    if "color" in kwargs:
        del kwargs["color"] # make sure we don't pass it to builtin print.

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

class Flag:
    def __init__(self, name, short="", help="", require_value=False):
        """ Initializes Flag.
        """
        self.name = name
        self.help = help
        self.long = "--" + name
        self.short = short
        self.require_value = require_value

    def build_help_line(self):
        """ Builds a help line for this command.
            Format:
            [    ][flag][/][short][                        ][help]
        """
        b = " " * 4
        b += self.long
        b += "/"
        b += self.short
        b += " " * (24 - len(b))
        b += self.help
        return b

class SubCommand:
    def __init__(self, name, help="", required_flags=[], require_one_of=[]):
        """ Initializes SubCommand.
        """
        self.name = name
        self.help = help
        self.aliases = []
        self.required_flags = required_flags
        self.require_one_of = require_one_of

    def build_help_line(self):
        """ Builds a help line for this flag.
            Format:
            [    ][cmd][ ][(alias?)][                        ][help]
        """
        b = " " * 4
        b += self.name
        if len(self.aliases) > 0:
            b += f" ({", ".join(self.aliases)})"
        b += " " * (24 - len(b))
        b += self.help
        return b

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
    flag = Flag(*args, **kwargs)
    prg["flags"].append(flag)

def program_find_flag(prg, flag_name):
    """ Returns the flag information from a flag name.
    """
    for flag in prg["flags"]:
        if flag.name == flag_name:
            return flag
    return None

def program_add_subcommand(prg, *args, **kwargs):
    """ Add a program subcommand.
    """
    cmd = SubCommand(*args, **kwargs)
    prg["subcommands"][cmd.name] = cmd

def program_add_alias(prg, cmdname, alias):
    """ Add a sub-command alias.

        Returns None in case of success and error string in case of error.
    """
    cmd = prg["subcommands"].get(cmdname)
    if cmd == None:
        return f"unknown subcommand: {cmdname}"
    cmd.aliases.append(alias)
    return None

def program_get_subcommand_information(prg):
    """ Returns the subcommand information from the subcommand option.
    """
    return prg["subcommands"][prg["opts"]["subcommand"]]

def program_set_default_options(prg):
    """ Set default program options values.
    """
    for flag in prg["flags"]:
        name = flag.name
        value = None if flag.require_value else False
        prg["opts"][name] = value

def program_set_subcommand(prg, args):
    """ Set program subcommand option.

        Returns remaining arguments and None in case of success, or None and
        error string in case of error.
    """
    cmdname, args = shift(args)
    if cmdname == None:
        return None, "missing subcommand"
    for cmd in prg["subcommands"].values():
        if cmdname in cmd.aliases:
            cmdname = cmd.name
            break
    cmd = prg["subcommands"].get(cmdname)
    if cmd == None:
        return None, f"unknown subcommand: {cmdname}"
    prg["opts"]["subcommand"] = cmdname
    return args, None

def program_parse_flags(prg, args):
    """ Parses remaining arguments as flags.

        Returns remaining arguments and None in case of success, or None and
        error string in case of error.
    """
    while len(args) > 0:
        found = None
        flag, args = shift(args)

        for itflag in prg["flags"]:
            if itflag.short == flag or itflag.long == flag:
                found = itflag

        if found == None:
            return None, f"invalid flag: {flag}"

        name = found.name
        if found.require_value:
            if len(args) < 1:
                return None, f"required value for flag: {flag}"
            prg["opts"][name], args = shift(args)
        else:
            prg["opts"][name] = True
    return args, None

def error_require_one_of_flags(prg, subcmd):
    """ Build error message for missing one of the required flags.
    """
    out = "missing one of the following flags: "
    required_flags = subcmd.require_one_of
    for i in range(len(required_flags)):
        flag_name = required_flags[i]
        flag = program_find_flag(prg, flag_name)
        out += flag.long
        out += "/"
        out += flag.short
        if i < len(required_flags) - 2:
            out += ", "
        elif i < len(required_flags) - 1:
            out += " or "
    return out

def program_check_required_flags(prg):
    """ Check subcommand required flags.
    """
    opts = prg["opts"]
    flags = prg["flags"]
    subcmd = program_get_subcommand_information(prg)

    for flagname in subcmd.required_flags:
        if opts[flagname] == None:
            flag = program_find_flag(prg, flagname)
            return False, f"missing required flag: {flag}"

    require_one_of = subcmd.require_one_of
    if len(require_one_of) > 0:
        has_one = False
        for flag_name in require_one_of:
            if prg["opts"][flag_name] != None:
                has_one = True
                break
        if has_one == False:
            return False, error_require_one_of_flags(prg, subcmd)

    return True, None

def program_parse_arguments(prg, args):
    """ Parse arguments into program and returns remaining arguments.
    """
    _, args = shift(args) # ignore program name.
    program_set_default_options(prg)
    args, err = program_set_subcommand(prg, args)
    if err != None:
        return None, err
    args, err = program_parse_flags(prg, args)
    if err != None:
        return None, err
    ok, err = program_check_required_flags(prg)
    if not ok:
        return None, err
    return args, None

def program_usage_string(prg):
    """ Returns the program usage message.
    """
    b = "usage: mita [SUBCOMMAND] [FLAGS...]\n"
    b += "\n"
    b += "SUBCOMMANDS:\n"
    for subcmd in prg["subcommands"].values():
        b += subcmd.build_help_line()
        b += "\n"
    b += "\n"
    b += "FLAGS:\n"
    for flag in prg["flags"]:
        b += flag.build_help_line()
        b += "\n"
    return b

def mita_program():
    """ Create mita default program.
    """
    prg = program("mita")
    # subcommands.
    program_add_subcommand(prg, "add", "Add a task",
                           required_flags=["desc"])
    program_add_subcommand(prg, "list", "Lists tasks")
    program_add_subcommand(prg, "remove", "Remove a task",
                           require_one_of=["id", "pattern", "status"])
    program_add_subcommand(prg, "done", "Mark task(s) as done",
                           require_one_of=["id", "pattern", "status"])
    program_add_subcommand(prg, "todo", "Mark task(s) as todo",
                           require_one_of=["id", "pattern", "status"])
    program_add_subcommand(prg, "file", "Print current tasks file")
    program_add_subcommand(prg, "local", "Create local tasks file")
    # flags.
    program_add_flag(prg, "id", "-i",
                     require_value=True,
                     help="Select task by ID")
    program_add_flag(prg, "desc", "-d",
                     require_value=True,
                     help="Define task description")
    program_add_flag(prg, "status", "-s",
                     require_value=True,
                     help="Filter by task status: done|todo")
    program_add_flag(prg, "pattern", "-p",
                     require_value=True,
                     help="Search pattern for tasks")
    program_add_flag(prg, "multiple", "-m",
                     require_value=False,
                     help="Allow operate on multiple tasks")
    program_add_flag(prg, "no-color", "-n",
                     require_value=False,
                     help="Disable terminal colors output")
    program_add_flag(prg, "verbose", "-v",
                     require_value=False,
                     help="Print extra tasks information")
    # aliases.
    err = program_add_alias(prg, "list", "ls")
    assert err == None
    err = program_add_alias(prg, "remove", "rm")
    assert err == None
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

        Returns None in case of success and a error message in case of error.
    """
    filtered_tasks = list(mita_filter(tasks, opts))
    match filtered_tasks:
        case []:
            return "multiple tasks found (hint: use -m flag)"
        case [(id, _)]:
            printx("Removed tasks:")
            mita_print(tasks[id], id, opts)
            del tasks[id]
        case _:
            if opts["multiple"] == False:
                return "multiple tasks found (hint: use -m flag)"
            printx("Removed tasks:")
            for id, _ in filtered_tasks:
                mita_print(tasks[id], id, opts)
                del tasks[id]
    return None

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
            assert False, "invalid task status"

    printx(f"Listing {len(filtered_tasks)} of {total_tasks} tasks", end="")

    printx(f", {done_task_count} ", end="")
    printx("done", color="green", end="")

    printx(f", {todo_task_count} ", end="")
    printx("todo", color="yellow")

    for id, task in filtered_tasks:
        mita_print(task, id if opts["verbose"] else None, opts)

def mita_set_status(tasks, opts, status):
    """ Set status of filtered tasks.

        Returns None in case of success and error string in case of error.
    """
    filtered_tasks = list(mita_filter(tasks, opts))

    def set_status(id, task):
        task["status"] = status
        printx("Task ", end="")
        printx(f"#{id}", color="blue", end="")
        printx(f" set to {status}")

    match filtered_tasks:
        case []:
            return "no task found"
        case [(id, task)]:
            set_status(id, task)
        case _:
            if opts["multiple"] == False:
                return "multiple task found (hint: use -m flag)"
            for id, task in filtered_tasks:
                set_status(id, task)
    return None

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
        printx(f"#{id}:", color="blue", end="")

    if task["status"] == DONE:
        printx("done: ", color="green", end="")
    elif task["status"] == TODO:
        printx("todo: ", color="yellow", end="")
    else:
        assert False, "invalid task status"

    desc, *rest = task["desc"].split("//") # remove comments

    if opts["verbose"]:
        printx(desc, end="")
        printx("//", color="blue", end="")
        for whatever in rest:
            printx(whatever, color="blue", end="")
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
            return None
        case "list":
            mita_list(tasks, opts)
            return None
        case "done":
            err = mita_done(tasks, opts)
            return err
        case "todo":
            err = mita_todo(tasks, opts)
            return err
        case "remove":
            err = mita_remove(tasks, opts)
            return err
        case "file":
            printx(mita_tasks_file())
            return None
        case "local":
            path = os.getcwd()
            filepath = os.path.join(path, "tasks.json")

            if not os.path.exists(filepath):
                with open(filepath, "w") as file:
                    json.dump({}, file, indent=2)

            printx(filepath)
            return None
        case _:
            return "unknown sub-command"

def main(args):
    prg = mita_program()
    try:
        _, err = program_parse_arguments(prg, args)
        if err != None:
            raise Exception(err)

        if prg["opts"]["no-color"] == True:
            global no_color
            no_color = True

        created = mita_create_directory()
        if created:
            loginfo(f"mita directory created at {mita_diretory()}")

        created = mita_create_tasks_file()
        if created:
            loginfo(f"mita tasks file created at {mita_tasks_file()}")

        file = mita_tasks_file()
        tasks = mita_load_tasks(file)

        err = mita_process(prg, tasks)
        if err != None:
            raise Exception(err)

        mita_save_tasks(tasks, file)
    except Exception as e:
        mita_debug = os.getenv("MITA_DEBUG")
        if mita_debug == "1":
            raise e

        logerror(e)
        printx(program_usage_string(prg))

if __name__ == "__main__":
    exit(main(sys.argv))
