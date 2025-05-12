"""
词云插件工具函数
"""

import os
import time
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

import jieba
from astrbot.api import logger
from astrbot.api.star import StarTools

from .constant import DATA_DIR, DEFAULT_STOPWORDS


def ensure_directory(path: Path) -> None:
    """确保目录存在"""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {path}")


def get_current_timestamp() -> int:
    """获取当前时间戳"""
    return int(time.time())


def format_timestamp(timestamp: int) -> str:
    """格式化时间戳为可读字符串"""
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d_%H-%M-%S")


def format_date(timestamp: Optional[int] = None) -> str:
    """格式化时间戳为日期字符串"""
    if timestamp is None:
        timestamp = get_current_timestamp()
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y年%m月%d日")


def parse_time_str(time_str: str) -> Tuple[int, int]:
    """
    解析时间字符串为小时和分钟
    格式为 HH:MM，例如 23:30

    Args:
        time_str: 时间字符串，如 "23:30"

    Returns:
        小时和分钟的元组，如 (23, 30)

    Raises:
        ValueError: 如果时间格式无效
    """
    try:
        hour, minute = time_str.split(":")
        hour = int(hour.strip())
        minute = int(minute.strip())

        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError(f"无效的时间值: {hour}:{minute}")

        return hour, minute
    except Exception as e:
        logger.error(f"解析时间字符串失败 '{time_str}': {e}")
        # 默认返回晚上11:30
        return 23, 30


def time_str_to_cron(time_str: str) -> str:
    """
    将时间字符串转换为cron表达式

    Args:
        time_str: 格式为HH:MM的时间字符串，如 "23:30"

    Returns:
        cron表达式，如 "30 23 * * *"
    """
    try:
        # 去除可能的空白字符
        time_str = time_str.strip()

        # 验证时间格式
        if ":" not in time_str:
            logger.error(f"时间格式错误 '{time_str}': 缺少冒号分隔符")
            return "0 0 * * *"  # 默认午夜执行

        # 分割小时和分钟
        try:
            hour_str, minute_str = time_str.split(":")
            hour = int(hour_str.strip())
            minute = int(minute_str.strip())

            # 验证小时和分钟范围
            if not (0 <= hour < 24):
                logger.error(f"小时值超出范围: {hour}")
                hour = 0  # 修正为有效值

            if not (0 <= minute < 60):
                logger.error(f"分钟值超出范围: {minute}")
                minute = 0  # 修正为有效值

        except ValueError:
            logger.error(f"无法解析时间字符串: '{time_str}'")
            return "0 0 * * *"  # 默认午夜执行

        # 检查时区问题 - 中国是UTC+8，如果系统可能在内部使用UTC时间
        import time

        timezone_offset = -time.timezone // 3600  # 获取本地时区偏移（小时）
        logger.info(
            f"系统时区信息: UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}"
        )

        # 如果是UTC时区而不是本地时区，需调整
        if timezone_offset != 0:
            logger.info(
                f"检测到时区差异，将调整时间从本地时间 {hour:02d}:{minute:02d} 到cron时间"
            )

        # 构建cron表达式 - 标准cron格式为：分 时 日 月 周
        # 我们直接使用本地时间，不进行时区转换，让croniter基于本地时间处理
        cron_expression = f"{minute} {hour} * * *"
        logger.info(f"时间字符串 '{time_str}' 已转换为cron表达式: '{cron_expression}'")

        # 验证cron表达式格式
        try:
            from croniter import croniter

            if not croniter.is_valid(cron_expression):
                logger.error(f"生成的cron表达式无效: '{cron_expression}'")
                return "0 0 * * *"  # 默认午夜执行

            # 附加检查：计算下一个执行时间，确保表达式可以正确工作
            import datetime

            base = datetime.datetime.now()
            cron = croniter(cron_expression, base)
            next_run = cron.get_next(datetime.datetime)

            # 输出下次执行的本地时间，方便验证
            local_next_run = next_run
            logger.info(
                f"使用cron表达式 '{cron_expression}' 计算的下次执行时间: {local_next_run.strftime('%Y-%m-%d %H:%M:%S')} (本地时间)"
            )

        except Exception as croniter_error:
            logger.error(f"cron表达式验证失败: {croniter_error}")
            return "0 0 * * *"  # 默认午夜执行

        return cron_expression
    except Exception as e:
        logger.error(f"转换时间字符串到cron表达式失败 '{time_str}': {e}")
        import traceback

        logger.error(f"转换错误详情: {traceback.format_exc()}")
        return "0 0 * * *"  # 默认午夜执行


def parse_group_list(group_list_str: str) -> Set[str]:
    """
    解析群列表字符串为群号集合

    Args:
        group_list_str: 以逗号分隔的群号字符串，如 "123456789,987654321"

    Returns:
        群号的集合
    """
    if not group_list_str or not group_list_str.strip():
        return set()

    # 分割并去除空白
    groups = set()
    for group_id in group_list_str.split(","):
        group_id = group_id.strip()
        if group_id:
            groups.add(group_id)

    return groups


def is_group_enabled(group_id: str, enabled_groups: Set[str]) -> bool:
    """
    检查群是否启用词云功能

    Args:
        group_id: 群ID
        enabled_groups: 启用词云的群集合，空集合表示全部启用

    Returns:
        群是否启用词云功能
    """
    # 输入类型验证，确保group_id是字符串
    if not isinstance(group_id, str):
        try:
            group_id = str(group_id)
        except:
            # 如果转换失败，默认不启用
            logger.warning(f"群ID类型错误: {type(group_id)}，无法判断群聊是否启用")
            return False

    # 如果启用列表为空，表示没有群被特别指定启用，因此默认不启用此群
    if not enabled_groups:
        logger.debug(f"启用群列表为空，群 {group_id} 未在指定启用列表中，默认不启用。")
        return False

    # 否则，检查是否在启用列表中
    result = group_id in enabled_groups
    logger.debug(f"群 {group_id} {'在' if result else '不在'}启用列表中")
    return result


def get_day_start_end_timestamps() -> Tuple[int, int]:
    """
    获取今天的开始和结束时间戳

    Returns:
        (开始时间戳, 结束时间戳)的元组
    """
    now = datetime.datetime.now()
    start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)

    return int(start_of_day.timestamp()), int(end_of_day.timestamp())


def get_image_path(session_id: str, timestamp: Optional[int] = None) -> Path:
    """获取词云图片存储路径"""
    if timestamp is None:
        timestamp = get_current_timestamp()

    # 使用会话ID作为目录名，避免不同会话的图片混淆
    safe_session_id = session_id.replace("/", "_").replace(":", "_")

    # 确保DATA_DIR已经初始化
    if DATA_DIR is None:
        # 尝试通过StarTools获取数据目录
        try:
            from .constant import PLUGIN_NAME

            data_dir = StarTools.get_data_dir(PLUGIN_NAME)
            logger.info(f"通过StarTools获取数据目录: {data_dir}")
        except Exception as e:
            # 使用临时目录作为备用
            from pathlib import Path

            data_dir = Path(__file__).parent / "temp_data"
            data_dir.mkdir(exist_ok=True)
            logger.warning(
                f"DATA_DIR未初始化且无法通过StarTools获取，使用临时目录存储图片: {data_dir}"
            )
    else:
        data_dir = DATA_DIR

    # 在数据目录下创建images子目录
    images_dir = data_dir / "images"
    ensure_directory(images_dir)

    # 在images目录下为每个会话创建子目录
    session_dir = images_dir / safe_session_id
    ensure_directory(session_dir)

    # 生成图片路径
    image_path = session_dir / f"wordcloud_{format_timestamp(timestamp)}.png"
    return image_path


def get_daily_image_path(session_id: str, date: Optional[datetime.date] = None) -> Path:
    """
    获取每日词云图片存储路径

    Args:
        session_id: 会话ID
        date: 日期，默认为今天

    Returns:
        图片路径
    """
    if date is None:
        date = datetime.date.today()

    # 使用会话ID作为目录名，避免不同会话的图片混淆
    safe_session_id = session_id.replace("/", "_").replace(":", "_")

    # 确保DATA_DIR已经初始化
    if DATA_DIR is None:
        # 尝试通过StarTools获取数据目录
        try:
            from .constant import PLUGIN_NAME

            data_dir = StarTools.get_data_dir(PLUGIN_NAME)
            logger.info(f"通过StarTools获取数据目录: {data_dir}")
        except Exception as e:
            # 使用临时目录作为备用
            from pathlib import Path

            data_dir = Path(__file__).parent / "temp_data"
            data_dir.mkdir(exist_ok=True)
            logger.warning(
                f"DATA_DIR未初始化且无法通过StarTools获取，使用临时目录存储图片: {data_dir}"
            )
    else:
        data_dir = DATA_DIR

    # 在数据目录下创建daily_images子目录
    images_dir = data_dir / "daily_images"
    ensure_directory(images_dir)

    # 在daily_images目录下为每个会话创建子目录
    session_dir = images_dir / safe_session_id
    ensure_directory(session_dir)

    # 生成图片路径，使用日期作为文件名
    date_str = date.strftime("%Y-%m-%d")
    image_path = session_dir / f"daily_wordcloud_{date_str}.png"
    return image_path


def segment_text(
    text: str, min_length: int = 2, stop_words: Optional[List[str]] = None
) -> List[str]:
    """
    使用jieba进行中文分词

    Args:
        text: 需要分词的文本
        min_length: 最小词长度
        stop_words: 停用词列表

    Returns:
        分词后的词语列表
    """
    if stop_words is None:
        stop_words = DEFAULT_STOPWORDS

    # 使用jieba进行分词
    words = jieba.lcut(text)

    # 过滤停用词和短词
    filtered_words = []
    for word in words:
        if (
            len(word.strip()) >= min_length
            and word not in stop_words
            and not word.isdigit()  # 过滤纯数字
            and not all(c.isascii() and not c.isalpha() for c in word)  # 过滤纯符号
        ):
            filtered_words.append(word)

    return filtered_words


def load_stop_words(file_path: Optional[str] = None) -> List[str]:
    """
    从文件加载停用词

    Args:
        file_path: 停用词文件路径

    Returns:
        停用词列表，如果文件不存在则返回默认停用词
    """
    stop_words = DEFAULT_STOPWORDS.copy()
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word and word not in stop_words:
                        stop_words.append(word)
        except Exception as e:
            logger.error(f"加载停用词文件失败: {e}")

    return stop_words


def extract_group_id_from_session(session_id: str) -> Optional[str]:
    """
    从会话ID中提取群号，支持多种格式

    Args:
        session_id: 会话ID，支持多种格式:
                   - "aiocqhttp:GroupMessage:123456789"
                   - "aiocqhttp:GroupMessage:0_123456789"
                   - "qqofficial:group:123456789"
                   - "aiocqhttp_group_123456789"
                   - "123456789"（纯群号）
                   - 其他可能的格式

    Returns:
        群号，如果不是群消息则返回None
    """
    try:
        if not session_id:
            logger.warning("会话ID为空，无法提取群号")
            return None

        # 处理会话ID为纯数字的情况
        if isinstance(session_id, str) and session_id.isdigit():
            logger.debug(f"会话ID是纯数字，直接作为群号: {session_id}")
            return session_id

        # 处理 "platform_group_groupid" 格式 (例如 "aiocqhttp_group_142443871")
        if isinstance(session_id, str) and "_group_" in session_id:
            parts = session_id.split("_group_")
            if len(parts) == 2 and parts[1].isdigit():
                logger.debug(
                    f"从下划线分隔的会话ID '{session_id}' 提取到群号: {parts[1]}"
                )
                return parts[1]

        # 处理复杂格式会话ID
        if isinstance(session_id, str) and ":" in session_id:
            parts = session_id.split(":")

            # 1. 标准三段式QQ格式: [平台]:[类型]:[群号]
            if len(parts) >= 3:
                # 检查中间部分是否包含群聊关键词
                middle_part = parts[1].lower()
                if (
                    "group" in middle_part
                    or "群" in middle_part
                    or "multi" in middle_part
                    or "channel" in middle_part
                ):
                    # 提取第三部分作为群号
                    third_part = parts[2]

                    # 处理可能包含前缀的情况，如 "0_123456789"
                    if "_" in third_part:
                        group_id = third_part.split("_")[-1]
                    else:
                        group_id = third_part

                    if group_id.isdigit():
                        logger.debug(
                            f"从三段式会话ID '{session_id}' 提取到群号: {group_id}"
                        )
                        return group_id

            # 2. 从会话ID的各部分中寻找可能的群号，优先选择最后一部分
            for i in range(len(parts) - 1, -1, -1):  # 从后向前查找
                part = parts[i]

                # 处理可能包含前缀的情况，如 "0_123456789"
                if "_" in part:
                    potential_id = part.split("_")[-1]
                else:
                    potential_id = part

                if potential_id.isdigit() and len(potential_id) >= 5:  # 群号通常至少5位
                    logger.debug(
                        f"从会话ID '{session_id}' 的第{i + 1}部分提取到可能的群号: {potential_id}"
                    )
                    return potential_id

        # 使用正则表达式提取会话ID中的任何数字序列
        import re

        # 匹配连续5位及以上的数字（可能的群号）
        matches = re.findall(r"\d{5,}", str(session_id))
        if matches:
            # 找出最长的数字串
            longest_match = max(matches, key=len)
            logger.debug(
                f"使用正则表达式从会话ID '{session_id}' 提取到可能的群号: {longest_match}"
            )
            return longest_match

        logger.warning(f"无法从会话ID '{session_id}' 提取群号")
        return None
    except Exception as e:
        logger.error(f"提取群号时出错: {e}")
        import traceback

        logger.error(f"提取群号错误详情: {traceback.format_exc()}")
        return None
