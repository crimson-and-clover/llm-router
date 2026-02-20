# exec uvicorn src.main:app --host 0.0.0.0 --port 12000 --workers 4
exec hypercorn src.main:app --bind 0.0.0.0:12000 --workers 4
