#!/usr/bin/python -tt

import os, sys, subprocess, tempfile

merlin_dir = "/opt/monitor/op5/merlin"
libexec_dir = "/usr/libexec/merlin"
pushed_logs = "/opt/monitor/pushed_logs"
archive_dir = "/opt/monitor/var/archives"

if not libexec_dir in sys.path:
	sys.path.append(libexec_dir)
import node

# run a generic helper from the libexec dir
def run_helper(helper, args):
	app = libexec_dir + "/" + helpers[helper]
	ret = os.spawnv(os.P_WAIT, app, [app] + args)
	if ret < 0:
		print("Helper %s was killed by signal %d" % (app, ret))

## log commands ##
# force running push_logs on poller and peer systems
def cmd_log_fetch(args):
	since = ''
	for arg in args:
		if arg.startswith('--incremental='):
			since = '--since=' + arg[14:]

	for node in configured_nodes.values():
		if node.ntype == 'master':
			continue
		ctrl = "mon log push"
		if since:
			ctrl += ' ' + since
		if not node.ctrl(ctrl):
			print("Failed to force %s to push its logs. Exiting" % node.name)
			sys.exit(1)

def cmd_log_sortmerge(args):
	since = False
	for arg in args:
		if (arg.startswith('--since=')):
			since = arg.split('=', 1)[1]

	if since:
		since = '--incremental=' + since

	pushed = {}
	for (name, node) in configured_nodes.items():
		if node.ntype == 'master':
			continue
		if not os.access(pushed_logs + '/' + node.name, os.X_OK):
			print("Failed to access() pushed_logs dir for %s" % node.name)
			return False

		pushed[name] = os.listdir(pushed_logs + '/' + node.name)
		if len(pushed[name]) == 0:
			print("%s hasn't pushed any logs yet" % name)
			return False

		if 'in-transit.log' in pushed[name]:
			print("Log files still in transit for node '%s'" % node.name)
			return False

	if len(pushed) != node.num_nodes['peer'] + node.num_nodes['poller']:
		print("Some nodes haven't pushed their logs. Aborting")
		return False

	last_files = False
	for (name, files) in pushed.items():
		if last_files and not last_files == files:
			print("Some nodes appear to not have pushed the files they should have done")
			return False
		last_files = files

	app = merlin_dir + "/import"
	cmd_args = [app, '--list-files', args, archive_dir]
	stuff = subprocess.Popen(cmd_args, stdout=subprocess.PIPE)
	output = stuff.communicate()[0]
	sort_args = ['sort']
	sort_args += output.strip().split('\n')
	for (name, more_files) in pushed.items():
		for fname in more_files:
			sort_args.append(pushed_logs + '/' + name + '/' + fname)

	print("sort-merging %d files. This could take a while" % (len(sort_args) - 1))
	(fileno, tmpname) = tempfile.mkstemp()
	subprocess.check_call(sort_args, stdout=fileno)
	print("Logs sorted into temporary file %s" % tmpname)
	return tmpname


# run the import program
def cmd_log_import(args):
	since = ''
	fetch = False
	i = 0
	for arg in args:
		if arg.startswith('--incremental='):
			since = arg[14:]
		elif arg == '--truncate-db':
			since = '1'
		elif arg == '--fetch':
			fetch = True
			args.pop(i)
		i += 1

	if not '--list-files' in args:
		if node.num_nodes['poller'] or node.num_nodes['peer']:
			if fetch == True:
				cmd_log_fetch(since)
			tmpname = cmd_log_sortmerge(['--since=' + since])
			print("importing from %s" % tmpname)
			import_args = [merlin_dir + '/import', tmpname] + args
			subprocess.check_call(import_args, stdout=sys.stdout.fileno())
			return True

	app = merlin_dir + "/import"
	ret = os.spawnv(os.P_WAIT, app, [app] + args)
	if ret < 0:
		print("The import program was killed by signal %d" % ret)
	return ret


# run the showlog program
def cmd_log_show(args):
	app = merlin_dir + "/showlog"
	ret = os.spawnv(os.P_WAIT, app, [app] + args)
	if ret < 0:
		print("The showlog helper was killed by signal %d" % ret)
	return ret

def cmd_start(args):
	print("This should start the op5 Monitor system")

def cmd_stop(args):
	print("This should stop the op5 Monitor system")

# the list of commands
commands = { 'log.fetch': cmd_log_fetch, 'log.sortmerge': cmd_log_sortmerge,
	'log.import': cmd_log_import, 'log.show': cmd_log_show}
categories = {}
help_helpers = []
helpers = {}
init_funcs = {}

def load_command_module(path):
	global commands, init_funcs
	ret = False

	if not libexec_dir in sys.path:
		sys.path.append(libexec_dir)

	modname = os.path.basename(path)[:-3]
	module = __import__(os.path.basename(path)[:-3])

	if getattr(module, "pure_script", False):
		return False
	# we grab the init function here, but delay running it
	# until we know which module we'll be using.
	init_func = getattr(module, "module_init", False)

	for f in dir(module):
		if not f.startswith('cmd_'):
			continue
		ret = True
		func = getattr(module, f)
		callname = modname + '.' + func.__name__[4:]
		commands[callname] = func
		init_funcs[callname] = init_func

	return ret

if os.access(libexec_dir, os.X_OK):
	raw_helpers = os.listdir(libexec_dir)
	for rh in raw_helpers:
		path = libexec_dir + '/' + rh

		# ignore entries starting with dot or dash
		if rh[0] == '.' or rh[0] == '-':
			continue

		# also ignore non-executables and directories
		if os.path.isdir(path) or not os.access(path, os.X_OK):
			continue

		# remove script suffixes
		ary = rh.split('.')
		if len(ary) > 1 and ary[-1] in ['sh', 'php', 'pl', 'py', 'pyc']:
			if ary[-1] == 'pyc':
				continue
			if len(ary) == 2 and ary[-1] == 'py':
				if load_command_module(libexec_dir + '/' + rh):
					continue

			helper = '.'.join(ary[:-1])
		else:
			helper = '.'.join(ary)

		cat_cmd = helper.split('.', 1)
		if len(cat_cmd) == 2:
			(cat, cmd) = cat_cmd
			helper = cat + '.' + cmd
			if not cat in categories:
				categories[cat] = []
			if cmd in categories[cat]:
				print("Can't override builtin category+command with helper %s" % helper)
				continue
			categories[cat].append(cmd)
		else:
			help_helpers.append(helper)

		if helper in commands:
			print("Can't override builtin command with helper '%s'" % helper)
			continue

		commands[helper] = run_helper
		helpers[helper] = rh

# we break things down to categories and subcommands
for raw_cmd in commands:
	if not '.' in raw_cmd:
		if not raw_cmd in help_helpers:
			help_helpers.append(raw_cmd)
		continue

	(cat, cmd) = raw_cmd.split('.')
	if not cat in categories:
		categories[cat] = []
	if not cmd in categories[cat]:
		categories[cat].append(cmd)

def show_usage():
	print('''usage: mon [category] <command> [options]

Where category is sometimes optional.\n''')
	topic = 'Available categorized commands:'
	print("%s\n%s" % (topic, '-' * len(topic)))
	cat_keys = categories.keys()
	cat_keys.sort()
	for cat in cat_keys:
		print("  %-7s: %s" % (cat, ', '.join(categories[cat])))
	if len(help_helpers):
		topic = "Commands without category:"
		print("\n%s\n%s\n   %s" % (topic, '-' * len(topic), ', '.join(help_helpers)))

	print('''\nOptions naturally depend on which command you choose.

Some commands accept a --help flag to print some helptext, and some
categories have a help-command associated with them.
''')
	sys.exit(1)

if len(sys.argv) < 2 or sys.argv[1] == '--help' or sys.argv[1] == 'help':
	show_usage()

args = []
autohelp = False
cmd = cat = sys.argv[1]
if cat in commands:
	args = sys.argv[2:]
elif len(sys.argv) > 2:
	if sys.argv[2] == '--help' or sys.argv[2] == 'help':
		cmd = cat + '.help'
		autohelp = True
	else:
		cmd = cat + '.' + sys.argv[2]
	args = sys.argv[3:]
else:
	# only one argument passed, and it's not a stand-alone command.
	# Take it to mean 'help' for that category
	cmd = cat + '.help'
	autohelp = True

if not cmd in commands:
	print("")
	if not cat in categories.keys():
		print("No category '%s' available, and it's not a raw command" % cat)
	elif autohelp == True:
		print("Category '%s' has no help overview." % cat)
		print("Available commands: %s" % ', '.join(categories[cat]))
	else:
		print("Bad category/command: %s" % cmd.replace('.', ' '))
	print("")
	sys.exit(1)

if commands[cmd] == run_helper:
	run_helper(cmd, args)
else:
	# now we run the command module's possibly costly
	# intialization routines
	init = init_funcs.get(cmd, False)
	if init != False:
		init(args)

	commands[cmd](args)
