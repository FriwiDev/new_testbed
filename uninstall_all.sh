#!/bin/bash

#cd to script dir
cd "$( dirname "$0" )"

read -p "Uninstall bridge-utils? (yes/no, default: no): " ANSWER
if [ "$ANSWER" = "yes" ]||[ "$ANSWER" = "y" ]; then
  if command -v pacman &> /dev/null
  then
      pacman -Rcns bridge-utils
  else
      apt-get purge bridge-utils
  fi
fi

read -p "Uninstall lxd? (yes/no, default: no): " ANSWER
if [ "$ANSWER" = "yes" ]||[ "$ANSWER" = "y" ]; then
  # Delete containers and images
  DEL=$(lxc list -c n --format csv)
  if [ -n "$DEL" ]; then
    # shellcheck disable=SC2086
    lxc delete $DEL
  fi
  DEL=$(lxc image list -c f --format csv)
  if [ -n "$DEL" ]; then
    # shellcheck disable=SC2086
    lxc image delete $DEL
  fi
  # Delete storage
  printf 'config: {}\ndevices: {}' | lxc profile edit default
  lxc storage delete default
  if command -v pacman &> /dev/null
  then
      pacman -Rcns lxd
  else
      apt-get purge lxd
  fi
fi

read -p "Uninstall python3? (yes/no, default: no): " ANSWER
if [ "$ANSWER" = "yes" ]||[ "$ANSWER" = "y" ]; then
  if command -v pacman &> /dev/null
  then
      pacman -Rcns python3 tk
  else
      apt-get purge python3 python3-tk
  fi
fi

if test -f "installed_files.txt"; then
  echo "::Uninstalling testbed python package"
  xargs rm -rf < installed_files.txt
fi

echo "Uninstall completed"
