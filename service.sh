#!/bin/sh
./wait4db.py && cd migrations && alembic upgrade head && cd - &&  ./service.py
