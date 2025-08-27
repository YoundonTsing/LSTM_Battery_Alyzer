#!/usr/bin/env python3
"""
充电策略切换测试脚本
专门测试不同RUL条件下的充电策略切换功能
"""

import requests
import time
import json
from typing import Dict, List

class ChargingStrategyTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Origin': 'http://localhost:5111',
            'Content-Type': 'application/json'
        })
        
        # 测试场景定义
        self.test_scenarios = [
            {
                'name': '新电池 - 高RUL',
                'rul': 90,
                'temp': 25,
                'soc': 50,
                'expected_strategy': 'standard',
                'expected_cc_range': (0.8, 1.0),
                'expected_max_soc': 100
            },
            {
                'name': '正常使用 - 中等RUL',
                'rul': 65,
                'temp': 30,
                'soc': 60,
                'expected_strategy': 'eco',
                'expected_cc_range': (0.7, 0.9),
                'expected_max_soc': 90
            },
            {
                'name': '老化电池 - 低RUL',
                'rul': 35,
                'temp': 25,
                'soc': 40,
                'expected_strategy': 'longevity',
                'expected_cc_range': (0.5, 0.7),
                'expected_max_soc': 80
            },
            {
                'name': '高温环境 - 中等RUL',
                'rul': 70,
                'temp': 40,
                'soc': 50,
                'expected_strategy': 'eco',
                'expected_cc_range': (0.6, 0.8),
                'expected_max_soc': 90
            },
            {
                'name': '高SOC状态 - 中等RUL',
                'rul': 60,
                'temp': 25,
                'soc': 85,
                'expected_strategy': 'eco',
                'expected_cc_range': (0.4, 0.7),
                'expected_max_soc': 90
            }
        ]

    def get_current_battery_state(self) -> Dict:
        """获取当前电池状态"""
        try:
            response = self.session.get(f"{self.base_url}/api/status")
            if response.status_code == 200:
                data = response.json()
                return data.get('battery_state', {})
            else:
                print(f"获取电池状态失败: {response.status_code}")
                return {}
        except Exception as e:
            print(f"获取电池状态异常: {e}")
            return {}

    def analyze_charging_parameters(self, battery_state: Dict, scenario: Dict) -> Dict:
        """分析充电参数"""
        charging_optimization = battery_state.get('charging_optimization', {})
        adjusted_params = charging_optimization.get('adjusted_params', {})
        
        analysis = {
            'scenario_name': scenario['name'],
            'input_rul': scenario['rul'],
            'input_temp': scenario['temp'],
            'input_soc': scenario['soc'],
            'actual_rul': battery_state.get('estimated_rul'),
            'actual_temp': battery_state.get('temperature'),
            'actual_soc': battery_state.get('soc'),
            'optimization_enabled': charging_optimization.get('enabled', False),
            'actual_strategy': adjusted_params.get('charging_strategy'),
            'actual_cc_current': adjusted_params.get('cc_current'),
            'actual_cv_voltage': adjusted_params.get('cv_voltage'),
            'actual_max_soc': adjusted_params.get('max_soc'),
            'charging_advice': charging_optimization.get('charging_advice', []),
            'expected_strategy': scenario['expected_strategy'],
            'expected_cc_range': scenario['expected_cc_range'],
            'expected_max_soc': scenario['expected_max_soc']
        }
        
        return analysis

    def validate_strategy(self, analysis: Dict) -> Dict:
        """验证策略是否正确"""
        validation = {
            'strategy_correct': False,
            'cc_current_correct': False,
            'max_soc_correct': False,
            'overall_correct': False,
            'issues': []
        }
        
        # 验证策略选择
        actual_strategy = analysis['actual_strategy']
        expected_strategy = analysis['expected_strategy']
        
        if actual_strategy == expected_strategy:
            validation['strategy_correct'] = True
        else:
            validation['issues'].append(f"策略不匹配: 实际={actual_strategy}, 预期={expected_strategy}")
        
        # 验证CC电流范围
        actual_cc = analysis['actual_cc_current']
        expected_cc_range = analysis['expected_cc_range']
        
        if actual_cc and expected_cc_range[0] <= actual_cc <= expected_cc_range[1]:
            validation['cc_current_correct'] = True
        else:
            validation['issues'].append(f"CC电流超出预期范围: 实际={actual_cc}, 预期={expected_cc_range}")
        
        # 验证最大SOC
        actual_max_soc = analysis['actual_max_soc']
        expected_max_soc = analysis['expected_max_soc']
        
        if actual_max_soc == expected_max_soc:
            validation['max_soc_correct'] = True
        else:
            validation['issues'].append(f"最大SOC不匹配: 实际={actual_max_soc}, 预期={expected_max_soc}")
        
        # 整体验证
        validation['overall_correct'] = (
            validation['strategy_correct'] and 
            validation['cc_current_correct'] and 
            validation['max_soc_correct']
        )
        
        return validation

    def print_analysis_result(self, analysis: Dict, validation: Dict):
        """打印分析结果"""
        print(f"\n📋 场景: {analysis['scenario_name']}")
        print("─" * 60)
        
        # 输入参数
        print("📥 输入参数:")
        print(f"   RUL: {analysis['input_rul']}%")
        print(f"   温度: {analysis['input_temp']}°C")
        print(f"   SOC: {analysis['input_soc']}%")
        
        # 实际状态
        print("\n📊 实际状态:")
        print(f"   RUL: {analysis['actual_rul']:.1f}%" if analysis['actual_rul'] else "   RUL: N/A")
        print(f"   温度: {analysis['actual_temp']:.1f}°C" if analysis['actual_temp'] else "   温度: N/A")
        print(f"   SOC: {analysis['actual_soc']:.1f}%" if analysis['actual_soc'] else "   SOC: N/A")
        print(f"   优化启用: {'是' if analysis['optimization_enabled'] else '否'}")
        
        # 充电参数
        print("\n⚙️ 充电参数:")
        print(f"   策略: {analysis['actual_strategy']} (预期: {analysis['expected_strategy']})")
        if analysis['actual_cc_current']:
            print(f"   CC电流: {analysis['actual_cc_current']:.3f}C (预期: {analysis['expected_cc_range'][0]:.1f}-{analysis['expected_cc_range'][1]:.1f}C)")
        if analysis['actual_cv_voltage']:
            print(f"   CV电压: {analysis['actual_cv_voltage']:.2f}V")
        if analysis['actual_max_soc']:
            print(f"   最大SOC: {analysis['actual_max_soc']}% (预期: {analysis['expected_max_soc']}%)")
        
        # 充电建议
        if analysis['charging_advice']:
            print("\n💡 充电建议:")
            for advice in analysis['charging_advice']:
                print(f"   • {advice}")
        
        # 验证结果
        print("\n✅ 验证结果:")
        for key, result in validation.items():
            if key == 'issues':
                continue
            status = "✅" if result else "❌"
            print(f"   {status} {key.replace('_', ' ').title()}")
        
        if validation['issues']:
            print("\n⚠️ 发现问题:")
            for issue in validation['issues']:
                print(f"   • {issue}")
        
        overall_status = "✅ 通过" if validation['overall_correct'] else "❌ 失败"
        print(f"\n🎯 整体评估: {overall_status}")

    def test_single_scenario(self, scenario: Dict) -> bool:
        """测试单个场景"""
        print(f"\n🧪 测试场景: {scenario['name']}")
        
        try:
            # 获取当前电池状态
            battery_state = self.get_current_battery_state()
            
            if not battery_state:
                print("❌ 无法获取电池状态")
                return False
            
            # 分析充电参数
            analysis = self.analyze_charging_parameters(battery_state, scenario)
            
            # 验证策略
            validation = self.validate_strategy(analysis)
            
            # 打印结果
            self.print_analysis_result(analysis, validation)
            
            return validation['overall_correct']
            
        except Exception as e:
            print(f"❌ 测试场景失败: {e}")
            return False

    def test_all_scenarios(self) -> List[Dict]:
        """测试所有场景"""
        print("🚀 开始充电策略切换测试")
        print("=" * 80)
        
        results = []
        
        for scenario in self.test_scenarios:
            success = self.test_single_scenario(scenario)
            results.append({
                'scenario': scenario['name'],
                'success': success
            })
            
            # 等待一段时间再测试下一个场景
            time.sleep(2)
        
        return results

    def print_summary(self, results: List[Dict]):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("📊 充电策略切换测试总结")
        print("=" * 80)
        
        passed = 0
        total = len(results)
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['scenario']}")
            if result['success']:
                passed += 1
        
        print(f"\n📈 测试结果: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 所有策略切换测试通过！")
            print("   RUL优化充电策略工作完全正常。")
        elif passed >= total * 0.8:
            print("👍 大部分策略切换正常工作。")
            print("   可能存在个别场景的参数微调问题。")
        else:
            print("⚠️ 策略切换存在重要问题。")
            print("   需要检查RUL预测模型和参数调控逻辑。")
        
        return passed == total

    def run_comprehensive_test(self):
        """运行综合测试"""
        # 首先检查系统状态
        print("🔍 检查系统状态...")
        battery_state = self.get_current_battery_state()
        
        if not battery_state:
            print("❌ 系统连接失败，无法继续测试")
            return False
        
        charging_optimization = battery_state.get('charging_optimization', {})
        rul_value = battery_state.get('estimated_rul')
        
        print(f"   RUL模型状态: {'可用' if rul_value is not None else '不可用'}")
        print(f"   充电优化状态: {'启用' if charging_optimization.get('enabled') else '禁用'}")
        
        if rul_value is None:
            print("⚠️ RUL模型未激活，某些测试可能不准确")
        
        # 运行所有场景测试
        results = self.test_all_scenarios()
        
        # 打印总结
        success = self.print_summary(results)
        
        return success

def main():
    """主函数"""
    import sys
    
    base_url = "http://localhost:8001"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"测试地址: {base_url}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = ChargingStrategyTester(base_url)
    success = tester.run_comprehensive_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()