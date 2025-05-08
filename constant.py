"""
WordCloud插件常量定义
"""
import os
from pathlib import Path

# 插件信息
PLUGIN_NAME = "wordcloud"
PLUGIN_AUTHOR = "GEMILUXVII"
PLUGIN_DESC = "词云插件 (WordCloud) 是一个文本可视化工具，能将聊天记录关键词以词云形式展现，支持定时或手动生成。"
PLUGIN_VERSION = "1.0.0"
PLUGIN_REPO = "https://github.com/GEMILUXVII/astrbot_plugin_wordcloud"

# 路径常量
PLUGIN_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# DATA_DIR通过StarTools.get_data_dir动态获取
# 这里只是定义一个占位变量，真正的目录会在初始化时设置
# 正确的数据目录应该是：data/plugin_data/wordcloud
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

# 默认停用词列表
DEFAULT_STOPWORDS = [
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", 
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", 
    "着", "没有", "看", "好", "自己", "这", "the", "and", "to", "of", 
    "a", "is", "in", "it", "that", "for", "on", "with", "as", "be", 
    "at", "this", "have", "from", "by", "was", "are", "or", "an", 
    "I", "but", "not", "you", "he", "they", "she", "we"
] 