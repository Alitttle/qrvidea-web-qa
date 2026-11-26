# QRVidea Web 自动化测试框架

![web-qa](https://github.com/Alitttle/qrvidea-web-qa/actions/workflows/qa.yml/badge.svg)

面向**真实在线站点**的端到端自动化测试：Python + pytest + Playwright，覆盖多语言切换、手机端响应式菜单、FAQ 交互、iframe 正文渲染、匿名访客访问控制与视频播放状态。目标站点为 QRVidea（拉美市场的二维码内容发布平台）。

> 用例不是为了凑数：一次全量执行 15 条中 11 条通过、4 条失败，失败被定位到 2 个真实产品缺陷（见[已知缺陷](#已知缺陷)）。测试报告如实记录失败，比一片绿色更有价值。

## 技术栈

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.12 | 运行环境 |
| pytest | 8.4.2 | 用例组织、参数化、marker 分层 |
| pytest-playwright | 0.7.1 | 浏览器 fixture、截图/trace |
| Playwright | 1.56.0 | 浏览器驱动、自动等待、网络与媒体状态读取 |

## 目录结构

```
conftest.py                     # fixture：base_url 归一化、会话级 locale、移动端视口、测试视频地址校验
pytest.ini                      # 默认目标站点、marker 定义、失败截图
tests/
  test_public_site.py           # 首页锚点、多语言刷新保留、手机菜单、FAQ 展开/搜索、方案页正文
  test_guest_access.py          # 商家/审核入口的访客跳转、管理接口匿名鉴权
  test_guest_video.py           # 游客点击起播、拖动进度后继续播放
.github/workflows/qa.yml        # CI：提交跑稳定子集，定时/手动跑全量
```

## 快速开始

```bash
python -m venv .venv
```

```powershell
# Windows PowerShell
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m playwright install chromium
.venv\Scripts\python -m pytest
```

```bash
# macOS / Linux
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest
```

换目标站点：`--base-url https://your-staging.example.com`（默认值在 `pytest.ini`）。
想用本机 Chrome 而不是下载 Chromium，加 `--browser-channel chrome`。

播放用例需要一段**已获授权**的公开测试视频，未设置时两条用例会 skip 而不是失败：

```powershell
$env:QRVIDEA_QA_VIDEO_URL = 'https://videa.qrveo.com/watch/videos/测试视频ID'
$env:QRVIDEA_QA_VIDEO_TITLE = '测试视频标题'   # 可选，用于校验页面标题
```

## 分层执行

`--strict-markers` 已开启，marker 写错会直接报错，避免"以为筛过了其实全跑了"。

| 命令 | 条数 | 最近结果 | 说明 |
| --- | ---: | --- | --- |
| `pytest -m smoke` | 6 | 6 通过 | 首页、多语言、手机菜单、FAQ，不依赖额外数据 |
| `pytest -m security` | 4 | 4 通过 | 匿名访问控制与接口鉴权 |
| `pytest -m solutions` | 3 | 0 通过 | 方案页正文，命中已知缺陷 |
| `pytest -m media` | 2 | 1 通过 | 需要 `QRVIDEA_QA_VIDEO_URL` |

## 设计取舍

1. **断言落在行为上，不落在元素存在上**：`aria-expanded` 的真实翻转、`scrollWidth <= innerWidth` 判定无横向溢出、`video.currentTime / paused / readyState / seeking` 判定播放推进，而不是"按钮可见"。
2. **不写 sleep**：等待交给 Playwright 的自动重试（`expect`）和 `wait_for_function` 轮询，超时才失败并打印现场状态。
3. **用例之间互不污染**：每条用例独立浏览器上下文，语言选择和匿名身份不会串味；移动端用 `390x844 + is_mobile + has_touch` 模拟触屏视口。
4. **失败可诊断**：播放用例超时会 dump `currentTime/duration/readyState/error`；方案页用例额外收集浏览器 console 里的 `frame-src` 报错——外层页面 200 但 iframe 被拦时，能直接指到 CSP 而不是只说"元素没出现"。
5. **不污染生产数据**：全程匿名只读操作，不上传、不写库；播放使用授权测试片，地址走环境变量，不进仓库。
6. **参数化代替复制粘贴**：两种语言、三个方案页、两个后台接口共用一套逻辑。

## 最近一次线上执行

2026-11-20，Python 3.12 / pytest 8.4.2 / Playwright 1.56.0，本机 Chrome 访问线上站点 + 一段 12 秒授权测试视频。

| 模块 | 条数 | 通过 | 失败 |
| --- | ---: | ---: | ---: |
| 官网导航、多语言、FAQ、iframe 正文 | 9 | 6 | 3 |
| 入口跳转、访客接口鉴权 | 4 | 4 | 0 |
| 移动端起播、进度跳转 | 2 | 1 | 1 |
| **合计** | **15** | **11** | **4** |

## 已知缺陷

1. **方案页正文被 CSP 拦截**（`/plans`、`/trial`、`/cases`）：外层页面 200，正文在 `#solution-page-frame` 内，浏览器报同一类 `frame-src` 违规。三条用例分别复测，归因为同一个产品缺陷。
2. **移动端首次点击播放停在 0 秒**：等待 `readyState >= 2` 后再点可正常起播。已用专项用例验证 seek 与续播，冷启动仍需真机复核。

## CI

`.github/workflows/qa.yml`：

- `push` / `pull_request`：只跑 `smoke or security`（当前全绿），避免已知产品缺陷把每次提交变红。
- `schedule`（每周一 09:00 UTC+8）/ `workflow_dispatch`：跑全量，保留失败截图与 trace，用来观察缺陷是否修复。
- 视频地址通过仓库变量 `QRVIDEA_QA_VIDEO_URL` 注入，不写入代码。

## Roadmap

- [ ] 方案页 `frame-src` 修复后，把 `solutions` 并入 push 门禁
- [ ] 引入 axe-core 做关键页可访问性冒烟
- [ ] 关键区块视觉回归（截图比对）
- [ ] 用例超过 30 条时再引入 Page Object 收敛选择器（现在抽 helper 更划算）

## English

An end-to-end test suite for a live production site, built with Python, pytest and Playwright. It covers locale switching persistence, a simulated 390×844 touch viewport, FAQ interactions, iframe-hosted solution pages, anonymous access control on merchant/reviewer routes and media playback state (`currentTime`, `seeked`, `readyState`). Failures are attributed to product defects with browser console evidence rather than retried away. MIT licensed.

## License

[MIT](LICENSE)
