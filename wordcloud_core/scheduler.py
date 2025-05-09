"""
词云插件的定时任务调度器
"""

import asyncio
import threading
import time
import os
import datetime
from typing import Dict, Any, Callable, Optional, Set, List
import inspect
import traceback

from croniter import croniter
import astrbot.api.message_components as Comp
from astrbot.api.event import MessageChain
from astrbot.api import logger


class TaskScheduler:
    """
    定时任务调度器类，用于管理定时任务
    """

    def __init__(
        self, context, main_loop: asyncio.AbstractEventLoop, debug_mode: bool = False
    ):
        """
        初始化定时任务调度器

        Args:
            context: AstrBot上下文
            main_loop: 主事件循环的引用
            debug_mode: 是否启用调试模式
        """
        self.context = context
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.thread = None
        self.main_loop = main_loop
        self.debug_mode = debug_mode  # Store debug mode flag
        logger.info(
            f"TaskScheduler initialized with main loop ID: {id(self.main_loop)}, Debug Mode: {self.debug_mode}"
        )

    def add_task(self, cron_expression: str, callback, task_id: str) -> bool:
        """
        添加定时任务

        Args:
            cron_expression: cron表达式，如 "30 20 * * *"（分 时 日 月 周）
            callback: 回调函数，必须是可等待的
            task_id: 任务ID，用于标识任务

        Returns:
            是否成功添加任务
        """
        try:
            # 验证cron表达式
            if not croniter.is_valid(cron_expression):
                logger.error(f"无效的cron表达式: {cron_expression}")
                return False

            # 获取时区信息
            timezone_offset = -time.timezone // 3600  # 转换为小时
            logger.info(
                f"系统时区信息: UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}"
            )

            # 创建croniter对象
            current_time_dt = datetime.datetime.now()
            logger.info(
                f"当前本地时间: {current_time_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            try:
                cron = croniter(cron_expression, current_time_dt)

                # 获取下一次执行时间
                next_run_datetime = cron.get_next(datetime.datetime)
                next_run = next_run_datetime.timestamp()  # 转为时间戳

                # 输出详细的时间信息以便调试
                next_run_str = datetime.datetime.fromtimestamp(next_run).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                logger.info(f"任务 {task_id} 下次执行时间: {next_run_str} (本地时间)")
                # 添加任务
                self.tasks[task_id] = {
                    "cron_expression": cron_expression,
                    "callback": callback,
                    "next_run": next_run,
                    "cron": cron,
                    "running": False,
                }

                logger.info(
                    f"成功添加定时任务: {task_id}, 下次执行时间: {next_run_str}"
                )
                return True

            except Exception as e:
                logger.error(f"创建cron对象失败: {e}")
                logger.error(f"错误详情: {traceback.format_exc()}")
                return False

        except Exception as e:
            logger.error(f"添加定时任务失败: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """
        移除定时任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功移除任务
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"成功移除定时任务: {task_id}")
            return True
        else:
            logger.warning(f"任务ID不存在: {task_id}")
        return False

    def start(self) -> None:
        """启动调度器"""
        if self.running:
            logger.warning("调度器已经在运行")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        logger.info("调度器已启动")

    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            logger.warning("调度器未运行")
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("调度器已停止")

    def _run_scheduler(self) -> None:
        """运行调度器线程"""
        logger.info("调度器线程已启动")
        last_heartbeat = time.time()
        heartbeat_interval = 600  # 每10分钟记录一次心跳日志

        # 创建一个线程专用的事件循环
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("为调度器线程创建了新的事件循环")
        except Exception as e:
            logger.error(f"为调度器线程创建事件循环失败: {e}")
            logger.error(f"事件循环创建错误详情: {traceback.format_exc()}")
            return

        while self.running:
            try:
                now = time.time()
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))

                # 记录心跳日志
                if now - last_heartbeat >= heartbeat_interval:
                    logger.info(
                        f"调度器正在运行 - 当前时间: {current_time}, 任务数量: {len(self.tasks)}"
                    )
                    last_heartbeat = now
                else:
                    logger.debug(f"调度器检查时间点: {current_time}")

                # 检查任务是否需要执行
                for task_id, task in list(self.tasks.items()):
                    try:
                        # 确保任务有所有必要的字段
                        if not all(
                            k in task
                            for k in ["next_run", "running", "cron", "callback"]
                        ):
                            missing_keys = [
                                k
                                for k in ["next_run", "running", "cron", "callback"]
                                if k not in task
                            ]
                            logger.warning(
                                f"任务 {task_id} 缺少必要字段: {missing_keys}"
                            )
                            continue

                        next_run = task["next_run"]
                        scheduled_time = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(next_run)
                        )
                        time_diff = next_run - now

                        # 输出即将执行的任务信息
                        if 0 < time_diff < 60:  # 如果任务将在1分钟内执行
                            logger.info(
                                f"任务 {task_id} 将在 {time_diff:.1f} 秒后执行，计划时间: {scheduled_time} (本地时间)"
                            )
                        elif (
                            time_diff < 0
                            and abs(time_diff) > 300
                            and not task["running"]
                        ):
                            # 任务已经过期5分钟以上但尚未执行
                            logger.warning(
                                f"发现过期未执行的任务 {task_id}，应在 {scheduled_time} 执行，已延迟 {abs(time_diff):.1f} 秒"
                            )

                        # 三种条件会触发任务执行：
                        # 1. 已到执行时间（next_run <= now）
                        # 2. 任务未在运行中（not task["running"]）
                        # 3. 如果任务已经过期超过5秒但不到1小时，仍然执行（防止小的时间差异或系统休眠导致任务被跳过）
                        on_time_execution = next_run <= now
                        grace_period_execution = 5 < now - next_run < 3600

                        if (on_time_execution or grace_period_execution) and not task[
                            "running"
                        ]:
                            # 记录任务执行时间
                            execution_time = time.strftime(
                                "%Y-%m-%d %H:%M:%S", time.localtime(now)
                            )

                            if grace_period_execution:
                                logger.warning(
                                    f"延迟执行任务: {task_id}，当前时间: {execution_time}，计划时间: {scheduled_time}，延迟: {now - next_run:.1f}秒"
                                )
                            else:
                                logger.info(
                                    f"开始执行定时任务: {task_id}，执行时间: {execution_time}，计划时间: {scheduled_time}"
                                )

                            # 标记任务为运行中
                            task["running"] = True

                            # 获取主应用的事件循环用于执行任务
                            try:
                                # --- 使用存储的主循环引用 ---
                                if not self.main_loop:
                                    logger.error(
                                        f"SCHED_CRITICAL_ERROR: [{task_id}] Stored main_loop reference is None! Cannot submit task."
                                    )
                                    task["running"] = False
                                    continue

                                loop_running = self.main_loop.is_running()
                                if self.debug_mode:
                                    logger.debug(
                                        f"SCHED_RUNNER: [{task_id}] Using stored main loop for task submission: ID {id(self.main_loop)}, Running: {loop_running}"
                                    )

                                if not loop_running:
                                    # Keep CRITICAL log level, but check debug mode before logging potentially sensitive future state
                                    logger.critical(
                                        f"SCHED_CRITICAL_ERROR: [{task_id}] Stored main loop (ID {id(self.main_loop)}) is NOT RUNNING when trying to submit task! Task cannot execute."
                                    )
                                    # Skip submission if loop is not running
                                    task["running"] = (
                                        False  # Ensure task is marked not running
                                    )
                                    continue  # Skip this task attempt

                                coro_to_run = self._execute_task(task_id, task)
                                if self.debug_mode:
                                    logger.debug(
                                        f"SCHED_RUNNER: [{task_id}] Coroutine object for _execute_task created: {type(coro_to_run)}"
                                    )

                                future = asyncio.run_coroutine_threadsafe(
                                    coro_to_run, self.main_loop
                                )
                                if self.debug_mode:
                                    logger.debug(
                                        f"SCHED_RUNNER: [{task_id}] run_coroutine_threadsafe called using stored loop. Future object: {future}. State: {future._state if hasattr(future, '_state') else 'N/A'}"
                                    )
                                # ------------------------------

                                # 定义回调函数
                                def handle_future_done(fut):
                                    # Make internal runner logs debug level
                                    if self.debug_mode:
                                        logger.debug(
                                            f"SCHED_RUNNER: [{task_id}] handle_future_done CALLED. Future state: {fut._state if hasattr(fut, '_state') else 'N/A'}"
                                        )
                                    try:
                                        result = fut.result()
                                        if self.debug_mode:
                                            logger.debug(
                                                f"SCHED_RUNNER: [{task_id}] Future result: {result}"
                                            )
                                        logger.info(
                                            f"任务 {task_id} 在主循环中成功完成."
                                        )
                                    except asyncio.CancelledError:
                                        logger.warning(
                                            f"任务 {task_id} 在主循环中被取消."
                                        )  # Keep warning level
                                        if self.debug_mode:
                                            logger.debug(
                                                f"SCHED_RUNNER: [{task_id}] Future was cancelled."
                                            )
                                    except Exception as e_inner:
                                        if self.debug_mode:
                                            logger.debug(
                                                f"SCHED_RUNNER: [{task_id}] Exception from future: {e_inner}"
                                            )
                                        logger.error(
                                            f"任务 {task_id} 在主循环中执行失败: {e_inner}"
                                        )
                                        logger.error(
                                            f"任务 {task_id} 错误详情 (从主循环回调): {traceback.format_exc()}"
                                        )

                                future.add_done_callback(handle_future_done)
                                if self.debug_mode:
                                    logger.debug(
                                        f"SCHED_RUNNER: [{task_id}] handle_future_done callback ADDED to future."
                                    )

                            except Exception as e_submit:
                                logger.error(
                                    f"提交任务 {task_id} 到主事件循环失败: {e_submit}"
                                )  # Keep as error
                                task["running"] = False
                                logger.error(
                                    f"任务提交错误详情: {traceback.format_exc()}"
                                )  # Keep as error
                                if self.debug_mode:  # Add debug log for context
                                    logger.debug(
                                        f"SCHED_RUNNER: [{task_id}] Failed to submit task using stored main event loop: {e_submit}"
                                    )
                                    logger.debug(
                                        f"SCHED_RUNNER: [{task_id}] Task submission error details: {traceback.format_exc()}"
                                    )

                    except Exception as task_check_error:
                        logger.error(f"检查任务 {task_id} 时出错: {task_check_error}")
                        logger.error(f"任务检查错误详情: {traceback.format_exc()}")

                # 每1秒检查一次任务
                time.sleep(1)
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                logger.error(f"调度器循环错误详情: {traceback.format_exc()}")
                time.sleep(5)  # 出错后等待5秒再继续

        # 关闭事件循环
        try:
            loop.close()
            logger.info("调度器线程的事件循环已关闭")
        except Exception as e:
            logger.error(f"关闭事件循环失败: {e}")

        logger.info("调度器线程已退出")

    async def _execute_task(self, task_id: str, task: Dict[str, Any]) -> None:
        """
        执行定时任务

        Args:
            task_id: 任务ID
            task: 任务信息
        """
        current_loop_id = None
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            if self.debug_mode:
                logger.debug(
                    f"SCHED: [{task_id}] _execute_task: Cannot get current running loop."
                )

        if self.debug_mode:
            logger.debug(
                f"SCHED: [{task_id}] _execute_task ENTERED. Will run in loop ID: {current_loop_id if current_loop_id else 'Unknown'}"
            )
        try:
            # Keep essential start log at INFO level
            start_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
            )
            logger.info(f"[{task_id}] 开始执行定时任务，开始时间: {start_time_str}")
            execution_start = time.time()

            callback = task.get("callback")
            if not callback or not callable(callback):
                logger.error(f"[{task_id}] 任务回调函数无效或不可调用")  # Keep as error
                if self.debug_mode:
                    logger.debug(
                        f"SCHED: [{task_id}] Callback is invalid or not callable."
                    )
                return

            if self.debug_mode:
                logger.debug(
                    f"SCHED: [{task_id}] Callback obtained: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}"
                )

            try:
                import inspect

                if inspect.iscoroutinefunction(callback):
                    if self.debug_mode:
                        logger.debug(
                            f"SCHED: [{task_id}] Callback is a coroutine function. Preparing to call it to get coroutine object."
                        )
                    coro = None
                    try:
                        coro = callback()
                        if self.debug_mode:
                            logger.debug(
                                f"SCHED: [{task_id}] Successfully CALLED callback function, got coroutine object: {type(coro)}"
                            )
                    except Exception as coro_creation_e:
                        logger.error(
                            f"[{task_id}] 调用回调函数创建协程对象时出错: {coro_creation_e}"
                        )  # Keep as error
                        import traceback

                        logger.error(
                            f"[{task_id}] 协程创建错误详情: {traceback.format_exc()}"
                        )  # Keep as error
                        if self.debug_mode:
                            logger.debug(
                                f"SCHED: [{task_id}] EXCEPTION during calling callback() to get coroutine object: {coro_creation_e}"
                            )
                        raise

                    if coro is not None:
                        if self.debug_mode:
                            logger.debug(
                                f"SCHED: [{task_id}] Preparing to AWAIT the coroutine object."
                            )
                        await coro
                        if self.debug_mode:
                            logger.debug(
                                f"SCHED: [{task_id}] Successfully AWAITED the coroutine."
                            )
                        logger.info(f"[{task_id}] 成功执行协程回调函数")
                    else:
                        logger.error(
                            f"[{task_id}] 协程对象为空，无法执行 await."
                        )  # Keep as error
                        if self.debug_mode:
                            logger.debug(
                                f"SCHED: [{task_id}] Coroutine object is None after creation attempt, cannot await."
                            )

                else:
                    logger.warning(
                        f"[{task_id}] 任务回调不是协程函数，尝试直接执行"
                    )  # Keep as warning
                    if self.debug_mode:
                        logger.debug(
                            f"SCHED: [{task_id}] Task callback is not a coroutine function, executing directly."
                        )
                    callback()
                    logger.info(f"[{task_id}] 成功执行非协程回调函数")
            except Exception as callback_error:
                logger.error(
                    f"[{task_id}] 执行回调函数时出错: {callback_error}"
                )  # Keep as error
                import traceback

                logger.error(
                    f"[{task_id}] 回调执行错误详情: {traceback.format_exc()}"
                )  # Keep as error
                raise

            execution_time = time.time() - execution_start
            logger.info(f"[{task_id}] 定时任务执行完成，耗时: {execution_time:.2f}秒")
        except Exception as e:
            logger.error(
                f"[{task_id}] 执行定时任务的主体部分失败: {e}"
            )  # Keep as error
            import traceback

            logger.error(
                f"[{task_id}] 任务主体执行错误详情: {traceback.format_exc()}"
            )  # Keep as error
        finally:
            if self.debug_mode:  # Make finally log debug
                logger.debug(
                    f"[{task_id}] _execute_task 执行完毕 (finally块)，事件循环 ID: {current_loop_id if current_loop_id else '未知'}"
                )
            # --- Update next run time logic (keep INFO for essential updates) ---
            if task_id in self.tasks:
                try:
                    cron = task.get("cron")
                    if not cron:
                        from croniter import croniter

                        cron_expression = task.get("cron_expression", "0 0 * * *")
                        logger.warning(
                            f"[{task_id}] cron对象丢失，使用表达式重新创建: {cron_expression}"
                        )  # Keep warning
                        import datetime

                        current_time_dt_finally = datetime.datetime.now()
                        cron = croniter(cron_expression, current_time_dt_finally)
                        task["cron"] = cron

                    import datetime

                    next_run_datetime = cron.get_next(datetime.datetime)
                    next_run = next_run_datetime.timestamp()
                    task["next_run"] = next_run
                    next_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(next_run)
                    )
                    task["running"] = False
                    time_diff = next_run - time.time()
                    hours = int(time_diff // 3600)
                    minutes = int((time_diff % 3600) // 60)
                    logger.info(
                        f"[{task_id}] 更新任务下次执行时间: {next_time} (本地时间) (还有{hours}小时{minutes}分钟)"
                    )  # Keep essential log
                except Exception as e_update:
                    logger.error(
                        f"[{task_id}] 更新任务下次执行时间失败: {e_update}"
                    )  # Keep error
                    import traceback

                    logger.error(
                        f"[{task_id}] 更新时间错误详情: {traceback.format_exc()}"
                    )  # Keep error
                    task["next_run"] = time.time() + 3600
                    task["running"] = False
                    fallback_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(task["next_run"])
                    )
                    logger.warning(
                        f"[{task_id}] 已设置任务一小时后重试，时间: {fallback_time}"
                    )  # Keep warning
        if self.debug_mode:
            logger.debug(f"SCHED: [{task_id}] _execute_task EXITED.")

    async def send_to_session(
        self, session_id: str, message_text: str, image_path: Optional[str] = None
    ) -> bool:
        """
        向指定会话发送消息

        Args:
            session_id: 会话ID
            message_text: 消息文本
            image_path: 可选的图片路径

        Returns:
            是否成功发送消息
        """
        try:
            logger.info(f"准备发送消息到会话: {session_id}")

            # 尝试多种会话ID格式
            attempted_session_ids = []
            success = False

            # 检查图片路径是否存在
            if image_path and not os.path.exists(image_path):
                logger.error(f"图片路径不存在: {image_path}")
                # 尝试查找可能存在的图片文件
                if os.path.dirname(image_path):
                    dir_path = os.path.dirname(image_path)
                    if os.path.exists(dir_path):
                        files = os.listdir(dir_path)
                        logger.info(f"目录 {dir_path} 中存在的文件: {files}")

                        # 尝试找到类似名称的图片文件
                        basename = os.path.basename(image_path)
                        for file in files:
                            if file.startswith(basename.split(".")[0]):
                                logger.info(
                                    f"找到可能的替代图片: {os.path.join(dir_path, file)}"
                                )
                                image_path = os.path.join(dir_path, file)
                                break

            # 创建消息链
            message_components = [Comp.Plain(message_text)]

            # 如果提供了图片路径，添加图片组件
            if image_path and os.path.exists(image_path):
                try:
                    logger.info(f"添加图片到消息: {image_path}")
                    message_components.append(Comp.Image.fromFileSystem(image_path))
                except Exception as img_error:
                    logger.error(f"添加图片到消息链失败: {img_error}")
                    logger.error(f"添加图片错误详情: {traceback.format_exc()}")
                    # 继续发送纯文本消息

            # 创建消息链
            message_chain = MessageChain(message_components)

            # 首先尝试使用原始会话ID
            logger.info(f"尝试使用原始会话ID发送: {session_id}")
            attempted_session_ids.append(session_id)
            success = await self.context.send_message(session_id, message_chain)

            # 如果失败，尝试使用其他会话ID格式
            if not success:
                # 检查是否是群号，如果是，尝试构建完整会话ID
                if session_id.isdigit() or (":" not in session_id):
                    # 从session_id提取可能的群号
                    group_id = session_id
                    if ":" in session_id:
                        # 可能是部分会话ID，尝试提取最后部分作为群号
                        parts = session_id.split(":")
                        group_id = parts[-1]

                    # 尝试QQ常见会话ID格式
                    for platform in ["aiocqhttp", "qqofficial"]:
                        for msg_type in ["GroupMessage", "group"]:
                            fixed_id = f"{platform}:{msg_type}:{group_id}"
                            if fixed_id not in attempted_session_ids:
                                logger.info(f"尝试使用构造会话ID发送: {fixed_id}")
                                attempted_session_ids.append(fixed_id)
                                success = await self.context.send_message(
                                    fixed_id, message_chain
                                )
                                if success:
                                    logger.info(f"使用会话ID {fixed_id} 发送成功")
                                    break
                        if success:
                            break

                # 如果仍未成功，尝试直接获取平台实例并发送
                if not success and group_id.isdigit():
                    try:
                        # 尝试使用aiocqhttp平台直接发送
                        platform = self.context.get_platform("aiocqhttp")
                        if platform and hasattr(platform, "send_group_msg"):
                            logger.info(
                                f"尝试使用aiocqhttp平台直接发送到群: {group_id}"
                            )
                            try:
                                await platform.send_group_msg(
                                    group_id=group_id, message=message_chain
                                )
                                logger.info(f"使用aiocqhttp平台发送成功")
                                success = True
                            except Exception as e:
                                logger.error(f"使用aiocqhttp平台发送失败: {e}")

                        # 尝试使用qqofficial平台
                        if not success:
                            platform = self.context.get_platform("qqofficial")
                            if platform and hasattr(platform, "send_group_msg"):
                                logger.info(
                                    f"尝试使用qqofficial平台直接发送到群: {group_id}"
                                )
                                try:
                                    await platform.send_group_msg(
                                        group_id=group_id, message=message_chain
                                    )
                                    logger.info(f"使用qqofficial平台发送成功")
                                    success = True
                                except Exception as e:
                                    logger.error(f"使用qqofficial平台发送失败: {e}")
                    except Exception as platform_error:
                        logger.error(f"尝试直接使用平台发送失败: {platform_error}")

            if success:
                logger.info(f"成功发送消息到会话: {session_id}")
            else:
                logger.warning(f"所有尝试都失败，无法发送消息到会话: {session_id}")
                logger.warning(f"尝试过的会话ID: {attempted_session_ids}")

            return success
        except Exception as e:
            logger.error(f"发送消息到会话失败: {session_id}, 错误: {e}")
            logger.error(f"发送消息错误详情: {traceback.format_exc()}")
            return False
