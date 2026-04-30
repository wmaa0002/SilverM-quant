"""
Integration tests for strategy registry.

Tests verify that Registry works correctly with existing strategies:
- Loading strategy classes from files
- Metadata consistency with STRATEGY_CONFIG
- Backward compatibility
- Strategy instantiation validation

Run with: pytest tests/strategies/test_registry_integration.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from strategies.registry import Registry, StrategyMetadata


class TestLoadExistingStrategies:
    def test_load_existing_strategies(self):
        registry = Registry()
        
        expected_strategies = [
            '天宫B2策略v2',
            '天宫B1策略v2.1',
            '天宫暴力K策略V1',
            '天宫暴力K+B2策略V1',
            '天宫地量策略V1',
            '天宫沙尘暴策略V1',
            '天宫单针30策略V1',
        ]
        
        registered_strategies = registry.list()
        
        loaded_count = 0
        for strategy_name in expected_strategies:
            if strategy_name in registered_strategies:
                strategy_class = registry.get(strategy_name)
                if strategy_class is not None:
                    loaded_count += 1
                    assert isinstance(strategy_class, type), \
                        f"{strategy_name} should return a class type"
        
        assert loaded_count >= 5, \
            f"Expected at least 5 strategies to be loadable, got {loaded_count}"

    def test_b2_strategy_class_loadable(self):
        registry = Registry()
        
        strategy_name = '天宫B2策略v2'
        assert strategy_name in registry.list(), \
            f"{strategy_name} should be in registry"
        
        strategy_class = registry.get(strategy_name)
        assert strategy_class is not None, f"Failed to load {strategy_name}"
        assert isinstance(strategy_class, type), f"{strategy_name} should be a class"


class TestB2StrategyMetadata:
    def test_b2_strategy_metadata(self):
        registry = Registry()
        
        b2_strategies = [name for name in registry.list() if 'B2' in name and '暴力K' not in name]
        assert len(b2_strategies) > 0, "No B2 strategies registered"
        
        for name in b2_strategies:
            metadata = registry.get_metadata(name)
            assert metadata is not None, f"No metadata for {name}"
            
            assert metadata.threshold_required is True, \
                f"{name} should require threshold"
            
            assert metadata.min_data_days >= 60, \
                f"{name} should need at least 60 days of data"

    def test_b2_strategy_metadata_consistency(self):
        registry = Registry()
        
        b2_strategies = [name for name in registry.list() if 'B2' in name and '暴力K' not in name]
        
        for name in b2_strategies:
            assert registry.is_registered(name), f"{name} should be registered"
            
            metadata = registry.get_metadata(name)
            assert metadata is not None
            assert metadata.name == name
            
            filtered = registry.filter(threshold_required=True)
            assert name in filtered, f"{name} should be in threshold_required=True filter"


class TestBLKStrategyMetadata:
    def test_blk_strategy_metadata(self):
        registry = Registry()
        
        strategy_name = '天宫暴力K策略V1'
        assert strategy_name in registry.list(), \
            f"{strategy_name} should be registered"
        
        metadata = registry.get_metadata(strategy_name)
        assert metadata is not None, f"No metadata for {strategy_name}"
        
        assert metadata.threshold_required is False, \
            f"{strategy_name} should NOT require threshold"
        
        assert metadata.min_data_days == 30, \
            f"{strategy_name} should need exactly 30 days of data"

    def test_blk_strategy_filter(self):
        registry = Registry()
        
        no_threshold_strategies = registry.filter(threshold_required=False)
        
        strategy_name = '天宫暴力K策略V1'
        assert strategy_name in no_threshold_strategies, \
            f"{strategy_name} should be in threshold_required=False filter"


class TestBackwardCompatWithStrategyConfig:
    def test_backward_compat_with_strategy_config(self):
        registry = Registry()
        
        file_based_strategies = {
            '天宫B2策略v2': {'threshold_required': True, 'min_data_days': 60},
            '天宫暴力K策略V1': {'threshold_required': False, 'min_data_days': 30},
            '天宫暴力K+B2策略V1': {'threshold_required': True, 'min_data_days': 60},
            '天宫地量策略V1': {'threshold_required': False, 'min_data_days': 50},
            '天宫单针30策略V1': {'threshold_required': False, 'min_data_days': 60},
        }
        
        for strategy_name, expected_config in file_based_strategies.items():
            if strategy_name in registry.list():
                metadata = registry.get_metadata(strategy_name)
                assert metadata is not None, f"Missing metadata for {strategy_name}"
                
                assert metadata.threshold_required == expected_config['threshold_required'], \
                    f"{strategy_name}: threshold_required mismatch"
                assert metadata.min_data_days == expected_config['min_data_days'], \
                    f"{strategy_name}: min_data_days mismatch"

    def test_strategy_config_loaded_on_init(self):
        registry = Registry()
        
        config_strategies = [
            '天宫B2策略v2',
            '天宫暴力K策略V1',
            '天宫地量策略V1',
        ]
        
        for name in config_strategies:
            assert name in registry.list(), \
                f"{name} from STRATEGY_CONFIG should be loaded"


class TestAllRegisteredStrategiesValid:
    def test_all_registered_strategies_are_valid(self):
        registry = Registry()
        
        all_strategies = registry.list()
        assert len(all_strategies) >= 5, \
            f"Expected at least 5 registered strategies, got {len(all_strategies)}"
        
        base_strategy_based = [
            '天宫B2策略v2',
            '天宫暴力K策略V1',
            '天宫地量策略V1',
            '天宫沙尘暴策略V1',
            '天宫单针30策略V1',
        ]
        
        for name in base_strategy_based:
            if name in all_strategies:
                strategy_class = registry.get(name)
                assert strategy_class is not None and isinstance(strategy_class, type), \
                    f"{name} should be a valid loadable strategy class"

    def test_strategy_inheritance(self):
        registry = Registry()
        
        from strategies.base.framework_strategy import BaseStrategy
        
        for strategy_name in registry.list():
            strategy_class = registry.get(strategy_name)
            if strategy_class is not None:
                assert issubclass(strategy_class, BaseStrategy), \
                    f"{strategy_name} should inherit from BaseStrategy"

    def test_registry_list_returns_all_strategies(self):
        registry = Registry()
        
        strategies = registry.list()
        assert isinstance(strategies, list), "list() should return a list"
        assert len(strategies) >= 5, \
            f"Expected at least 5 strategies, got {len(strategies)}"
        
        expected_present = [
            '天宫B2策略v2',
            '天宫暴力K策略V1',
        ]
        
        for name in expected_present:
            if name not in strategies:
                b2_found = any('B2' in s for s in strategies)
                blk_found = any('暴力K' in s for s in strategies)
                assert b2_found or blk_found, \
                    f"Neither B2 nor BLK strategies found in {strategies}"


class TestRegistryIteration:
    def test_registry_contains(self):
        registry = Registry()
        
        for name in registry.list():
            assert name in registry, f"{name} should be in registry"

    def test_registry_len(self):
        registry = Registry()
        
        count = len(registry)
        assert count >= 5, f"Expected at least 5 strategies, got {count}"

    def test_registry_iter(self):
        registry = Registry()
        
        count = 0
        for name in registry:
            count += 1
            assert isinstance(name, str)
        
        assert count == len(registry)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
