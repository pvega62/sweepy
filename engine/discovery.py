from jobspy import scrape_jobs
import pandas as pd
from typing import List, Dict

def discover_jobs(titles: List[str], location: str, remote_only: bool = False, results_wanted: int = 30) -> List[Dict]:
    """
    Uses jobspy to scrape jobs from multiple boards (LinkedIn, Indeed, Glassdoor, ZipRecruiter).
    """
    all_jobs = []
    
    print(f"  -> Scraping jobs for titles: {', '.join(titles)} in {location}...")
    
    # We can do one query or iterate over titles. 
    # Jobspy accepts a search_term. Let's combine titles into an OR query if possible, 
    # or just run the first title for simplicity, or iterate. Let's iterate to be safe.
    
    for title in titles:
        try:
            jobs: pd.DataFrame = scrape_jobs(
                site_name=["linkedin", "indeed", "glassdoor", "zip_recruiter"],
                search_term=title,
                location=location,
                results_wanted=results_wanted,
                hours_old=72,  # recent jobs
                is_remote=remote_only,
                country_alice="usa"
            )
            
            if not jobs.empty:
                # Convert DataFrame to list of dicts
                # JobSpy columns include: id, site, job_url, title, company, location, job_type, 
                # date_posted, interval, min_amount, max_amount, currency, is_remote, description
                
                # Fill NaNs with None or empty string
                jobs = jobs.fillna("")
                
                for _, row in jobs.iterrows():
                    job_data = {
                        "id": row.get("id", ""),
                        "platform": row.get("site", "Aggregator"),
                        "url": row.get("job_url", ""),
                        "title": row.get("title", ""),
                        "company": row.get("company", ""),
                        "location": row.get("location", ""),
                        "job_type": row.get("job_type", ""),
                        "date_posted": row.get("date_posted", ""),
                        "description": row.get("description", ""),
                        "min_amount": row.get("min_amount", ""),
                        "max_amount": row.get("max_amount", ""),
                        "currency": row.get("currency", "")
                    }
                    all_jobs.append(job_data)
        except Exception as e:
            print(f"  [Error] Scraping for {title}: {e}")
            
    print(f"  * Total discovered before deduplication: {len(all_jobs)}")
    
    # Deduplicate by URL
    unique_jobs = {job["url"]: job for job in all_jobs if job.get("url")}
    final_jobs = list(unique_jobs.values())
    
    print(f"  * Total unique discovered: {len(final_jobs)}")
    
    return final_jobs
