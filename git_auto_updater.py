from subprocess import Popen, check_output
from os import path
from shlex import split as shell_split
from time import sleep

class RunningContext:
	git_repo_url: str
	soft_path: str
	startup_command: str
	prod_branch: str
	allow_shut_down: bool
	interval_sec: int

	pipe: Popen = None

running_context = RunningContext()


def exec_commands(*args: str) -> str or list[str]:
	results: list[str] = []
	for command in args:
		results.append(check_output(shell_split(command), cwd=running_context.soft_path).decode('utf-8'))
	return results if len(results) > 1 else results[0]


def get_current_commit() -> str:
	return exec_commands('git rev-parse HEAD').strip()


def get_commit_from_git(branch_from: str) -> str:
	output = exec_commands(f'git ls-remote {running_context.git_repo_url}')
	for l in output.split('\n'):
		commit, branch = l.split('\t')[:2]
		if branch == 'refs/heads/' + branch_from:
			return commit
	raise Exception(f'could not find {branch_from} branch in {running_context.git_repo_url}')


flatten = lambda l: [item for sublist in l for item in sublist]
def pull_last_version(branch_from: str) -> None:
	if not path.isdir(path.join(running_context.soft_path, '.git')):
		exec_commands(f'git clone -b {branch_from} {running_context.git_repo_url} {running_context.soft_path}')
		return

	changes_exists = len(exec_commands('git diff-index HEAD').strip()) > 1
	if changes_exists:
		exec_commands(f'git stash')

	curr_branch = exec_commands(f'git branch --show-current').strip()
	if curr_branch != branch_from:
		exec_commands(f'git checkout {branch_from}')

	exec_commands('git pull')


def try_update(branch_from: str) -> bool:
	cur_ver = get_current_commit()
	last_ver = get_commit_from_git(branch_from)
	res = cur_ver != last_ver
	if res:
		pull_last_version(branch_from)
	return res


def terminate_and_wait():
	if running_context.pipe is not None:
		running_context.pipe.terminate()
		running_context.pipe.wait(30)


def process():
	while True:
		updated = try_update(running_context.prod_branch)
		if updated and running_context.allow_shut_down:
			terminate_and_wait()
			running_context.pipe = None
		if running_context.pipe is None:
			running_context.pipe = Popen(shell_split(running_context.startup_command), cwd=running_context.soft_path)
		sleep(running_context.interval_sec)


def main():
	from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
	parser = ArgumentParser(description='Runs always relevant software from git',
							formatter_class=ArgumentDefaultsHelpFormatter)
	parser.add_argument('-p', '--path', help='full or relative path to running software', required=True)
	parser.add_argument('-c', '--cmd', help='command to start software', required=True)
	parser.add_argument('-g', '--git', help='url to git repository', required=True)
	parser.add_argument('-b', '--branch', default='master', help='branch from which software would be taken')
	parser.add_argument('-m', '--mins', default=60, type=int, help='interval in minutes to check for update')
	parser.add_argument('-dsd', '--disallow-shut-down', action='store_true',
						help='disallow to shutdown software if new version found')
	args = parser.parse_args()

	running_context.soft_path = args.path
	running_context.startup_command = args.cmd
	running_context.git_repo_url = args.git
	running_context.prod_branch = args.branch
	running_context.interval_sec = 60 * args.mins
	running_context.allow_shut_down = not args.disallow_shut_down

	try:
		process()
	except KeyboardInterrupt:
		terminate_and_wait()
	except:
		terminate_and_wait()
		raise


if __name__ == '__main__':
	main()
