import subprocess, os

project_dir = r"c:\Users\me\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a6dd9404ecc48ebebd9c897"
git_exe = r"C:\Program Files\Git\cmd\git.exe"

def run_git(args):
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    r = subprocess.run([git_exe] + args, cwd=project_dir, capture_output=True, text=True, encoding='utf-8', env=env)
    if r.stdout: print(r.stdout)
    if r.stderr: print(r.stderr)
    return r.returncode

# config
run_git(["config", "user.email", "user@example.com"])
run_git(["config", "user.name", "user"])
# add
run_git(["add", "-A"])
# commit
run_git(["commit", "-m", "Initial commit: 奥拉星立绘提取器"])
