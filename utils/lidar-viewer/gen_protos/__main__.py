import os
import subprocess


def run_shell_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()

    if error:
        print(f"Error: {error}")


if __name__ == '__main__':
    # Check if the directory '../protos' exists
    if not os.path.exists('./protos'):
        # If the directory does not exist, create it
        os.makedirs('./protos')

    run_shell_command('python -m grpc_tools.protoc '
                      '-I../../protos '
                      '--python_out=./protos '
                      '--pyi_out=./protos '
                      '--grpc_python_out=./protos '
                      '../../protos/service.proto')

    run_shell_command('python -m grpc_tools.protoc '
                      '-I../../protos '
                      '--python_out=./protos '
                      '--pyi_out=./protos '
                      '--grpc_python_out=./protos '
                      '../../protos/gateway.proto')
