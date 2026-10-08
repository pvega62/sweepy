import requests
import re
from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    """
    Validate a job URL to ensure it is still active.
    Handles standard HTTP 404s and platform-specific dead pages (e.g., Ashby).
    """
    try:
        # Use a generic user-agent to avoid basic blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Standard HTTP error check
        if response.status_code >= 400:
            return False
            
        domain = urlparse(url).netloc.lower()
        
        # Platform-specific checks for "soft" 404s
        if "ashbyhq.com" in domain:
            # Ashby returns a 200 OK but renders a blank page or error state if posting is null
            if "window.__appData.posting = null;" in response.text or "window.__appData.posting: null" in response.text or 'window.__appData.posting=null' in response.text.replace(' ', ''):
                return False
                
        # Future-proofing: add other platforms like Greenhouse/Lever if they do soft 404s
        if "greenhouse.io" in domain and "Sorry, this job has been filled" in response.text:
             return False

        if "lever.co" in domain and "This job is no longer available" in response.text:
             return False

        return True

    except requests.RequestException:
        # If the request fails entirely (timeout, DNS error), assume the URL is dead
        return False

def filter_valid_jobs(jobs: list) -> tuple:
    """
    Take a list of job dictionaries and return only those with valid URLs, 
    plus the count of expired jobs.
    """
    valid_jobs = []
    expired_count = 0
    for job in jobs:
        url = job.get('url')
        if not url:
            expired_count += 1
            continue
            
        if is_valid_url(url):
            valid_jobs.append(job)
        else:
            expired_count += 1
            
    return valid_jobs, expired_count
