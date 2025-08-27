import sqlite3
import logging
import json
from datetime import datetime
import os
import sys

# 获取项目根目录
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from config import DATABASE_CONFIG

logger = logging.getLogger("battery-simulator.database")

def get_db_connection():
    """获取数据库连接"""
    # 使用绝对路径确保数据库文件位置正确
    db_path = os.path.join(backend_dir, "db", "battery_data.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # 确保db目录存在
    conn = sqlite3.connect(db_path, check_same_thread=DATABASE_CONFIG["connect_args"].get("check_same_thread", True))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库，创建表"""
    logger.info("正在初始化数据库...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查 charging_records 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='charging_records'")
        table_exists = cursor.fetchone()

        required_columns = [
            'id', 'start_time', 'end_time', 'initial_soc', 'final_soc',
            'initial_temperature', 'final_temperature', 'initial_internal_resistance',
            'initial_polarization_resistance', 'duration_seconds', 'charging_phases'
        ]

        if table_exists:
            # 检查表结构
            cursor.execute("PRAGMA table_info(charging_records)")
            columns = [row['name'] for row in cursor.fetchall()]
            
            if all(col in columns for col in required_columns):
                logger.info("数据库表 'charging_records' 已存在并且结构正确。")
                conn.close()
                return

        logger.info("数据库表 'charging_records' 不存在或结构不正确，正在创建/重建...")
        cursor.execute("DROP TABLE IF EXISTS charging_records")
        
        # 创建 charging_records 表
        cursor.execute("""
            CREATE TABLE charging_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                initial_soc REAL NOT NULL,
                final_soc REAL,
                initial_temperature REAL NOT NULL,
                final_temperature REAL,
                initial_internal_resistance REAL NOT NULL,
                initial_polarization_resistance REAL NOT NULL,
                duration_seconds INTEGER,
                charging_phases TEXT
            )
        """)
        conn.commit()
        logger.info("数据库表 'charging_records' 创建成功。")
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)

def add_charging_record(record):
    """添加一条新的充电记录"""
    logger.info(f"添加新的充电记录: {record}")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO charging_records (
                start_time, initial_soc, initial_temperature, 
                initial_internal_resistance, initial_polarization_resistance,
                charging_phases
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            record['start_time'],
            record['initial_soc'],
            record['initial_temperature'],
            record['initial_internal_resistance'],
            record['initial_polarization_resistance'],
            json.dumps(record.get('charging_phases', []))
        ))
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"成功添加充电记录，ID: {record_id}")
        return record_id
    except sqlite3.Error as e:
        logger.error(f"添加充电记录失败: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def update_charging_record(record_id, updates):
    """更新一条充电记录"""
    logger.info(f"更新充电记录 ID: {record_id} with updates: {updates}")
    conn = get_db_connection()
    try:
        # 计算充电时长
        start_time_str = None
        end_time_str = updates.get('end_time')
        duration = None
        
        # 获取当前记录的开始时间
        cursor = conn.cursor()
        cursor.execute("SELECT start_time FROM charging_records WHERE id = ?", (record_id,))
        record = cursor.fetchone()
        if record:
            start_time_str = record['start_time']
        
        # 如果更新中包含开始时间，则使用更新中的开始时间
        if 'start_time' in updates and updates['start_time']:
            start_time_str = updates['start_time']
        
        # 计算时长
        if start_time_str and end_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                duration = int((end_time - start_time).total_seconds())
                logger.info(f"计算充电记录 ID: {record_id} 的时长: {duration}秒")
            except Exception as e:
                logger.error(f"计算充电时长失败: {e}", exc_info=True)

        cursor.execute("""
            UPDATE charging_records 
            SET end_time = ?, final_soc = ?, final_temperature = ?, duration_seconds = ?, charging_phases = ?
            WHERE id = ?
        """, (
            updates.get('end_time'),
            updates.get('final_soc'),
            updates.get('final_temperature'),
            duration,
            json.dumps(updates.get('charging_phases', [])),
            record_id
        ))
        conn.commit()
        logger.info(f"成功更新充电记录 ID: {record_id}")
    except (sqlite3.Error, KeyError, TypeError) as e:
        logger.error(f"更新充电记录失败: {e}", exc_info=True)
    finally:
        conn.close()

def delete_charging_record(record_id):
    """删除一条充电记录
    
    参数:
        record_id: 要删除的充电记录ID
        
    返回:
        bool: 删除是否成功
    """
    logger.info(f"删除充电记录 ID: {record_id}")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM charging_records WHERE id = ?", (record_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"成功删除充电记录 ID: {record_id}")
            return True
        else:
            logger.warning(f"未找到要删除的充电记录 ID: {record_id}")
            return False
    except sqlite3.Error as e:
        logger.error(f"删除充电记录失败: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_charging_record_by_id(record_id):
    """根据ID获取单条充电记录
    
    参数:
        record_id: 充电记录ID
        
    返回:
        dict: 充电记录字典，如果未找到则返回None
    """
    logger.info(f"获取充电记录 ID: {record_id}")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM charging_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        
        if row:
            record = dict(row)
            # 解析JSON字符串为Python对象
            if record.get('charging_phases'):
                try:
                    record['charging_phases'] = json.loads(record['charging_phases'])
                except json.JSONDecodeError:
                    record['charging_phases'] = []
            else:
                record['charging_phases'] = []
            return record
        else:
            logger.warning(f"未找到充电记录 ID: {record_id}")
            return None
    except sqlite3.Error as e:
        logger.error(f"获取充电记录失败: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_all_charging_records():
    """获取所有充电记录"""
    logger.info("正在从数据库获取所有充电记录...")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM charging_records ORDER BY start_time DESC")
        records = cursor.fetchall()
        result = []
        for row in records:
            record = dict(row)
            # 解析JSON字符串为Python对象
            if record.get('charging_phases'):
                try:
                    record['charging_phases'] = json.loads(record['charging_phases'])
                except json.JSONDecodeError:
                    record['charging_phases'] = []
            else:
                record['charging_phases'] = []
            result.append(record)
        return result
    except sqlite3.Error as e:
        logger.error(f"获取充电记录失败: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def get_charging_records_by_date_range(start_date, end_date):
    """根据日期范围获取充电记录
    
    参数:
        start_date: 开始日期，ISO格式字符串 (YYYY-MM-DD)
        end_date: 结束日期，ISO格式字符串 (YYYY-MM-DD)
        
    返回:
        list: 充电记录列表
    """
    logger.info(f"获取日期范围内的充电记录: {start_date} 至 {end_date}")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 为了包含整个结束日期，我们需要将end_date加上一天
        cursor.execute("""
            SELECT * FROM charging_records 
            WHERE start_time >= ? AND start_time < date(?, '+1 day')
            ORDER BY start_time DESC
        """, (start_date, end_date))
        
        records = cursor.fetchall()
        result = []
        for row in records:
            record = dict(row)
            # 解析JSON字符串为Python对象
            if record.get('charging_phases'):
                try:
                    record['charging_phases'] = json.loads(record['charging_phases'])
                except json.JSONDecodeError:
                    record['charging_phases'] = []
            else:
                record['charging_phases'] = []
            result.append(record)
        return result
    except sqlite3.Error as e:
        logger.error(f"获取日期范围内的充电记录失败: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def get_recent_charging_records(limit=10):
    """获取最近的N条充电记录
    
    参数:
        limit: 返回记录的最大数量
        
    返回:
        list: 充电记录列表
    """
    logger.info(f"获取最近 {limit} 条充电记录")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM charging_records 
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,))
        
        records = cursor.fetchall()
        result = []
        for row in records:
            record = dict(row)
            # 解析JSON字符串为Python对象
            if record.get('charging_phases'):
                try:
                    record['charging_phases'] = json.loads(record['charging_phases'])
                except json.JSONDecodeError:
                    record['charging_phases'] = []
            else:
                record['charging_phases'] = []
            result.append(record)
        return result
    except sqlite3.Error as e:
        logger.error(f"获取最近充电记录失败: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def delete_all_charging_records():
    """删除所有充电记录
    
    返回:
        bool: 删除是否成功
    """
    logger.info("删除所有充电记录")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM charging_records")
        conn.commit()
        count = cursor.rowcount
        logger.info(f"成功删除 {count} 条充电记录")
        return True
    except sqlite3.Error as e:
        logger.error(f"删除所有充电记录失败: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def delete_charging_records_by_ids(record_ids):
    """批量删除充电记录
    
    参数:
        record_ids: 要删除的充电记录ID列表
        
    返回:
        int: 成功删除的记录数量
    """
    if not record_ids:
        return 0
        
    logger.info(f"批量删除充电记录: {record_ids}")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 构建参数占位符
        placeholders = ','.join(['?'] * len(record_ids))
        cursor.execute(f"DELETE FROM charging_records WHERE id IN ({placeholders})", record_ids)
        conn.commit()
        count = cursor.rowcount
        logger.info(f"成功删除 {count} 条充电记录")
        return count
    except sqlite3.Error as e:
        logger.error(f"批量删除充电记录失败: {e}", exc_info=True)
        return 0
    finally:
        conn.close()

def get_charging_statistics():
    """获取充电统计信息
    
    返回:
        dict: 包含统计信息的字典
    """
    logger.info("获取充电统计信息")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) as count FROM charging_records")
        total_count = cursor.fetchone()['count']
        
        # 获取平均充电时长
        cursor.execute("SELECT AVG(duration_seconds) as avg_duration FROM charging_records WHERE duration_seconds IS NOT NULL")
        avg_duration = cursor.fetchone()['avg_duration'] or 0
        
        # 获取平均SOC增长
        cursor.execute("""
            SELECT AVG(final_soc - initial_soc) as avg_soc_increase 
            FROM charging_records 
            WHERE final_soc IS NOT NULL AND initial_soc IS NOT NULL
        """)
        avg_soc_increase = cursor.fetchone()['avg_soc_increase'] or 0
        
        # 获取最长充电时间
        cursor.execute("""
            SELECT MAX(duration_seconds) as max_duration, id
            FROM charging_records 
            WHERE duration_seconds IS NOT NULL
        """)
        result = cursor.fetchone()
        max_duration = result['max_duration'] or 0
        max_duration_id = result['id']
        
        # 获取最短充电时间
        cursor.execute("""
            SELECT MIN(duration_seconds) as min_duration, id
            FROM charging_records 
            WHERE duration_seconds IS NOT NULL
        """)
        result = cursor.fetchone()
        min_duration = result['min_duration'] or 0
        min_duration_id = result['id']
        
        # 获取每个月的充电次数
        cursor.execute("""
            SELECT strftime('%Y-%m', start_time) as month, COUNT(*) as count
            FROM charging_records
            GROUP BY month
            ORDER BY month DESC
        """)
        monthly_counts = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_count": total_count,
            "avg_duration_seconds": avg_duration,
            "avg_soc_increase": avg_soc_increase,
            "max_duration": {
                "seconds": max_duration,
                "record_id": max_duration_id
            },
            "min_duration": {
                "seconds": min_duration,
                "record_id": min_duration_id
            },
            "monthly_counts": monthly_counts
        }
    except sqlite3.Error as e:
        logger.error(f"获取充电统计信息失败: {e}", exc_info=True)
        return {
            "total_count": 0,
            "avg_duration_seconds": 0,
            "avg_soc_increase": 0,
            "max_duration": {"seconds": 0, "record_id": None},
            "min_duration": {"seconds": 0, "record_id": None},
            "monthly_counts": []
        }
    finally:
        conn.close()

def get_charging_phases_statistics():
    """获取充电阶段统计信息
    
    返回:
        dict: 包含各充电阶段统计信息的字典
    """
    logger.info("获取充电阶段统计信息")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT charging_phases FROM charging_records")
        records = cursor.fetchall()
        
        # 统计各阶段信息
        phases_stats = {
            "cc": {"count": 0, "total_duration": 0, "avg_duration": 0},
            "cv": {"count": 0, "total_duration": 0, "avg_duration": 0},
            "trickle": {"count": 0, "total_duration": 0, "avg_duration": 0}
        }
        
        for record in records:
            if not record['charging_phases']:
                continue
                
            try:
                phases = json.loads(record['charging_phases'])
                for phase in phases:
                    phase_type = phase.get('phase')
                    if phase_type not in phases_stats:
                        continue
                        
                    # 计算阶段持续时间
                    if phase.get('start_time') and phase.get('end_time'):
                        start_time = datetime.fromisoformat(phase['start_time'])
                        end_time = datetime.fromisoformat(phase['end_time'])
                        duration = (end_time - start_time).total_seconds()
                        
                        phases_stats[phase_type]["count"] += 1
                        phases_stats[phase_type]["total_duration"] += duration
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        # 计算平均持续时间
        for phase_type in phases_stats:
            if phases_stats[phase_type]["count"] > 0:
                phases_stats[phase_type]["avg_duration"] = (
                    phases_stats[phase_type]["total_duration"] / 
                    phases_stats[phase_type]["count"]
                )
        
        return phases_stats
    except sqlite3.Error as e:
        logger.error(f"获取充电阶段统计信息失败: {e}", exc_info=True)
        return {
            "cc": {"count": 0, "total_duration": 0, "avg_duration": 0},
            "cv": {"count": 0, "total_duration": 0, "avg_duration": 0},
            "trickle": {"count": 0, "total_duration": 0, "avg_duration": 0}
        }
    finally:
        conn.close()

def search_charging_records(search_params):
    """根据条件搜索充电记录
    
    参数:
        search_params: 搜索条件字典，可能包含以下键：
            - start_date: 开始日期 (ISO格式字符串)
            - end_date: 结束日期 (ISO格式字符串)
            - min_soc: 最小初始SOC
            - max_soc: 最大初始SOC
            - min_temperature: 最小初始温度
            - max_temperature: 最大初始温度
            - min_duration: 最小充电时长(秒)
            - max_duration: 最大充电时长(秒)
            - limit: 返回结果数量限制
            - offset: 分页偏移量
            
    返回:
        dict: 包含搜索结果和总记录数的字典
    """
    logger.info(f"搜索充电记录: {search_params}")
    conn = get_db_connection()
    try:
        # 构建查询条件
        conditions = []
        params = []
        
        if search_params.get('start_date'):
            conditions.append("start_time >= ?")
            params.append(search_params['start_date'])
        
        if search_params.get('end_date'):
            conditions.append("start_time < date(?, '+1 day')")
            params.append(search_params['end_date'])
        
        if search_params.get('min_soc') is not None:
            conditions.append("initial_soc >= ?")
            params.append(search_params['min_soc'])
        
        if search_params.get('max_soc') is not None:
            conditions.append("initial_soc <= ?")
            params.append(search_params['max_soc'])
        
        if search_params.get('min_temperature') is not None:
            conditions.append("initial_temperature >= ?")
            params.append(search_params['min_temperature'])
        
        if search_params.get('max_temperature') is not None:
            conditions.append("initial_temperature <= ?")
            params.append(search_params['max_temperature'])
        
        if search_params.get('min_duration') is not None:
            conditions.append("duration_seconds >= ?")
            params.append(search_params['min_duration'])
        
        if search_params.get('max_duration') is not None:
            conditions.append("duration_seconds <= ?")
            params.append(search_params['max_duration'])
        
        # 构建WHERE子句
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 获取总记录数
        cursor = conn.cursor()
        count_query = f"SELECT COUNT(*) as count FROM charging_records WHERE {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['count']
        
        # 构建分页查询
        limit = search_params.get('limit', 50)  # 默认限制50条
        offset = search_params.get('offset', 0)
        
        # 执行查询
        query = f"""
            SELECT * FROM charging_records 
            WHERE {where_clause}
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        
        records = cursor.fetchall()
        result = []
        for row in records:
            record = dict(row)
            # 解析JSON字符串为Python对象
            if record.get('charging_phases'):
                try:
                    record['charging_phases'] = json.loads(record['charging_phases'])
                except json.JSONDecodeError:
                    record['charging_phases'] = []
            else:
                record['charging_phases'] = []
            result.append(record)
        
        return {
            "records": result,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    except sqlite3.Error as e:
        logger.error(f"搜索充电记录失败: {e}", exc_info=True)
        return {
            "records": [],
            "total_count": 0,
            "limit": search_params.get('limit', 50),
            "offset": search_params.get('offset', 0)
        }
    finally:
        conn.close()

def export_charging_records_to_json(file_path, record_ids=None):
    """将充电记录导出为JSON文件
    
    参数:
        file_path: 导出文件路径
        record_ids: 要导出的记录ID列表，如果为None则导出所有记录
        
    返回:
        bool: 导出是否成功
    """
    logger.info(f"导出充电记录到JSON文件: {file_path}")
    try:
        # 获取记录
        if record_ids:
            # 获取指定ID的记录
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(record_ids))
            cursor.execute(f"SELECT * FROM charging_records WHERE id IN ({placeholders})", record_ids)
            records = cursor.fetchall()
            conn.close()
        else:
            # 获取所有记录
            records = get_all_charging_records()
        
        # 将记录转换为可序列化的格式
        export_data = []
        for record in records:
            if isinstance(record, sqlite3.Row):
                record = dict(record)
            
            # 解析充电阶段
            if record.get('charging_phases') and isinstance(record['charging_phases'], str):
                try:
                    record['charging_phases'] = json.loads(record['charging_phases'])
                except json.JSONDecodeError:
                    record['charging_phases'] = []
            
            export_data.append(record)
        
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # 写入JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"成功导出 {len(export_data)} 条充电记录到 {file_path}")
        return True
    except Exception as e:
        logger.error(f"导出充电记录失败: {e}", exc_info=True)
        return False

def import_charging_records_from_json(file_path):
    """从JSON文件导入充电记录
    
    参数:
        file_path: JSON文件路径
        
    返回:
        dict: 包含导入结果的字典
    """
    logger.info(f"从JSON文件导入充电记录: {file_path}")
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
        
        if not isinstance(records, list):
            logger.error("导入失败：JSON文件格式不正确，应为记录列表")
            return {"success": False, "message": "JSON文件格式不正确", "imported_count": 0}
        
        # 导入记录
        conn = get_db_connection()
        cursor = conn.cursor()
        imported_count = 0
        
        for record in records:
            try:
                # 检查必要字段
                required_fields = ['start_time', 'initial_soc', 'initial_temperature', 
                                  'initial_internal_resistance', 'initial_polarization_resistance']
                if not all(field in record for field in required_fields):
                    logger.warning(f"跳过记录：缺少必要字段 - {record}")
                    continue
                
                # 处理充电阶段
                charging_phases = record.get('charging_phases', [])
                if not isinstance(charging_phases, list):
                    charging_phases = []
                
                # 插入记录
                cursor.execute("""
                    INSERT INTO charging_records (
                        start_time, end_time, initial_soc, final_soc,
                        initial_temperature, final_temperature,
                        initial_internal_resistance, initial_polarization_resistance,
                        duration_seconds, charging_phases
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record['start_time'],
                    record.get('end_time'),
                    record['initial_soc'],
                    record.get('final_soc'),
                    record['initial_temperature'],
                    record.get('final_temperature'),
                    record['initial_internal_resistance'],
                    record['initial_polarization_resistance'],
                    record.get('duration_seconds'),
                    json.dumps(charging_phases)
                ))
                imported_count += 1
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"导入记录失败: {e} - {record}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"成功导入 {imported_count} 条充电记录")
        return {
            "success": True,
            "message": f"成功导入 {imported_count} 条充电记录",
            "imported_count": imported_count
        }
    except Exception as e:
        logger.error(f"导入充电记录失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"导入失败: {str(e)}",
            "imported_count": 0
        } 

def update_all_charging_record_durations():
    """重新计算所有充电记录的时长
    
    返回:
        int: 更新的记录数量
    """
    logger.info("开始更新所有充电记录的时长...")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取所有有开始和结束时间的记录
        cursor.execute("""
            SELECT id, start_time, end_time 
            FROM charging_records 
            WHERE start_time IS NOT NULL AND end_time IS NOT NULL
        """)
        
        records = cursor.fetchall()
        updated_count = 0
        
        for record in records:
            try:
                # 解析ISO格式的时间字符串
                start_time = datetime.fromisoformat(record['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(record['end_time'].replace('Z', '+00:00'))
                
                # 计算时长（秒）
                duration_seconds = int((end_time - start_time).total_seconds())
                
                # 更新记录
                cursor.execute("""
                    UPDATE charging_records 
                    SET duration_seconds = ? 
                    WHERE id = ?
                """, (duration_seconds, record['id']))
                
                updated_count += 1
            except Exception as e:
                logger.error(f"更新记录 {record['id']} 的时长时出错: {e}", exc_info=True)
        
        conn.commit()
        logger.info(f"成功更新 {updated_count}/{len(records)} 条充电记录的时长")
        return updated_count
    except sqlite3.Error as e:
        logger.error(f"更新充电记录时长失败: {e}", exc_info=True)
        return 0
    finally:
        conn.close() 