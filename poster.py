"""
Chicago Fleet Wraps Reddit Bot — Reddit Poster
Posts comments, DMs, and threads using RedditSession (requests-based).
No browser automation needed — works on any server.
"""
import time
import random
from config import MIN_DELAY_BETWEEN_COMMENTS, MAX_DELAY_BETWEEN_COMMENTS


def random_delay():
    """Wait a random amount of time between actions to appear human."""
    delay = random.randint(MIN_DELAY_BETWEEN_COMMENTS, MAX_DELAY_BETWEEN_COMMENTS)
    print(f"  [DELAY] Waiting {delay} seconds before next action...", flush=True)
    time.sleep(delay)


def post_comment(reddit_session, thread_id: str, comment_text: str) -> bool:
    """Post a comment to a Reddit thread.
    thread_id: the short ID (e.g., 'abc123'), will be converted to fullname 't3_abc123'
    """
    fullname = f"t3_{thread_id}" if not thread_id.startswith("t3_") else thread_id
    return reddit_session.post_comment(fullname, comment_text)


def send_dm(reddit_session, to_user: str, subject: str, message: str) -> bool:
    """Send a DM to a Reddit user."""
    return reddit_session.send_dm(to_user, subject, message)


def create_thread(reddit_session, subreddit: str, title: str, body: str) -> bool:
    """Create a new thread in a subreddit."""
    return reddit_session.create_thread(subreddit, title, body)
