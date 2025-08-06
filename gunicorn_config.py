# gunicorn_config.py
import threading
from app import queue_worker

def post_fork(server, worker):
    """Gunicorn worker start hone ke baad yeh function chalega"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")
    
    # Har worker ke andar apna background thread start karein
    worker_thread = threading.Thread(target=queue_worker)
    worker_thread.daemon = True # Ab daemon True kaam karega
    worker_thread.start()
    server.log.info("✅ Queue worker thread started inside Gunicorn worker.")
