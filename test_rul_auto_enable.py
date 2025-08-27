#!/usr/bin/env python3
"""
测试RUL优化充电自动启用功能
验证服务器启动时是否自动启用RUL优化充电
"""

import asyncio
import aiohttp
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RulAutoEnableTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url

    async def test_rul_auto_enable(self):
        """测试RUL优化充电自动启用功能"""
        logger.info("[TEST] 测试RUL优化充电自动启用功能...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # 等待服务器完全启动
                logger.info("等待服务器启动...")
                await asyncio.sleep(3)
                
                # 1. 检查服务器状态
                logger.info("步骤1: 检查服务器启动状态...")
                async with session.get(f"{self.base_url}/api/status") as response:
                    if response.status == 200:
                        status_data = await response.json()
                        logger.info("✅ 服务器响应正常")
                        
                        # 检查RUL优化充电状态
                        battery_state = status_data.get("battery_state", {})
                        rul_optimized = battery_state.get("rul_optimized_charging", False)
                        
                        if rul_optimized:
                            logger.info("✅ RUL优化充电已自动启用")
                        else:
                            logger.warning("❌ RUL优化充电未自动启用")
                        
                        # 显示相关状态
                        logger.info(f"   电池SOC: {battery_state.get('soc', 'N/A')}%")
                        logger.info(f"   电池电压: {battery_state.get('voltage', 'N/A')}V")
                        logger.info(f"   RUL优化状态: {'已启用' if rul_optimized else '已禁用'}")
                        
                        # 检查充电优化信息
                        charging_opt = battery_state.get("charging_optimization", {})
                        if charging_opt:
                            logger.info(f"   充电优化功能: {'已启用' if charging_opt.get('enabled') else '已禁用'}")
                            if charging_opt.get('adjusted_params'):
                                params = charging_opt['adjusted_params']
                                logger.info(f"   调整后充电参数: CC={params.get('cc_current', 'N/A')}C, CV={params.get('cv_voltage', 'N/A')}V")
                        
                    else:
                        logger.error(f"❌ 服务器响应异常: {response.status}")
                        return False

                # 2. 测试RUL优化API响应
                logger.info("\n步骤2: 测试RUL优化API响应...")
                async with session.get(f"{self.base_url}/api/simulator/rul-optimization") as response:
                    if response.status == 200:
                        rul_data = await response.json()
                        logger.info("✅ RUL优化API响应正常")
                        logger.info(f"   API返回状态: {'已启用' if rul_data.get('rul_optimized_charging') else '已禁用'}")
                    else:
                        logger.warning(f"⚠️ RUL优化API响应异常: {response.status}")

                # 3. 测试前端状态同步
                logger.info("\n步骤3: 验证状态一致性...")
                await asyncio.sleep(1)
                
                async with session.get(f"{self.base_url}/api/status") as response:
                    if response.status == 200:
                        final_status = await response.json()
                        battery_state = final_status.get("battery_state", {})
                        rul_optimized = battery_state.get("rul_optimized_charging", False)
                        charging_opt = battery_state.get("charging_optimization", {})
                        
                        # 验证状态一致性
                        if rul_optimized and charging_opt.get("enabled"):
                            logger.info("✅ 状态一致性验证通过")
                            logger.info("   - RUL优化充电: 已启用")
                            logger.info("   - 充电优化功能: 已启用")
                            return True
                        else:
                            logger.warning("⚠️ 状态一致性验证失败")
                            logger.warning(f"   - RUL优化充电: {'已启用' if rul_optimized else '已禁用'}")
                            logger.warning(f"   - 充电优化功能: {'已启用' if charging_opt.get('enabled') else '已禁用'}")
                            return False
                
            except Exception as e:
                logger.error(f"测试过程中发生异常: {e}")
                return False

    async def test_charging_with_rul(self):
        """测试带RUL优化的充电功能"""
        logger.info("\n[TEST] 测试带RUL优化的充电功能...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # 设置电池到较低SOC
                logger.info("设置电池SOC到70%...")
                battery_params = {"soc": 70.0, "temperature": 25.0}
                async with session.post(f"{self.base_url}/api/battery/update-params", json=battery_params) as response:
                    if response.status == 200:
                        logger.info("✅ 电池参数设置成功")
                    else:
                        logger.warning(f"⚠️ 设置电池参数失败: {response.status}")

                await asyncio.sleep(1)

                # 开始充电
                logger.info("开始RUL优化充电...")
                async with session.post(f"{self.base_url}/api/charge/start") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ 充电已开始，记录ID: {data.get('charging_record_id')}")
                    else:
                        logger.error(f"❌ 充电开始失败: {response.status}")
                        return False

                # 监控充电过程5秒
                logger.info("监控RUL优化充电过程...")
                for i in range(5):
                    await asyncio.sleep(1)
                    async with session.get(f"{self.base_url}/api/status") as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            battery_state = status_data.get("battery_state", {})
                            soc = battery_state.get("soc", 0)
                            current = battery_state.get("current", 0)
                            mode = battery_state.get("charging_mode", "none")
                            rul_enabled = battery_state.get("rul_optimized_charging", False)
                            
                            logger.info(f"   第{i+1}秒: SOC={soc:.1f}%, 电流={current:.1f}A, 模式={mode}, RUL={'启用' if rul_enabled else '禁用'}")

                # 停止充电
                logger.info("停止充电...")
                async with session.post(f"{self.base_url}/api/charge/stop") as response:
                    if response.status == 200:
                        logger.info("✅ 充电已停止")
                    else:
                        logger.warning(f"⚠️ 充电停止失败: {response.status}")

                return True

            except Exception as e:
                logger.error(f"充电测试过程中发生异常: {e}")
                return False

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始RUL优化自动启用功能测试")
        logger.info("="*60)
        
        # 测试1: RUL自动启用
        test1_result = await self.test_rul_auto_enable()
        
        # 测试2: 带RUL的充电功能
        test2_result = await self.test_charging_with_rul()
        
        # 总结
        logger.info("\n" + "="*60)
        logger.info("测试结果总结:")
        logger.info(f"  RUL自动启用: {'✅ 通过' if test1_result else '❌ 失败'}")
        logger.info(f"  RUL优化充电: {'✅ 通过' if test2_result else '❌ 失败'}")
        
        if test1_result and test2_result:
            logger.info("\n🎉 所有测试通过！RUL优化充电自动启用功能正常工作。")
        else:
            logger.warning("\n⚠️ 存在测试失败，请检查服务器配置。")

async def main():
    print("\n" + "="*60)
    print("RUL优化充电自动启用功能测试")
    print("="*60)
    print("此测试将验证:")
    print("1. 服务器启动时RUL优化充电是否自动启用")
    print("2. 前端状态是否正确同步")
    print("3. RUL优化充电功能是否正常工作")
    print("="*60)
    
    tester = RulAutoEnableTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())