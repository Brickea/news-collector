# Task Template P2 — Tracker

## 动态表单扩展（RL 场景）— 奖励函数控件

### 调研结论：Antcode API 接入方案

> 调研时间：2026-03-11  
> API 参考：https://yuque.antfin.com/antcode/help/common-api  
> Antcode 基于 GitLab CE 构建，API 风格与 GitLab API v4 高度一致。

---

#### API 认证

所有请求需在 Header 中携带访问令牌：

```
Private-Token: <your_access_token>
```

或通过 URL 参数传入：

```
?private_token=<your_access_token>
```

---

#### 场景 1：用户填写仓库 Git 地址后，分页查询 Branch

**接口：** `GET /api/v4/projects/{encoded_project_path}/repository/branches`

- `encoded_project_path`：将 `namespace/repo` 进行 URL 编码，如 `myteam%2Fmyrepo`
- 支持分页：`?page=1&per_page=20`
- 支持搜索过滤：`?search=feature`（按 branch 名称模糊匹配）

**响应示例：**
```json
[
  {
    "name": "main",
    "commit": {
      "id": "abc123",
      "short_id": "abc123",
      "message": "Initial commit",
      "author_name": "Alice",
      "authored_date": "2024-01-01T00:00:00.000+00:00"
    },
    "protected": true
  }
]
```

分页信息通过响应头获取：
- `X-Total`：总条数
- `X-Total-Pages`：总页数
- `X-Page`：当前页
- `X-Per-Page`：每页条数

---

#### 场景 2.1：选中 Branch 后查询该 Branch 最新 Commit 信息

**接口（方式一）：** 直接从 Branch 接口响应中读取 `commit` 字段（已包含最新 commit）

**接口（方式二）：** `GET /api/v4/projects/{encoded_project_path}/repository/branches/{branch_name}`

**接口（方式三）：** `GET /api/v4/projects/{encoded_project_path}/repository/commits?ref_name={branch}&per_page=1`

---

#### 场景 3：Commit 方式——模糊匹配 Commit 供用户选择

**接口：** `GET /api/v4/projects/{encoded_project_path}/repository/commits`

- 参数 `ref_name`：指定 branch（可选）
- 参数 `search`：按 commit message 模糊匹配
- 支持分页：`?page=1&per_page=20`

**响应示例：**
```json
[
  {
    "id": "abc123def456",
    "short_id": "abc123de",
    "title": "Fix reward function calculation",
    "message": "Fix reward function calculation\n\nDetailed description...",
    "author_name": "Bob",
    "authored_date": "2024-03-01T10:00:00.000+00:00"
  }
]
```

---

### 控件实现方案调整

**之前：** 控件支持三种奖励类型（内置奖励函数类型选择）

**调整后：** 控件直接支持用户指定代码仓库 + Branch 或 Commit 定位方式

#### 控件交互流程

```
1. 用户填写仓库地址
   └── 输入框：http://xxx.antfin.com/namespace/repo.git

2. 选择定位方式（单选）
   ├── Branch 方式
   │   ├── 分页展示 Branch 列表（支持搜索过滤）
   │   └── 选择 Branch 后，展示该 Branch 的最新 Commit 信息（只读）
   └── Commit 方式
       └── 输入搜索关键词，实时模糊匹配 Commit Message，选择目标 Commit
```

#### Python 实现模块

实现参见 [`src/git_repo_selector.py`](../../../../src/git_repo_selector.py)，提供以下功能：
- `parse_repo_url(git_url)` — 解析 Git HTTP 地址，提取 base_url 和 project_path
- `list_branches(...)` — 分页查询 Branch 列表
- `get_branch_latest_commit(...)` — 获取指定 Branch 的最新 Commit 信息
- `search_commits(...)` — 按关键词模糊搜索 Commit 列表

---

### 参考资料

- [GitLab Branches API](https://docs.gitlab.com/ee/api/branches.html)
- [GitLab Commits API](https://docs.gitlab.com/ee/api/commits.html)
- [Antcode 通用 API 文档](https://yuque.antfin.com/antcode/help/common-api)（内网）
