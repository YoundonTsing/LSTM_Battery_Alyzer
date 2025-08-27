#!/usr/bin/env python3
"""
RUL优化充电策略测试运行器
提供统一的测试入口和结果汇总
"""

import subprocess
import sys
import time
import os
from datetime import datetime
from pathlib import Path

class TestRunner:
    def __init__(self, backend_url="http://localhost:8001"):
        self.backend_url = backend_url
        self.test_scripts = [
            {
                'name': '快速功能测试',
                'script': 'quick_rul_test.py',
                'description': '测试基本功能是否正常工作',
                'required': True
            },
            {
                'name': '策略切换测试',
                'script': 'test_charging_strategy_switch.py', 
                'description': '测试不同RUL条件下的策略切换',
                'required': True
            },
            {
                'name': '完整系统测试',
                'script': 'test_rul_optimization_system.py',
                'description': '全面的系统集成测试',
                'required': False
            }
        ]
        
        self.results = []

    def check_prerequisites(self):
        """检查测试前提条件"""
        print("🔍 检查测试环境...")
        
        # 检查测试脚本是否存在
        missing_scripts = []
        for test in self.test_scripts:
            if not Path(test['script']).exists():
                missing_scripts.append(test['script'])
        
        if missing_scripts:
            print(f"❌ 缺少测试脚本: {', '.join(missing_scripts)}")
            return False
        
        # 检查Python依赖
        required_packages = ['requests', 'asyncio', 'aiohttp']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ 缺少Python包: {', '.join(missing_packages)}")
            print("请运行: pip install requests aiohttp")
            return False
        
        print("✅ 测试环境检查通过")
        return True

    def run_test_script(self, script_info):
        """运行单个测试脚本"""
        script_name = script_info['script']
        test_name = script_info['name']
        
        print(f"\n{'='*60}")
        print(f"🧪 运行测试: {test_name}")
        print(f"📄 脚本: {script_name}")
        print(f"📝 描述: {script_info['description']}")
        print('='*60)
        
        start_time = time.time()
        
        try:
            # 运行测试脚本
            cmd = [sys.executable, script_name, self.backend_url]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            duration = time.time() - start_time
            
            # 处理结果
            success = result.returncode == 0
            
            test_result = {
                'name': test_name,
                'script': script_name,
                'success': success,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'required': script_info['required']
            }
            
            self.results.append(test_result)
            
            # 显示测试输出
            if result.stdout:
                print(result.stdout)
            
            if result.stderr:
                print(f"\n⚠️ 错误输出:\n{result.stderr}")
            
            status = "✅ 成功" if success else "❌ 失败"
            print(f"\n🎯 测试结果: {status} (耗时: {duration:.1f}秒)")
            
            return success
            
        except subprocess.TimeoutExpired:
            print("⏰ 测试超时 (>5分钟)")
            test_result = {
                'name': test_name,
                'script': script_name,
                'success': False,
                'duration': 300,
                'stdout': '',
                'stderr': 'Test timeout',
                'required': script_info['required']
            }
            self.results.append(test_result)
            return False
            
        except Exception as e:
            print(f"❌ 运行测试失败: {e}")
            test_result = {
                'name': test_name,
                'script': script_name,
                'success': False,
                'duration': 0,
                'stdout': '',
                'stderr': str(e),
                'required': script_info['required']
            }
            self.results.append(test_result)
            return False

    def generate_summary_report(self):
        """生成测试总结报告"""
        print("\n" + "="*80)
        print("📊 RUL优化充电策略测试总结报告")
        print("="*80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试地址: {self.backend_url}")
        print(f"总测试数: {len(self.results)}")
        
        # 分类统计
        required_tests = [r for r in self.results if r['required']]
        optional_tests = [r for r in self.results if not r['required']]
        
        required_passed = sum(1 for r in required_tests if r['success'])
        optional_passed = sum(1 for r in optional_tests if r['success'])
        
        print(f"\n📋 必需测试: {required_passed}/{len(required_tests)} 通过")
        print(f"📋 可选测试: {optional_passed}/{len(optional_tests)} 通过")
        
        # 详细结果
        print(f"\n📄 详细结果:")
        for result in self.results:
            status = "✅" if result['success'] else "❌"
            required = "🔴" if result['required'] else "🔵"
            duration = f"{result['duration']:.1f}s"
            print(f"{status} {required} {result['name']} ({duration})")
            
            if not result['success'] and result['stderr']:
                print(f"    错误: {result['stderr']}")
        
        # 总体评估
        print(f"\n🎯 总体评估:")
        
        if required_passed == len(required_tests):
            if optional_passed == len(optional_tests):
                print("🎉 所有测试通过！RUL优化充电策略完全正常工作。")
                overall_status = "excellent"
            else:
                print("👍 核心功能正常！可选功能存在问题。")
                overall_status = "good"
        else:
            if required_passed >= len(required_tests) * 0.8:
                print("⚠️ 大部分核心功能正常，存在一些问题需要修复。")
                overall_status = "fair"
            else:
                print("❌ 核心功能存在重要问题，系统可能无法正常工作。")
                overall_status = "poor"
        
        # 建议
        print(f"\n💡 建议:")
        if overall_status == "excellent":
            print("   • 系统工作完美，可以正常使用")
            print("   • 可以考虑添加更多高级功能")
        elif overall_status == "good":
            print("   • 核心功能正常，可以投入使用")
            print("   • 建议修复可选功能的问题")
        elif overall_status == "fair":
            print("   • 需要修复失败的测试项")
            print("   • 建议检查模型文件和配置")
        else:
            print("   • 需要全面检查系统配置")
            print("   • 确保后端服务正常运行")
            print("   • 检查RUL模型是否正确加载")
        
        return overall_status

    def save_detailed_report(self):
        """保存详细测试报告"""
        report_file = f"rul_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("RUL优化充电策略测试详细报告\n")
            f.write("="*80 + "\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试地址: {self.backend_url}\n\n")
            
            for result in self.results:
                f.write(f"测试: {result['name']}\n")
                f.write(f"脚本: {result['script']}\n")
                f.write(f"结果: {'成功' if result['success'] else '失败'}\n")
                f.write(f"耗时: {result['duration']:.1f}秒\n")
                f.write(f"必需: {'是' if result['required'] else '否'}\n")
                
                if result['stdout']:
                    f.write(f"\n标准输出:\n{result['stdout']}\n")
                
                if result['stderr']:
                    f.write(f"\n错误输出:\n{result['stderr']}\n")
                
                f.write("\n" + "-"*60 + "\n\n")
        
        print(f"\n📄 详细报告已保存到: {report_file}")

    def run_all_tests(self, run_optional=True):
        """运行所有测试"""
        if not self.check_prerequisites():
            return False
        
        print("🚀 开始RUL优化充电策略测试套件")
        print(f"目标地址: {self.backend_url}")
        
        all_success = True
        
        # 运行必需测试
        for test in self.test_scripts:
            if test['required']:
                success = self.run_test_script(test)
                if not success:
                    all_success = False
        
        # 运行可选测试
        if run_optional:
            for test in self.test_scripts:
                if not test['required']:
                    self.run_test_script(test)
        
        # 生成报告
        overall_status = self.generate_summary_report()
        self.save_detailed_report()
        
        return overall_status in ['excellent', 'good']

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RUL优化充电策略测试运行器')
    parser.add_argument('--backend-url', default='http://localhost:8001',
                       help='后端服务地址 (默认: http://localhost:8001)')
    parser.add_argument('--skip-optional', action='store_true',
                       help='跳过可选测试，只运行必需测试')
    parser.add_argument('--test', choices=['quick', 'strategy', 'full'],
                       help='运行特定测试 (quick: 快速测试, strategy: 策略测试, full: 完整测试)')
    
    args = parser.parse_args()
    
    runner = TestRunner(args.backend_url)
    
    if args.test:
        # 运行特定测试
        test_map = {
            'quick': 'quick_rul_test.py',
            'strategy': 'test_charging_strategy_switch.py',
            'full': 'test_rul_optimization_system.py'
        }
        
        script_name = test_map[args.test]
        test_info = next((t for t in runner.test_scripts if t['script'] == script_name), None)
        
        if test_info:
            success = runner.run_test_script(test_info)
            sys.exit(0 if success else 1)
        else:
            print(f"❌ 未找到测试: {args.test}")
            sys.exit(1)
    else:
        # 运行所有测试
        success = runner.run_all_tests(not args.skip_optional)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()