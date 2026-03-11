"""
git_repo_selector: Utilities for querying branches and commits from an
Antcode / GitLab-compatible repository API.

This module supports the "reward function control" widget in the dynamic form
(RL scenario), letting users specify a code repository and then locate their
reward function implementation by either branch or commit.

Supported workflows
-------------------
1. User enters a git HTTP URL (e.g. ``http://code.example.com/ns/repo.git``).
2. **Branch mode** – paginated branch listing + latest commit for a selected branch.
3. **Commit mode** – fuzzy commit search by message keyword.

API compatibility
-----------------
The module targets Antcode (internal) and any GitLab v4-compatible API.
Authentication uses the ``Private-Token`` request header.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_repo_url(git_url: str) -> Dict[str, str]:
    """Parse a git HTTP URL and return its components.

    Parameters
    ----------
    git_url:
        A git remote URL such as ``http://code.antfin.com/myteam/myrepo.git``
        or ``https://codeup.aliyun.com/org/proj.git``.

    Returns
    -------
    dict with keys:

    * ``base_url``    – scheme + host, e.g. ``https://codeup.aliyun.com``
    * ``namespace``   – the group / owner segment, e.g. ``myteam``
    * ``project``     – the repository name (without ``.git``), e.g. ``myrepo``
    * ``project_path`` – URL-encoded ``namespace/project``, e.g. ``myteam%2Fmyrepo``

    Raises
    ------
    ValueError
        If the URL cannot be parsed into at least two path segments.
    """
    git_url = git_url.strip()
    parsed = urllib.parse.urlparse(git_url)
    # Strip trailing .git from path
    path = re.sub(r"\.git$", "", parsed.path).strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(
            f"Cannot parse git URL '{git_url}': expected at least "
            "namespace/project in the path."
        )
    # The last segment is the project name; everything before is the namespace.
    project = parts[-1]
    namespace = "/".join(parts[:-1])
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    project_path = urllib.parse.quote(f"{namespace}/{project}", safe="")
    return {
        "base_url": base_url,
        "namespace": namespace,
        "project": project,
        "project_path": project_path,
    }


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

_ALLOWED_SCHEMES = {"http", "https"}


def _validate_url(url: str) -> None:
    """Raise ``ValueError`` if *url* does not use an allowed scheme.

    Only ``http`` and ``https`` are permitted.  This prevents accidental or
    malicious use of ``file://``, ``ftp://``, or other schemes when a
    user-supplied repository URL is propagated into API calls.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. "
            f"Only {sorted(_ALLOWED_SCHEMES)} are allowed."
        )


def _api_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Tuple[Any, Dict[str, str]]:
    """Perform a GET request against the GitLab-compatible API.

    Parameters
    ----------
    url:
        Full endpoint URL (without query string).
    token:
        Personal access token sent as ``Private-Token`` header.
    params:
        Optional query parameters.

    Returns
    -------
    Tuple of ``(parsed_json_body, response_headers_dict)``.

    Raises
    ------
    ValueError
        If *url* uses a disallowed scheme.
    urllib.error.HTTPError
        On non-2xx responses.
    """
    _validate_url(url)
    if params:
        # Remove None values and stringify the rest
        clean = {k: str(v) for k, v in params.items() if v is not None}
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers={"Private-Token": token})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        body = json.loads(resp.read().decode())
        # Normalise header names to lowercase so callers can use consistent keys
        # regardless of whether the server returns 'X-Page', 'x-page', etc.
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return body, headers


# ---------------------------------------------------------------------------
# Branch API
# ---------------------------------------------------------------------------

def list_branches(
    base_url: str,
    project_path: str,
    token: str,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """List repository branches with pagination.

    Parameters
    ----------
    base_url:
        API host, e.g. ``https://code.antfin.com``.
    project_path:
        URL-encoded project path, e.g. ``myteam%2Fmyrepo``.
    token:
        Personal access token.
    page:
        1-based page number (default: 1).
    per_page:
        Branches per page (default: 20, max: 100).
    search:
        Optional filter string to match branch names (server-side).

    Returns
    -------
    dict with keys:

    * ``branches`` – list of branch objects, each containing at minimum
      ``name`` and ``commit`` (the latest commit on that branch).
    * ``page_info`` – dict with ``page``, ``per_page``, ``total``,
      ``total_pages`` extracted from response headers.
    """
    url = f"{base_url}/api/v4/projects/{project_path}/repository/branches"
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if search:
        params["search"] = search
    branches, headers = _api_get(url, token, params)
    page_info = {
        "page": int(headers.get("x-page", page)),
        "per_page": int(headers.get("x-per-page", per_page)),
        "total": int(headers.get("x-total", 0)),
        "total_pages": int(headers.get("x-total-pages", 1)),
    }
    return {"branches": branches, "page_info": page_info}


def get_branch_latest_commit(
    base_url: str,
    project_path: str,
    branch_name: str,
    token: str,
) -> Dict[str, Any]:
    """Return the latest commit on a specific branch.

    Parameters
    ----------
    base_url:
        API host.
    project_path:
        URL-encoded project path.
    branch_name:
        Branch name, e.g. ``main`` or ``feature/my-branch``.
    token:
        Personal access token.

    Returns
    -------
    The commit object for the branch tip, containing (at minimum) ``id``,
    ``short_id``, ``title``, ``author_name``, and ``authored_date``.
    """
    encoded_branch = urllib.parse.quote(branch_name, safe="")
    url = (
        f"{base_url}/api/v4/projects/{project_path}"
        f"/repository/branches/{encoded_branch}"
    )
    branch, _ = _api_get(url, token)
    return branch.get("commit", {})


# ---------------------------------------------------------------------------
# Commit API
# ---------------------------------------------------------------------------

def search_commits(
    base_url: str,
    project_path: str,
    token: str,
    query: Optional[str] = None,
    ref_name: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Search commits by message keyword with optional branch scope.

    This function supports the "commit mode" of the reward-function control,
    where users type a keyword and get a ranked list of matching commits.

    Parameters
    ----------
    base_url:
        API host.
    project_path:
        URL-encoded project path.
    token:
        Personal access token.
    query:
        Free-text search string matched against commit messages (server-side).
    ref_name:
        Restrict search to a specific branch or tag (optional).
    page:
        1-based page number (default: 1).
    per_page:
        Results per page (default: 20, max: 100).

    Returns
    -------
    dict with keys:

    * ``commits``   – list of commit objects.
    * ``page_info`` – same structure as :func:`list_branches`.
    """
    url = f"{base_url}/api/v4/projects/{project_path}/repository/commits"
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if query:
        params["search"] = query
    if ref_name:
        params["ref_name"] = ref_name
    commits, headers = _api_get(url, token, params)
    page_info = {
        "page": int(headers.get("x-page", page)),
        "per_page": int(headers.get("x-per-page", per_page)),
        "total": int(headers.get("x-total", 0)),
        "total_pages": int(headers.get("x-total-pages", 1)),
    }
    return {"commits": commits, "page_info": page_info}
