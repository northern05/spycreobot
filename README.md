# spycreobot

Use Python 3.10 for the pinned dependencies in `requirements.txt`. Python 3.14
cannot build several of these older native dependencies.

```bash
python3.10 -m venv .venv310
source .venv310/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

If `.venv310` already exists, activate it before installing dependencies. Select
`.venv310/bin/python` as the project interpreter in your IDE as well.
