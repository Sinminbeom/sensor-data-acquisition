import os
import subprocess


def run_shell_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()

    if error:
        print(f"Error: {error}")


if __name__ == '__main__':
    if not os.path.exists('./src/protos'):
        os.makedirs('./src/protos')

    run_shell_command('python -m grpc_tools.protoc '
                      '-I../protos '
                      '--python_out=./src/protos '
                      '--pyi_out=./src/protos '
                      '--grpc_python_out=./src/protos '
                      '../protos/service.proto')
