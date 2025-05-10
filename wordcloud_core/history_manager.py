"""
聊天历史记录管理器
"""

import json
import time
import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
import traceback

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context

from ..utils import get_current_timestamp, get_day_start_end_timestamps


class HistoryManager:
    """聊天历史记录管理器类"""

    def __init__(self, context: Context):
        """
        初始化历史记录管理器

        Args:
            context: AstrBot上下文
        """
        self.context = context
        self.db = self.context.get_db()

        # 确保数据库中有我们需要的表
        self._ensure_table()

    def _ensure_table(self) -> None:
        """确保数据库中有消息历史表"""
        # 创建历史消息表，表名加上插件前缀避免冲突
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS wordcloud_message_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_name TEXT,
            message TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            is_group BOOLEAN NOT NULL
        );
        """
        try:
            # 在AstrBot中，SQLiteDatabase没有直接的execute方法
            # 通常会有_exec_sql或其他方法
            if hasattr(self.db, "_exec_sql"):
                self.db._exec_sql(create_table_sql)
            else:
                # 尝试其他通用方法，如果没有_exec_sql
                if hasattr(self.db, "execute"):
                    self.db.execute(create_table_sql)
                    if hasattr(self.db, "commit"):
                        self.db.commit()

            # 创建索引以提高查询性能
            try:
                # 为session_id创建索引
                index_sql = """
                CREATE INDEX IF NOT EXISTS idx_wordcloud_session_id ON wordcloud_message_history (session_id);
                """
                if hasattr(self.db, "_exec_sql"):
                    self.db._exec_sql(index_sql)
                else:
                    if hasattr(self.db, "execute"):
                        self.db.execute(index_sql)
                        if hasattr(self.db, "commit"):
                            self.db.commit()

                # 为timestamp创建索引
                timestamp_index_sql = """
                CREATE INDEX IF NOT EXISTS idx_wordcloud_timestamp ON wordcloud_message_history (timestamp);
                """
                if hasattr(self.db, "_exec_sql"):
                    self.db._exec_sql(timestamp_index_sql)
                else:
                    if hasattr(self.db, "execute"):
                        self.db.execute(timestamp_index_sql)
                        if hasattr(self.db, "commit"):
                            self.db.commit()

                # 为session_id和timestamp组合创建索引，用于高效查询特定会话的特定时间范围消息
                combined_index_sql = """
                CREATE INDEX IF NOT EXISTS idx_wordcloud_session_timestamp ON wordcloud_message_history (session_id, timestamp);
                """
                if hasattr(self.db, "_exec_sql"):
                    self.db._exec_sql(combined_index_sql)
                else:
                    if hasattr(self.db, "execute"):
                        self.db.execute(combined_index_sql)
                        if hasattr(self.db, "commit"):
                            self.db.commit()

                logger.info("WordCloud历史消息表索引创建成功")
            except Exception as e:
                logger.warning(f"创建WordCloud历史消息表索引失败，这不会影响功能: {e}")

            logger.info("WordCloud历史消息表创建成功或已存在")
        except Exception as e:
            logger.error(f"创建WordCloud历史消息表失败: {e}")

    def _get_db_cursor(self):
        """
        获取数据库游标，处理连接问题

        Returns:
            数据库游标对象
        """
        try:
            # 尝试直接获取cursor
            return self.db.conn.cursor()
        except Exception as e:
            # 如果失败，尝试重新获取连接
            if hasattr(self.db, "_get_conn") and callable(
                getattr(self.db, "_get_conn")
            ):
                conn = self.db._get_conn(self.db.db_path)
                return conn.cursor()
            else:
                logger.error(f"无法获取数据库连接: {e}")
                raise

    def save_message(self, event: AstrMessageEvent) -> bool:
        """
        保存消息到历史记录

        Args:
            event: 消息事件

        Returns:
            是否保存成功
        """
        try:
            # session_id = event.unified_msg_origin # 旧的获取方式
            sender_id = event.get_sender_id()
            sender_name = event.get_sender_name()
            message = event.message_str if hasattr(event, "message_str") else None
            timestamp = get_current_timestamp()

            group_id_val = event.get_group_id()
            is_group = bool(group_id_val)

            session_id_to_save: str
            if group_id_val:  # 是群聊消息
                platform_name = event.get_platform_name()
                if not platform_name:  # 做个兜底，万一平台名获取不到
                    platform_name = "unknown_platform"
                session_id_to_save = f"{platform_name}_group_{group_id_val}"
            else:  # 非群聊消息（例如私聊）
                session_id_to_save = event.unified_msg_origin

            # 增强空消息检测逻辑
            if message is None:
                # 尝试从其他来源获取消息内容
                try:
                    # 尝试从消息链中提取纯文本内容
                    if hasattr(event, "get_messages") and callable(
                        getattr(event, "get_messages")
                    ):
                        messages = event.get_messages()
                        text_parts = []
                        for msg in messages:
                            if hasattr(msg, "text") and msg.text:
                                text_parts.append(msg.text)
                        if text_parts:
                            message = " ".join(text_parts)

                    # 尝试从message_obj获取内容
                    if not message and hasattr(event, "message_obj"):
                        if hasattr(event.message_obj, "raw_message"):
                            message = event.message_obj.raw_message
                        elif hasattr(event.message_obj, "message"):
                            message = str(event.message_obj.message)
                except Exception as e:
                    logger.debug(f"尝试提取消息内容失败: {e}")

                if not message:
                    logger.debug(
                        f"跳过None消息: 会话ID={session_id_to_save}, 发送者={sender_name}"
                    )
                    return False

            # 确保message是字符串
            if not isinstance(message, str):
                try:
                    message = str(message)
                except:
                    logger.debug(f"消息内容无法转换为字符串: {type(message)}")
                    return False

            # 清理消息内容，去除前后空白
            message = message.strip()

            # 过滤空消息
            if not message:
                logger.debug(
                    f"跳过空消息: 会话ID={session_id_to_save}, 发送者={sender_name}"
                )
                return False

            # 日志详细记录收到的消息
            logger.debug(
                f"准备保存消息: 会话ID={session_id_to_save}, 发送者={sender_name}, 内容前30字符: {message[:30]}..."
            )

            # 插入数据
            insert_sql = """
            INSERT INTO wordcloud_message_history 
            (session_id, sender_id, sender_name, message, timestamp, is_group)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                session_id_to_save,
                sender_id,
                sender_name,
                message,
                timestamp,
                is_group,
            )

            # 使用_get_db_cursor获取游标并执行
            try:
                cursor = self._get_db_cursor()
                cursor.execute(insert_sql, params)
                cursor.connection.commit()
                cursor.close()
                logger.debug(
                    f"消息保存成功 - 会话ID: {session_id_to_save}, 时间戳: {timestamp}"
                )
                return True
            except Exception as db_error:
                logger.error(f"数据库操作失败: {db_error}")
                return False

        except Exception as e:
            logger.error(f"保存消息到历史记录失败: {e}")
            return False

    def get_history_messages(
        self, session_id: str, days: int = 7, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        获取指定会话的历史消息

        Args:
            session_id: 会话ID
            days: 获取最近几天的消息
            limit: 最大消息数量

        Returns:
            历史消息列表
        """
        try:
            # 计算起始时间戳
            current_time = get_current_timestamp()
            start_time = current_time - (days * 24 * 60 * 60)

            # 查询数据
            query_sql = """
            SELECT session_id, sender_id, sender_name, message, timestamp, is_group
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
            """

            messages = []

            # 使用_get_db_cursor获取游标并执行
            try:
                cursor = self._get_db_cursor()
                cursor.execute(query_sql, (session_id, start_time, limit))

                # 获取结果
                for row in cursor.fetchall():
                    messages.append(
                        {
                            "session_id": row[0],
                            "sender_id": row[1],
                            "sender_name": row[2],
                            "message": row[3],
                            "timestamp": row[4],
                            "is_group": bool(row[5]),
                        }
                    )

                logger.debug(
                    f"获取到{len(messages)}条历史消息(会话ID: {session_id}, 天数: {days})"
                )
                return messages
            except Exception as db_error:
                logger.error(f"获取历史消息数据库操作失败: {db_error}")
                return []

        except Exception as e:
            logger.error(f"获取历史消息失败: {e}")
            return []

    def get_active_sessions(self, days: int = 7) -> List[str]:
        """
        获取有活动的会话ID列表

        Args:
            days: 最近几天有活动的会话

        Returns:
            会话ID列表
        """
        try:
            # 计算起始时间戳
            current_time = get_current_timestamp()
            start_time = current_time - (days * 24 * 60 * 60)

            # 查询数据
            query_sql = """
            SELECT DISTINCT session_id
            FROM wordcloud_message_history
            WHERE timestamp >= ?
            """

            sessions = []

            # 使用_get_db_cursor获取游标并执行
            try:
                cursor = self._get_db_cursor()
                cursor.execute(query_sql, (start_time,))

                # 获取结果
                sessions = [row[0] for row in cursor.fetchall()]

                cursor.close()
                logger.info(f"获取到{len(sessions)}个活跃会话(天数: {days})")
                return sessions
            except Exception as db_error:
                logger.error(f"获取活跃会话数据库操作失败: {db_error}")
                return []

        except Exception as e:
            logger.error(f"获取活跃会话失败: {e}")
            return []

    def get_message_texts(
        self, session_id: str, days: int = 7, limit: int = 1000
    ) -> List[str]:
        """
        获取指定会话的消息文本列表

        Args:
            session_id: 会话ID
            days: 获取最近几天的消息
            limit: 最大消息数量

        Returns:
            消息文本列表，按时间顺序返回（旧的在前，新的在后）
        """
        try:
            # 计算起始时间戳
            current_time = get_current_timestamp()
            start_time = current_time - (days * 24 * 60 * 60)

            # 查询数据 - 使用正序而不是倒序，使旧的消息在前，新的在后
            query_sql = """
            SELECT message
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            LIMIT ?
            """

            messages = []

            # 使用_get_db_cursor获取游标并执行
            try:
                cursor = self._get_db_cursor()
                cursor.execute(query_sql, (session_id, start_time, limit))

                # 获取结果 - 直接获取消息文本
                messages = [row[0] for row in cursor.fetchall()]

                cursor.close()
                logger.debug(
                    f"获取到{len(messages)}条历史消息(会话ID: {session_id}, 天数: {days})"
                )

                # 检查消息长度
                total_chars = sum(len(msg) for msg in messages)
                logger.debug(f"消息文本总长度: {total_chars} 字符")

                return messages
            except Exception as db_error:
                logger.error(f"获取消息文本数据库操作失败: {db_error}")
                return []

        except Exception as e:
            logger.error(f"获取消息文本失败: {e}")
            return []

    def get_todays_message_texts(self, session_id: str, limit: int = 1000) -> List[str]:
        """
        获取今天的消息文本列表

        Args:
            session_id: 会话ID
            limit: 最大消息数量限制

        Returns:
            今天的消息文本列表
        """
        try:
            # 获取今天的开始和结束时间戳
            start_timestamp, end_timestamp = get_day_start_end_timestamps()
            logger.info(
                f"获取今日消息 - 会话ID: {session_id}, 时间范围: {start_timestamp} 到 {end_timestamp}"
            )

            # 查询数据
            query_sql = """
            SELECT message
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            LIMIT ?
            """

            messages = []

            # 使用_get_db_cursor获取游标并执行
            try:
                cursor = self._get_db_cursor()
                cursor.execute(
                    query_sql, (session_id, start_timestamp, end_timestamp, limit)
                )

                # 获取结果
                for row in cursor.fetchall():
                    if row[0] and isinstance(row[0], str) and row[0].strip():
                        messages.append(row[0])

                cursor.close()
                logger.info(
                    f"今日消息获取成功 - 会话ID: {session_id}, 消息数量: {len(messages)}"
                )
                return messages
            except Exception as db_error:
                logger.error(f"数据库操作失败: {db_error}")

                # 尝试重新连接数据库并重试一次
                try:
                    logger.info("尝试重新连接数据库并重试查询...")
                    if hasattr(self.db, "_get_conn") and callable(
                        getattr(self.db, "_get_conn")
                    ):
                        conn = self.db._get_conn(self.db.db_path)
                        cursor = conn.cursor()
                        cursor.execute(
                            query_sql,
                            (session_id, start_timestamp, end_timestamp, limit),
                        )

                        # 获取结果
                        for row in cursor.fetchall():
                            if row[0] and isinstance(row[0], str) and row[0].strip():
                                messages.append(row[0])

                        cursor.close()
                        logger.info(
                            f"重试成功，今日消息获取成功 - 会话ID: {session_id}, 消息数量: {len(messages)}"
                        )
                        return messages
                    else:
                        logger.error("无法重新连接数据库")
                        return []
                except Exception as retry_error:
                    logger.error(f"重试数据库操作失败: {retry_error}")
                    return []
        except Exception as e:
            logger.error(f"获取今日消息文本失败: {e}")
            return []

    def get_active_group_sessions(self, days: int = 1) -> List[str]:
        """
        获取有活动的群聊会话ID列表

        Args:
            days: 最近几天有活动的群聊

        Returns:
            群聊会话ID列表
        """
        try:
            # 计算起始时间戳
            current_time = get_current_timestamp()
            start_time = current_time - (days * 24 * 60 * 60)

            # 查询数据，只获取群聊会话
            query_sql = """
            SELECT DISTINCT session_id
            FROM wordcloud_message_history
            WHERE timestamp >= ? AND is_group = 1
            """

            sessions = []

            # 使用_get_db_cursor获取游标并执行
            try:
                cursor = self._get_db_cursor()
                cursor.execute(query_sql, (start_time,))

                # 获取结果
                sessions = [row[0] for row in cursor.fetchall()]

                cursor.close()
                logger.info(f"获取到{len(sessions)}个活跃群聊会话(天数: {days})")
                return sessions
            except Exception as db_error:
                logger.error(f"获取活跃群聊会话数据库操作失败: {db_error}")
                return []

        except Exception as e:
            logger.error(f"获取活跃群聊会话失败: {e}")
            return []

    def get_message_count_today(self, session_id: str) -> int:
        """
        获取今天的消息数量

        Args:
            session_id: 会话ID

        Returns:
            消息数量
        """
        try:
            # 获取今天的开始和结束时间戳
            start_timestamp, end_timestamp = get_day_start_end_timestamps()

            # 查询今天的消息数量
            query_sql = """
            SELECT COUNT(*) as count
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ? AND timestamp <= ?
            """

            # 使用_get_db_cursor获取游标并执行
            cursor = self._get_db_cursor()
            cursor.execute(query_sql, (session_id, start_timestamp, end_timestamp))

            # 获取结果
            result = cursor.fetchone()
            cursor.close()

            if result:
                return result[0]
            return 0
        except Exception as e:
            logger.error(f"获取今天的消息数量失败: {e}")
            return 0

    def get_message_count_for_days(self, session_id: str, days: int) -> int:
        """
        获取指定会话在过去N天内的总消息数量。

        Args:
            session_id: 会话ID
            days: 获取最近几天的消息

        Returns:
            指定天数内的消息总数量
        """
        try:
            # 计算起始时间戳
            current_time = get_current_timestamp()
            start_time = current_time - (days * 24 * 60 * 60)

            # 查询数据
            query_sql = """
            SELECT COUNT(*) as count
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ?
            """

            # 使用_get_db_cursor获取游标并执行
            cursor = self._get_db_cursor()
            cursor.execute(query_sql, (session_id, start_time))

            # 获取结果
            result = cursor.fetchone()
            cursor.close()

            if result:
                logger.debug(
                    f"获取到 {days} 天内消息总数: {result[0]} (会话ID: {session_id})"
                )
                return result[0]
            return 0
        except Exception as e:
            logger.error(f"获取 {days} 天内消息总数失败: {e}, session_id={session_id}")
            return 0

    def get_active_users(
        self, session_id: str, days: int = 1, limit: int = 10
    ) -> List[Tuple[str, str, int]]:
        """
        获取指定会话中最活跃的用户（按发言数量排序）

        Args:
            session_id: 会话ID
            days: 统计最近几天的数据，默认为1天（今天）
            limit: 返回的用户数量限制

        Returns:
            用户活跃度排名列表，格式为 [(user_id, user_name, message_count), ...]
        """
        try:
            # 计算时间范围
            if days == 1:
                # 使用当天时间范围
                start_timestamp, end_timestamp = get_day_start_end_timestamps()
            else:
                # 计算过去days天的时间范围
                current_time = get_current_timestamp()
                start_timestamp = current_time - (days * 24 * 60 * 60)
                end_timestamp = current_time

            # 查询活跃用户数据
            query_sql = """
            SELECT sender_id, sender_name, COUNT(*) as message_count
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ? AND timestamp <= ?
            GROUP BY sender_id
            ORDER BY message_count DESC
            LIMIT ?
            """

            # 使用_get_db_cursor获取游标并执行
            cursor = self._get_db_cursor()
            cursor.execute(
                query_sql, (session_id, start_timestamp, end_timestamp, limit)
            )

            # 获取结果
            results = cursor.fetchall()
            cursor.close()

            # 转换为所需格式
            user_list = []
            for row in results:
                user_id = row[0]
                user_name = row[1] or user_id  # 如果没有名称，使用ID
                message_count = row[2]
                user_list.append((user_id, user_name, message_count))

            return user_list
        except Exception as e:
            logger.error(f"获取活跃用户失败: {e}, session_id={session_id}, days={days}")
            return []

    def get_total_users_today(self, session_id: str) -> int:
        """
        获取今天在指定会话中发言的总用户数

        Args:
            session_id: 会话ID

        Returns:
            用户数量
        """
        try:
            # 获取今天的开始和结束时间戳
            start_timestamp, end_timestamp = get_day_start_end_timestamps()

            # 查询今天发言的不同用户数量
            query_sql = """
            SELECT COUNT(DISTINCT sender_id) as user_count
            FROM wordcloud_message_history
            WHERE session_id = ? AND timestamp >= ? AND timestamp <= ?
            """

            # 使用_get_db_cursor获取游标并执行
            cursor = self._get_db_cursor()
            cursor.execute(query_sql, (session_id, start_timestamp, end_timestamp))

            # 获取结果
            result = cursor.fetchone()
            cursor.close()

            if result:
                return result[0]
            return 0
        except Exception as e:
            logger.error(f"获取今天的用户数量失败: {e}")
            return 0

    def extract_group_id_from_session(self, session_id: str) -> Optional[str]:
        """
        从会话ID中提取群号

        Args:
            session_id: 会话ID

        Returns:
            群号，如果不是群聊则返回None
        """
        try:
            # 会话ID格式通常为 "platform:GroupMessage:group_id"
            parts = session_id.split(":")
            if len(parts) >= 3 and "GroupMessage" in parts[1]:
                return parts[2]
            return None
        except Exception as e:
            logger.error(f"从会话ID提取群号失败: {e}")
            return None

    def close(self):
        """
        关闭历史管理器，释放资源
        """
        logger.info("关闭历史管理器...")
        
        try:
            # 关闭数据库连接
            if hasattr(self, "connection") and self.connection is not None:
                try:
                    self.connection.close()
                    logger.info("数据库连接已关闭")
                except Exception as e:
                    logger.error(f"关闭数据库连接时出错: {e}")
            
            # 清理数据和缓存
            self.word_data = {}
            self.cached_word_counts = {}
            logger.info("历史数据缓存已清理")
            
            # 允许垃圾回收
            self.connection = None
            self.cursor = None
            
            logger.info("历史管理器已成功关闭")
        except Exception as e:
            logger.error(f"关闭历史管理器时出错: {e}")
            logger.error(traceback.format_exc())
