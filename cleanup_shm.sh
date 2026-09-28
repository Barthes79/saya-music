#!/bin/bash
while true; do
  find /dev/shm/saya_dl -name "*.part" -mmin +10 -delete 2>/dev/null
  sleep 300
done
