"""
Tests for src/git_repo_selector.py

Run with:  pytest tests/test_git_repo_selector.py -v
"""

import io
import json
import sys
import urllib.error
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from git_repo_selector import (  # noqa: E402
    _validate_url,
    get_branch_latest_commit,
    list_branches,
    parse_repo_url,
    search_commits,
)


# ---------------------------------------------------------------------------
# _validate_url (security)
# ---------------------------------------------------------------------------

class TestValidateUrl:
    def test_http_allowed(self):
        _validate_url("http://code.example.com/api/v4/projects/ns%2Frepo/repository/branches")

    def test_https_allowed(self):
        _validate_url("https://codeup.aliyun.com/api/v4/projects/ns%2Frepo/repository/commits")

    def test_file_scheme_rejected(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _validate_url("file:///etc/passwd")

    def test_ftp_scheme_rejected(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _validate_url("ftp://evil.com/resource")


# ---------------------------------------------------------------------------
# parse_repo_url
# ---------------------------------------------------------------------------

class TestParseRepoUrl:
    def test_http_with_dot_git(self):
        result = parse_repo_url("http://code.antfin.com/myteam/myrepo.git")
        assert result["base_url"] == "http://code.antfin.com"
        assert result["namespace"] == "myteam"
        assert result["project"] == "myrepo"
        assert result["project_path"] == "myteam%2Fmyrepo"

    def test_https_without_dot_git(self):
        result = parse_repo_url("https://codeup.aliyun.com/org/proj")
        assert result["base_url"] == "https://codeup.aliyun.com"
        assert result["namespace"] == "org"
        assert result["project"] == "proj"
        assert result["project_path"] == "org%2Fproj"

    def test_nested_namespace(self):
        result = parse_repo_url("https://code.example.com/group/subgroup/repo.git")
        assert result["namespace"] == "group/subgroup"
        assert result["project"] == "repo"
        assert result["project_path"] == "group%2Fsubgroup%2Frepo"

    def test_strips_trailing_whitespace(self):
        result = parse_repo_url("  http://code.example.com/ns/myrepo.git  ")
        assert result["project"] == "myrepo"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Cannot parse git URL"):
            parse_repo_url("http://code.example.com/singlepath.git")

    def test_url_encodes_special_chars_in_namespace(self):
        # Slashes in namespace/project are encoded
        result = parse_repo_url("https://host.com/my-team/my-repo.git")
        assert "my-team" in result["project_path"]
        assert "my-repo" in result["project_path"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(body: object, headers: dict):
    """Return a mock object that behaves like urllib.request.urlopen context."""
    raw = json.dumps(body).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    msg = HTTPMessage()
    for k, v in headers.items():
        msg[k] = v
    mock_resp.headers = msg
    return mock_resp


# ---------------------------------------------------------------------------
# list_branches
# ---------------------------------------------------------------------------

class TestListBranches:
    def test_returns_branches_and_page_info(self, mocker):
        branches_data = [
            {"name": "main", "commit": {"id": "abc", "title": "init"}},
            {"name": "dev", "commit": {"id": "def", "title": "wip"}},
        ]
        resp = _make_mock_response(
            branches_data,
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "2", "X-Total-Pages": "1"},
        )
        mocker.patch("urllib.request.urlopen", return_value=resp)

        result = list_branches("https://host.com", "ns%2Frepo", "tok")
        assert len(result["branches"]) == 2
        assert result["branches"][0]["name"] == "main"
        assert result["page_info"]["total"] == 2
        assert result["page_info"]["total_pages"] == 1

    def test_passes_search_param(self, mocker):
        resp = _make_mock_response(
            [{"name": "feature/x", "commit": {}}],
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "1", "X-Total-Pages": "1"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        list_branches("https://host.com", "ns%2Frepo", "tok", search="feature")

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert "search=feature" in request_obj.full_url

    def test_passes_pagination_params(self, mocker):
        resp = _make_mock_response(
            [],
            {"X-Page": "2", "X-Per-Page": "5", "X-Total": "10", "X-Total-Pages": "2"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        list_branches("https://host.com", "ns%2Frepo", "tok", page=2, per_page=5)

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert "page=2" in request_obj.full_url
        assert "per_page=5" in request_obj.full_url


# ---------------------------------------------------------------------------
# get_branch_latest_commit
# ---------------------------------------------------------------------------

class TestGetBranchLatestCommit:
    def test_returns_commit_object(self, mocker):
        commit = {"id": "abc123", "short_id": "abc123", "title": "Fix bug", "author_name": "Alice"}
        branch_data = {"name": "main", "commit": commit}
        resp = _make_mock_response(branch_data, {})
        mocker.patch("urllib.request.urlopen", return_value=resp)

        result = get_branch_latest_commit("https://host.com", "ns%2Frepo", "main", "tok")
        assert result["id"] == "abc123"
        assert result["author_name"] == "Alice"

    def test_encodes_branch_name_with_slashes(self, mocker):
        resp = _make_mock_response({"name": "feature/my-feat", "commit": {}}, {})
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        get_branch_latest_commit("https://host.com", "ns%2Frepo", "feature/my-feat", "tok")

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert "feature%2Fmy-feat" in request_obj.full_url

    def test_returns_empty_dict_when_no_commit(self, mocker):
        resp = _make_mock_response({"name": "empty-branch"}, {})
        mocker.patch("urllib.request.urlopen", return_value=resp)

        result = get_branch_latest_commit("https://host.com", "ns%2Frepo", "empty-branch", "tok")
        assert result == {}


# ---------------------------------------------------------------------------
# search_commits
# ---------------------------------------------------------------------------

class TestSearchCommits:
    def test_returns_commits_and_page_info(self, mocker):
        commits_data = [
            {"id": "aaa", "title": "Add reward function"},
            {"id": "bbb", "title": "Update reward logic"},
        ]
        resp = _make_mock_response(
            commits_data,
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "2", "X-Total-Pages": "1"},
        )
        mocker.patch("urllib.request.urlopen", return_value=resp)

        result = search_commits("https://host.com", "ns%2Frepo", "tok", query="reward")
        assert len(result["commits"]) == 2
        assert result["commits"][0]["title"] == "Add reward function"

    def test_passes_search_query(self, mocker):
        resp = _make_mock_response(
            [],
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "0", "X-Total-Pages": "1"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        search_commits("https://host.com", "ns%2Frepo", "tok", query="fix bug")

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert "search=fix+bug" in request_obj.full_url or "search=fix%20bug" in request_obj.full_url

    def test_passes_ref_name(self, mocker):
        resp = _make_mock_response(
            [],
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "0", "X-Total-Pages": "1"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        search_commits("https://host.com", "ns%2Frepo", "tok", ref_name="main")

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert "ref_name=main" in request_obj.full_url

    def test_no_query_no_search_param(self, mocker):
        resp = _make_mock_response(
            [],
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "0", "X-Total-Pages": "1"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        search_commits("https://host.com", "ns%2Frepo", "tok")

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert "search" not in request_obj.full_url

    def test_pagination(self, mocker):
        resp = _make_mock_response(
            [],
            {"X-Page": "3", "X-Per-Page": "10", "X-Total": "25", "X-Total-Pages": "3"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        result = search_commits("https://host.com", "ns%2Frepo", "tok", page=3, per_page=10)

        assert result["page_info"]["page"] == 3
        assert result["page_info"]["total"] == 25

    def test_sets_private_token_header(self, mocker):
        resp = _make_mock_response(
            [],
            {"X-Page": "1", "X-Per-Page": "20", "X-Total": "0", "X-Total-Pages": "1"},
        )
        urlopen_mock = mocker.patch("urllib.request.urlopen", return_value=resp)

        search_commits("https://host.com", "ns%2Frepo", "my-secret-token")

        call_args = urlopen_mock.call_args
        request_obj = call_args[0][0]
        assert request_obj.get_header("Private-token") == "my-secret-token"
