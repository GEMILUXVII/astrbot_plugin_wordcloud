# <div align="center">📊 AstrBot 词云插件 (WordCloud)</div>

<p align="center">
  <a href="https://github.com/YourName/astrbot_plugin_wordcloud/releases">
    <img src="https://img.shields.io/github/v/release/YourName/astrbot_plugin_wordcloud?color=blueviolet&include_prereleases&label=version&style=flat-square">
  </a>
  <a href="https://github.com/YourName/astrbot_plugin_wordcloud/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/YourName/astrbot_plugin_wordcloud?color=blue&style=flat-square">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square">
</p>

## 📝 介绍

AstrBot词云插件是一个功能强大的文本可视化工具，能够将聊天记录中的关键词以词云的形式展现。支持定时自动生成和手动请求，让你轻松了解会话中的热门话题。

## ✨ 功能特性

- 🕒 **定时生成词云**：根据配置的时间，自动为活跃会话生成词云图片
- 📊 **手动请求词云**：随时随地查看指定天数的聊天词云
- 🔄 **自动记录消息**：自动保存聊天记录用于词云生成
- ⚙️ **高度可配置**：自定义词云颜色、字体、过滤规则等
- 🧹 **停用词过滤**：内置中英文停用词列表，过滤无意义的高频词

## 🚀 安装方法

### 方法一：直接下载

1. 下载本仓库所有文件
2. 将所有文件放入`AstrBot/data/plugins/wordcloud`目录
3. 安装依赖：`pip install -r requirements.txt`
4. 重启AstrBot

### 方法二：使用git克隆

```bash
cd AstrBot/data/plugins/
git clone https://github.com/YourName/astrbot_plugin_wordcloud.git wordcloud
cd wordcloud
pip install -r requirements.txt
```

## 📋 使用指南

### 命令列表

| 命令 | 描述 | 参数 |
|------|------|------|
| `/wordcloud` | 生成当前会话的词云 | 可选：统计天数（默认为配置值） |
| `/wordcloud 3` | 生成最近3天的聊天词云 | `days`：要统计的天数 |
| `/wc config` | 查看当前词云插件配置 | 无 |
| `/wc help` | 显示帮助信息 | 无 |

### 配置说明

插件通过`_conf_schema.json`文件进行配置，你可以在AstrBot后台的插件配置页面修改这些设置：

| 配置项 | 类型 | 描述 | 默认值 |
|-------|------|------|-------|
| `auto_generate_enabled` | 布尔值 | 是否启用自动生成词云功能 | `true` |
| `auto_generate_cron` | 字符串 | 自动生成词云的cron表达式 | `0 0 20 * * *`（每天晚上8点） |
| `min_word_length` | 整数 | 词云中最小词语长度 | `2` |
| `max_word_count` | 整数 | 词云中显示的最大词语数量 | `100` |
| `history_days` | 整数 | 默认统计的历史消息天数 | `7` |
| `stop_words_file` | 字符串 | 停用词文件路径 | `stop_words.txt` |
| `background_color` | 字符串 | 词云背景颜色 | `white` |
| `colormap` | 字符串 | 词云颜色方案 | `viridis` |
| `font_path` | 字符串 | 自定义字体文件路径 | `""` |

## 📊 词云样例

![词云样例](https://example.com/wordcloud_sample.png)

## 🧩 项目结构

```
wordcloud/
├── data/                     # 数据目录
│   └── stop_words.txt        # 停用词列表
├── wordcloud_core/           # 核心模块
│   ├── generator.py          # 词云生成器
│   ├── history_manager.py    # 历史记录管理
│   └── scheduler.py          # 定时任务调度
├── _conf_schema.json         # 配置模式定义
├── constant.py               # 常量定义
├── main.py                   # 插件主类
├── metadata.yaml             # 插件元数据
├── requirements.txt          # 依赖列表
├── README.md                 # 说明文档
└── utils.py                  # 工具函数
```

## 📢 注意事项

- 首次使用词云命令可能需要等待几秒钟，因为需要加载jieba分词库
- 如需使用中文字体，请在配置中指定`font_path`为系统中可用的中文字体
- 插件会自动创建数据库表存储历史消息，请确保AstrBot有足够的存储空间
- 如需自定义更多停用词，可编辑`data/stop_words.txt`文件

## 📝 版本历史

### V1.0.0 (2023.05.20)
- 初始版本发布
- 支持定时和手动生成聊天词云
- 完整的配置系统
- 中英文分词支持
- 停用词过滤

## 🔧 问题排查

如果遇到问题，请检查：

1. 是否已安装所有依赖（`pip install -r requirements.txt`）
2. Python版本是否 >= 3.8
3. 检查AstrBot日志中的错误信息
4. 确保插件有足够的权限访问和创建文件

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)
