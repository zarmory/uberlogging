#!/bin/bash

echo -e "Running with tty output. First line should text with colors\n"
python demo.py

echo -e "\nRunning with pipe output. First line should be JSON with no colors\n"
python demo.py 2>&1 | tee
