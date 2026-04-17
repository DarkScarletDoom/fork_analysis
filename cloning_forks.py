import subprocess

def cloning_forks(forks, limit=None):
    i = 0
    forks_to_process = forks[:limit] if limit is not None else forks
    for fork in forks_to_process:
        print('Fork ' + str(i) + ' in process:')
        clone_url = fork.clone_url
        fork_name = fork.owner.login
        res = subprocess.run(f"git clone {clone_url} forks/{fork_name}", shell=True)
        print(res)
        print()
        i += 1
