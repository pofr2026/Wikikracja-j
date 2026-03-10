import logging
import os
import atexit
import signal
import sys
import errno
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management import call_command

log = logging.getLogger(__name__)

# Global scheduler instance (singleton)
_scheduler_instance = None
_lock_file = None  # File handle for fcntl lock (if using fcntl)


def _acquire_lock():
    """Acquire a cross-process lock to ensure only one scheduler starts."""
    global _lock_file
    lock_path = os.path.join(settings.BASE_DIR, 'scheduler.lock')
    try:
        # Try using fcntl (Linux/Unix) if available
        import fcntl
        # Ensure lock directory exists
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        # Open lock file (keep it open for the duration of the lock)
        _lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore
            log.info("Acquired scheduler lock via fcntl")
            return True
        except IOError:
            # Lock already held by another process
            _lock_file.close()
            _lock_file = None
            log.info("Scheduler lock not acquired - another process holds it")
            return False
    except ImportError:
        # fcntl not available (e.g., Windows). Fallback to PID file lock.
        try:
            if os.path.exists(lock_path):
                try:
                    with open(lock_path, 'r') as f:
                        old_pid = int(f.read().strip())
                    # Check if process is still running
                    try:
                        os.kill(old_pid, 0)
                        # Process exists, lock held
                        log.info(f"Scheduler lock held by process {old_pid}")
                        return False
                    except OSError as e:
                        # Check if process does not exist (ESRCH) or permission denied (EPERM)
                        if getattr(e, 'errno', None) == errno.ESRCH:
                            # Process not running, stale lock
                            log.warning(f"Removing stale scheduler lock (PID {old_pid})")
                            os.remove(lock_path)
                        elif getattr(e, 'errno', None) == errno.EPERM:
                            # Process exists but no permission -> still running
                            log.info(f"Scheduler lock held by process {old_pid} (no permission to signal)")
                            return False
                        else:
                            # For other errors, assume stale to be safe
                            log.warning(f"Error checking PID {old_pid}: {e}, assuming stale")
                            os.remove(lock_path)
                except (ValueError, IOError) as e:
                    log.warning(f"Corrupted lock file, removing: {e}")
                    os.remove(lock_path)
            # Write our PID
            with open(lock_path, 'w') as f:
                f.write(str(os.getpid()))
            log.info(f"Acquired scheduler lock via PID file (PID {os.getpid()})")
            return True
        except Exception as e:
            log.error(f"Failed to acquire PID lock: {e}", exc_info=True)
            return False
    except Exception as e:
        log.error(f"Failed to acquire lock: {e}", exc_info=True)
        return False


def _release_lock():
    """Release the lock if held."""
    global _lock_file
    # fcntl path: close file and release lock
    if _lock_file:
        try:
            import fcntl
            fcntl.flock(_lock_file, fcntl.LOCK_UN)  # type: ignore
            _lock_file.close()
            log.info("Released scheduler lock (fcntl)")
        except Exception as e:
            log.error(f"Error releasing fcntl lock: {e}")
        finally:
            _lock_file = None
    else:
        # PID file lock: remove lock file if we own it
        lock_path = os.path.join(settings.BASE_DIR, 'scheduler.lock')
        try:
            if os.path.exists(lock_path):
                with open(lock_path, 'r') as f:
                    pid_in_file = int(f.read().strip())
                if pid_in_file == os.getpid():
                    os.remove(lock_path)
                    log.info("Released scheduler lock (PID file)")
        except Exception as e:
            log.error(f"Error releasing PID lock: {e}")


def start_scheduler():
    """
    Start APScheduler to run management commands on schedule.
    Replaces cron jobs:
    - 1 12,18 * * * -> chat_messages
    - */5 * * * * -> chat_rooms (every 5 minutes)
    - 5 8 * * * -> vote
    - */5 * * * * -> count_citizens (every 5 minutes)
    - 2 * * * * -> update_site (every hour)
    """
    global _scheduler_instance
    
    # Fast path: already started in this process
    if _scheduler_instance is not None:
        log.info("Scheduler already started in this process, returning existing instance")
        return _scheduler_instance
    
    # Try to acquire lock to prevent multiple processes from starting the scheduler
    if not _acquire_lock():
        log.info("Scheduler not started - lock not acquired (another process has it)")
        return None
    
    try:
        # Double-check after lock acquisition (in case another thread set it)
        if _scheduler_instance is not None:
            _release_lock()
            return _scheduler_instance
        
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        _scheduler_instance = scheduler
        
        # Chat messages - runs at 12, 18
        scheduler.add_job(
            run_chat_messages,
            trigger=CronTrigger(hour='12,18', minute=1),
            id='chat_messages',
            name='Send chat message emails',
            replace_existing=True,
            max_instances=1,
        )
        log.info("Scheduled job: chat_messages at 12, 18")
        
        # Chat rooms - runs every 5 minutes
        scheduler.add_job(
            run_chat_rooms,
            trigger=CronTrigger(minute='*/5'),
            id='chat_rooms',
            name='Create/Delete/Archive chat rooms',
            replace_existing=True,
            max_instances=1,
        )
        log.info("Scheduled job: chat_rooms every 5 minutes")
        
        # Vote - runs daily at 08:05
        scheduler.add_job(
            run_vote,
            trigger=CronTrigger(hour=8, minute=5),
            id='vote',
            name='Process voting and create 1-to-1 rooms',
            replace_existing=True,
            max_instances=1,
        )
        log.info("Scheduled job: vote at 08:05 daily")
        
        # Count citizens - runs every 5 minutes
        scheduler.add_job(
            run_count_citizens,
            trigger=CronTrigger(minute='*/5'),
            id='count_citizens',
            name='Count citizens and manage reputation',
            replace_existing=True,
            max_instances=1,
        )
        log.info("Scheduled job: count_citizens every 5 minutes")
        
        # Update site - runs every hour
        scheduler.add_job(
            run_update_site,
            trigger=CronTrigger(minute=2),
            id='update_site',
            name='Update Site domain and name from environment variables',
            replace_existing=True,
            max_instances=1,
        )
        log.info("Scheduled job: update_site every hour")
        
        scheduler.start()
        log.info("APScheduler started successfully")
        
        return scheduler
    except Exception as e:
        log.error(f"Failed to start scheduler: {e}", exc_info=True)
        _release_lock()
        raise

# Ensure lock is released on process exit
atexit.register(_release_lock)

# Handle termination signals to release lock
def _signal_handler(signum, frame):
    _release_lock()
    sys.exit(0)

for sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(sig, _signal_handler)
    except (ValueError, AttributeError):
        # Can't set signal in non-main thread or platform limitation; ignore
        pass

def run_chat_messages():
    """Execute chat_messages management command"""
    try:
        log.info("Running chat_messages command")
        call_command('chat_messages')
        log.info("chat_messages command completed")
    except Exception as e:
        log.error(f"Error running chat_messages: {e}", exc_info=True)

def run_chat_rooms():
    """Execute chat_rooms management command"""
    try:
        log.info("Running chat_rooms command")
        call_command('chat_rooms')
        log.info("chat_rooms command completed")
    except Exception as e:
        log.error(f"Error running chat_rooms: {e}", exc_info=True)

def run_vote():
    """Execute vote management command"""
    try:
        log.info("Running vote command")
        call_command('vote')
        log.info("vote command completed")
    except Exception as e:
        log.error(f"Error running vote: {e}", exc_info=True)

def run_count_citizens():
    """Execute count_citizens management command"""
    try:
        log.info("Running count_citizens command")
        call_command('count_citizens')
        log.info("count_citizens command completed")
    except Exception as e:
        log.error(f"Error running count_citizens: {e}", exc_info=True)

def run_update_site():
    """Execute update_site management command"""
    try:
        log.info("Running update_site command")
        call_command('update_site')
        log.info("update_site command completed")
    except Exception as e:
        log.error(f"Error running update_site: {e}", exc_info=True)