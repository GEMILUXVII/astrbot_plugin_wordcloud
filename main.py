"""
AstrBot 词云生成插件
"""

import os
import time
import datetime
import traceback
import asyncio
from pathlib import Path

from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.api.star import Star, Context, register, StarTools
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType
import astrbot.api.message_components as Comp

from .constant import (
    PLUGIN_NAME,
    CMD_GENERATE,
    CMD_GROUP,
    CMD_CONFIG,
    CMD_HELP,
    NATURAL_KEYWORDS,
)
from .utils import (
    format_date,
    time_str_to_cron,
    parse_group_list,
    is_group_enabled,
    parse_time_str,
    extract_group_id_from_session,
)
from .wordcloud_core.generator import WordCloudGenerator
from .wordcloud_core.history_manager import HistoryManager
from .wordcloud_core.scheduler import TaskScheduler

# 导入常量模块以便修改DATA_DIR
from . import constant as constant_module


@register(
    "CloudRank",
    "GEMILUXVII",
    "词云与排名插件 (CloudRank) 是一个文本可视化工具，能将聊天记录关键词以词云形式展现，并显示用户活跃度排行榜，支持定时或手动生成。",
    "1.3.8",
    "https://github.com/GEMILUXVII/astrbot_plugin_cloudrank",
)
class WordCloudPlugin(Star):
    """AstrBot 词云生成插件"""

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config

        logger.info("正在初始化词云插件...")

        # --- 读取调试模式配置 ---
        self.debug_mode = self.config.get("debug_mode", False)
        if self.debug_mode:
            logger.warning("WordCloud插件调试模式已启用，将输出详细日志。")
        # -----------------------

        # --- 读取时区配置 ---
        self.timezone_str = self.config.get("timezone", "Asia/Shanghai")
        try:
            import pytz

            self.timezone = pytz.timezone(self.timezone_str)
            logger.info(f"WordCloud插件已加载时区设置: {self.timezone_str}")
        except Exception as e:
            logger.error(
                f"加载时区 '{self.timezone_str}' 失败: {e}，将使用默认UTC时区。"
            )
            import pytz

            self.timezone = pytz.utc
            self.timezone_str = "UTC"
        # --------------------

        # --- 获取主事件循环 ---
        try:
            self.main_loop = asyncio.get_running_loop()
            logger.info(
                f"WordCloudPlugin: Successfully got running main loop ID: {id(self.main_loop)}"
            )
        except RuntimeError:
            logger.warning(
                "WordCloudPlugin: No running loop found via get_running_loop(), trying get_event_loop()."
            )
            self.main_loop = asyncio.get_event_loop()
            logger.info(
                f"WordCloudPlugin: Got loop via get_event_loop() ID: {id(self.main_loop)}"
            )

        # 设置数据目录为AstrBot官方推荐的数据存储路径
        # 通过StarTools获取官方数据存储路径
        try:
            data_dir = StarTools.get_data_dir(PLUGIN_NAME)
            logger.info(f"词云插件数据目录: {data_dir}")

            # 修改常量模块中的DATA_DIR
            constant_module.DATA_DIR = data_dir
            # 确保目录存在
            data_dir.mkdir(parents=True, exist_ok=True)

            # 确保资源目录存在并复制必要的资源文件
            self._ensure_resource_files(data_dir)
        except Exception as e:
            logger.error(f"设置数据目录失败: {e}")
            # 创建临时目录作为备用
            fallback_dir = Path(__file__).parent / "temp_data"
            fallback_dir.mkdir(exist_ok=True)
            constant_module.DATA_DIR = fallback_dir
            logger.warning(f"使用临时目录作为备用: {fallback_dir}")

            # 同样为临时目录准备资源文件
            self._ensure_resource_files(fallback_dir)

        # 加载群聊配置
        self.enabled_groups = set()
        self._load_group_configs()

        # 现在可以初始化历史记录管理器
        self.history_manager = HistoryManager(context)
        logger.info("历史记录管理器初始化完成")

        # --- 将主循环和调试模式传递给 Scheduler ---
        self.scheduler = TaskScheduler(
            context,
            main_loop=self.main_loop,
            debug_mode=self.debug_mode,
            timezone=self.timezone,
        )
        # -----------------------------------------
        logger.info("任务调度器初始化完成")

        # 初始化词云生成器变量，确保不为None
        self.wordcloud_generator = None

        # 尝试直接初始化词云生成器
        try:
            self._init_wordcloud_generator()
        except Exception as e:
            logger.error(f"词云生成器初始化失败: {e}")
            # 创建一个最基本的词云生成器作为备用
            try:
                from .wordcloud_core.generator import WordCloudGenerator

                self.wordcloud_generator = WordCloudGenerator()
                logger.warning("使用默认配置创建了备用词云生成器")
            except Exception as backup_error:
                logger.error(f"创建备用词云生成器也失败了: {backup_error}")

        # 立即执行初始化
        asyncio.create_task(self.initialize())

    def _get_astrbot_sendable_session_id(self, internal_db_session_id: str) -> str:
        """将插件内部数据库使用的 session_id 转换为 AstrBot 发送消息时可接受的格式"""
        if not internal_db_session_id:
            logger.error("尝试转换空的 internal_db_session_id")
            return ""

        # 检查是否已经是 AstrBot 的标准格式 (包含':')
        if ":" in internal_db_session_id:
            # 可能是私聊ID (e.g., "qq:private:12345") 或其他已正确格式化的ID
            return internal_db_session_id

        # 尝试解析 "platform_group_groupid" 格式, e.g., "aiocqhttp_group_142443871"
        parts = internal_db_session_id.split("_group_", 1)
        if len(parts) == 2:
            platform_name = parts[0]
            group_id_val = parts[1]
            if platform_name and group_id_val:
                # 对微信平台不加0_
                if platform_name.startswith("wechat"):
                    return f"{platform_name}:GroupMessage:{group_id_val}"
                else:
                    return f"{platform_name}:GroupMessage:0_{group_id_val}"

        logger.warning(
            f"无法将内部 session ID '{internal_db_session_id}' 转换为 AstrBot 发送格式。将按原样使用。"
        )
        return internal_db_session_id

    def _ensure_resource_files(self, data_dir: Path) -> None:
        """
        确保数据目录中存在必要的资源文件，如字体和停用词文件
        如果文件不存在，从插件目录复制

        Args:
            data_dir: 数据目录路径
        """
        try:
            # 创建必要的子目录
            resources_dir = data_dir / "resources"
            resources_dir.mkdir(exist_ok=True)

            # 创建字体目录
            fonts_dir = resources_dir / "fonts"
            fonts_dir.mkdir(exist_ok=True)

            # 创建用于存放自定义蒙版图片的目录 (在resources下)
            custom_masks_dir = resources_dir / "images"
            custom_masks_dir.mkdir(exist_ok=True)

            # 创建图片目录 (这个是用于存放生成的词云图，在数据目录顶层)
            output_images_dir = data_dir / "images"
            output_images_dir.mkdir(exist_ok=True)

            # 创建调试目录
            debug_dir = data_dir / "debug"
            debug_dir.mkdir(exist_ok=True)

            # 复制字体文件
            plugin_font_path = (
                constant_module.PLUGIN_DIR / "fonts" / "LXGWWenKai-Regular.ttf"
            )
            data_font_path = fonts_dir / "LXGWWenKai-Regular.ttf"

            if plugin_font_path.exists() and not data_font_path.exists():
                import shutil

                shutil.copy(plugin_font_path, data_font_path)
                logger.info(f"已复制字体文件到数据目录: {data_font_path}")

            # 复制停用词文件
            plugin_stopwords_path = constant_module.PLUGIN_DIR / "stop_words.txt"
            data_stopwords_path = resources_dir / "stop_words.txt"

            if plugin_stopwords_path.exists() and not data_stopwords_path.exists():
                import shutil

                shutil.copy(plugin_stopwords_path, data_stopwords_path)
                logger.info(f"已复制停用词文件到数据目录: {data_stopwords_path}")

            # 如果字体文件和停用词文件都不存在，创建基本的文件确保插件仍能工作
            if not data_font_path.exists() and not plugin_font_path.exists():
                logger.warning("找不到字体文件，将使用系统默认字体")

            if not data_stopwords_path.exists() and not plugin_stopwords_path.exists():
                # 创建一个基本的停用词文件
                with open(data_stopwords_path, "w", encoding="utf-8") as f:
                    f.write("的\n了\n我\n你\n在\n是\n有\n和\n就\n不")
                logger.info(f"已创建基本停用词文件: {data_stopwords_path}")

        except Exception as e:
            logger.error(f"准备资源文件时出错: {e}")
            import traceback

            logger.error(f"错误详情: {traceback.format_exc()}")

    def _load_group_configs(self) -> None:
        """加载群聊配置"""
        try:
            # 获取启用的群列表
            enabled_groups_str = self.config.get("enabled_group_list", "")
            self.enabled_groups = parse_group_list(enabled_groups_str)

            logger.info(f"词云功能已启用的群数量: {len(self.enabled_groups)}")
            if not self.enabled_groups:
                logger.info("未指定启用群列表，所有群都会启用词云功能")
        except Exception as e:
            logger.error(f"加载群聊配置失败: {e}")
            # 设置为空集合，表示默认全部启用
            self.enabled_groups = set()

    async def initialize(self):
        """初始化插件"""
        try:
            # 如果之前初始化失败，再次尝试初始化词云生成器
            if self.wordcloud_generator is None:
                logger.info("开始初始化词云生成器...")
                # 初始化词云生成器
                self._init_wordcloud_generator()

            logger.info("设置定时任务...")
            # 设置并启动定时任务
            self._setup_scheduled_tasks()

            # 输出状态信息
            try:
                active_sessions = self.history_manager.get_active_sessions()
                session_info = []
                for session_id in active_sessions:
                    msg_count = len(self.history_manager.get_message_texts(session_id))
                    session_info.append(f"会话 {session_id}: {msg_count}条消息")

                if session_info:
                    logger.debug(f"已有历史消息统计: {', '.join(session_info)}")
                else:
                    logger.debug("暂无历史消息记录")
            except Exception as e:
                logger.error(f"获取历史消息统计失败: {e}")

            logger.info("WordCloud插件初始化完成")
        except Exception as e:
            logger.error(f"WordCloud插件初始化失败: {e}")
            # 尝试记录详细的堆栈跟踪
            import traceback

            logger.error(f"错误详情: {traceback.format_exc()}")

    def _init_wordcloud_generator(self):
        """初始化词云生成器"""
        # 确保DATA_DIR已初始化
        if constant_module.DATA_DIR is None:
            raise RuntimeError("DATA_DIR未初始化，无法创建词云生成器")        # 获取配置参数
        max_words = self.config.get("max_word_count", 100)
        min_word_length = self.config.get("min_word_length", 2)
        min_word_frequency = self.config.get("min_word_frequency", 2)  # 新增：读取最小词频配置
        background_color = self.config.get("background_color", "white")
        colormap = self.config.get("colormap", "viridis")
        shape = self.config.get("shape", "rectangle")  # 默认形状为矩形
        custom_mask_path_config = self.config.get(
            "custom_mask_path", ""
        )  # 读取自定义蒙版路径配置
        
        # 获取字体大小配置
        min_font_size = self.config.get("min_font_size", 8)
        max_font_size = self.config.get("max_font_size", 200)

        # 获取字体路径，如果配置中没有，则使用默认值
        font_path = self.config.get("font_path", "")

        # 解析字体路径
        if font_path:
            # 如果是相对路径，解析为相对于数据目录
            if not os.path.isabs(font_path):
                # 优先检查数据目录
                data_font_path = (
                    constant_module.DATA_DIR
                    / "resources"
                    / "fonts"
                    / os.path.basename(font_path)
                )
                if os.path.exists(data_font_path):
                    font_path = str(data_font_path)
                    logger.info(f"使用数据目录中的字体: {font_path}")
                else:
                    # 如果数据目录中不存在，则检查插件目录
                    plugin_font_path = constant_module.PLUGIN_DIR / font_path
                    if os.path.exists(plugin_font_path):
                        font_path = str(plugin_font_path)
                        logger.info(f"使用插件目录中的字体: {font_path}")

        # 获取停用词文件路径
        stop_words_file = self.config.get("stop_words_file", "stop_words.txt")

        # 解析停用词文件路径
        if stop_words_file and not os.path.isabs(stop_words_file):
            # 优先检查数据目录
            data_stopwords_path = (
                constant_module.DATA_DIR
                / "resources"
                / os.path.basename(stop_words_file)
            )
            if os.path.exists(data_stopwords_path):
                stop_words_file = str(data_stopwords_path)
                logger.info(f"使用数据目录中的停用词文件: {stop_words_file}")
            else:
                # 如果数据目录中不存在，则检查插件目录
                plugin_stopwords_path = constant_module.PLUGIN_DIR / stop_words_file
                if os.path.exists(plugin_stopwords_path):
                    stop_words_file = str(plugin_stopwords_path)
                    logger.info(f"使用插件目录中的停用词文件: {stop_words_file}")        # 初始化词云生成器
        self.wordcloud_generator = WordCloudGenerator(
            max_words=max_words,
            min_word_length=min_word_length,
            min_word_frequency=min_word_frequency,  # 新增：传递最小词频参数
            background_color=background_color,
            colormap=colormap,
            font_path=font_path,
            stop_words_file=stop_words_file
            if os.path.exists(stop_words_file)
            else None,
            shape=shape,
            custom_mask_path=custom_mask_path_config,  # 传递自定义蒙版路径
            min_font_size=min_font_size,  # 传递最小字体大小
            max_font_size=max_font_size,  # 传递最大字体大小
        )

        logger.info("词云生成器初始化完成")

    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        try:
            # 检查是否启用自动生成功能
            auto_generate_enabled = self.config.get("auto_generate_enabled", True)
            if auto_generate_enabled:
                # 获取cron表达式
                cron_expression = self.config.get("auto_generate_cron", "0 20 * * *")
                logger.info(f"自动生成词云cron表达式: {cron_expression}")

                # 兼容旧版本的6字段cron格式（带秒的格式）
                # 如果是6字段格式（0 0 20 * * *），转换为5字段格式（0 20 * * *）
                if cron_expression.count(" ") == 5:  # 6字段格式
                    fields = cron_expression.split(" ")
                    if len(fields) == 6:
                        # 去掉秒字段，只保留后5个字段
                        cron_expression = " ".join(fields[1:])
                        logger.info(
                            f"转换6字段cron表达式为5字段: {' '.join(fields)} -> {cron_expression}"
                        )

                # 添加定时生成词云任务
                try:
                    self.scheduler.add_task(
                        cron_expression=cron_expression,
                        callback=self.auto_generate_wordcloud,
                        task_id="auto_generate_wordcloud",
                    )
                    logger.info(f"已添加自动生成词云任务，执行时间: {cron_expression}")
                except Exception as auto_task_error:
                    logger.error(f"添加自动生成词云任务失败: {auto_task_error}")
            else:
                logger.info("自动生成词云功能已禁用")

            # 检查是否启用每日生成功能
            daily_generate_enabled = self.config.get("daily_generate_enabled", True)
            if daily_generate_enabled:
                # 获取每日生成时间
                daily_time = self.config.get("daily_generate_time", "23:30")
                daily_cron = time_str_to_cron(daily_time)

                # 检查生成的cron是否有效
                logger.info(
                    f"每日词云生成时间: {daily_time}, 转换为cron表达式: {daily_cron}"
                )

                # 验证时间和计算下一次执行时间
                try:
                    import datetime
                    from croniter import croniter

                    # 解析时间字符串
                    hour, minute = parse_time_str(daily_time)
                    logger.info(f"每日词云设置为 {hour:02d}:{minute:02d} 执行")

                    # 验证cron表达式
                    if not croniter.is_valid(daily_cron):
                        logger.error(
                            f"每日词云cron表达式无效: {daily_cron}，使用默认值"
                        )
                        daily_cron = "0 0 * * *"  # 默认午夜执行

                    # 计算下次执行时间
                    base = datetime.datetime.now()
                    cron = croniter(daily_cron, base)
                    next_run = cron.get_next(datetime.datetime)
                    logger.info(
                        f"每日词云下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
                    )

                    # 检查时间差
                    time_diff = next_run - base
                    hours, remainder = divmod(time_diff.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    logger.info(
                        f"距离下次执行还有: {int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
                    )

                    # 检查本地时区
                    import time

                    timezone_offset = -time.timezone // 3600  # 转换为小时
                    logger.info(
                        f"系统时区信息: UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}"
                    )

                except Exception as time_error:
                    logger.error(f"验证时间失败: {time_error}")

                # 添加每日词云生成任务
                try:
                    task_added = self.scheduler.add_task(
                        cron_expression=daily_cron,
                        callback=self.daily_generate_wordcloud,
                        task_id="daily_generate_wordcloud",
                    )

                    if task_added:
                        logger.info(
                            f"已成功添加每日词云生成任务，执行时间: {daily_time}({daily_cron})"
                        )
                    else:
                        logger.error("添加每日词云生成任务失败，返回值为False")

                except Exception as daily_task_error:
                    logger.error(f"添加每日词云生成任务失败: {daily_task_error}")
                    import traceback

                    logger.error(f"任务添加错误详情: {traceback.format_exc()}")
            else:
                logger.info("每日生成词云功能已禁用")

            # 启动调度器
            logger.info("准备启动定时任务调度器...")
            self.scheduler.start()
            logger.info("定时任务调度器已启动")

            # 输出当前注册的所有任务信息
            tasks = getattr(self.scheduler, "tasks", {})
            if tasks:
                logger.info(f"当前注册的定时任务数量: {len(tasks)}")
                for task_id, task_info in tasks.items():
                    if isinstance(task_info, dict) and "next_run" in task_info:
                        next_time = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(task_info["next_run"])
                        )
                        logger.info(f"任务 '{task_id}' 下次执行时间: {next_time}")

                        # 验证回调函数
                        if "callback" in task_info:
                            callback = task_info["callback"]
                            if callback:
                                logger.info(
                                    f"任务 '{task_id}' 回调函数: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}"
                                )
                            else:
                                logger.warning(f"任务 '{task_id}' 回调函数为空")
                    else:
                        logger.warning(
                            f"任务 '{task_id}' 信息格式不正确或缺少next_run字段"
                        )
            else:
                logger.warning("未找到任何注册的定时任务")

        except Exception as e:
            logger.error(f"设置定时任务失败: {e}")
            import traceback

            logger.error(f"设置定时任务错误详情: {traceback.format_exc()}")

    @filter.event_message_type(EventMessageType.ALL)
    async def record_message(self, event: AstrMessageEvent):
        """监听所有消息并记录用于后续词云生成"""
        try:
            # 获取是否计入机器人消息的配置
            include_bot_msgs = self.config.get("include_bot_messages", False)

            # 跳过命令消息
            if event.message_str is not None and event.message_str.startswith("/"):
                return

            # 如果不计入机器人消息，则跳过机器人自身消息
            if not include_bot_msgs and event.get_sender_id() == event.get_self_id():
                return

            # 尝试匹配自然语言关键词
            if event.message_str is not None:
                # 检查是否触发了自然语言命令
                handled = await self._check_natural_language_keywords(event)
                if handled:
                    # 如果已经处理了命令，就不需要继续记录消息
                    return True

            # 获取消息详情，用于日志
            sender_id = event.get_sender_id()
            sender_name = event.get_sender_name()
            session_id = event.unified_msg_origin
            is_group = bool(event.get_group_id())

            # 如果是群消息，检查是否启用了该群的词云功能
            if is_group:
                group_id = event.get_group_id()
                if not is_group_enabled(group_id, self.enabled_groups):
                    logger.debug(f"群 {group_id} 未启用词云功能，跳过消息记录")
                    return True

            # 检测和提取消息内容
            content = event.message_str if hasattr(event, "message_str") else None
            msg_type = "群聊" if is_group else "私聊"

            # 尝试从消息链中获取非空内容描述
            message_desc = "[无文本内容]"
            try:
                if hasattr(event, "get_messages") and callable(
                    getattr(event, "get_messages")
                ):
                    messages = event.get_messages()
                    if messages:
                        content_types = []
                        for msg in messages:
                            if hasattr(msg, "__class__") and hasattr(
                                msg.__class__, "__name__"
                            ):
                                msg_class = msg.__class__.__name__
                                if (
                                    msg_class != "Plain"
                                    and msg_class not in content_types
                                ):
                                    content_types.append(msg_class)

                        if content_types:
                            message_desc = f"[{', '.join(content_types)}]"
            except Exception as e:
                logger.debug(f"提取消息类型失败: {e}")

            # 提取文本内容
            if content is None or content.strip() == "":
                # 输出详细日志，标记无文本内容
                logger.debug(
                    f"收到{msg_type}消息 - 会话ID: {session_id}, 发送者: {sender_name}({sender_id}), 内容: {message_desc}"
                )

                # 将消息内容设为特殊标记，以便history_manager能识别出这是特殊消息
                if not hasattr(event, "message_str") or event.message_str is None:
                    event.message_str = ""

                # 如果是图片等非文本内容，我们直接跳过不记录到词云数据
                # 因为词云只关注文本内容
                return True

            # 处理有文本内容的消息
            content = content.strip()

            # 检查消息是否为空
            if not content:
                logger.debug(
                    f"跳过空消息 - 会话ID: {session_id}, 发送者: {sender_name}({sender_id})"
                )
                return True  # 空消息直接跳过，不记录也不报错

            # 输出详细日志
            logger.debug(
                f"收到{msg_type}消息 - 会话ID: {session_id}, 发送者: {sender_name}({sender_id}), 内容: {content[:30]}{'...' if len(content) > 30 else ''}"
            )

            # 确保消息内容长度合理
            if len(content) > 1000:  # 防止过长的消息
                logger.debug(f"消息内容过长({len(content)}字符)，截断至1000字符")
                content = content[:1000] + "..."

            # 更新消息内容
            event.message_str = content

            # 保存消息到历史记录
            try:
                success = self.history_manager.save_message(event)
                if success:
                    logger.debug(f"成功保存消息到历史记录 - 会话ID: {session_id}")
                else:
                    # 检查session_id格式是否正确
                    if not session_id or len(session_id.split(":")) < 2:
                        logger.warning(
                            f"保存消息到历史记录失败 - 可能是会话ID格式异常: {session_id}"
                        )
                    # 检查发送者信息是否完整
                    elif not sender_id or not sender_name:
                        logger.warning(
                            f"保存消息到历史记录失败 - 发送者信息可能不完整: ID={sender_id}, 名称={sender_name}"
                        )
                    # 检查消息内容
                    elif not content:
                        logger.warning("保存消息到历史记录失败 - 消息内容为空")
                    else:
                        logger.warning(
                            f"保存消息到历史记录失败 - 会话ID: {session_id}, 可能是数据库操作失败"
                        )
            except Exception as save_error:
                # 导入traceback模块
                try:
                    import traceback

                    error_stack = traceback.format_exc()
                    logger.error(
                        f"保存消息过程中发生异常: {save_error}, 错误类型: {type(save_error).__name__}"
                    )
                    logger.error(f"错误堆栈: {error_stack}")
                except:
                    # 如果traceback也出错，使用简单日志
                    logger.error(
                        f"保存消息过程中发生异常: {save_error}, 无法获取详细堆栈"
                    )

            # 继续处理事件，不阻断其他插件
            return True
        except Exception as e:
            logger.error(f"记录消息时发生错误: {e}")
            # 出错时仍然继续处理事件
            return True

    @filter.command(CMD_GENERATE)
    async def generate_wordcloud_command(
        self, event: AstrMessageEvent, days: int = None
    ):
        """生成指定天数内当前会话的词云图"""
        try:
            actual_days = (
                days if days is not None else self.config.get("history_days", 7)
            )
            if actual_days <= 0:
                yield event.plain_result("天数必须大于0")
                return

            # target_session_id = event.unified_msg_origin # 旧的获取方式
            target_session_id_for_query: str
            group_id_val = event.get_group_id()
            platform_name = event.get_platform_name()
            if not platform_name:  # 兜底
                platform_name = "unknown_platform"

            if group_id_val:  # 命令来自群聊
                target_session_id_for_query = f"{platform_name}_group_{group_id_val}"
            else:  # 命令来自私聊
                target_session_id_for_query = event.unified_msg_origin

            if self.debug_mode:
                logger.info(
                    f"WordCloud生成请求: 会话ID={target_session_id_for_query}, 天数={actual_days}"
                )

            # 检查群聊是否启用
            if group_id_val and not is_group_enabled(group_id_val, self.enabled_groups):
                yield event.plain_result(f"群聊 {group_id_val} 未启用词云功能。")
                return

            max_messages_for_generation = 5000  # 增加单次生成处理的消息上限

            texts = self.history_manager.get_message_texts(
                session_id=target_session_id_for_query,
                days=actual_days,
                limit=max_messages_for_generation,
            )
            # 获取真实的消息总数
            actual_total_messages = self.history_manager.get_message_count_for_days(
                session_id=target_session_id_for_query, days=actual_days
            )

            if not texts:
                # 即便没有文本（可能都是图片等），也报告一下总消息数
                if actual_total_messages > 0:
                    yield event.plain_result(
                        f"最近{actual_days}天内有 {actual_total_messages} 条消息，但没有足够的可用于生成词云的文本内容。"
                    )
                else:
                    yield event.plain_result(f"最近{actual_days}天内没有消息。")
                return

            # 处理消息文本并生成词云
            word_counts = self.wordcloud_generator.process_texts(texts)

            # 设置标题
            title = f"{'群聊' if group_id_val else '私聊'}词云 - 最近{actual_days}天"

            # 生成词云图片
            image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                word_counts, target_session_id_for_query, title=title
            )

            # 发送结果
            yield event.chain_result(
                [
                    Comp.Plain(f"词云生成成功，共统计了{actual_total_messages}条消息:"),
                    Comp.Image.fromFileSystem(image_path),
                ]
            )

        except Exception as e:
            logger.error(f"生成词云失败: {e}")
            import traceback

            logger.error(f"生成词云失败详细信息: {traceback.format_exc()}")
            yield event.plain_result(f"生成词云失败: {str(e)}")

    @filter.command_group(CMD_GROUP)
    async def wordcloud_group(self):
        """词云插件命令组"""
        pass

    @wordcloud_group.command(CMD_CONFIG)
    async def config_command(self, event: AstrMessageEvent):
        """查看当前词云插件配置"""
        config_info = [
            "【词云插件配置】",
            f"自动生成: {'开启' if self.config.get('auto_generate_enabled', True) else '关闭'}",
            f"自动生成时间: {self.config.get('auto_generate_cron', '0 20 * * *')}",
            f"每日词云: {'开启' if self.config.get('daily_generate_enabled', True) else '关闭'}",
            f"每日词云时间: {self.config.get('daily_generate_time', '23:30')}",
            f"最大词数量: {self.config.get('max_word_count', 100)}",
            f"最小词长度: {self.config.get('min_word_length', 2)}",
            f"统计天数: {self.config.get('history_days', 7)}",
            f"背景颜色: {self.config.get('background_color', 'white')}",
            f"配色方案: {self.config.get('colormap', 'viridis')}",
            f"形状: {self.config.get('shape', 'rectangle')}",
        ]

        # 添加群聊配置信息
        if self.enabled_groups:
            config_info.append(f"启用的群: {', '.join(self.enabled_groups)}")
        else:
            config_info.append("启用的群: 全部（未指定特定群）")

        yield event.plain_result("\n".join(config_info))

    @wordcloud_group.command(CMD_HELP)
    async def help_command(self, event: AstrMessageEvent):
        """查看词云插件帮助"""
        help_text = [
            "【词云插件帮助】",
            "1. /wordcloud - 生成当前会话的词云",
            "2. /wordcloud [天数] - 生成指定天数的词云",
            "3. /wc config - 查看当前词云配置",
            "4. /wc help - 显示本帮助信息",
            "5. /wc test - 生成测试词云（无需历史数据）",
            "6. /wc today - 生成今天的词云",
            "7. /wc enable [群号] - 为指定群启用词云功能",
            "8. /wc disable [群号] - 为指定群禁用词云功能",
            "9. /wc clean_config - 清理过时的配置项",
            "10. /wc force_daily - 强制执行每日词云生成（管理员）",
            "",
            "【自然语言关键词】",
            "除了上述命令外，您还可以直接使用以下关键词触发相应功能：",
            "- 「今日词云」「获取今日词云」等 - 生成今天的词云",
            "- 「生成词云」「查看词云」等 - 生成最近7天的词云",
            "- 「词云帮助」「词云功能」等 - 显示帮助信息",
        ]

        yield event.plain_result("\n".join(help_text))

    @wordcloud_group.command("test")
    async def test_command(self, event: AstrMessageEvent):
        """生成测试词云，用于测试功能是否正常"""
        try:
            # 检查群聊限制
            if event.get_group_id():
                group_id = event.get_group_id()
                if not is_group_enabled(group_id, self.enabled_groups):
                    yield event.plain_result(
                        f"该群({group_id})未启用词云功能，无法生成词云。请联系管理员开启。"
                    )
                    return
        except Exception as e:
            logger.error(f"检查群聊限制失败: {e}")
            # 失败时继续执行，不阻止生成

        try:
            # 提示开始生成
            yield event.plain_result("正在生成测试词云，请稍候...")

            # 创建测试文本
            test_texts = [
                "霞鹜文楷是一款开源中文字体",
                "该字体基于FONTWORKS出品字体Klee One衍生",
                "支持简体中文、繁体中文和日文等",
                "词云是一种文本可视化方式",
                "它将文本中词语的频率以图形方式展示",
                "频率越高的词语，在词云中显示得越大",
                "AstrBot是一个强大的聊天机器人框架",
                "支持多平台、多账号、多功能",
                "插件系统让开发者能够轻松扩展功能",
                "这是一个测试词云，包含示例文本",
                "Python是一种流行的编程语言",
                "广泛应用于数据分析、人工智能和Web开发",
                "自然语言处理是计算机科学的一个分支",
                "它研究如何让计算机理解和生成人类语言",
                "机器学习是人工智能的一个子领域",
                "它使用统计方法使计算机系统能够学习和改进",
                "深度学习是机器学习的一种方法",
                "它使用多层神经网络来模拟人脑的学习过程",
                "词向量是自然语言处理中的一种技术",
                "它将词语映射到向量空间中",
                "词云是文本可视化的一种流行工具",
            ]

            # 生成词频统计
            word_counts = self.wordcloud_generator.process_texts(test_texts)

            # 设置标题
            title = "测试词云 - Test WordCloud"

            # 生成词云图片
            session_id = event.unified_msg_origin
            image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                word_counts, session_id, title=title
            )

            # 发送结果
            yield event.chain_result(
                [
                    Comp.Plain("词云生成成功，这是一个测试词云:"),
                    Comp.Image.fromFileSystem(image_path),
                ]
            )

        except Exception as e:
            logger.error(f"生成测试词云失败: {e}")
            yield event.plain_result(f"生成测试词云失败: {str(e)}")

    @wordcloud_group.command("today")
    async def today_command(self, event: AstrMessageEvent):
        """生成当前会话今天的词云图"""
        try:
            # target_session_id = event.unified_msg_origin # 旧的获取方式
            target_session_id_for_query: str
            group_id_val = event.get_group_id()
            platform_name = event.get_platform_name()
            if not platform_name:  # 兜底
                platform_name = "unknown_platform"

            if group_id_val:  # 命令来自群聊
                target_session_id_for_query = f"{platform_name}_group_{group_id_val}"
            else:  # 命令来自私聊
                target_session_id_for_query = event.unified_msg_origin

            if self.debug_mode:
                logger.info(f"今日词云生成请求: 会话ID={target_session_id_for_query}")

            # 检查群聊是否启用
            if group_id_val and not is_group_enabled(group_id_val, self.enabled_groups):
                yield event.plain_result(f"群聊 {group_id_val} 未启用词云功能。")
                return

            # 增加单次生成处理的消息上限
            max_messages_for_generation = 5000

            texts = self.history_manager.get_todays_message_texts(
                session_id=target_session_id_for_query,
                limit=max_messages_for_generation,
            )
            # 获取今天的真实消息总数
            actual_total_messages_today = self.history_manager.get_message_count_today(
                target_session_id_for_query
            )

            if not texts:
                if actual_total_messages_today > 0:
                    yield event.plain_result(
                        f"今天有 {actual_total_messages_today} 条消息，但没有足够的可用于生成词云的文本内容。"
                    )
                else:
                    yield event.plain_result("今天没有消息。")
                return

            # 处理消息文本并生成词云
            word_counts = self.wordcloud_generator.process_texts(texts)

            # 获取今天的日期
            date_str = format_date()

            # 设置标题
            title = f"{'群聊' if group_id_val else '私聊'}词云 - {date_str}"

            # 生成词云图片
            image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                word_counts, target_session_id_for_query, title=title
            )

            # 发送结果
            yield event.chain_result(
                [
                    Comp.Plain(
                        f"今日词云生成成功，共统计了{actual_total_messages_today}条消息:"
                    ),
                    Comp.Image.fromFileSystem(image_path),
                ]
            )

            # 如果配置中启用了用户排行榜功能，则生成并发送排行榜
            show_ranking_config = self.config.get("show_user_ranking", True)
            logger.info(f"排行榜配置 show_user_ranking: {show_ranking_config}")

            if show_ranking_config:
                try:
                    logger.info(
                        f"开始为会话 {target_session_id_for_query} 生成用户排行榜"
                    )
                    total_users = self.history_manager.get_total_users_today(
                        target_session_id_for_query
                    )
                    logger.info(f"本日总参与用户数: {total_users}")

                    ranking_limit = self.config.get("ranking_user_count", 5)
                    logger.info(f"排行榜显示数量上限: {ranking_limit}")
                    active_users = self.history_manager.get_active_users(
                        target_session_id_for_query, days=1, limit=ranking_limit
                    )
                    logger.info(
                        f"获取到活跃用户数量: {len(active_users) if active_users else 0}"
                    )
                    if active_users and len(active_users) > 0:
                        ranking_text_lines = []
                        ranking_text_lines.append(
                            f"本群 {total_users} 位朋友共产生 {actual_total_messages_today} 条发言"
                        )
                        ranking_text_lines.append("👀 看下有没有你感兴趣的关键词?")
                        ranking_text_lines.append("")  # Blank line

                        ranking_text_lines.append("活跃用户排行榜:")

                        medals_str = self.config.get("ranking_medals", "🥇,🥈,🥉,🏅,🏅")
                        medals = [m.strip() for m in medals_str.split(",")]

                        for i, (user_id, user_name, count) in enumerate(active_users):
                            medal = medals[i] if i < len(medals) else medals[-1]
                            ranking_text_lines.append(
                                f"{medal} {user_name} 贡献: {count} 条"
                            )

                        ranking_text_lines.append("")  # Blank line
                        ranking_text_lines.append("🎉 感谢这些朋友今天的分享! 🎉")

                        final_ranking_str = "\n".join(ranking_text_lines)
                        sendable_session_id = self._get_astrbot_sendable_session_id(
                            target_session_id_for_query
                        )
                        logger.info(f"准备发送排行榜到会话: {sendable_session_id}")
                        ranking_msg_chain = MessageChain(
                            [Comp.Plain(final_ranking_str)]
                        )
                        await self.context.send_message(
                            sendable_session_id, ranking_msg_chain
                        )
                        logger.info(f"用户排行榜已成功发送到 {sendable_session_id}")
                    else:
                        logger.info(
                            "没有活跃用户数据可用于生成排行榜，或活跃用户数为0。跳过排行榜发送。"
                        )

                except Exception as ranking_error:
                    logger.error(
                        f"为会话 {target_session_id_for_query} (群 {group_id_val}) 生成用户排行榜失败: {ranking_error}"
                    )
                    if self.debug_mode:
                        logger.debug(f"排行榜错误详情: {traceback.format_exc()}")

        except Exception as e:
            logger.error(f"生成今日词云失败: {e}")
            # import traceback # 全局导入已存在，此局部导入通常不需要，但UnboundLocalError提示可能存在作用域问题
            # 为了确保 traceback.format_exc() 在此处可用，我们依赖顶部的全局导入
            logger.error(f"生成今日词云失败详细信息: {traceback.format_exc()}")
            yield event.plain_result(f"生成今日词云失败: {str(e)}")

    @wordcloud_group.command("enable")
    async def enable_group_command(self, event: AstrMessageEvent, group_id: str = None):
        """为指定群启用词云功能"""
        # 如果没有提供群号且当前是群聊，使用当前群
        if group_id is None and event.get_group_id():
            group_id = event.get_group_id()

        if not group_id:
            yield event.plain_result("请提供群号，例如: /wc enable 123456789")
            return

        try:
            # 更新内存中的配置
            self.enabled_groups.add(group_id)

            # 更新配置文件
            try:
                # 更新配置
                enabled_str = ",".join(self.enabled_groups)
                self.config["enabled_group_list"] = enabled_str

                # 保存配置
                if hasattr(self.config, "save_config") and callable(
                    getattr(self.config, "save_config")
                ):
                    self.config.save_config()
                    logger.info("更新并保存了群组配置")
            except Exception as config_error:
                logger.error(f"保存群组配置失败: {config_error}")

            yield event.plain_result(f"已为群 {group_id} 启用词云功能")
        except Exception as e:
            logger.error(f"启用群词云功能失败: {e}")
            yield event.plain_result(f"启用群词云功能失败: {str(e)}")

    @wordcloud_group.command("disable")
    async def disable_group_command(
        self, event: AstrMessageEvent, group_id: str = None
    ):
        """为指定群禁用词云功能"""
        # 如果没有提供群号且当前是群聊，使用当前群
        if group_id is None and event.get_group_id():
            group_id = event.get_group_id()

        if not group_id:
            yield event.plain_result("请提供群号，例如: /wc disable 123456789")
            return

        try:
            # 更新内存中的配置
            # 如果启用列表为空，表示之前所有群都启用
            # 现在需要禁用特定群，需要先获取所有当前活跃群
            if not self.enabled_groups:
                try:
                    # 获取所有活跃群
                    active_groups = self.history_manager.get_active_group_sessions()
                    for session_id in active_groups:
                        active_group_id = (
                            self.history_manager.extract_group_id_from_session(
                                session_id
                            )
                        )
                        if active_group_id and active_group_id != group_id:
                            self.enabled_groups.add(active_group_id)
                    logger.info(
                        f"从所有活跃群中排除目标群 {group_id}, 启用了 {len(self.enabled_groups)} 个群"
                    )
                except Exception as e:
                    logger.error(f"获取活跃群失败: {e}")
                    # 如果失败，创建一个空的启用列表，这意味着除了指定禁用的群，其他都启用
                    self.enabled_groups = set()
            else:
                # 从启用列表中移除
                if group_id in self.enabled_groups:
                    self.enabled_groups.remove(group_id)
                    logger.info(f"从启用列表移除群: {group_id}")

            # 更新配置文件
            try:
                # 更新配置
                enabled_str = ",".join(self.enabled_groups)
                self.config["enabled_group_list"] = enabled_str

                # 保存配置
                if hasattr(self.config, "save_config") and callable(
                    getattr(self.config, "save_config")
                ):
                    self.config.save_config()
                    logger.info("更新并保存了群组配置")
            except Exception as config_error:
                logger.error(f"保存群组配置失败: {config_error}")

            yield event.plain_result(f"已为群 {group_id} 禁用词云功能")
        except Exception as e:
            logger.error(f"禁用群词云功能失败: {e}")
            yield event.plain_result(f"禁用群词云功能失败: {str(e)}")

    @wordcloud_group.command("clean_config")
    async def clean_config_command(self, event: AstrMessageEvent):
        """清理词云插件配置中的过时配置项"""
        try:
            cleaned = False

            # 检查是否有过时的配置项
            if self.config and hasattr(self.config, "__contains__"):
                # 已知过时配置项列表
                deprecated_configs = ["disabled_group_list"]

                # 检查并删除过时配置项
                for item in deprecated_configs:
                    if item in self.config:
                        try:
                            del self.config[item]
                            cleaned = True
                            logger.info(f"已删除过时配置项: {item}")
                        except Exception as e:
                            logger.warning(f"删除配置项 {item} 失败: {e}")

                # 保存配置
                if (
                    cleaned
                    and hasattr(self.config, "save_config")
                    and callable(getattr(self.config, "save_config"))
                ):
                    self.config.save_config()
                    yield event.plain_result(
                        "已清理词云插件配置中的过时配置项。请刷新配置页面查看。"
                    )
                else:
                    yield event.plain_result("没有发现需要清理的过时配置项。")
            else:
                yield event.plain_result("无法访问插件配置。")
        except Exception as e:
            logger.error(f"清理配置失败: {e}")
            yield event.plain_result(f"清理配置失败: {str(e)}")

    async def auto_generate_wordcloud(self):
        """自动生成词云的定时任务回调"""
        logger.info("开始执行自动生成词云任务")

        try:
            # 获取配置
            days = self.config.get("history_days", 7)

            # 获取活跃会话
            active_sessions = self.history_manager.get_active_sessions(days)

            for session_id in active_sessions:
                try:
                    # 如果是群聊，检查是否启用
                    group_id = self.history_manager.extract_group_id_from_session(
                        session_id
                    )
                    if group_id and not is_group_enabled(group_id, self.enabled_groups):
                        logger.info(f"群 {group_id} 未启用词云功能，跳过自动生成")
                        continue

                    # 获取历史消息 (用于生成词云，仍受limit限制)
                    message_texts = self.history_manager.get_message_texts(
                        session_id, days, limit=5000
                    )  # 使用与手动命令一致的limit

                    # 获取真实的消息总数 (不受limit限制)
                    actual_total_messages = (
                        self.history_manager.get_message_count_for_days(
                            session_id, days
                        )
                    )

                    if not message_texts or len(message_texts) < self.config.get(
                        "min_messages_for_auto_wordcloud", 20
                    ):  # 至少要有N条消息才生成
                        logger.info(
                            f"会话 {session_id} 文本消息不足 ({len(message_texts)}条) 或总消息不足 ({actual_total_messages}条)，跳过自动生成"
                        )
                        continue

                    # 处理消息文本并生成词云
                    word_counts = self.wordcloud_generator.process_texts(message_texts)

                    # 生成词云图片
                    title = f"聊天词云 - 定时生成 - 最近{days}天"
                    image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                        word_counts, session_id, title=title
                    )

                    # 发送结果
                    sendable_session_id = self._get_astrbot_sendable_session_id(
                        session_id
                    )
                    await self.scheduler.send_to_session(
                        sendable_session_id,
                        f"[自动词云] 这是最近{days}天的聊天词云，共统计了{actual_total_messages}条消息:",
                        str(path_obj),
                    )

                    # 避免发送过快
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"为会话 {session_id} 自动生成词云失败: {e}")
                    continue

            logger.info("自动生成词云任务执行完成")

        except Exception as e:
            logger.error(f"自动生成词云任务执行失败: {e}")

    async def daily_generate_wordcloud(self):
        """
        生成每日词云定时任务
        """
        logger.info("开始执行每日词云生成任务")

        # 使用任务ID创建任务锁，防止并发执行
        task_id = "daily_wordcloud_task"
        # 确保DATA_DIR存在
        if constant_module.DATA_DIR is None:
            logger.error("DATA_DIR未初始化，无法创建任务锁")
            return

        # 创建锁文件
        task_lock_file = os.path.join(constant_module.DATA_DIR, f"{task_id}.lock")

        # 检查锁文件是否存在
        if os.path.exists(task_lock_file):
            # 检查锁文件的时间
            lock_time = os.path.getmtime(task_lock_file)
            current_time = time.time()

            # 如果锁文件创建时间在30分钟内，说明可能有其他任务正在执行
            if current_time - lock_time < 1800:  # 30分钟
                logger.warning(
                    f"每日词云生成任务可能正在进行中(pid:{os.getpid()})，跳过本次执行"
                )
                return
            else:
                # 锁文件太旧，可能是之前的任务异常退出，删除旧锁文件
                try:
                    os.remove(task_lock_file)
                    logger.info("发现陈旧的任务锁文件，已删除")
                except Exception as e:
                    logger.error(f"删除陈旧的任务锁文件失败: {e}")
                    # 如果无法删除，仍跳过本次执行
                    return

        try:
            # 创建锁文件
            with open(task_lock_file, "w") as f:
                f.write(
                    f"PID: {os.getpid()}, Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            # 使用一个标志来跟踪任务是否执行成功
            task_completed = False

            try:
                # 获取当前日期作为目标日期
                date = datetime.date.today()
                logger.info(f"任务执行日期: {date}")

                # 获取所有活跃的会话
                active_sessions = self.history_manager.get_active_sessions()
                logger.info(f"发现活跃会话数量: {len(active_sessions)}")

                # 遍历所有活跃会话
                for session_id in active_sessions:
                    try:
                        # 检查是否是群聊
                        if (
                            "group" not in session_id.lower()
                            and "GroupMessage" not in session_id
                            and "_group_" not in session_id
                        ):
                            logger.debug(f"会话 {session_id} 不是群聊，跳过")
                            continue

                        # 使用工具函数提取群ID
                        group_id = extract_group_id_from_session(session_id)

                        if not group_id:
                            logger.warning(f"无法从会话ID {session_id} 提取群ID，跳过")
                            continue

                        # 检查群是否启用了词云功能
                        if not is_group_enabled(group_id, self.enabled_groups):
                            logger.info(f"群 {group_id} 未启用词云功能，跳过")
                            continue

                        logger.info(
                            f"为群 {group_id} (会话ID: {session_id}) 生成每日词云"
                        )

                        # 计算当前的时间范围
                        today_start = datetime.datetime.combine(date, datetime.time.min)
                        today_end = datetime.datetime.combine(date, datetime.time.max)
                        start_timestamp = int(today_start.timestamp())
                        end_timestamp = int(today_end.timestamp())

                        # 使用新添加的方法获取指定时间范围内的消息
                        all_messages = (
                            self.history_manager.get_messages_by_timestamp_range(
                                session_id=session_id,
                                start_timestamp=start_timestamp,
                                end_timestamp=end_timestamp,
                                limit=5000,  # 增加限制以获取更多消息
                            )
                        )

                        if not all_messages:
                            logger.info(f"群 {group_id} 在 {date} 没有消息记录，跳过")
                            continue

                        logger.info(
                            f"群 {group_id} 在 {date} 有 {len(all_messages)} 条消息"
                        )
                        total_messages_for_date = len(all_messages)

                        # 生成词云
                        # image_path = get_daily_image_path(session_id, date) # image_path variable seems unused later for wordcloud generation

                        # 处理消息文本并生成词云
                        word_counts = self.wordcloud_generator.process_texts(
                            all_messages
                        )

                        # 设置标题
                        date_str_title = date.strftime(
                            "%Y年%m月%d日"
                        )  # Full date for titles
                        title = f"群聊词云 - {date_str_title}"

                        # 生成词云图片
                        image_path_wc, path_obj = (
                            self.wordcloud_generator.generate_wordcloud(  # Renamed to avoid conflict
                                word_counts, session_id, title=title
                            )
                        )

                        if not path_obj:
                            logger.warning(f"为群 {group_id} 生成词云失败")
                            continue

                        logger.info(f"成功为群 {group_id} 生成词云: {image_path_wc}")

                        # 构建消息
                        message_chain_wc = [  # Renamed
                            Comp.Plain(f"【每日词云】{date_str_title}热词统计\n"),
                            Comp.Image(file=str(path_obj)),
                        ]

                        # 发送消息到群
                        sendable_session_id = self._get_astrbot_sendable_session_id(
                            session_id
                        )
                        logger.info(f"准备发送词云到会话: {sendable_session_id}")

                        # 使用适当的API发送消息
                        try:
                            logger.info(
                                f"Attempting to send message to session_id: {sendable_session_id} (derived from group_id: {group_id})"
                            )
                            result = await self.context.send_message(
                                sendable_session_id, MessageChain(message_chain_wc)
                            )
                            if result:
                                logger.info(
                                    f"Successfully sent daily wordcloud to session: {sendable_session_id}"
                                )

                                # --- BEGIN: Add user ranking logic ---
                                show_ranking_config = self.config.get(
                                    "show_user_ranking", True
                                )
                                logger.info(
                                    f"[排行榜-每日] show_user_ranking配置: {show_ranking_config} for session {session_id}"
                                )

                                if show_ranking_config:
                                    try:  # Outer try for overall ranking generation and sending
                                        logger.info(
                                            f"[排行榜-每日] 开始为会话 {session_id} 生成用户排行榜"
                                        )

                                        target_date_start_ts = int(
                                            datetime.datetime.combine(
                                                date, datetime.time.min
                                            ).timestamp()
                                        )
                                        target_date_end_ts = int(
                                            datetime.datetime.combine(
                                                date, datetime.time.max
                                            ).timestamp()
                                        )

                                        ranking_limit = self.config.get(
                                            "ranking_user_count", 5
                                        )

                                        active_users = self.history_manager.get_active_users_for_date_range(
                                            session_id,
                                            target_date_start_ts,
                                            target_date_end_ts,
                                            limit=ranking_limit,
                                        )
                                        total_users = self.history_manager.get_total_users_for_date_range(
                                            session_id,
                                            target_date_start_ts,
                                            target_date_end_ts,
                                        )

                                        logger.info(
                                            f"[排行榜-每日] 会话 {session_id} 在 {date} 的总参与用户数: {total_users}"
                                        )
                                        logger.info(
                                            f"[排行榜-每日] 获取到活跃用户数量: {len(active_users) if active_users else 0}"
                                        )

                                        if active_users and len(active_users) > 0:
                                            # day_description_for_header_and_thanks = date.strftime('%m月%d日') # No longer needed for this exact style
                                            # date_str_title = date.strftime("%Y年%m月%d日") # Still needed for WC image title and intro

                                            ranking_text_lines = []
                                            ranking_text_lines.append(
                                                f"本群 {total_users} 位朋友共产生 {total_messages_for_date} 条发言"
                                            )  # Style of 图二
                                            ranking_text_lines.append(
                                                "👀 看下有没有你感兴趣的关键词?"
                                            )  # Style of 图二
                                            ranking_text_lines.append("")  # Blank line
                                            ranking_text_lines.append(
                                                "活跃用户排行榜:"
                                            )  # Style of 图二

                                            medals_str = self.config.get(
                                                "ranking_medals", "🥇,🥈,🥉,🏅,🏅"
                                            )
                                            medals = [
                                                m.strip() for m in medals_str.split(",")
                                            ]

                                            for i, (
                                                user_id,
                                                user_name,
                                                count,
                                            ) in enumerate(active_users):
                                                medal = (
                                                    medals[i]
                                                    if i < len(medals)
                                                    else medals[-1]
                                                )
                                                ranking_text_lines.append(
                                                    f"{medal} {user_name} 贡献: {count} 条"
                                                )

                                            ranking_text_lines.append("")  # Blank line
                                            ranking_text_lines.append(
                                                "🎉 感谢这些朋友今天的分享! 🎉"
                                            )  # Style of 图二

                                            final_ranking_str = "\n".join(
                                                ranking_text_lines
                                            )
                                            # sendable_ranking_session_id = self._get_astrbot_sendable_session_id(target_session_id_for_query) # Incorrect, target_session_id_for_query not in this scope
                                            # daily_generate_wordcloud already uses sendable_session_id derived earlier for the wordcloud image.
                                            logger.info(
                                                f"[排行榜-每日] 准备发送排行榜到会话: {sendable_session_id}"
                                            )
                                            ranking_msg_chain = MessageChain(
                                                [Comp.Plain(final_ranking_str)]
                                            )
                                            await self.context.send_message(
                                                sendable_session_id, ranking_msg_chain
                                            )
                                    except Exception as ranking_error:  # Catch errors during ranking generation/sending
                                        logger.error(
                                            f"[排行榜-每日] 为会话 {session_id} 生成或发送排行榜时出错: {ranking_error}"
                                        )
                                        logger.error(
                                            f"[排行榜-每日] 排行榜错误详情: {traceback.format_exc()}"
                                        )
                                # --- END: Add user ranking logic ---
                            else:
                                logger.warning(
                                    f"Failed to send daily wordcloud to session: {sendable_session_id}. Result: {result}"
                                )

                        except (
                            Exception
                        ) as send_err:  # This except is for the daily wordcloud sending
                            logger.error(
                                f"Error sending daily wordcloud to session {sendable_session_id}: {send_err}"
                            )
                            logger.error(
                                f"Traceback for send error: {traceback.format_exc()}"
                            )

                    except Exception as e:  # This except is for the per-session processing in daily_generate_wordcloud
                        logger.error(f"处理会话 {session_id} 时出错: {e}")
                        logger.error(f"错误详情: {traceback.format_exc()}")

                # 标记任务完成
                task_completed = True
                logger.info("成功完成每日词云生成任务")

            except Exception as e:
                logger.error(f"执行每日词云生成任务时出错: {e}")
                logger.error(f"错误详情: {traceback.format_exc()}")

            # 更新锁文件状态或删除锁文件
            if task_completed:
                try:
                    # 成功执行后删除锁文件
                    os.remove(task_lock_file)
                    logger.info("删除任务锁文件")
                except Exception as e:
                    logger.error(f"删除任务锁文件失败: {e}")

        except Exception as e:
            logger.error(f"创建任务锁时出错: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")

    @wordcloud_group.command("force_daily")
    async def force_daily_command(self, event: AstrMessageEvent):
        """强制执行每日词云生成任务（管理员命令）"""
        # 检查是否是管理员
        if not event.is_admin():
            yield event.plain_result("此命令仅供管理员使用")
            return

        try:
            yield event.plain_result("正在强制执行每日词云生成任务，请稍候...")

            # 直接调用每日词云生成函数
            await self.daily_generate_wordcloud()

            yield event.plain_result("每日词云生成任务执行完毕，请查看日志或群聊消息")
        except Exception as e:
            logger.error(f"强制执行每日词云生成任务失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            yield event.plain_result(f"强制执行每日词云生成任务失败: {str(e)}")

    def terminate(self):
        """
        插件终止时的清理操作
        """
        try:
            logger.info("WordCloud plugin terminating...")

            # 确保调度器被正确停止
            if hasattr(self, "scheduler") and self.scheduler is not None:
                logger.info("Stopping scheduler...")
                try:
                    self.scheduler.stop()
                    logger.info("Scheduler stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping scheduler: {e}")

                # 移除调度器引用
                self.scheduler = None

            # 确保历史管理器被正确关闭
            if hasattr(self, "history_manager") and self.history_manager is not None:
                logger.info("Closing history manager...")
                try:
                    self.history_manager.close()
                    logger.info("History manager closed successfully")
                except Exception as e:
                    logger.error(f"Error closing history manager: {e}")

                # 移除历史管理器引用
                self.history_manager = None

            # 如果有事件循环引用，确保它被清理
            if hasattr(self, "main_loop") and self.main_loop is not None:
                logger.info("Cleaning up main loop reference")
                self.main_loop = None

            logger.info("WordCloud plugin terminated")
        except Exception as e:
            logger.error(f"Error during plugin termination: {e}")
            logger.error(traceback.format_exc())

    async def _check_natural_language_keywords(self, event: AstrMessageEvent):
        """
        检查消息是否匹配自然语言关键词，如果匹配则执行相应命令

        Args:
            event: 消息事件

        Returns:
            bool: 如果处理了关键词命令返回True，否则返回False
        """
        if not event.message_str:
            return False

        message = event.message_str.strip()

        # 检查是否匹配任何自然语言关键词
        for (
            command_type,
            keywords,
        ) in (
            NATURAL_KEYWORDS.items()
        ):  # Renamed command to command_type to avoid conflict
            for keyword in keywords:
                if message == keyword:
                    logger.info(
                        f"检测到自然语言关键词: {keyword}, 执行命令: {command_type}"
                    )

                    try:
                        # 根据命令执行相应的函数
                        if command_type == "today":
                            async for result in self.today_command(event):
                                if hasattr(result, "send") and callable(
                                    getattr(result, "send")
                                ):
                                    await result.send()
                                else:
                                    sendable_session_id = (
                                        self._get_astrbot_sendable_session_id(
                                            event.unified_msg_origin
                                        )
                                    )
                                    if isinstance(result, MessageChain):
                                        await self.context.send_message(
                                            sendable_session_id, result
                                        )
                                    elif hasattr(result, "to_message_chain"):
                                        message_chain = result.to_message_chain()
                                        await self.context.send_message(
                                            sendable_session_id, message_chain
                                        )
                            return True  # Command processed

                        elif command_type == "wordcloud":
                            days = self.config.get("history_days", 7)
                            async for result in self.generate_wordcloud_command(
                                event, days
                            ):
                                if hasattr(result, "send") and callable(
                                    getattr(result, "send")
                                ):
                                    await result.send()
                                else:
                                    sendable_session_id = (
                                        self._get_astrbot_sendable_session_id(
                                            event.unified_msg_origin
                                        )
                                    )
                                    if isinstance(result, MessageChain):
                                        await self.context.send_message(
                                            sendable_session_id, result
                                        )
                                    elif hasattr(result, "to_message_chain"):
                                        message_chain = result.to_message_chain()
                                        await self.context.send_message(
                                            sendable_session_id, message_chain
                                        )
                            return True  # Command processed

                        elif command_type == "help":
                            async for result in self.help_command(event):
                                if hasattr(result, "send") and callable(
                                    getattr(result, "send")
                                ):
                                    await result.send()
                                else:
                                    sendable_session_id = (
                                        self._get_astrbot_sendable_session_id(
                                            event.unified_msg_origin
                                        )
                                    )
                                    if isinstance(result, MessageChain):
                                        await self.context.send_message(
                                            sendable_session_id, result
                                        )
                                    elif hasattr(result, "to_message_chain"):
                                        message_chain = result.to_message_chain()
                                        await self.context.send_message(
                                            sendable_session_id, message_chain
                                        )
                            return True  # Command processed

                    except (
                        Exception
                    ) as e_cmd_exec:  # Catch exceptions during command execution
                        logger.error(
                            f"执行自然语言命令 {command_type} 失败: {e_cmd_exec}"
                        )
                        logger.error(
                            f"Traceback for command execution error: {traceback.format_exc()}"
                        )
                        try:
                            sendable_session_id = self._get_astrbot_sendable_session_id(
                                event.unified_msg_origin
                            )
                            await self.context.send_message(
                                sendable_session_id,
                                MessageChain(
                                    f'执行命令"{keyword}"时出错: {str(e_cmd_exec)}'
                                ),
                            )
                        except Exception as send_error_report_e:
                            logger.error(
                                f"发送命令执行错误报告失败: {send_error_report_e}"
                            )
                    return True  # Indicate that a keyword was matched and attempt was made to process it

        return False  # No keyword matched
