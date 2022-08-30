#!/bin/bash

echo "Checking for dependencies"
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

echo "::Checking for ZFS"
if ! command -v zfs &> /dev/null
then
    echo "::ZFS=>not found=>prompting installation"
    if command -v pacman &> /dev/null
    then
        pacman -Sy zfs-utils
    else
        apt-get install zfs-utils-linux
    fi
else
    echo "::ZFS=>found"
fi

echo "::Checking for ZFS kernel module"
if lsmod | grep "zfs" &> /dev/null ; then
  echo "::ZFS kernel module is already loaded!"
else
  echo "::ZFS kernel module is not loaded=>loading"
  modprobe zfs
fi

if ! systemctl is-enabled --quiet zfs.target; then
    echo "::ZFS not running=>enabling & starting service"
    systemctl enable zfs.target --now
fi

echo "::Checking for ZFS pool"
POOL_NAME="default"
if zpool list | grep "$POOL_NAME" &> /dev/null ; then
  echo "::ZFS pool already present"
else
  echo "::ZFS pool not present=>initializing lxc/lxd"
  lxd init --preseed < lxd_preseed.yml
fi

echo "::Python3"
if ! command -v python3 &> /dev/null
then
    echo "::Python3=>not found=>prompting installation"
    if command -v pacman &> /dev/null
    then
        pacman -Sy python3
    else
        apt-get install python3
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
