from src.topo.util import CommandUtil


def setup():
    download_img('https://friwi.me/testbed_img/ovs-ubuntu-18.04-minimal.tar.gz', 'ovs')
    download_img('https://friwi.me/testbed_img/ryu-ubuntu-18.04-minimal.tar.gz', 'ryu')
    download_img('https://friwi.me/testbed_img/simple-host-ubuntu-18.04-minimal.tar.gz', 'simple-host')
    pass


def download_img(url: str, alias: str):
    print(f"::Checking if image {alias} exists locally")
    code, output = CommandUtil.run_command(['lxc', 'image', 'ls', '-f', 'csv', '-c' 'l'], True, False)
    if code <= 0 and alias in output:
        print(f"::Image {alias} exists=>skipping")
        return

    if code > 0:
        print("::Failed to run LXC image ls command=>aborting")
        exit(code)

    print(f"::Retrieving image {alias} from {url}")
    CommandUtil.run_command(['rm', '-f', f'{alias}.tar.gz'])
    CommandUtil.run_command(['wget', '-O', f'{alias}.tar.gz', url, '-q', '--show-progress',
                             '--progress=bar:force'])

    print(f"::Installing image {alias}")
    code, ret = CommandUtil.run_command(['lxc', 'image', 'import', f'{alias}.tar.gz', '--alias', alias,
                                         '--public'])

    CommandUtil.run_command(['rm', '-f', f'{alias}.tar.gz'])
    if code > 0:
        print("::Failed to run LXC image import command=>aborting")
        exit(code)


if __name__ == "__main__":
    setup()
