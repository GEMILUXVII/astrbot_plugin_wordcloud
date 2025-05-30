"""
CloudRank插件常量定义
"""

import os
from pathlib import Path

# 插件信息
PLUGIN_NAME = "cloudrank"
PLUGIN_AUTHOR = "GEMILUXVII"
PLUGIN_DESC = "词云与排名插件 (CloudRank) 是一个文本可视化工具，能将聊天记录关键词以词云形式展现，并显示用户活跃度排行榜，支持定时或手动生成。"
PLUGIN_VERSION = "1.3.8-rev1"
PLUGIN_REPO = "https://github.com/GEMILUXVII/astrbot_plugin_cloudrank"

# 路径常量
PLUGIN_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# DATA_DIR通过StarTools.get_data_dir动态获取
# 这里只是定义一个占位变量，真正的目录会在初始化时设置
# 正确的数据目录应该是：data/plugin_data/cloudrank
DATA_DIR = None  # 由主模块初始化

# 词云生成常量
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 400
DEFAULT_MAX_WORDS = 200
DEFAULT_BACKGROUND_COLOR = "white"
DEFAULT_COLORMAP = "viridis"
DEFAULT_MIN_WORD_LENGTH = 2

# 命令常量
CMD_GENERATE = "wordcloud"
CMD_GROUP = "wc"
CMD_CONFIG = "config"
CMD_HELP = "help"

# 自然语言关键词 - 用于触发命令的关键词
# 格式: {"command": ["关键词1", "关键词2", ...]}
NATURAL_KEYWORDS = {
    "today": ["今日词云", "获取今日词云", "查看今日词云", "生成今日词云"],
    "wordcloud": ["生成词云", "查看词云", "最近词云", "历史词云"],
    "help": ["词云帮助", "词云功能", "词云说明", "词云指令"],
}

# 默认停用词列表
DEFAULT_STOPWORDS = [
    "的",
    "了",
    "在",
    "是",
    "我",
    "有",
    "和",
    "就",
    "不",
    "人",
    "都",
    "一",
    "一个",
    "上",
    "也",
    "很",
    "到",
    "说",
    "要",
    "去",
    "你",
    "会",
    "着",
    "没有",
    "看",
    "好",
    "自己",
    "这",
    "the",
    "and",
    "to",
    "of",
    "a",
    "is",
    "in",
    "it",
    "that",
    "for",
    "on",
    "with",
    "as",
    "be",
    "at",
    "this",
    "have",
    "from",
    "by",
    "was",
    "are",
    "or",
    "an",
    "I",
    "but",
    "not",
    "you",
    "he",
    "they",
    "she",
    "we",
]
