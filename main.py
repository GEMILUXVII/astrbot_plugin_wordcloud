"""
AstrBot 词云生成插件
"""
import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.api.star import Star, Context, register, StarTools
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api.event.filter import EventMessageType
import astrbot.api.message_components as Comp

from .constant import (
    PLUGIN_NAME, PLUGIN_AUTHOR, PLUGIN_DESC, PLUGIN_VERSION, PLUGIN_REPO,
    CMD_GENERATE, CMD_GROUP, CMD_CONFIG, CMD_HELP
)
from .utils import (
    load_stop_words, get_image_path, get_daily_image_path,
    format_date, time_str_to_cron, parse_group_list, is_group_enabled, parse_time_str
)
from .wordcloud_core.generator import WordCloudGenerator
from .wordcloud_core.history_manager import HistoryManager
from .wordcloud_core.scheduler import TaskScheduler

# 导入常量模块以便修改DATA_DIR
import sys
import importlib
from . import constant as constant_module

@register(PLUGIN_NAME, PLUGIN_AUTHOR, PLUGIN_DESC, PLUGIN_VERSION, PLUGIN_REPO)
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
        
        # --- 获取主事件循环 ---
        try:
            self.main_loop = asyncio.get_running_loop()
            logger.info(f"WordCloudPlugin: Successfully got running main loop ID: {id(self.main_loop)}")
        except RuntimeError:
            logger.warning("WordCloudPlugin: No running loop found via get_running_loop(), trying get_event_loop().")
            self.main_loop = asyncio.get_event_loop()
            logger.info(f"WordCloudPlugin: Got loop via get_event_loop() ID: {id(self.main_loop)}")
        # ---------------------
        
        # 清理旧的禁用群列表配置项（如果存在）
        if self.config and hasattr(self.config, "__contains__") and "disabled_group_list" in self.config:
            try:
                # 删除旧配置项
                if hasattr(self.config, "__delitem__"):
                    del self.config["disabled_group_list"]
                    # 保存配置
                    if hasattr(self.config, "save_config") and callable(getattr(self.config, "save_config")):
                        self.config.save_config()
                        logger.info("已清理旧的禁用群列表配置项")
            except Exception as e:
                logger.warning(f"清理旧配置项失败: {e}")
        
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
        self.scheduler = TaskScheduler(context, main_loop=self.main_loop, debug_mode=self.debug_mode)
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
            
            # 创建图片目录
            images_dir = data_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # 创建调试目录
            debug_dir = data_dir / "debug"
            debug_dir.mkdir(exist_ok=True)
            
            # 复制字体文件
            plugin_font_path = constant_module.PLUGIN_DIR / "fonts" / "LXGWWenKai-Regular.ttf"
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
                    logger.info(f"已有历史消息统计: {', '.join(session_info)}")
                else:
                    logger.info("暂无历史消息记录")
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
            raise RuntimeError("DATA_DIR未初始化，无法创建词云生成器")
            
        # 获取配置参数
        max_words = self.config.get("max_word_count", 100)
        min_word_length = self.config.get("min_word_length", 2)
        background_color = self.config.get("background_color", "white")
        colormap = self.config.get("colormap", "viridis")
        shape = self.config.get("shape", "circle")
        
        # 获取字体路径，如果配置中没有，则使用默认值
        font_path = self.config.get("font_path", "")
        
        # 解析字体路径
        if font_path:
            # 如果是相对路径，解析为相对于数据目录
            if not os.path.isabs(font_path):
                # 优先检查数据目录
                data_font_path = constant_module.DATA_DIR / "resources" / "fonts" / os.path.basename(font_path)
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
            data_stopwords_path = constant_module.DATA_DIR / "resources" / os.path.basename(stop_words_file)
            if os.path.exists(data_stopwords_path):
                stop_words_file = str(data_stopwords_path)
                logger.info(f"使用数据目录中的停用词文件: {stop_words_file}")
            else:
                # 如果数据目录中不存在，则检查插件目录
                plugin_stopwords_path = constant_module.PLUGIN_DIR / stop_words_file
                if os.path.exists(plugin_stopwords_path):
                    stop_words_file = str(plugin_stopwords_path)
                    logger.info(f"使用插件目录中的停用词文件: {stop_words_file}")
        
        # 初始化词云生成器
        self.wordcloud_generator = WordCloudGenerator(
            max_words=max_words,
            min_word_length=min_word_length,
            background_color=background_color,
            colormap=colormap,
            font_path=font_path,
            stop_words_file=stop_words_file if os.path.exists(stop_words_file) else None,
            shape=shape
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
                        logger.info(f"转换6字段cron表达式为5字段: {' '.join(fields)} -> {cron_expression}")
                
                # 添加定时生成词云任务
                try:
                    self.scheduler.add_task(
                        cron_expression=cron_expression,
                        callback=self.auto_generate_wordcloud,
                        task_id="auto_generate_wordcloud"
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
                logger.info(f"每日词云生成时间: {daily_time}, 转换为cron表达式: {daily_cron}")
                
                # 验证时间和计算下一次执行时间
                try:
                    import datetime
                    from croniter import croniter
                    
                    # 解析时间字符串
                    hour, minute = parse_time_str(daily_time)
                    logger.info(f"每日词云设置为 {hour:02d}:{minute:02d} 执行")
                    
                    # 验证cron表达式
                    if not croniter.is_valid(daily_cron):
                        logger.error(f"每日词云cron表达式无效: {daily_cron}，使用默认值")
                        daily_cron = "0 0 * * *"  # 默认午夜执行
                    
                    # 计算下次执行时间
                    base = datetime.datetime.now()
                    cron = croniter(daily_cron, base)
                    next_run = cron.get_next(datetime.datetime)
                    logger.info(f"每日词云下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 检查时间差
                    time_diff = next_run - base
                    hours, remainder = divmod(time_diff.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    logger.info(f"距离下次执行还有: {int(hours)}小时{int(minutes)}分钟{int(seconds)}秒")
                    
                    # 检查本地时区
                    import time
                    timezone_offset = -time.timezone // 3600  # 转换为小时
                    logger.info(f"系统时区信息: UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}")
                    
                except Exception as time_error:
                    logger.error(f"验证时间失败: {time_error}")
                
                # 添加每日词云生成任务
                try:
                    task_added = self.scheduler.add_task(
                        cron_expression=daily_cron,
                        callback=self.daily_generate_wordcloud,
                        task_id="daily_generate_wordcloud"
                    )
                    
                    if task_added:
                        logger.info(f"已成功添加每日词云生成任务，执行时间: {daily_time}({daily_cron})")
                    else:
                        logger.error(f"添加每日词云生成任务失败，返回值为False")
                    
                except Exception as daily_task_error:
                    logger.error(f"添加每日词云生成任务失败: {daily_task_error}")
                    import traceback
                    logger.error(f"任务添加错误详情: {traceback.format_exc()}")
            else:
                logger.info("每日生成词云功能已禁用")
            
            # 启动调度器
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
            
            # 输出当前注册的所有任务信息
            tasks = getattr(self.scheduler, 'tasks', {})
            if tasks:
                logger.info(f"当前注册的定时任务数量: {len(tasks)}")
                for task_id, task_info in tasks.items():
                    if isinstance(task_info, dict) and 'next_run' in task_info:
                        next_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task_info['next_run']))
                        logger.info(f"任务 '{task_id}' 下次执行时间: {next_time}")
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
            # 跳过命令消息
            if event.message_str is not None and event.message_str.startswith("/"):
                return
            # 跳过机器人自身消息
            if event.get_sender_id() == event.get_self_id():
                return
            
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
            content = event.message_str if hasattr(event, 'message_str') else None
            msg_type = "群聊" if is_group else "私聊"
            
            # 尝试从消息链中获取非空内容描述
            message_desc = "[无文本内容]"
            try:
                if hasattr(event, 'get_messages') and callable(getattr(event, 'get_messages')):
                    messages = event.get_messages()
                    if messages:
                        content_types = []
                        for msg in messages:
                            if hasattr(msg, '__class__') and hasattr(msg.__class__, '__name__'):
                                msg_class = msg.__class__.__name__
                                if msg_class != 'Plain' and msg_class not in content_types:
                                    content_types.append(msg_class)
                        
                        if content_types:
                            message_desc = f"[{', '.join(content_types)}]"
            except Exception as e:
                logger.debug(f"提取消息类型失败: {e}")
            
            # 提取文本内容
            if content is None or content.strip() == "":
                # 输出详细日志，标记无文本内容
                logger.info(f"收到{msg_type}消息 - 会话ID: {session_id}, 发送者: {sender_name}({sender_id}), 内容: {message_desc}")
                
                # 将消息内容设为特殊标记，以便history_manager能识别出这是特殊消息
                if not hasattr(event, 'message_str') or event.message_str is None:
                    event.message_str = ""
                
                # 如果是图片等非文本内容，我们直接跳过不记录到词云数据
                # 因为词云只关注文本内容
                return True
            
            # 处理有文本内容的消息
            content = content.strip()
            
            # 检查消息是否为空
            if not content:
                logger.debug(f"跳过空消息 - 会话ID: {session_id}, 发送者: {sender_name}({sender_id})")
                return True  # 空消息直接跳过，不记录也不报错
            
            # 输出详细日志
            logger.info(f"收到{msg_type}消息 - 会话ID: {session_id}, 发送者: {sender_name}({sender_id}), 内容: {content[:30]}{'...' if len(content) > 30 else ''}")
            
            # 确保消息内容长度合理
            if len(content) > 1000:  # 防止过长的消息
                logger.warning(f"消息内容过长({len(content)}字符)，截断至1000字符")
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
                    if not session_id or len(session_id.split(':')) < 2:
                        logger.warning(f"保存消息到历史记录失败 - 可能是会话ID格式异常: {session_id}")
                    # 检查发送者信息是否完整
                    elif not sender_id or not sender_name:
                        logger.warning(f"保存消息到历史记录失败 - 发送者信息可能不完整: ID={sender_id}, 名称={sender_name}")
                    # 检查消息内容
                    elif not content:
                        logger.warning(f"保存消息到历史记录失败 - 消息内容为空")
                    else:
                        logger.warning(f"保存消息到历史记录失败 - 会话ID: {session_id}, 可能是数据库操作失败")
            except Exception as save_error:
                # 导入traceback模块
                try:
                    import traceback
                    error_stack = traceback.format_exc()
                    logger.error(f"保存消息过程中发生异常: {save_error}, 错误类型: {type(save_error).__name__}")
                    logger.error(f"错误堆栈: {error_stack}")
                except:
                    # 如果traceback也出错，使用简单日志
                    logger.error(f"保存消息过程中发生异常: {save_error}, 无法获取详细堆栈")
                
            # 继续处理事件，不阻断其他插件
            return True
        except Exception as e:
            logger.error(f"记录消息时发生错误: {e}")
            # 出错时仍然继续处理事件
            return True
    
    @filter.command(CMD_GENERATE)
    async def generate_wordcloud_command(self, event: AstrMessageEvent, days: int = None):
        """
        生成当前会话的词云图片
        
        参数:
            days: 统计最近几天的消息，默认为配置值或7天
        """
        try:
            # 检查群聊限制
            if event.get_group_id():
                group_id = event.get_group_id()
                if not is_group_enabled(group_id, self.enabled_groups):
                    yield event.plain_result(f"该群({group_id})未启用词云功能，无法生成词云。请联系管理员开启。")
                    return
        except Exception as e:
            logger.error(f"检查群聊限制失败: {e}")
            # 失败时继续执行，不阻止生成
        
        if days is None:
            days = self.config.get("history_days", 7)
        
        try:
            # 检查词云生成器是否初始化成功
            if self.wordcloud_generator is None:
                yield event.plain_result("词云生成器未初始化成功，正在尝试重新初始化...")
                try:
                    self._init_wordcloud_generator()
                    if self.wordcloud_generator is None:
                        yield event.plain_result("无法初始化词云生成器，请联系管理员检查日志。")
                        return
                except Exception as e:
                    yield event.plain_result(f"初始化词云生成器失败: {e}")
                    return
            
            # 提示开始生成
            yield event.plain_result(f"正在为您生成最近{days}天的聊天词云，请稍候...")
            
            # 获取会话ID
            session_id = event.unified_msg_origin
            group_id = event.get_group_id()
            
            # 获取历史消息
            message_texts = self.history_manager.get_message_texts(session_id, days)
            
            if not message_texts:
                yield event.plain_result(f"找不到最近{days}天的聊天记录，无法生成词云。请尝试使用 '/wc test' 命令生成测试词云。")
                return
            
            # 处理消息文本并生成词云
            word_counts = self.wordcloud_generator.process_texts(message_texts)
            
            # 设置标题
            title = f"{'群聊' if group_id else '私聊'}词云 - 最近{days}天"
            
            # 生成词云图片
            image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                word_counts, session_id, title=title
            )
            
            # 发送结果
            yield event.chain_result([
                Comp.Plain(f"词云生成成功，共统计了{len(message_texts)}条消息:"),
                Comp.Image.fromFileSystem(image_path)
            ])
            
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
            f"【词云插件配置】",
            f"自动生成: {'开启' if self.config.get('auto_generate_enabled', True) else '关闭'}",
            f"自动生成时间: {self.config.get('auto_generate_cron', '0 20 * * *')}",
            f"每日词云: {'开启' if self.config.get('daily_generate_enabled', True) else '关闭'}",
            f"每日词云时间: {self.config.get('daily_generate_time', '23:30')}",
            f"最大词数量: {self.config.get('max_word_count', 100)}",
            f"最小词长度: {self.config.get('min_word_length', 2)}",
            f"统计天数: {self.config.get('history_days', 7)}",
            f"背景颜色: {self.config.get('background_color', 'white')}",
            f"配色方案: {self.config.get('colormap', 'viridis')}",
            f"形状: {self.config.get('shape', 'circle')}"
        ]
        
        # 添加群聊配置信息
        if self.enabled_groups:
            config_info.append(f"启用的群: {', '.join(self.enabled_groups)}")
        else:
            config_info.append(f"启用的群: 全部（未指定特定群）")
        
        yield event.plain_result("\n".join(config_info))
    
    @wordcloud_group.command(CMD_HELP)
    async def help_command(self, event: AstrMessageEvent):
        """查看词云插件帮助"""
        help_text = [
            f"【词云插件帮助】",
            f"1. /wordcloud - 生成当前会话的词云",
            f"2. /wordcloud [天数] - 生成指定天数的词云",
            f"3. /wc config - 查看当前词云配置",
            f"4. /wc help - 显示本帮助信息",
            f"5. /wc test - 生成测试词云（无需历史数据）",
            f"6. /wc today - 生成今天的词云",
            f"7. /wc enable [群号] - 为指定群启用词云功能",
            f"8. /wc disable [群号] - 为指定群禁用词云功能",
            f"9. /wc clean_config - 清理过时的配置项",
            f"10. /wc force_daily - 强制执行每日词云生成（管理员）"
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
                    yield event.plain_result(f"该群({group_id})未启用词云功能，无法生成词云。请联系管理员开启。")
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
            yield event.chain_result([
                Comp.Plain("词云生成成功，这是一个测试词云:"),
                Comp.Image.fromFileSystem(image_path)
            ])
            
        except Exception as e:
            logger.error(f"生成测试词云失败: {e}")
            yield event.plain_result(f"生成测试词云失败: {str(e)}")
    
    @wordcloud_group.command("today")
    async def today_command(self, event: AstrMessageEvent):
        """生成今天的聊天词云"""
        try:
            # 检查群聊限制
            if event.get_group_id():
                group_id = event.get_group_id()
                if not is_group_enabled(group_id, self.enabled_groups):
                    yield event.plain_result(f"该群({group_id})未启用词云功能，无法生成词云。请联系管理员开启。")
                    return
        except Exception as e:
            logger.error(f"检查群聊限制失败: {e}")
            # 失败时继续执行，不阻止生成
        
        try:
            # 提示开始生成
            yield event.plain_result("正在生成今天的聊天词云，请稍候...")
            
            # 获取会话ID
            session_id = event.unified_msg_origin
            group_id = event.get_group_id()
            
            # 获取今天的消息
            message_texts = self.history_manager.get_todays_message_texts(session_id)
            
            if not message_texts:
                yield event.plain_result("今天还没有聊天记录，无法生成词云。")
                return
            
            # 处理消息文本并生成词云
            word_counts = self.wordcloud_generator.process_texts(message_texts)
            
            # 获取今天的日期
            date_str = format_date()
            
            # 设置标题
            title = f"{'群聊' if group_id else '私聊'}词云 - {date_str}"
            
            # 生成词云图片
            image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                word_counts, session_id, title=title
            )
            
            # 发送结果
            yield event.chain_result([
                Comp.Plain(f"今日词云生成成功，共统计了{len(message_texts)}条消息:"),
                Comp.Image.fromFileSystem(image_path)
            ])
            
        except Exception as e:
            logger.error(f"生成今日词云失败: {e}")
            import traceback
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
                if hasattr(self.config, "save_config") and callable(getattr(self.config, "save_config")):
                    self.config.save_config()
                    logger.info("更新并保存了群组配置")
            except Exception as config_error:
                logger.error(f"保存群组配置失败: {config_error}")
            
            yield event.plain_result(f"已为群 {group_id} 启用词云功能")
        except Exception as e:
            logger.error(f"启用群词云功能失败: {e}")
            yield event.plain_result(f"启用群词云功能失败: {str(e)}")
    
    @wordcloud_group.command("disable")
    async def disable_group_command(self, event: AstrMessageEvent, group_id: str = None):
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
                        active_group_id = self.history_manager.extract_group_id_from_session(session_id)
                        if active_group_id and active_group_id != group_id:
                            self.enabled_groups.add(active_group_id)
                    logger.info(f"从所有活跃群中排除目标群 {group_id}, 启用了 {len(self.enabled_groups)} 个群")
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
                if hasattr(self.config, "save_config") and callable(getattr(self.config, "save_config")):
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
                if cleaned and hasattr(self.config, "save_config") and callable(getattr(self.config, "save_config")):
                    self.config.save_config()
                    yield event.plain_result("已清理词云插件配置中的过时配置项。请刷新配置页面查看。")
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
                    group_id = self.history_manager.extract_group_id_from_session(session_id)
                    if group_id and not is_group_enabled(group_id, self.enabled_groups):
                        logger.info(f"群 {group_id} 未启用词云功能，跳过自动生成")
                        continue
                    
                    # 获取历史消息
                    message_texts = self.history_manager.get_message_texts(session_id, days)
                    
                    if not message_texts or len(message_texts) < 20:  # 至少要有20条消息才生成
                        continue
                    
                    # 处理消息文本并生成词云
                    word_counts = self.wordcloud_generator.process_texts(message_texts)
                    
                    # 生成词云图片
                    title = f"聊天词云 - 定时生成 - 最近{days}天"
                    image_path, path_obj = self.wordcloud_generator.generate_wordcloud(
                        word_counts, session_id, title=title
                    )
                    
                    # 发送结果
                    await self.scheduler.send_to_session(
                        session_id,
                        f"[自动词云] 这是最近{days}天的聊天词云，共统计了{len(message_texts)}条消息:",
                        str(path_obj)
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
        """每日生成词云的定时任务回调"""
        import datetime
        now = datetime.datetime.now()
        local_time = now.strftime("%Y-%m-%d %H:%M:%S")
        # --- 使用 DEBUG 级别并检查 self.debug_mode ---
        if self.debug_mode:
            logger.debug(f"daily_generate_wordcloud method ENTERED at {local_time}")
        
        try:
            daily_time = self.config.get("daily_generate_time", "23:30")
            try:
                hour, minute = parse_time_str(daily_time)
                now_hour, now_minute = now.hour, now.minute
                time_diff_minutes = abs((now_hour * 60 + now_minute) - (hour * 60 + minute))
                
                if self.debug_mode:
                    logger.debug(f"Expected execution time: {hour:02d}:{minute:02d}, Actual: {now_hour:02d}:{now_minute:02d}, Difference: {time_diff_minutes} mins")
                
                if time_diff_minutes > 30:
                     if self.debug_mode: # Keep warning level but make it conditional
                        logger.warning(f"Execution time difference is large ({time_diff_minutes} mins). Possible timezone issue, but continuing.")
            except Exception as time_error:
                logger.error(f"Failed to parse time info: {time_error}") # Keep as error
            
            date_str = format_date()
            if self.debug_mode:
                logger.debug(f"Current date: {date_str}. Time checks passed or logged.")
            
            if self.wordcloud_generator is None:
                if self.debug_mode:
                    logger.debug("Wordcloud generator is None. Attempting re-initialization.")
                try:
                    if self.debug_mode: logger.debug("Calling asyncio.to_thread for _init_wordcloud_generator [BEFORE AWAIT]")
                    await asyncio.to_thread(self._init_wordcloud_generator)
                    if self.debug_mode: logger.debug("asyncio.to_thread for _init_wordcloud_generator [AFTER AWAIT]")
                    if self.wordcloud_generator is None:
                        logger.error("Failed to re-initialize wordcloud generator. Aborting task.") # Keep as error
                        return
                    if self.debug_mode: logger.debug("Wordcloud generator re-initialized successfully.")
                except Exception as e:
                    logger.error(f"Exception during wordcloud generator re-initialization: {e}") # Keep as error
                    import traceback
                    logger.error(f"Initialization error details: {traceback.format_exc()}") # Keep as error
                    return
            
            if self.debug_mode: logger.debug("Calling asyncio.to_thread for get_active_group_sessions [BEFORE AWAIT]")
            active_group_sessions = await asyncio.to_thread(self.history_manager.get_active_group_sessions, days=1)
            if self.debug_mode: logger.debug(f"asyncio.to_thread for get_active_group_sessions [AFTER AWAIT]. Found {len(active_group_sessions)} sessions: {active_group_sessions}")
            
            if not active_group_sessions:
                 if self.debug_mode: # Keep warning level but make it conditional
                    logger.warning("No active group sessions found. Task ending.")
                 return
            
            if self.enabled_groups:
                 if self.debug_mode: logger.debug(f"Enabled groups: {self.enabled_groups}")
            else:
                 if self.debug_mode: logger.debug("No specific groups enabled, will attempt for all active.")
            if self.debug_mode: logger.debug(f"Enabled groups check done.")

            processed_count = 0
            skipped_count = 0
            error_count = 0
            
            for session_id in active_group_sessions:
                if self.debug_mode: logger.debug(f"Processing session {session_id} [LOOP START]")
                try:
                    if self.debug_mode: logger.debug(f"Session {session_id}: Calling extract_group_id_from_session [BEFORE AWAIT]")
                    group_id = await asyncio.to_thread(self.history_manager.extract_group_id_from_session, session_id)
                    if self.debug_mode: logger.debug(f"Session {session_id}: extract_group_id_from_session [AFTER AWAIT]. group_id: {group_id}")

                    if not group_id:
                        if self.debug_mode: logger.debug(f"Session {session_id}: group_id is None. Trying util function.")
                        from .utils import extract_group_id_from_session as util_extract_group_id
                        if self.debug_mode: logger.debug(f"Session {session_id}: Calling util_extract_group_id [BEFORE AWAIT]")
                        group_id = await asyncio.to_thread(util_extract_group_id, session_id)
                        if self.debug_mode: logger.debug(f"Session {session_id}: util_extract_group_id [AFTER AWAIT]. group_id: {group_id}")
                        
                    if not group_id:
                        if self.debug_mode: logger.debug(f"Session {session_id}: Still no group_id. Skipping.")
                        skipped_count += 1
                        continue
                    
                    if self.debug_mode: logger.debug(f"Session {session_id}: Group ID {group_id}. Checking if enabled.")
                    if not is_group_enabled(group_id, self.enabled_groups):
                        if self.debug_mode: logger.debug(f"Session {session_id}: Group {group_id} is not enabled. Skipping.")
                        skipped_count += 1
                        continue
                    
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Calling get_message_count_today [BEFORE AWAIT]")
                    message_count = await asyncio.to_thread(self.history_manager.get_message_count_today, session_id)
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): get_message_count_today [AFTER AWAIT]. Count: {message_count}")
                    
                    min_daily_messages = self.config.get("min_daily_messages", 10)
                    if message_count < min_daily_messages:
                        if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Message count {message_count} < {min_daily_messages}. Skipping.")
                        skipped_count += 1
                        continue
                    
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Calling get_todays_message_texts [BEFORE AWAIT]")
                    message_texts = await asyncio.to_thread(self.history_manager.get_todays_message_texts, session_id)
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): get_todays_message_texts [AFTER AWAIT]. Found {len(message_texts) if message_texts else 0} texts.")

                    if not message_texts:
                        if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): No message texts found. Skipping.")
                        skipped_count += 1
                        continue
                    
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Calling process_texts [BEFORE AWAIT]")
                    word_counts = await asyncio.to_thread(self.wordcloud_generator.process_texts, message_texts)
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): process_texts [AFTER AWAIT]. Found {len(word_counts) if word_counts else 0} word_counts.")

                    if not word_counts:
                        if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): No word counts. Skipping.")
                        skipped_count += 1
                        continue
                    
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Getting group name...")
                    group_name = f"群{group_id}"
                    try:
                        for platform_name in ["aiocqhttp", "qqofficial"]:
                            platform = self.context.get_platform(platform_name)
                            if platform and hasattr(platform, "get_group_info"):
                                try:
                                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Calling {platform_name}.get_group_info [BEFORE AWAIT]")
                                    group_info = await platform.get_group_info(group_id)
                                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): {platform_name}.get_group_info [AFTER AWAIT]")
                                    if group_info and "group_name" in group_info:
                                        group_name = group_info["group_name"]
                                        if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Got group name: {group_name}")
                                        break 
                                except Exception as platform_error:
                                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Failed to get group info from {platform_name}: {platform_error}")
                                    continue
                    except Exception as e:
                        if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Failed to get group name: {e}")
                    
                    title_template = self.config.get("daily_summary_title", "{date} {group_name} 今日词云")
                    title = title_template.format(date=date_str, group_name=group_name)
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Title: '{title}'. Calling generate_wordcloud [BEFORE AWAIT]")
                    
                    # generate_wordcloud is wrapped in to_thread below, keep internal logs
                    image_path, path_obj = await asyncio.to_thread(
                        self.wordcloud_generator.generate_wordcloud,
                        word_counts,
                        f"daily_{session_id.replace(':', '_')}", 
                        title=title
                    )
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): generate_wordcloud [AFTER AWAIT]. Image path: {image_path}")
                    
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Sending image. Checking path {path_obj}")
                    if not os.path.exists(str(path_obj)):
                        logger.error(f"Session {session_id} (Group {group_id}): Image file does not exist: {path_obj}. Cannot send.") # Keep as error
                        error_count += 1
                        continue
                        
                    message_to_send = f"{title}\n今天共有{message_count}条消息。"
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): Calling scheduler.send_to_session [BEFORE AWAIT] for target {session_id}")
                    send_success = await self.scheduler.send_to_session(
                        session_id, 
                        message_to_send,
                        str(path_obj) 
                    )
                    if self.debug_mode: logger.debug(f"Session {session_id} (Group {group_id}): scheduler.send_to_session [AFTER AWAIT]. Success: {send_success}")

                    if send_success:
                        if self.debug_mode: logger.debug(f"Successfully sent word cloud to group {group_id} (Session: {session_id})")
                        processed_count += 1
                    else:
                         if self.debug_mode: # Keep warning level but make it conditional
                            logger.warning(f"Failed to send word cloud to group {group_id} (Session: {session_id}). Check scheduler logs.")
                         error_count += 1
                            
                except Exception as e_loop:
                    logger.error(f"Exception in loop for session {session_id}: {e_loop}") # Keep as error
                    import traceback
                    logger.error(f"Loop error details: {traceback.format_exc()}") # Keep as error
                    error_count += 1
                    continue
                if self.debug_mode: logger.debug(f"Session {session_id} processing finished. Sleeping for 2 seconds.")
                await asyncio.sleep(2) 
            
            logger.info(f"每日词云生成任务执行完毕: 成功 {processed_count}, 跳过 {skipped_count}, 失败 {error_count}") # Concise final summary for INFO level
            if self.debug_mode: # Detailed summary only in debug mode
                logger.debug(f"Finished processing all sessions. Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}")

        except Exception as e_global:
            logger.error(f"Global exception in daily_generate_wordcloud: {e_global}") # Keep as error
            import traceback
            logger.error(f"Global error details: {traceback.format_exc()}") # Keep as error
        if self.debug_mode:
             logger.debug(f"daily_generate_wordcloud method EXITED.")
    
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
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            yield event.plain_result(f"强制执行每日词云生成任务失败: {str(e)}")
    
    async def terminate(self):
        """插件终止时的清理工作"""
        # 停止定时任务调度器
        if hasattr(self, 'scheduler'):
            self.scheduler.stop()
        
        logger.info("WordCloud插件已终止")
