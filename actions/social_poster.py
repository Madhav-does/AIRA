"""
ARIA Autonomous Social Poster & Scheduler
Allows ARIA to schedule and publish LinkedIn and social media posts automatically.
"""

import threading
import time
from datetime import datetime


class SocialPosterScheduler:
    """Manages scheduled social media posts in the background."""

    def __init__(self):
        self._scheduled_posts = []
        self._running = True
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="ARIA-SocialPoster")
        self._thread.start()

    def schedule_post(self, content_or_topic: str, delay_seconds: int, platform: str = "linkedin") -> str:
        """Schedule a post to be published after delay_seconds."""
        publish_time = time.time() + delay_seconds
        dt_str = datetime.fromtimestamp(publish_time).strftime("%H:%M:%S")

        with self._lock:
            self._scheduled_posts.append({
                "content": content_or_topic,
                "publish_time": publish_time,
                "platform": platform,
                "status": "pending"
            })

        mins = round(delay_seconds / 60, 1)
        print(f"[SocialPoster] Scheduled {platform} post in {mins}m (at {dt_str}): '{content_or_topic[:40]}...'")
        return f"Scheduled {platform} post in {mins} minutes (at {dt_str})."

    def _worker(self):
        """Background thread checking for pending posts."""
        while self._running:
            now = time.time()
            due_posts = []
            with self._lock:
                remaining = []
                for p in self._scheduled_posts:
                    if p["status"] == "pending" and p["publish_time"] <= now:
                        p["status"] = "executing"
                        due_posts.append(p)
                    elif p["status"] == "pending":
                        remaining.append(p)
                self._scheduled_posts = remaining

            for post in due_posts:
                self._publish(post)

            time.sleep(5)

    def _publish(self, post: dict):
        """Execute the post publication."""
        content = post.get("content", "")
        platform = post.get("platform", "linkedin")
        print(f"[SocialPoster] Publishing scheduled post to {platform}...")

        if platform == "linkedin":
            from actions.linkedin_control import post_to_linkedin
            post_to_linkedin(content, via="auto")

    def list_scheduled(self) -> str:
        """List upcoming scheduled posts."""
        with self._lock:
            if not self._scheduled_posts:
                return "No upcoming social media posts scheduled."
            lines = []
            for i, p in enumerate(self._scheduled_posts, 1):
                t_str = datetime.fromtimestamp(p["publish_time"]).strftime("%H:%M:%S")
                lines.append(f"{i}. [{p['platform'].upper()}] at {t_str}: '{p['content'][:50]}...'")
            return "\n".join(lines)


# Singleton scheduler instance
scheduler = SocialPosterScheduler()


def schedule_linkedin_post(topic_or_content: str, minutes_from_now: int = 60) -> str:
    """Schedule a LinkedIn post to be drafted and posted in X minutes."""
    from actions.linkedin_control import generate_linkedin_draft
    draft = generate_linkedin_draft(topic_or_content)
    delay_sec = max(10, int(minutes_from_now * 60))
    return scheduler.schedule_post(draft, delay_seconds=delay_sec, platform="linkedin")


def list_scheduled_posts() -> str:
    """List all scheduled social media posts."""
    return scheduler.list_scheduled()
