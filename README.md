# 即梦视频批量生成自动化工具

自动驱动即梦网页端按队列顺序生成视频。一次只处理一个任务，前一个视频生成完毕并下载后，才会提交下一个。

## 首次使用

### 1. 安装依赖

```bat
pip install -r requirements.txt
playwright install chromium
```

### 2. 双击 start.bat

弹出浏览器窗口后，手动扫码登录即梦账号。登录后关闭浏览器，再次双击 `start.bat` 即可进入自动模式。

### 3. 创建任务

在 `inputs/` 下新建任务文件夹，例如：

```
inputs/
└── 001/
    ├── ref1.jpg
    ├── ref2.jpg
    └── prompt.txt
```

`prompt.txt` 是 UTF-8 编码的纯文本，可以用 `@图片1` `@图片2` 引用参考图。

### 4. 编辑 queue.json

添加一条任务：

```json
{
  "id": "001",
  "references": ["inputs/001/ref1.jpg", "inputs/001/ref2.jpg"],
  "prompt_file": "inputs/001/prompt.txt",
  "params": {
    "model": "Seedance 2.0 Fast",
    "aspect_ratio": "9:16",
    "duration": "5s",
    "count": 1
  },
  "output": "outputs/001.mp4",
  "status": "pending"
}
```

### 5. 双击 start.bat 启动

程序会：
- 自动打开即梦
- 上传参考图、填写提示词、设置参数
- 点击生成、等待完成
- 下载视频到 `outputs/`
- 处理 `queue.json` 中的下一个任务

## 中断恢复

程序崩溃或主动关闭后，重新双击 `start.bat` 即可。已完成的任务不会重跑。

## 任务状态

| status | 含义 |
|--------|------|
| pending | 等待处理 |
| processing | 已提交到即梦 |
| downloading | 视频已生成，正在下载 |
| completed | 完成 |
| failed | 失败（重试超限） |

## 日志

每日运行日志在 `logs/run-YYYY-MM-DD.log`。

## 故障排查

**生成按钮始终灰色**：检查参数是否冲突（如模型不支持所选时长）、积分是否充足、提示词是否超长。

**下载失败**：先尝试 HTTP，失败后用 UI 兜底。连续失败 3 次标记为 failed。

**浏览器崩溃**：重启即可，`queue.json` 是 source of truth。

## 项目结构

```
jimeng-batch/
├── jimeng_automation.py    # 主程序入口
├── browser_driver.py       # Playwright 浏览器管理
├── jimeng_page.py          # 即梦页面交互
├── queue_manager.py        # 任务队列管理
├── video_downloader.py     # 视频下载
├── config_loader.py        # 配置加载
├── logger_setup.py         # 日志配置
├── models.py               # 数据模型
├── start.bat               # Windows 启动器
├── config.yaml             # 全局配置
├── requirements.txt
└── README.md
```