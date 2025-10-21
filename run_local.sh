#!/bin/bash
docker compose -f ocav1.yml down mongol || true
docker compose -f xolo.yml down || true
docker compose -f ocav1.yml up mongol -d
docker compose -f xolo.yml up -d
uvicorn ocaapi.server:app --host ${OCA_HOST-0.0.0.0} --port ${OCA_PORT-5000} --reload
