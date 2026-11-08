import threading

# The sqlite connection is opened with check_same_thread=False so that Streamlit's
# ScriptRunner threads can share it. Every write serializes through this lock.
write_lock = threading.Lock()
