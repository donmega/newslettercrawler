import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

# Configuration
EMAIL_ADDRESS = "your_email@example.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36"
}
TIMEOUT = 10
DELAY_BETWEEN_REQUESTS = 2  # seconds

# Added log file for successful submissions
SUCCESS_LOG_FILE = 'successful_submissions.txt'

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def find_forms(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    signup_forms = []
    for form in forms:
        # Look for input fields that are likely for email signup
        input_types = [inp.get("type") for inp in form.find_all("input")]
        if "email" in input_types:
            signup_forms.append(form)
    return signup_forms

def submit_form(form, base_url):
    action = form.get("action")
    method = form.get("method", "get").lower()
    url = urljoin(base_url, action) if action else base_url

    # Prepare form data
    data = {}
    for input_tag in form.find_all("input"):
        input_type = input_tag.get("type", "text")
        name = input_tag.get("name")
        if not name:
            continue
        if input_type == "email":
            data[name] = EMAIL_ADDRESS
        elif input_type in ["text", "hidden"]:
            data[name] = input_tag.get("value", "")
        elif input_type == "submit":
            data[name] = input_tag.get("value", "")
        # Add more input types if necessary

    try:
        if method == "post":
            response = requests.post(url, data=data, headers=HEADERS, timeout=TIMEOUT)
        else:
            response = requests.get(url, params=data, headers=HEADERS, timeout=TIMEOUT)

        # Log successful submissions
        if response.status_code >= 200 and response.status_code < 300:
            with open(SUCCESS_LOG_FILE, 'a') as f:
                f.write(f"{url}\n")
        return response.status_code, response.url
    except requests.RequestException as e:
        print(f"Failed to submit form at {url}: {e}")
        return None, None

def crawl(url, max_pages=100):
    visited = set()
    to_visit = [url]
    pages_crawled = 0

    while to_visit and pages_crawled < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        print(f"Crawling: {current_url}")
        visited.add(current_url)
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=TIMEOUT)
            if response.status_code != 200:
                print(f"Failed to retrieve {current_url}: Status code {response.status_code}")
                continue
            forms = find_forms(response.text, current_url)
            for form in forms:
                status, submitted_url = submit_form(form, current_url)
                if status:
                    print(f"Submitted form at {submitted_url} with status code {status}")
            # Find and add new links to the queue
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                full_url = urljoin(current_url, href)
                if is_valid_url(full_url) and full_url not in visited:
                    to_visit.append(full_url)
            pages_crawled += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)
        except requests.RequestException as e:
            print(f"Error crawling {current_url}: {e}")
            continue

if __name__ == "__main__":
    start_url = "https://ahrefs.com/top/shopping"  # Replace with the starting URL
    crawl(start_url, max_pages=50)
