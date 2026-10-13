import os, tempfile
os.environ.setdefault('SESSION_SECRET', 'test-secret')
os.environ.setdefault('TOKEN_ENC_KEY', 'p8bX0E0ZbYQH8u0f6WqT2T0w8Q2cZ9rVd3J1kT9m3so=')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
os.environ['MEETINGS_DB'] = os.path.join(tempfile.mkdtemp(), 'test.sqlite3')
