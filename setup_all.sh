#!/bin/bash
set -e

#cd to script dir
cd "$( dirname "$0" )"

#Make scripts executable
chmod +x ./*.sh
chmod +x testbed/*.sh

#Enable ipv4 forwarding
sysctl -w net.ipv4.ip_forward=1

echo "Checking for dependencies"

echo "::Checking for bridge-utils"
if ! command -v brctl &> /dev/null
then
    echo "::bridge-utils=>not found=>prompting installation"
    if command -v pacman &> /dev/null
    then
        pacman -Sy bridge-utils
    else
        apt-get install bridge-utils
    fi
else
    echo "::bridge-utils=>found"
fi

echo "::Checking for LXC/LXD"
if ! command -v lxc &> /dev/null
then
    echo "::LCX/LXD=>not found=>prompting installation"
    if command -v pacman &> /dev/null
    then
        pacman -Sy lxd
    else
        apt-get install lxd
    fi
    # Add to lxd group
    usermod -a -G lxd "$USER"
    # Add uids & gids for current user
    touch /etc/subuid
    touch /etc/subgid
    usermod --add-subuids 100000-1001000000 "$USER"
    usermod --add-subgids 100000-1001000000 "$USER"
    # Initialize lxd
    lxd init --preseed < lxd_preseed.yml
else
    echo "::LXC/LXD=>found"
fi

if ! systemctl is-enabled --quiet lxd; then
    echo "::LXD not running=>enabling & starting service"
    systemctl enable lxd --now
fi

echo "Checking permissions for lxc"
if ! lxc info &> /dev/null; then
  echo "Could not connect to lxc daemon. Is it running and do you have permissions? Check with \"systemctl status lxd\" and \"lxc info\""
  exit 1
fi
echo "::Permissions ok"

echo "::Checking for Python3"
if ! command -v python3 &> /dev/null
then
    echo "::Python3=>not found=>prompting installation"
    if command -v pacman &> /dev/null
    then
        pacman -Sy python3 tk
    else
        apt-get install python3 python3-tk
    fi
else
    echo "::Python3=>found"
fi

echo "All components located or installed"

echo "Installing package"

echo "::Fetching images"
python3 get_images.py

echo "::Installing testbed python package"
python3 setup.py install --record installed_files.txt | sed 's/^/>>>/'

echo "Installation completed"
