#!/bin/bash

echo "::Deleting containers"
# Delete lxc containers and images
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
echo "::Done deleting containers"