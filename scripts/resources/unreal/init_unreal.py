import os
import sys
import unreal
from pathlib import Path

REPO_ROOT = os.environ.get('CONTAINER_REPO_FOLDER')
if REPO_ROOT:
    REPO_ROOT = Path(REPO_ROOT)
else:
    REPO_ROOT = Path(__file__).parent.parent.parent.parent

debug = os.environ.get('UNREAL_DEBUGGING_ON', 'no').lower() == 'yes'

if debug:
    try:
        import debugpy
        python_exe_path = Path(sys.executable).parent.parent / 'ThirdParty' / 'Python3' / 'Linux' / 'bin' / 'python3'
        if sys.platform == 'win32':
            python_exe_path = Path(sys.executable).parent.parent / 'ThirdParty' / 'Python3' / 'Win64' / 'python'

        port = int(os.environ.get('UNREAL_DEBUG_PORT', 5679))
        debugpy.configure(python=os.environ.get('UNREAL_PYTHON_EXE', str(python_exe_path)))
        if os.environ.get('TEST_ENVIRONMENT'):
            debugpy.listen(('0.0.0.0', port))
        else:
            debugpy.listen(port)

        unreal.log(f'Waiting for debugger to attach on port {port}...') # type: ignore
        debugpy.wait_for_client()
    except ImportError:
        unreal.log_error( # type: ignore
            'Failed to initialize debugger because debugpy is not available '
            'in the current python environment.'
        )

sys.path.append(str(REPO_ROOT / 'src' / 'addons'/ 'send2ue' / 'dependencies'))
if os.environ.get('TEST_ENVIRONMENT'):
    from rpc.server import RPCServer
    rpc_server = RPCServer()
    rpc_server.start_server_blocking()
else:
    from rpc import unreal_server
    rpc_server = unreal_server.RPCServer()
    rpc_server.start(threaded=True)

print('Unreal Engine RPC Server started')
