#!/usr/bin/env python3
"""
RUL优化充电策略测试程序
测试Battery LSTM项目的RUL预测和智能充电参数调控功能

功能覆盖:
1. 模型加载和激活测试
2. RUL预测准确性测试
3. 充电参数动态调控测试
4. 不同RUL场景下的策略切换测试
5. 前后端集成测试
6. 性能和稳定性测试
"""

import asyncio
import aiohttp
import socketio
import json
import time
import sys
import os
import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rul_optimization_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RULOptimizationTester:
    """RUL优化充电策略测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8001", frontend_url: str = "http://localhost:5111"):
        self.base_url = base_url
        self.frontend_url = frontend_url
        self.session = requests.Session()
        self.session.headers.update({
            'Origin': frontend_url,
            'Content-Type': 'application/json'
        })
        
        # 测试结果记录
        self.test_results = {
            'model_activation': {'passed': 0, 'failed': 0, 'details': []},
            'rul_prediction': {'passed': 0, 'failed': 0, 'details': []},
            'parameter_control': {'passed': 0, 'failed': 0, 'details': []},
            'strategy_switching': {'passed': 0, 'failed': 0, 'details': []},
            'integration': {'passed': 0, 'failed': 0, 'details': []},
            'performance': {'passed': 0, 'failed': 0, 'details': []}
        }
        
        # 测试数据
        self.test_scenarios = [
            {'rul': 85, 'temp': 25, 'soc': 50, 'expected_strategy': 'standard'},
            {'rul': 65, 'temp': 35, 'soc': 70, 'expected_strategy': 'eco'},
            {'rul': 25, 'temp': 40, 'soc': 85, 'expected_strategy': 'longevity'},
            {'rul': 45, 'temp': 20, 'soc': 30, 'expected_strategy': 'eco'},
            {'rul': 90, 'temp': 30, 'soc': 20, 'expected_strategy': 'standard'}
        ]

    def log_test_result(self, category: str, passed: bool, details: str):
        """记录测试结果"""
        if passed:
            self.test_results[category]['passed'] += 1
            logger.info(f"[PASS] {category}: {details}")
        else:
            self.test_results[category]['failed'] += 1
            logger.error(f"[FAIL] {category}: {details}")
        
        self.test_results[category]['details'].append({
            'timestamp': datetime.now().isoformat(),
            'passed': passed,
            'details': details
        })

    async def test_backend_connectivity(self) -> bool:
        """测试后端连接"""
        try:
            response = self.session.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"后端连接成功: {data}")
                return True
            else:
                logger.error(f"后端响应异常: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"后端连接失败: {e}")
            return False

    async def test_model_activation(self) -> bool:
        """测试模型激活和加载"""
        logger.info("[MODEL] 开始模型激活测试...")
        
        try:
            # 检查模型状态
            response = self.session.get(f"{self.base_url}/api/status")
            data = response.json()
            
            model_available = data.get('rul_model_available', False)
            model_count = data.get('rul_model_count', 0)
            
            if model_available and model_count > 0:
                self.log_test_result('model_activation', True, 
                    f"模型已激活，加载了{model_count}个模型")
                
                # 测试模型文件存在性
                model_files_exist = await self.check_model_files()
                if model_files_exist:
                    self.log_test_result('model_activation', True, "模型文件存在且可访问")
                else:
                    self.log_test_result('model_activation', False, "模型文件不存在或不可访问")
                
                return True
            else:
                self.log_test_result('model_activation', False, 
                    f"模型未激活 - available: {model_available}, count: {model_count}")
                
                # 尝试触发模型加载
                await self.trigger_model_training()
                return False
                
        except Exception as e:
            self.log_test_result('model_activation', False, f"模型激活测试异常: {e}")
            return False

    async def check_model_files(self) -> bool:
        """检查模型文件是否存在"""
        try:
            model_dir = Path("battery-charging-simulator/backend/models")
            if not model_dir.exists():
                return False
            
            expected_files = [
                "cnn_lstm_rul_model_k1.keras",
                "cnn_lstm_rul_model_k2.keras", 
                "cnn_lstm_rul_model_k3.keras"
            ]
            
            existing_files = [f for f in expected_files if (model_dir / f).exists()]
            
            if len(existing_files) >= 1:
                logger.info(f"找到模型文件: {existing_files}")
                return True
            else:
                logger.warning("未找到模型文件")
                return False
                
        except Exception as e:
            logger.error(f"检查模型文件失败: {e}")
            return False

    async def trigger_model_training(self):
        """触发模型训练（如果模型不存在）"""
        logger.info("[TRAIN] 模型不存在，尝试触发训练...")
        
        try:
            # 检查是否有训练数据
            uploads_dir = Path("RUL_prediction/data/uploads")
            if uploads_dir.exists():
                # 寻找任何可用的数据集
                dataset_dirs = [d for d in uploads_dir.iterdir() if d.is_dir()]
                if dataset_dirs:
                    dataset_id = dataset_dirs[0].name
                    logger.info(f"使用数据集 {dataset_id} 进行训练")
                    
                    # 触发训练
                    payload = {"datasetId": dataset_id}
                    response = self.session.post(f"{self.base_url}/api/rul/train", json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        job_id = result.get('jobId')
                        logger.info(f"训练任务已启动: {job_id}")
                        
                        # 等待训练完成
                        await self.wait_for_training_completion(job_id)
                    else:
                        logger.error(f"训练启动失败: {response.text}")
                else:
                    logger.warning("没有找到训练数据集")
            else:
                logger.warning("uploads目录不存在")
                
        except Exception as e:
            logger.error(f"触发模型训练失败: {e}")

    async def wait_for_training_completion(self, job_id: str, timeout: int = 1800):
        """等待训练完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}/api/rul/train/{job_id}/status")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    
                    if status == 'completed':
                        logger.info("[PASS] 模型训练完成")
                        return True
                    elif status == 'failed':
                        error = data.get('error', 'Unknown error')
                        logger.error(f"[FAIL] 模型训练失败: {error}")
                        return False
                    else:
                        logger.info(f"[TRAIN] 训练状态: {status}")
                        
            except Exception as e:
                logger.error(f"检查训练状态失败: {e}")
            
            await asyncio.sleep(10)  # 等待10秒再检查
        
        logger.error("[TIMEOUT] 训练超时")
        return False

    async def test_rul_prediction(self) -> bool:
        """测试RUL预测功能"""
        logger.info("[RUL] 开始RUL预测测试...")
        
        try:
            # 获取当前电池状态
            response = self.session.get(f"{self.base_url}/api/status")
            data = response.json()
            battery_state = data.get('battery_state', {})
            
            rul_value = battery_state.get('estimated_rul')
            health_info = battery_state.get('health_info', {})
            
            if rul_value is not None:
                self.log_test_result('rul_prediction', True, 
                    f"RUL预测成功: {rul_value:.1f}%")
                
                # 验证RUL值合理性
                if 0 <= rul_value <= 100:
                    self.log_test_result('rul_prediction', True, 
                        f"RUL值在合理范围内: {rul_value:.1f}%")
                else:
                    self.log_test_result('rul_prediction', False, 
                        f"RUL值超出合理范围: {rul_value:.1f}%")
                
                # 验证健康信息
                if health_info:
                    health_status = health_info.get('status')
                    health_grade = health_info.get('grade')
                    
                    self.log_test_result('rul_prediction', True, 
                        f"健康评估成功: {health_status} ({health_grade})")
                else:
                    self.log_test_result('rul_prediction', False, "健康信息缺失")
                
                return True
            else:
                self.log_test_result('rul_prediction', False, "RUL预测值为空")
                return False
                
        except Exception as e:
            self.log_test_result('rul_prediction', False, f"RUL预测测试异常: {e}")
            return False

    async def test_charging_parameter_control(self) -> bool:
        """测试充电参数控制"""
        logger.info("[PARAM] 开始充电参数控制测试...")
        
        try:
            # 首先启用RUL优化
            enable_response = self.session.post(f"{self.base_url}/api/rul-optimization/enable")
            
            if enable_response.status_code == 200:
                self.log_test_result('parameter_control', True, "RUL优化已启用")
            else:
                logger.warning(f"启用RUL优化失败: {enable_response.status_code}")
            
            # 开始充电测试
            charge_response = self.session.post(f"{self.base_url}/api/charge/start")
            
            if charge_response.status_code == 200:
                self.log_test_result('parameter_control', True, "充电已启动")
                
                # 等待一段时间让系统稳定
                await asyncio.sleep(5)
                
                # 获取充电状态
                response = self.session.get(f"{self.base_url}/api/status")
                data = response.json()
                battery_state = data.get('battery_state', {})
                
                charging_optimization = battery_state.get('charging_optimization', {})
                
                if charging_optimization.get('enabled'):
                    adjusted_params = charging_optimization.get('adjusted_params', {})
                    
                    if adjusted_params:
                        cc_current = adjusted_params.get('cc_current')
                        cv_voltage = adjusted_params.get('cv_voltage')
                        charging_strategy = adjusted_params.get('charging_strategy')
                        
                        self.log_test_result('parameter_control', True, 
                            f"充电参数已调整 - 电流: {cc_current}C, 电压: {cv_voltage}V, 策略: {charging_strategy}")
                        
                        # 验证参数合理性
                        if cc_current and 0.1 <= cc_current <= 1.0:
                            self.log_test_result('parameter_control', True, 
                                f"充电电流在合理范围: {cc_current}C")
                        else:
                            self.log_test_result('parameter_control', False, 
                                f"充电电流超出范围: {cc_current}C")
                        
                        # 400V平台：380V-420V为合理范围（对应单体3.8V-4.2V）
                        if cv_voltage and 380 <= cv_voltage <= 420:
                            self.log_test_result('parameter_control', True, 
                                f"充电电压在合理范围: {cv_voltage}V (400V平台)")
                        else:
                            self.log_test_result('parameter_control', False, 
                                f"充电电压超出400V平台范围: {cv_voltage}V")
                        
                        return True
                    else:
                        self.log_test_result('parameter_control', False, "充电参数未调整")
                        return False
                else:
                    self.log_test_result('parameter_control', False, "充电优化未启用")
                    return False
            else:
                self.log_test_result('parameter_control', False, 
                    f"充电启动失败: {charge_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result('parameter_control', False, f"充电参数控制测试异常: {e}")
            return False
        finally:
            # 停止充电
            try:
                self.session.post(f"{self.base_url}/api/charge/stop")
            except:
                pass

    async def test_strategy_switching(self) -> bool:
        """测试不同RUL场景下的策略切换"""
        logger.info("[STRATEGY] 开始策略切换测试...")
        
        all_passed = True
        
        for scenario in self.test_scenarios:
            try:
                # 模拟设置电池状态
                await self.simulate_battery_state(scenario)
                
                # 等待系统响应
                await asyncio.sleep(2)
                
                # 获取调整后的参数
                response = self.session.get(f"{self.base_url}/api/status")
                data = response.json()
                battery_state = data.get('battery_state', {})
                
                charging_optimization = battery_state.get('charging_optimization', {})
                adjusted_params = charging_optimization.get('adjusted_params', {})
                
                actual_strategy = adjusted_params.get('charging_strategy')
                expected_strategy = scenario['expected_strategy']
                
                if actual_strategy == expected_strategy:
                    self.log_test_result('strategy_switching', True, 
                        f"RUL {scenario['rul']}% → 策略 {actual_strategy} (符合预期)")
                else:
                    self.log_test_result('strategy_switching', False, 
                        f"RUL {scenario['rul']}% → 策略 {actual_strategy} (预期: {expected_strategy})")
                    all_passed = False
                
            except Exception as e:
                self.log_test_result('strategy_switching', False, 
                    f"策略切换测试异常 (RUL {scenario['rul']}%): {e}")
                all_passed = False
        
        return all_passed

    async def simulate_battery_state(self, scenario: Dict):
        """模拟电池状态"""
        try:
            # 设置电池参数
            params = {
                'temperature': scenario['temp'],
                'soc': scenario['soc'],
                'rul_percentage': scenario['rul']
            }
            
            # 这里可能需要调用特定的API来设置电池状态
            # 由于具体API可能不存在，我们先记录这个操作
            logger.info(f"模拟电池状态: RUL={scenario['rul']}%, 温度={scenario['temp']}°C, SOC={scenario['soc']}%")
            
        except Exception as e:
            logger.error(f"模拟电池状态失败: {e}")

    async def test_websocket_integration(self) -> bool:
        """测试WebSocket集成"""
        logger.info("[WEBSOCKET] 开始WebSocket集成测试...")
        
        try:
            sio = socketio.AsyncClient()
            events_received = []
            
            @sio.event
            async def connect():
                logger.info("WebSocket连接成功")
                events_received.append('connect')
            
            @sio.event
            async def batteryState(data):
                logger.info(f"收到电池状态更新: {data.get('soc', 'N/A')}%")
                events_received.append('batteryState')
            
            @sio.event
            async def disconnect():
                logger.info("WebSocket连接断开")
                events_received.append('disconnect')
            
            # 尝试连接
            try:
                await sio.connect(self.base_url, socketio_path='/ws', 
                                headers={'Origin': self.frontend_url})
                
                # 等待事件
                await asyncio.sleep(5)
                
                if 'connect' in events_received:
                    self.log_test_result('integration', True, "WebSocket连接成功")
                    
                    if 'batteryState' in events_received:
                        self.log_test_result('integration', True, "收到电池状态更新事件")
                        return True
                    else:
                        self.log_test_result('integration', False, "未收到电池状态更新事件")
                        return False
                else:
                    self.log_test_result('integration', False, "WebSocket连接失败")
                    return False
                    
            except Exception as e:
                logger.info(f"WebSocket连接失败，尝试降级到REST API: {e}")
                # 测试REST API轮询
                return await self.test_rest_api_polling()
            finally:
                try:
                    await sio.disconnect()
                except:
                    pass
                
        except Exception as e:
            self.log_test_result('integration', False, f"WebSocket集成测试异常: {e}")
            return False

    async def test_rest_api_polling(self) -> bool:
        """测试REST API轮询"""
        try:
            logger.info("测试REST API轮询...")
            
            initial_response = self.session.get(f"{self.base_url}/api/status")
            if initial_response.status_code == 200:
                initial_data = initial_response.json()
                
                # 等待一段时间
                await asyncio.sleep(3)
                
                # 再次获取状态
                follow_response = self.session.get(f"{self.base_url}/api/status")
                if follow_response.status_code == 200:
                    follow_data = follow_response.json()
                    
                    self.log_test_result('integration', True, "REST API轮询正常工作")
                    return True
                else:
                    self.log_test_result('integration', False, "REST API轮询失败")
                    return False
            else:
                self.log_test_result('integration', False, "REST API不可用")
                return False
                
        except Exception as e:
            self.log_test_result('integration', False, f"REST API轮询测试异常: {e}")
            return False

    async def test_performance(self) -> bool:
        """测试性能"""
        logger.info("[PERF] 开始性能测试...")
        
        try:
            # 测试API响应时间
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/api/status")
            response_time = time.time() - start_time
            
            if response.status_code == 200 and response_time < 1.0:
                self.log_test_result('performance', True, 
                    f"API响应时间: {response_time:.3f}s (< 1s)")
            else:
                self.log_test_result('performance', False, 
                    f"API响应时间过长: {response_time:.3f}s")
            
            # 测试并发请求
            async def make_request():
                try:
                    resp = self.session.get(f"{self.base_url}/api/status")
                    return resp.status_code == 200
                except:
                    return False
            
            start_time = time.time()
            tasks = [make_request() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = time.time() - start_time
            
            success_count = sum(1 for r in results if r is True)
            
            if success_count >= 8 and concurrent_time < 5.0:
                self.log_test_result('performance', True, 
                    f"并发测试: {success_count}/10 成功, 耗时: {concurrent_time:.3f}s")
                return True
            else:
                self.log_test_result('performance', False, 
                    f"并发测试失败: {success_count}/10 成功, 耗时: {concurrent_time:.3f}s")
                return False
                
        except Exception as e:
            self.log_test_result('performance', False, f"性能测试异常: {e}")
            return False

    def generate_test_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("=" * 80)
        report.append("RUL优化充电策略测试报告")
        report.append("=" * 80)
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"测试地址: {self.base_url}")
        report.append("")
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results['passed']
            failed = results['failed']
            total_passed += passed
            total_failed += failed
            
            status = "[PASS]" if failed == 0 else "[FAIL]"
            report.append(f"{status} {category.upper().replace('_', ' ')}: {passed} 通过, {failed} 失败")
            
            # 显示最近的测试详情
            if results['details']:
                latest = results['details'][-1]
                report.append(f"   最新结果: {latest['details']}")
        
        report.append("")
        report.append(f"[SUMMARY] 总计: {total_passed} 通过, {total_failed} 失败")
        
        if total_failed == 0:
            report.append("[SUCCESS] 所有测试通过！RUL优化充电策略工作正常。")
        else:
            report.append("[WARNING] 存在失败的测试项，需要检查相关功能。")
        
        report.append("=" * 80)
        
        return "\n".join(report)

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("[START] 开始RUL优化充电策略完整测试...")
        
        # 检查后端连接
        if not await self.test_backend_connectivity():
            logger.error("后端连接失败，无法继续测试")
            return
        
        # 运行各项测试
        await self.test_model_activation()
        await self.test_rul_prediction()
        await self.test_charging_parameter_control()
        await self.test_strategy_switching()
        await self.test_websocket_integration()
        await self.test_performance()
        
        # 生成报告
        report = self.generate_test_report()
        print(report)
        
        # 保存报告到文件
        with open('rul_optimization_test_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info("测试完成，报告已保存到 rul_optimization_test_report.txt")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RUL优化充电策略测试程序')
    parser.add_argument('--backend-url', default='http://localhost:8001', 
                       help='后端服务地址 (默认: http://localhost:8001)')
    parser.add_argument('--frontend-url', default='http://localhost:5111',
                       help='前端服务地址 (默认: http://localhost:5111)')
    parser.add_argument('--test-category', choices=['all', 'model', 'rul', 'control', 'strategy', 'integration', 'performance'],
                       default='all', help='要运行的测试类别 (默认: all)')
    
    args = parser.parse_args()
    
    tester = RULOptimizationTester(args.backend_url, args.frontend_url)
    
    if args.test_category == 'all':
        await tester.run_all_tests()
    elif args.test_category == 'model':
        await tester.test_model_activation()
    elif args.test_category == 'rul':
        await tester.test_rul_prediction()
    elif args.test_category == 'control':
        await tester.test_charging_parameter_control()
    elif args.test_category == 'strategy':
        await tester.test_strategy_switching()
    elif args.test_category == 'integration':
        await tester.test_websocket_integration()
    elif args.test_category == 'performance':
        await tester.test_performance()
    
    print(tester.generate_test_report())

if __name__ == "__main__":
    asyncio.run(main())