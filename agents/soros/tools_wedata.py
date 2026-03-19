# -*- coding: utf-8 -*-
"""
Wedata Tools - 腾讯大数据平台 API 工具
======================================
对接 Wedata 平台，支持查询：
- US 离线任务状态
- YARN Application 状态
- Oceanus 实时任务
- HDFS 状态
- SuperSql 执行结果
- TDBank 业务信息
- StarRocks 集群负载
"""

import json
import requests
from typing import Dict, List, Any, Optional


class WedataTools:
    """Wedata API 工具集"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # API 配置
        self.us_url = "https://us.woa.com/api"  # US 平台
        self.oceanus_url = "https://oceanus.woa.com/api"  # Oceanus
        self.supersql_url = "https://ss-qe-log.woa.com/api"  # SuperSql
        self.tdbank_url = "https://tdbank.woa.com/api"  # TDBank
        self.starrocks_url = "https://sr.woa.com/api"  # StarRocks
        
        # CMK 配置（如需要）
        self.cmk = self.config.get("cmk", "")
    
    # ═══════════════════════════════════════════════
    # US 离线任务查询
    # ═══════════════════════════════════════════════
    
    def query_us_task(self, task_id: str, instance_time: str = None) -> Dict:
        """
        查询 US 离线任务状态
        
        Args:
            task_id: 任务 ID
            instance_time: 实例时间，格式如 '2026-02-03'
        """
        try:
            url = f"{self.us_url}/task/instance"
            params = {
                "taskId": task_id,
            }
            if instance_time:
                params["instanceTime"] = instance_time
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                return self._format_task_status(data)
            else:
                return {"error": f"API返回错误: {resp.status_code}", "detail": resp.text}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_us_task_log(self, task_id: str, instance_time: str = None) -> Dict:
        """查询 US 任务日志"""
        try:
            url = f"{self.us_url}/task/log"
            params = {
                "taskId": task_id,
            }
            if instance_time:
                params["instanceTime"] = instance_time
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # YARN Application 查询
    # ═══════════════════════════════════════════════
    
    def query_yarn_app(self, application_id: str) -> Dict:
        """
        查询 YARN Application 状态
        
        Args:
            application_id: YARN Application ID，如 'application_1740xxx_1234'
        """
        try:
            url = f"{self.us_url}/yarn/application/{application_id}"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                return self._format_yarn_status(resp.json())
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_yarn_app_logs(self, application_id: str, container_id: str = None) -> Dict:
        """查询 YARN Application 日志"""
        try:
            url = f"{self.us_url}/yarn/application/{application_id}/logs"
            params = {}
            if container_id:
                params["containerId"] = container_id
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                return {"logs": resp.text[:5000]}  # 限制返回长度
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # Oceanus 实时任务
    # ═══════════════════════════════════════════════
    
    def query_oceanus_task(self, task_id: str, instance_id: str = None) -> Dict:
        """
        查询 Oceanus 实时任务状态
        
        Args:
            task_id: Oceanus 任务 ID
            instance_id: 实例 ID（可选）
        """
        try:
            url = f"{self.oceanus_url}/task/detail/{task_id}"
            if instance_id:
                url = f"{self.oceanus_url}/task/instance/{instance_id}"
            
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_oceanus_metrics(self, task_id: str) -> Dict:
        """查询 Oceanus 任务指标"""
        try:
            url = f"{self.oceanus_url}/task/metrics/{task_id}"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # HDFS 状态查询
    # ═══════════════════════════════════════════════
    
    def query_hdfs_health(self, file_path: str = None, cluster: str = None) -> Dict:
        """
        查询 HDFS 健康状态
        
        Args:
            file_path: 文件路径（可选）
            cluster: 集群名称（可选）
        """
        try:
            url = f"{self.us_url}/hdfs/health"
            params = {}
            if file_path:
                params["path"] = file_path
            if cluster:
                params["cluster"] = cluster
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_hdfs_block(self, file_path: str) -> Dict:
        """查询 HDFS 块信息"""
        try:
            url = f"{self.us_url}/hdfs/blocks"
            params = {"path": file_path}
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # SuperSql 查询
    # ═══════════════════════════════════════════════
    
    def query_supersql_session(self, session_id: str) -> Dict:
        """
        查询 SuperSql Session 状态
        
        Args:
            session_id: SuperSql Session ID
        """
        try:
            url = f"{self.supersql_url}/session/{session_id}"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_supersql_results(self, session_id: str, limit: int = 100) -> Dict:
        """查询 SuperSql 执行结果"""
        try:
            url = f"{self.supersql_url}/session/{session_id}/results"
            params = {"limit": limit}
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def execute_supersql(self, sql: str, database: str = None) -> Dict:
        """
        执行 SuperSql 查询
        
        Args:
            sql: SQL 语句
            database: 数据库名（可选）
        """
        try:
            url = f"{self.supersql_url}/query"
            payload = {
                "sql": sql,
            }
            if database:
                payload["database"] = database
            
            resp = requests.post(url, json=payload, timeout=120)
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "submitted",
                    "session_id": data.get("sessionId"),
                    "message": "SQL已提交执行，请使用session_id查询结果"
                }
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # TDBank 查询
    # ═══════════════════════════════════════════════
    
    def query_tdbank_table_info(self, bid: str) -> Dict:
        """
        查询 TDBank 表信息
        
        Args:
            bid: 表名，如 'b_teg_tube_index'
        """
        try:
            url = f"{self.tdbank_url}/table/info"
            params = {"bid": bid}
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_tdbank_partitions(self, bid: str) -> Dict:
        """查询 TDBank 表分区数"""
        try:
            url = f"{self.tdbank_url}/table/partitions"
            params = {"bid": bid}
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "bid": bid,
                    "partition_count": data.get("partitionCount", 0),
                    "partitions": data.get("partitions", [])[:10]  # 限制返回
                }
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # StarRocks 查询
    # ═══════════════════════════════════════════════
    
    def query_starrocks_cluster(self, cluster: str) -> Dict:
        """
        查询 StarRocks 集群状态
        
        Args:
            cluster: 集群名称，如 'starrocks-gz0-teg-common-txt-v33'
        """
        try:
            url = f"{self.starrocks_url}/cluster/{cluster}/status"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                return self._format_starrocks_status(resp.json())
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def query_starrocks_load(self, cluster: str) -> Dict:
        """查询 StarRocks 集群负载"""
        try:
            url = f"{self.starrocks_url}/cluster/{cluster}/load"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"API返回错误: {resp.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # 格式化输出
    # ═══════════════════════════════════════════════
    
    def _format_task_status(self, data: Dict) -> Dict:
        """格式化任务状态"""
        return {
            "task_id": data.get("taskId"),
            "status": data.get("status"),  # SUCCESS, FAILED, RUNNING
            "start_time": data.get("startTime"),
            "end_time": data.get("endTime"),
            "duration": data.get("duration"),
            "error_message": data.get("errorMessage"),
            "try_times": data.get("tryTimes")
        }
    
    def _format_yarn_status(self, data: Dict) -> Dict:
        """格式化 YARN 状态"""
        return {
            "application_id": data.get("applicationId"),
            "state": data.get("state"),  # ACCEPTED, RUNNING, FINISHED, FAILED
            "final_status": data.get("finalStatus"),
            "started_time": data.get("startedTime"),
            "finished_time": data.get("finishedTime"),
            "elapsed_time": data.get("elapsedTime"),
            "am_container_logs": data.get("amContainerLogs"),
            "diagnostics": data.get("diagnostics")
        }
    
    def _format_starrocks_status(self, data: Dict) -> Dict:
        """格式化 StarRocks 状态"""
        return {
            "cluster": data.get("cluster"),
            "status": data.get("status"),
            "backend_count": data.get("beCount"),
            "tablet_count": data.get("tabletCount"),
            "cpu_usage": data.get("cpuUsage"),
            "mem_usage": data.get("memUsage"),
            "disk_usage": data.get("diskUsage")
        }


# 全局实例
_wedata_tools = None


def get_wedata_tools(config: Dict = None) -> WedataTools:
    """获取 Wedata 工具实例"""
    global _wedata_tools
    if _wedata_tools is None:
        _wedata_tools = WedataTools(config)
    return _wedata_tools
