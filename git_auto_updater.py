from subprocess import Popen, check_output
from threading import Timer
from os import path

def get_current_commit(soft_path: str, git_repo_url: str) -> str:
	output = check_output('git rev-parse HEAD'.split(), shell=True, cwd=soft_path).decode('utf-8')
	return output.strip()

def get_commit_from_git(git_repo_url: str, prod_branch: str) -> str:
	output = check_output(f'git ls-remote {git_repo_url}'.split(), shell=True).decode('utf-8')
	for l in output.split('\n'):
		commit, branch = l.split('\t')[:2]
		if branch == 'refs/heads/' + prod_branch:
			return commit
	raise Exception(f'could not find {prod_branch} branch in {git_repo_url}')

flatten = lambda l: [item for sublist in l for item in sublist]
def pull_last_version(soft_path: str, git_repo_url: str, prod_branch: str) -> None:
	commands = [f'git checkout {prod_branch}', 'git pull'] \
		if path.isdir(path.join(soft_path, '.git')) \
		else [f'git clone -b {prod_branch} {git_repo_url} {soft_path}']
	for cmd in commands:
		out = check_output(cmd.split(' '), shell=True, cwd=soft_path)

def try_update(soft_path: str, startup_command: str, git_repo_url: str, prod_branch: str) -> bool:
	cur_ver = get_current_commit(soft_path, git_repo_url)
	last_ver = get_commit_from_git(git_repo_url, prod_branch)
	res = cur_ver != last_ver
	if res:
		pull_last_version(soft_path, git_repo_url, prod_branch)
	return res

pipe: Popen = None
def process(soft_path: str, startup_command: str, git_repo_url: str, prod_branch: str, allow_shut_down: bool, interval: int, kwargs) -> None:
	global pipe
	Timer(args.mins * 60, process, kwargs=kwargs).start()
	updated = try_update(soft_path, startup_command, git_repo_url, prod_branch)
	if updated and allow_shut_down and pipe is not None:
		pipe.terminate()
		pipe = None
	if pipe is None:
		pipe = Popen(startup_command.split(), shell=True, cwd=soft_path)

if __name__ == '__main__':
	from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
	parser = ArgumentParser(description='Runs always relevant software from git', formatter_class=ArgumentDefaultsHelpFormatter)
	parser.add_argument('-p', '--path', help='full or relative path to running software', required=True)
	parser.add_argument('-c', '--cmd', help='command to start software', required=True)
	parser.add_argument('-g', '--git', help='url to git repository', required=True)
	parser.add_argument('-b', '--branch', default='master', help='branch from which software would be taken')
	parser.add_argument('-m', '--mins', default=60, type=int, help='interval in minutes to check for update')
	parser.add_argument('-dsd', '--disallowShutDown', action='store_true', help='disallow to shutdown software if new version found')
	args = parser.parse_args()
	kwargs = {
		'soft_path': args.path,
		'startup_command': args.cmd,
		'git_repo_url': args.git,
		'prod_branch': args.branch,
		'allow_shut_down': not args.disallowShutDown,
		'interval': args.mins,
	}
	kwargs['kwargs'] = kwargs # kwargs is kek:)
	process(**kwargs) # first call
	input('Process starting, press any key to shut down')
