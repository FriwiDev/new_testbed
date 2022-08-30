import subprocess


def setup():
    download_img('https://friwi.me/testbed_img/ovs-ubuntu-18.04-minimal.tar.gz', 'ovs')
    download_img('https://friwi.me/testbed_img/ryu-ubuntu-18.04-minimal.tar.gz', 'ryu')
    download_img('https://friwi.me/testbed_img/simple-host-ubuntu-18.04-minimal.tar.gz', 'simple-host')
    pass


def download_img(url: str, alias: str):
    print(f"::Checking if image {alias} exists locally")
    code, output = run_command(['lxc', 'image', 'ls', '-f', 'csv', '-c' 'l'], True, False)
    if code <= 0 and alias in output:
        print(f"::Image {alias} exists=>skipping")
        return

    if code > 0:
        print("::Failed to run LXC image ls command=>aborting")
        exit(code)

    print(f"::Retrieving image {alias} from {url}")
    run_command(['rm', '-f', f'{alias}.tar.gz'])
    run_command(['wget', '-O', f'{alias}.tar.gz', url, '-q', '--show-progress',
                 '--progress=bar:force'])

    print(f"::Installing image {alias}")
    code, ret = run_command(['lxc', 'image', 'import', f'{alias}.tar.gz', '--alias', alias,
                             '--public'])

    run_command(['rm', '-f', f'{alias}.tar.gz'])
    if code > 0:
        print("::Failed to run LXC image import command=>aborting")
        exit(code)


def run_command(cmd: list[str], list_output: bool = False, do_output: bool = True) -> (int, list[str]):
    ret = []
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               universal_newlines=True)

    while True:
        output = process.stdout.readline()
        if not output.strip() == "":
            if do_output:
                print(output.strip())
            if list_output:
                ret.append(output.strip())
        # Do something else
        return_code = process.poll()
        if return_code is not None:
            # Process has finished, read rest of the output
            for output in process.stdout.readlines():
                if not output.strip() == "":
                    if do_output:
                        print(output.strip())
                    if list_output:
                        ret.append(output.strip())
            return return_code, ret


if __name__ == "__main__":
    setup()
