run:
	watchmedo auto-restart --pattern "*.py" --recursive --signal SIGTERM python3.12 main.py
