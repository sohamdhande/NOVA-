from dotenv import load_dotenv
load_dotenv()

import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "sohamdhande")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else "",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
BASE = "https://api.github.com"

def get_my_prs():
    try:
        url = f"{BASE}/search/issues?q=author:{GITHUB_USERNAME}+type:pr+state:open"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            return "No open PRs found."
        
        prs = []
        for i in items:
            repo_url = i.get("repository_url", "")
            repo = repo_url.replace("https://api.github.com/repos/", "") if repo_url else "unknown_repo"
            labels = ", ".join([l.get("name", "") for l in i.get("labels", [])])
            prs.append({
                "number": i['number'],
                "repo": repo,
                "title": i['title'],
                "state": i['state'],
                "url": i['html_url'],
                "labels": labels
            })
        return {
            "type": "pr_list",
            "prs": prs
        }
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"

def get_pr_status(repo: str, pr_number: int) -> str:
    try:
        url = f"{BASE}/repos/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Get review count via reviews endpoint
        reviews_url = f"{BASE}/repos/{repo}/pulls/{pr_number}/reviews"
        reviews_resp = requests.get(reviews_url, headers=HEADERS, timeout=10)
        review_count = len(reviews_resp.json()) if reviews_resp.status_code == 200 else "Unknown"
        
        return f"PR #{data['number']}: {data['title']} | State: {data['state']} | Mergeable: {data.get('mergeable')} | Reviews: {review_count}"
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"

def get_my_repos() -> str:
    try:
        url = f"{BASE}/user/repos?sort=updated&per_page=10"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            return "No repositories found."
            
        result = []
        for r in data:
            result.append(f"{r['name']} — {r.get('description', 'No description')} — ⭐{r['stargazers_count']} — {r['html_url']}")
        return "\n".join(result)
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"

def get_repo_issues(repo: str) -> str:
    try:
        url = f"{BASE}/repos/{repo}/issues?state=open"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        # GitHub API returns PRs as issues, so filter them out
        issues = [item for item in data if "pull_request" not in item]
        if not issues:
            return f"No open issues found in {repo}."
            
        result = []
        for i in issues:
            labels = ", ".join([l['name'] for l in i.get('labels', [])])
            result.append(f"#{i['number']} {i['title']} — {labels}")
        return "\n".join(result)
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"

def get_openmrs_prs():
    # First get all PRs
    prs_result = get_my_prs()
    if isinstance(prs_result, str):
        return prs_result
    
    # Filter for openmrs
    filtered = [pr for pr in prs_result.get("prs", []) if "openmrs" in pr["repo"].lower()]
    if not filtered:
        return "No open OpenMRS PRs found."
        
    return {
        "type": "pr_list",
        "prs": filtered
    }

def get_pr_reviews(repo: str, pr_number: int) -> str:
    try:
        url = f"{BASE}/repos/{repo}/pulls/{pr_number}/reviews"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            return "No reviews found."
            
        result = []
        for r in data:
            user = r.get("user", {}).get("login", "unknown")
            state = r.get("state", "UNKNOWN")
            result.append(f"{user}: {state}")
        return "\n".join(result)
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"

def get_repo_stats(repo: str) -> str:
    try:
        url = f"{BASE}/repos/{repo}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return f"{data['name']} | ⭐{data['stargazers_count']} | 🍴{data['forks_count']} | Issues: {data['open_issues_count']} | Language: {data.get('language', 'Unknown')}"
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"

def get_commit_activity(repo: str) -> str:
    try:
        url = f"{BASE}/repos/{repo}/commits?per_page=5"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            return "No commits found."
            
        result = []
        for c in data:
            sha = c['sha'][:7]
            message = c['commit']['message'].split('\n')[0]
            author = c['commit']['author']['name']
            date = c['commit']['author']['date']
            result.append(f"{sha} — {message} — {author} — {date}")
        return "\n".join(result)
    except requests.RequestException as e:
        return f"GitHub API error: {str(e)}"
