#!/usr/bin/env python3
import time
import random
import logging
import sys
from datetime import datetime, timedelta
from instagrapi import Client
from instagrapi.exceptions import ClientError, LoginRequired, TwoFactorRequired
from dotenv import load_dotenv
import os
import json
from typing import Any, Dict, List, Optional
import requests

# Configure enterprise-grade logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    handlers=[
        logging.FileHandler("engagement_audit.log"),
        logging.StreamHandler()
    ]
)

# Security Configuration
load_dotenv()
USERNAME: str = os.getenv("INSTA_USERNAME", "").strip()
PASSWORD: str = os.getenv("INSTA_PASSWORD", "").strip()

if not USERNAME or not PASSWORD:
    logging.critical("Credentials validation failed - aborting")
    sys.exit(1)

# Targeting Parameters
TARGET_ACCOUNTS: List[str] = [
  "troyesivan",
  "joeygraceffa",
  "tyleroakley",
  "connorfranta",
  "danielhowell",
  "amazingphil",
  "noataieb",
  "calummcswiggan",
  "milesmckenna",
  "nicktoteda",
  "bran_flakezz",
  "josh_rimer",
  "ulyandernesto",
  "grantandash",
  "michaelandmatt", "joelerdmann_", "whosyourjordan", "hannahrslattery", "tristanwesson", "collinpmcgee", "jacoby.dueck", "joeedmondss", "louisthebarber_"
]

# Engagement Protocol Settings
POST_AGE_LIMIT_DAYS: int = 15
CONTENT_BLACKLIST: set = {"#ad", "#sponsored", "#partner", "#commission"}

# Enterprise Monitoring System
LAST_RUN_FILE: str = "last_run.json"
SESSION_FILE: str = "session.json"
PROXY_FILE: str = "proxies.txt"
METRICS_FILE: str = "performance_metrics.ndjson"

# Enhanced Performance Monitor (Singleton)
class EnhancedPerformanceMonitor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnhancedPerformanceMonitor, cls).__new__(cls)
            cls._instance.metrics = {
                "api_calls": 0,
                "errors": 0,
                "engagements": 0,
                "response_times": [],
                "reciprocity": {},
                "hourly_engagement": {}
            }
        return cls._instance

    def track_call(self, response_time: float) -> None:
        self.metrics["api_calls"] += 1
        self.metrics["response_times"].append(response_time)

    def track_error(self) -> None:
        self.metrics["errors"] += 1

    def track_reciprocity(self, username: str) -> None:
        self.metrics["reciprocity"][username] = self.metrics["reciprocity"].get(username, 0) + 1

    def track_hourly_engagement(self) -> None:
        hour = datetime.now().hour
        self.metrics["hourly_engagement"][hour] = self.metrics["hourly_engagement"].get(hour, 0) + 1

    def save_metrics(self) -> None:
        try:
            with open(METRICS_FILE, "a") as f:
                f.write(json.dumps(self.metrics) + "\n")
        except Exception as e:
            logging.error(f"Metrics save failed: {str(e)}")

def get_time_aware_delay(base_range: tuple) -> float:
    """Adapt delays based on time of day"""
    current_hour = datetime.now().hour
    if 8 <= current_hour < 20:  # Peak hours
        return random.uniform(base_range[0] * 0.7, base_range[1] * 0.7)
    return random.uniform(base_range[0] * 1.3, base_range[1] * 1.3)

def get_follower_limit(follower_count: int) -> int:
    """Dynamic follower processing based on account size"""
    if follower_count < 10000:
        return random.randint(8, 12)
    elif follower_count < 100000:
        return random.randint(6, 9)
    return random.randint(4, 6)

# Proxy Manager with round-robin rotation
class ProxyManager:
    def __init__(self):
        self.proxies = self._load_proxies()
        self.index = 0

    def _load_proxies(self) -> List[str]:
        try:
            with open(PROXY_FILE, "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
                if not proxies:
                    logging.warning("Proxy file is empty - using direct connection")
                return proxies
        except FileNotFoundError:
            logging.warning("No proxy file found - using direct connection")
            return []

    def get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self.index]
        self.index = (self.index + 1) % len(self.proxies)
        return proxy

# Engagement Tracker using a singleton-like approach
class EngagementTracker:
    def __init__(self):
        self.reset_counters()

    def reset_counters(self) -> None:
        data = self.load_last_run()
        today = datetime.today().strftime("%Y-%m-%d")
        if data.get("date") != today:
            self.likes_today = 0
            self.save_last_run(0)
        else:
            self.likes_today = data.get("count", 0)

    def increment_likes(self) -> None:
        self.likes_today += 1
        if self.likes_today % 10 == 0:
            self.save_last_run(self.likes_today)

    @property
    def limit_reached(self) -> bool:
        return self.likes_today >= 200  # Example daily like limit

    @staticmethod
    def load_last_run() -> Dict[str, Any]:
        try:
            with open(LAST_RUN_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Could not load last run file: {e}")
            return {"date": "", "count": 0}

    @staticmethod
    def save_last_run(count: int) -> None:
        data = {"date": datetime.today().strftime("%Y-%m-%d"), "count": count}
        try:
            with open(LAST_RUN_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logging.error(f"Failed to save last run data: {e}")

# AdaptiveSafeClient using authenticated (private) API endpoints and handling 2FA
class AdaptiveSafeClient(Client):
    def __init__(self, proxy_manager: ProxyManager):
        super().__init__()
        self.proxy_manager = proxy_manager
        self.request_timeout = 15  # Set a single numeric value for timeout
        self._rotate_device()
        self._load_session()

    def _rotate_device(self) -> None:
        devices = [
            {"model": "iPhone15,4", "os": "iOS 17.1.2"},
            {"model": "Pixel 8 Pro", "os": "Android 14"},
            {"model": "SM-S928U", "os": "Android 13"}
        ]
        device = random.choice(devices)
        self.set_user_agent(
            f"Instagram 297.0.0.28.119 ({device['model']}; {device['os']}; en_US)"
        )

    def _load_session(self) -> None:
        log_event("Starting login process...")
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    settings = json.load(f)
                    self.set_settings(settings)
                self.secure_user_id_from_username(USERNAME)
                log_event("Loaded session from file.")
                return
            except (LoginRequired, ClientError, json.JSONDecodeError) as e:
                logging.warning(f"Session file invalid: {e}. Removing session file.")
                os.remove(SESSION_FILE)
        self._login()

    def _login(self) -> None:
        try:
            self.login(USERNAME, PASSWORD)
            self.dump_settings(SESSION_FILE)
            log_event("Logged in and saved session.")
        except TwoFactorRequired:
            verification_code = input("Enter the verification code from Instagram: ")
            self.login(USERNAME, PASSWORD, verification_code=verification_code)
            self.dump_settings(SESSION_FILE)
            log_event("Logged in with 2FA and saved session.")
        except ClientError as e:
            logging.critical(f"Login failed: {str(e)}")
            sys.exit(1)

    def _secure_request(self, func, *args, **kwargs):
        start = time.time()
        try:
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                self.set_proxy(proxy)
                logging.debug(f"Using proxy: {proxy}")
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            EnhancedPerformanceMonitor().track_call(elapsed)
            return result
        except LoginRequired:
            logging.warning("Secure request failed: login_required. Rotating device fingerprint.")
            self._rotate_device()
            self._login()  # Re-authenticate
            return self._secure_request(func, *args, **kwargs)  # Retry the request
        except ClientError as e:
            EnhancedPerformanceMonitor().track_error()
            logging.warning(f"Secure request failed: {str(e)}. Rotating device fingerprint.")
            self._rotate_device()
            raise
        except Exception as e:
            EnhancedPerformanceMonitor().track_error()
            logging.critical(f"Critical security breach: {str(e)}")
            raise Exception("EnterpriseSecurityException") from e

    # Secure wrappers for authenticated API calls (private endpoints)
    def secure_user_medias(self, user_id: int, **kwargs):
        return self._secure_request(super().user_medias, user_id, **kwargs)

    def secure_user_stories(self, user_id: int):
        return self._secure_request(super().user_stories, user_id)

    def secure_story_seen(self, story_ids: List[str]):
        return self._secure_request(super().story_seen, story_ids)

    def secure_story_like(self, story_id: str):
        return self._secure_request(super().story_like, story_id)

    def secure_media_like(self, media_id: str):
        return self._secure_request(super().media_like, media_id)

    def secure_user_followers(self, user_id: int, amount: int = 150):
        return self._secure_request(super().user_followers, user_id, amount=amount)

    def secure_user_id_from_username(self, username: str) -> int:
        return self._secure_request(super().user_id_from_username, username)

    def secure_user_info(self, user_id: int):
        return self._secure_request(super().user_info, user_id)

    def secure_account_insights(self):
        return self._secure_request(super().account_insights)

    def get_active_followers(self, username: str, limit: int) -> List[int]:
        user_id = self.secure_user_id_from_username(username)
        followers = self.secure_user_followers(user_id, amount=150)
        active_followers = []
        for fid in followers:
            try:
                user_info = self.secure_user_info(fid)
                if not user_info.is_private and (self.secure_user_stories(fid) or self.secure_user_medias(fid, amount=1)):
                    active_followers.append(fid)
            except Exception as e:
                logging.warning(f"Error checking activity for follower {fid}: {e}")
            if len(active_followers) >= limit:
                break
        return active_followers

    def process_target_account(self, username: str, tracker: EngagementTracker) -> None:
        try:
            user_id = self.secure_user_id_from_username(username)
            account_size = self.secure_user_info(user_id).follower_count
            follower_limit = get_follower_limit(account_size)
            log_event(f"Processing {username} (Size: {account_size} | Limit: {follower_limit})")
            active_followers = self.get_active_followers(username, follower_limit)
            for fid in active_followers:
                log_event(f"Engaging with follower: {fid}")
                process_posts(self, tracker, fid, username)  # Pass the username
                process_stories(self, tracker, fid, username)  # Pass the username
            log_event(f"Finished processing {username}")
        except Exception as e:
            logging.error(f"Error processing account {username}: {str(e)}")
            log_event_json("error", {"username": username, "error": str(e)})

def is_recent_post(post, max_days: int = POST_AGE_LIMIT_DAYS) -> bool:
    post_time = post.taken_at.replace(tzinfo=None)
    return (datetime.now() - post_time) < timedelta(days=max_days)

def log_event(message: str) -> None:
    logging.info(message)

def log_event_json(event_type: str, details: dict):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "details": details
    }
    with open("audit_log.json", "a") as f:
        f.write(json.dumps(entry) + "\n")

def process_posts(cl: AdaptiveSafeClient, tracker: EngagementTracker, user_id: int, username: str) -> int:
    try:
        log_event_json("attempt_like_post", {"username": username})
        posts = cl.secure_user_medias(user_id, amount=6)
        valid_posts = [p for p in posts if is_recent_post(p)]
        if not valid_posts:
            return 0
        post = random.choice(valid_posts)
        cl.secure_media_like(post.id)
        tracker.increment_likes()
        EnhancedPerformanceMonitor().track_hourly_engagement()
        log_event_json("liked_post", {"username": username, "post_id": post.id})
        print(f"✅ Liked post from @{username}")
        log_event(f"✅ Liked post from @{username}")
        time.sleep(random.uniform(30, 55))
        return 1
    except Exception as e:
        logging.error(f"Post processing error for user {username}: {str(e)}")
        log_event_json("error", {"username": username, "error": str(e)})
        return 0

def process_stories(cl: AdaptiveSafeClient, tracker: EngagementTracker, user_id: int, username: str) -> int:
    try:
        log_event_json("attempt_view_story", {"username": username})
        stories = cl.secure_user_stories(user_id)
        if not stories:
            return 0
        story = random.choice(stories)
        log_event_json("attempt_like_story", {"username": username, "story_id": story.id})
        cl.secure_story_like(story.id)
        tracker.increment_likes()
        EnhancedPerformanceMonitor().track_hourly_engagement()
        log_event_json("liked_story", {"username": username, "story_id": story.id})
        print(f"✅ Liked story from @{username}")
        log_event(f"✅ Liked story from @{username}")
        time.sleep(random.uniform(30, 55))
        return 1
    except Exception as e:
        logging.error(f"Story processing error for user {username}: {str(e)}")
        log_event_json("error", {"username": username, "error": str(e)})
        return 0

def main():
    log_event_json("session_start", {"message": "Starting engagement session..."})
    proxy_mgr = ProxyManager()
    cl = AdaptiveSafeClient(proxy_mgr)
    tracker = EngagementTracker()
    perf_monitor = EnhancedPerformanceMonitor()
    
    try:
        # Shuffle the target accounts list to process them in random order
        random.shuffle(TARGET_ACCOUNTS)
        
        for account in TARGET_ACCOUNTS:
            try:
                start_time = time.time()
                cl.process_target_account(account, tracker)
                processing_time = time.time() - start_time
                base_delay = (120, 300) if processing_time < 60 else (300, 600)
                delay = get_time_aware_delay(base_delay)
                log_event_json("account_cooldown", {"account": account, "delay": delay})
                time.sleep(delay)
            except Exception as e:
                logging.error(f"Error processing account {account}: {str(e)}")
                log_event_json("error", {"account": account, "error": str(e)})
    except Exception as e:
        logging.error(f"Orchestration error: {str(e)}")
        log_event_json("error", {"error": str(e)})
    finally:
        perf_monitor.save_metrics()
        EngagementTracker.save_last_run(tracker.likes_today)
        log_event_json("session_complete", {"message": "Session complete."})

if __name__ == "__main__":
    main()
