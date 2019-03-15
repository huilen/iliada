#!/bin/bash

rm *~ 2> /dev/null
aws s3 sync . s3://texto.iliada.com.ar/ --exclude ".venv/*" --exclude=".git/*" --acl public-read
