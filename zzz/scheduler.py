import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management import call_command

log = logging.getLogger(__name__)

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
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    
    # Chat messages - runs at 12, 18
    scheduler.add_job(
        run_chat_messages,
        trigger=CronTrigger(hour='12,18', minute=1),
        id='chat_messages',
        name='Send chat message emails',
        replace_existing=True,
    )
    log.info("Scheduled job: chat_messages at 12, 18")
    
    # Chat rooms - runs every 5 minutes
    scheduler.add_job(
        run_chat_rooms,
        trigger=CronTrigger(minute='*/5'),
        id='chat_rooms',
        name='Create/Delete/Archive chat rooms',
        replace_existing=True,
    )
    log.info("Scheduled job: chat_rooms every 5 minutes")
    
    # Vote - runs daily at 08:05
    scheduler.add_job(
        run_vote,
        trigger=CronTrigger(hour=8, minute=5),
        id='vote',
        name='Process voting and create 1-to-1 rooms',
        replace_existing=True,
    )
    log.info("Scheduled job: vote at 08:05 daily")
    
    # Count citizens - runs every 5 minutes
    scheduler.add_job(
        run_count_citizens,
        trigger=CronTrigger(minute='*/5'),
        id='count_citizens',
        name='Count citizens and manage reputation',
        replace_existing=True,
    )
    log.info("Scheduled job: count_citizens every 5 minutes")
    
    # Update site - runs every hour
    scheduler.add_job(
        run_update_site,
        trigger=CronTrigger(minute=2),
        id='update_site',
        name='Update Site domain and name from environment variables',
        replace_existing=True,
    )
    log.info("Scheduled job: update_site every hour")
    
    scheduler.start()
    log.info("APScheduler started successfully")
    
    return scheduler

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