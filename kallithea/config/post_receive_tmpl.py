import os
import sys

# set output mode on windows to binary for stderr
# this prevents python (or the windows console) from replacing \n with  \r\n
# git doesn't display remote output lines that contain \r
# and therefore without this modification git would displayes empty lines
# instead of the exception output
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

KALLITHEA_HOOK_VER = '_TMPL_'
os.environ['KALLITHEA_HOOK_VER'] = KALLITHEA_HOOK_VER
from kallithea.lib.hooks import handle_git_post_receive as _handler


def main():
    repo_path = os.path.abspath('.')
    push_data = sys.stdin.readlines()
    # os.environ is modified here by a subprocess call that
    # runs git and later git executes this hook.
    # Environ gets some additional info from kallithea system
    # like IP or username from basic-auth
    _handler(repo_path, push_data, os.environ)
    sys.exit(0)

if __name__ == '__main__':
    main()
