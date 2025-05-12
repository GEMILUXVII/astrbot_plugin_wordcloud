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


# 使用全局变量跟踪调度器实例
_SCHEDULER_INSTANCES = {}
_SCHEDULER_LOCK = threading.Lock()


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
        # 检查是否有同一个上下文的调度器实例
        global _SCHEDULER_INSTANCES

        with _SCHEDULER_LOCK:
            # 使用上下文的ID作为标识符
            context_id = id(context)

            if context_id in _SCHEDULER_INSTANCES:
                existing_scheduler = _SCHEDULER_INSTANCES[context_id]
                if existing_scheduler.running:
                    logger.warning(
                        f"已存在运行中的调度器实例(ID: {context_id})，正在复用该实例。"
                    )
                    # 复制现有实例的属性
                    self.context = existing_scheduler.context
                    self.tasks = existing_scheduler.tasks
                    self.running = existing_scheduler.running
                    self.thread = existing_scheduler.thread
                    self.main_loop = existing_scheduler.main_loop
                    self.debug_mode = existing_scheduler.debug_mode
                    self._event_loop = getattr(existing_scheduler, "_event_loop", None)
                    self._poller_task = getattr(
                        existing_scheduler, "_poller_task", None
                    )
                    return
                else:
                    # 如果实例存在但没有运行，我们应该清理它
                    logger.info(f"发现未运行的调度器实例(ID: {context_id})，将替换它。")

            # 如果没有找到实例或实例没有运行，创建一个新实例
            self.context = context
            self.tasks: Dict[str, Dict[str, Any]] = {}
            self.running = False
            self.thread = None
            self.main_loop = main_loop
            self.debug_mode = debug_mode
            self._event_loop: Optional[asyncio.AbstractEventLoop] = None
            self._poller_task: Optional[asyncio.Task] = None

            # 将新实例添加到全局字典
            _SCHEDULER_INSTANCES[context_id] = self

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
            # 检查任务是否已存在
            if task_id in self.tasks:
                logger.warning(f"任务ID {task_id} 已存在，将被覆盖")

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

        # 确保没有旧的线程在运行
        if self.thread and self.thread.is_alive():
            logger.warning("调度器已有线程正在运行，尝试停止它")
            # 尝试优雅地停止旧线程
            try:
                old_running_state = self.running
                self.running = False
                self.thread.join(timeout=2.0)
                self.running = old_running_state
            except Exception as e:
                logger.error(f"停止旧线程时出错: {e}")

        # 创建新线程
        self.thread = threading.Thread(
            target=self._run_scheduler, name=f"TaskScheduler-{id(self)}"
        )
        self.thread.daemon = True
        self.thread.start()
        logger.info("调度器已启动")

    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            logger.warning("调度器未运行")
            return

        logger.info("正在停止调度器...")
        self.running = False  # Signal the async_poller to stop

        # Stop the asyncio event loop in the scheduler's thread
        if self._event_loop and self._event_loop.is_running():
            logger.info(
                "SCHED: Calling loop.stop() via call_soon_threadsafe to stop run_forever."
            )
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)

        if self.thread and self.thread.is_alive():
            try:
                # Wait for the scheduler thread to finish
                logger.info("SCHED: Waiting for scheduler thread to join...")
                self.thread.join(timeout=10.0)  # Increased timeout
                if self.thread.is_alive():
                    logger.warning("SCHED: Scheduler thread did not join in time.")
                else:
                    logger.info("SCHED: Scheduler thread joined successfully.")
            except Exception as e:
                logger.error(f"SCHED: Error stopping scheduler thread: {e}")

        # Event loop cleanup is now primarily handled in _run_scheduler's finally block
        # self._event_loop = None # Nullify after thread has joined and loop is closed by _run_scheduler

        logger.info("调度器已停止")

        # 从实例字典中移除自己
        with _SCHEDULER_LOCK:
            for context_id, scheduler in list(_SCHEDULER_INSTANCES.items()):
                if scheduler is self:
                    del _SCHEDULER_INSTANCES[context_id]
                    break

    async def _async_poller(self, loop: asyncio.AbstractEventLoop):
        """Asynchronous task poller running inside the scheduler's event loop."""
        logger.info("SCHED ASYNC_POLLER: Async poller task started.")
        last_heartbeat = time.time()
        heartbeat_interval = 600  # Original: 600 seconds (10 minutes)
        task_check_interval = 1.0  # Check tasks every second

        try:
            while self.running:
                now = time.time()
                current_time_str = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(now)
                )

                # Heartbeat log
                if now - last_heartbeat >= heartbeat_interval:
                    logger.info(
                        f"SCHED ASYNC_POLLER: Heartbeat. Current time: {current_time_str}, Task count: {len(self.tasks)}"
                    )
                    last_heartbeat = now

                for task_id, task_details in list(self.tasks.items()):
                    try:
                        if not all(
                            k in task_details
                            for k in ["next_run", "running", "cron", "callback"]
                        ):
                            missing_keys = [
                                k
                                for k in ["next_run", "running", "cron", "callback"]
                                if k not in task_details
                            ]
                            logger.warning(
                                f"SCHED ASYNC_POLLER: Task '{task_id}' missing keys: {missing_keys}"
                            )
                            continue

                        if (
                            now >= task_details["next_run"]
                            and not task_details["running"]
                        ):
                            exec_time_str = time.strftime(
                                "%Y-%m-%d %H:%M:%S",
                                time.localtime(task_details["next_run"]),
                            )
                            logger.info(
                                f"SCHED ASYNC_POLLER: Triggering task '{task_id}'. Scheduled: {exec_time_str}, Current: {current_time_str}"
                            )

                            task_details["running"] = True
                            task_details["next_run"] = (
                                task_details["cron"]
                                .get_next(datetime.datetime)
                                .timestamp()
                            )

                            future = loop.create_task(
                                self._execute_task(task_id, task_details)
                            )

                            current_task_id_for_callback = task_id

                            def _task_done_callback(f):
                                try:
                                    f.result()
                                    logger.info(
                                        f"SCHED ASYNC_POLLER: Task '{current_task_id_for_callback}' (from create_task) completed successfully."
                                    )
                                except asyncio.CancelledError:
                                    logger.warning(
                                        f"SCHED ASYNC_POLLER: Task '{current_task_id_for_callback}' (from create_task) was cancelled."
                                    )
                                except Exception as e_callback:
                                    logger.error(
                                        f"SCHED ASYNC_POLLER: Exception in executed task '{current_task_id_for_callback}': {e_callback}"
                                    )
                                    logger.error(
                                        f"SCHED ASYNC_POLLER: Traceback for task '{current_task_id_for_callback}': {traceback.format_exc()}"
                                    )

                            future.add_done_callback(_task_done_callback)

                    except Exception as e_inner_loop:
                        logger.error(
                            f"SCHED ASYNC_POLLER: Error in task processing loop for task_id '{task_id}': {e_inner_loop}"
                        )
                        logger.error(
                            f"SCHED ASYNC_POLLER: Traceback: {traceback.format_exc()}"
                        )
                        if task_id in self.tasks and isinstance(
                            self.tasks.get(task_id), dict
                        ):
                            self.tasks[task_id]["running"] = False

                await asyncio.sleep(task_check_interval)

            logger.info("SCHED ASYNC_POLLER: Exiting as self.running is False.")
        except asyncio.CancelledError:
            logger.info("SCHED ASYNC_POLLER: Poller task was cancelled.")
        except Exception as e_poller:
            logger.error(f"SCHED ASYNC_POLLER: Poller task crashed: {e_poller}")
            logger.error(f"SCHED ASYNC_POLLER: Traceback: {traceback.format_exc()}")

    def _run_scheduler(self) -> None:
        """Runs the scheduler in a dedicated thread with its own asyncio event loop."""
        logger.info("调度器线程已启动")
        loop: Optional[asyncio.AbstractEventLoop] = None

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._event_loop = loop
            logger.info("为调度器线程创建了新的事件循环")

            self._poller_task = loop.create_task(self._async_poller(loop))

            logger.info("SCHED: Starting event loop with run_forever().")
            loop.run_forever()  # This blocks until loop.stop() is called
            logger.info("SCHED: Event loop run_forever() has exited.")

        except asyncio.CancelledError:
            logger.info(
                "SCHED: _run_scheduler's run_forever() was cancelled (likely during stop)."
            )
        except Exception as e_outer:
            logger.error(f"SCHED: _run_scheduler outer error: {e_outer}")
            logger.error(
                f"SCHED: _run_scheduler outer traceback: {traceback.format_exc()}"
            )
        finally:
            logger.info("SCHED: _run_scheduler finally block entered.")

            if self._poller_task and not self._poller_task.done():
                logger.info("SCHED: Cancelling poller task in finally.")
                self._poller_task.cancel()
                if (
                    loop and not loop.is_closed() and not loop.is_running()
                ):  # if run_forever exited
                    # Need to run the loop briefly to process the cancellation
                    try:
                        logger.info(
                            "SCHED: Running loop briefly to process poller cancellation."
                        )
                        loop.run_until_complete(self._poller_task)
                    except asyncio.CancelledError:
                        logger.info(
                            "SCHED: Poller task successfully cancelled in finally."
                        )
                    except Exception as e_poll_cancel_wait:
                        logger.error(
                            f"SCHED: Exception waiting for poller task cancellation in finally: {e_poll_cancel_wait}"
                        )

            if loop and not loop.is_closed():
                logger.info(
                    "SCHED: Shutting down remaining tasks in event loop (finally)."
                )

                # Ensure loop is stopped if it was running (e.g. if run_forever exited due to error)
                if loop.is_running():
                    logger.info(
                        "SCHED: Loop was still running in finally, stopping it."
                    )
                    loop.stop()

                # Gather all remaining tasks
                pending_tasks = [
                    t
                    for t in asyncio.all_tasks(loop)
                    if t is not self._poller_task and not t.done()
                ]
                if pending_tasks:
                    logger.info(
                        f"SCHED: {len(pending_tasks)} other pending tasks to cancel/gather."
                    )
                    for t in pending_tasks:
                        t.cancel()
                    try:
                        # Run loop to process cancellations and gather results
                        loop.run_until_complete(
                            asyncio.gather(*pending_tasks, return_exceptions=True)
                        )
                        logger.info("SCHED: Gathered other pending tasks in finally.")
                    except Exception as e_gather_final:
                        logger.error(
                            f"SCHED: Error during final gather in finally: {e_gather_final}"
                        )

                if hasattr(loop, "shutdown_asyncgens") and callable(
                    loop.shutdown_asyncgens
                ):
                    try:
                        logger.info("SCHED: Shutting down asyncgens in finally.")
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except RuntimeError as e_gens_runtime:
                        logger.warning(
                            f"SCHED: Runtime error shutting down asyncgens in finally (may be ok if loop closed): {e_gens_runtime}"
                        )
                    except Exception as e_gens:
                        logger.error(
                            f"SCHED: Error shutting down asyncgens in finally: {e_gens}"
                        )

                if not loop.is_closed():
                    logger.info("SCHED: Closing event loop in finally.")
                    loop.close()
                else:
                    logger.info("SCHED: Event loop was already closed in finally.")

            self._event_loop = None  # Clear the loop reference
            self._poller_task = None  # Clear task reference
            logger.info("调度器线程已退出 (end of _run_scheduler)")

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
                        try:
                            # 使用超时来防止协程长时间运行
                            # import asyncio # Already imported at top
                            # 设置一个合理的超时时间，这里使用30分钟
                            timeout = 30 * 60  # 30分钟
                            try:
                                await asyncio.wait_for(coro, timeout=timeout)
                                if self.debug_mode:
                                    logger.debug(
                                        f"SCHED: [{task_id}] Successfully AWAITED the coroutine."
                                    )
                                logger.info(f"[{task_id}] 成功执行协程回调函数")
                            except asyncio.TimeoutError:
                                logger.error(
                                    f"[{task_id}] 协程执行超时（超过{timeout}秒）"
                                )
                        except Exception as await_error:
                            logger.error(
                                f"[{task_id}] 等待协程执行时出错: {await_error}"
                            )
                            import traceback

                            logger.error(
                                f"[{task_id}] 协程执行错误详情: {traceback.format_exc()}"
                            )
                    else:
                        logger.error(f"[{task_id}] 协程对象为None，无法执行")
                else:
                    # 如果不是协程函数，直接调用
                    if self.debug_mode:
                        logger.debug(
                            f"SCHED: [{task_id}] Callback is NOT a coroutine function. Will call directly."
                        )
                    result = callback()
                    if self.debug_mode:
                        logger.debug(
                            f"SCHED: [{task_id}] Successfully called regular function. Result: {result}"
                        )
                    logger.info(f"[{task_id}] 成功执行普通回调函数")
            except Exception as call_error:
                logger.error(f"[{task_id}] 执行回调函数时出错: {call_error}")
                import traceback

                logger.error(f"[{task_id}] 执行错误详情: {traceback.format_exc()}")
                if self.debug_mode:
                    logger.debug(
                        f"SCHED: [{task_id}] EXCEPTION during execution: {call_error}"
                    )

            # 计算执行时间
            execution_time = time.time() - execution_start
            logger.info(f"[{task_id}] 任务执行完成，耗时: {execution_time:.2f}秒")
            if self.debug_mode:
                logger.debug(
                    f"SCHED: [{task_id}] Task execution completed in {execution_time:.2f} seconds"
                )
        except Exception as e:
            logger.error(f"[{task_id}] 执行任务过程中出错: {e}")
            import traceback

            logger.error(f"[{task_id}] 任务执行错误详情: {traceback.format_exc()}")
            if self.debug_mode:
                logger.debug(f"SCHED: [{task_id}] EXCEPTION in _execute_task: {e}")
        finally:
            # 无论成功失败，都重置任务状态
            try:
                if task_id in self.tasks:
                    self.tasks[task_id]["running"] = False
                    if self.debug_mode:
                        logger.debug(
                            f"SCHED: [{task_id}] Reset task running state to False"
                        )
            except Exception as reset_error:
                logger.error(f"[{task_id}] 重置任务状态时出错: {reset_error}")
                if self.debug_mode:
                    logger.debug(
                        f"SCHED: [{task_id}] EXCEPTION when resetting task state: {reset_error}"
                    )

            if self.debug_mode:
                logger.debug(f"SCHED: [{task_id}] _execute_task EXITED")

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
