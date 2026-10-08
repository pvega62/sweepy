from jobspy import scrape_jobs
import pandas as pd
from urllib.parse import urlparse
from typing import List, Dict, Tuple

def classify_platform(url: str, default_site: str) -> str:
    """Classify the target ATS or board platform based on URL and site name."""
    url_lower = url.lower()
    if "greenhouse.io" in url_lower:
        return "Greenhouse"
    if "ashbyhq.com" in url_lower:
        return "Ashby"
    if "lever.co" in url_lower:
        return "Lever"
    if "workable.com" in url_lower:
        return "Workable"
    
    site_clean = default_site.title() if default_site else "Aggregator"
    return site_clean

def discover_jobs(
    titles: List[str], 
    location: str, 
    remote_only: bool = False, 
    min_salary: int = 0,
    platforms: Dict[str, bool] = None,
    results_wanted: int = 25
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Scrapes jobs across configured platforms and job boards via jobspy,
    classifying ATS endpoints and aggregating statistics.
    """
    if platforms is None:
        platforms = {"greenhouse": True, "ashby": True, "lever": True, "workable": True, "aggregators": False}

    all_jobs = []
    platform_counts = {
        "Greenhouse": 0,
        "Ashby": 0,
        "Lever": 0,
        "Workable": 0,
    }
    if platforms.get("aggregators", False):
        platform_counts["Aggregators"] = 0

    sites_to_query = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]

    for title in titles:
        try:
            jobs_df: pd.DataFrame = scrape_jobs(
                site_name=sites_to_query,
                search_term=title,
                location=location,
                results_wanted=results_wanted,
                hours_old=72,
                is_remote=remote_only,
                country_alice="usa"
            )

            if not jobs_df.empty:
                jobs_df = jobs_df.fillna("")

                for _, row in jobs_df.iterrows():
                    raw_url = str(row.get("job_url", "")).strip()
                    if not raw_url:
                        continue

                    raw_site = str(row.get("site", "Aggregator"))
                    detected_platform = classify_platform(raw_url, raw_site)

                    # Filter out if platform is explicitly disabled in config
                    plat_key = detected_platform.lower()
                    if plat_key in platforms and not platforms[plat_key]:
                        continue

                    min_amt = row.get("min_amount") or 0
                    max_amt = row.get("max_amount") or 0
                    try:
                        min_amt = float(min_amt) if min_amt else 0
                        max_amt = float(max_amt) if max_amt else 0
                    except (ValueError, TypeError):
                        min_amt, max_amt = 0, 0

                    if min_salary > 0 and max_amt > 0 and max_amt < min_salary:
                        continue

                    job_data = {
                        "id": str(row.get("id", "")),
                        "platform": detected_platform,
                        "url": raw_url,
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company", "")),
                        "location": str(row.get("location", location)),
                        "job_type": str(row.get("job_type", "")),
                        "date_posted": str(row.get("date_posted", "")),
                        "description": str(row.get("description", "")),
                        "min_amount": min_amt,
                        "max_amount": max_amt,
                        "currency": str(row.get("currency", "USD"))
                    }
                    all_jobs.append(job_data)
        except Exception as e:
            print(f"  [Error] Scraping for '{title}': {e}")

    # Deduplicate by URL
    unique_jobs = {job["url"]: job for job in all_jobs if job.get("url")}
    final_jobs = list(unique_jobs.values())

    # Count jobs per platform for CLI reporting
    for job in final_jobs:
        plat = job["platform"]
        if plat in platform_counts:
            platform_counts[plat] += 1
        elif "Aggregators" in platform_counts:
            platform_counts["Aggregators"] += 1
        else:
            platform_counts[plat] = 1

    return final_jobs, platform_counts
