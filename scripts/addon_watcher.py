import sys
import os

def reload_addon(addon, scripts_path):
    sys.path.append(scripts_path)
    import dev_helpers
    dev_helpers.reload_addon_source_code([addon])


if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'send2ue', 'dependencies'))
    from rpc.rpc_factory import RPCFactory, RPCClient # type: ignore
    changed_file_path = os.path.normpath(sys.argv[-1])
    print(f'Checking path "{changed_file_path}"...')
    split_path = changed_file_path.split(os.sep)
    print('test')
    if split_path:
        root_folder = split_path[0]
        if root_folder in ['send2ue', 'ue2rigify']:
            addon_name = root_folder
            print(f'reloading "{addon_name}"...')
            rpc_factory = RPCFactory(rpc_client=RPCClient(9997))
            rpc_factory.run_function_remotely(reload_addon, [addon_name, os.path.basename(__file__)])
        else:
            print('No addon to reload')
