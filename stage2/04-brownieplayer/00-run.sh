#!/bin/bash -e

install -m 755 files/brownieplayer.py "${ROOTFS_DIR}/boot/"
install -m 644 files/autologin.conf "${ROOTFS_DIR}/etc/systemd/system/getty@tty1.service.d/"
install -m 644 files/profile "${ROOTFS_DIR}/home/pi/.profile"

