"""Tests for strategies registry module."""

import pytest
from strategies.registry import Registry, register, StrategyMetadata


class MockStrategy:
    """Mock strategy class for testing."""
    pass


class MockStrategy2:
    """Another mock strategy class for testing."""
    pass


class TestRegistrySingleton:
    """Tests for Registry singleton pattern."""

    def setup_method(self):
        Registry.clear()

    def test_registry_singleton(self):
        """Test that Registry uses singleton pattern."""
        registry1 = Registry()
        registry2 = Registry()
        assert registry1 is registry2


class TestRegisterDecorator:
    """Tests for @register decorator."""

    def setup_method(self):
        Registry.clear()

    def test_register_decorator(self):
        """Test @register decorator registers strategy correctly."""
        @register(name='TestStrategy', threshold_required=False, min_data_days=30, description='Test')
        class TestClass:
            pass

        registry = Registry()
        assert registry.is_registered('TestStrategy')
        strategy_class = registry.get('TestStrategy')
        assert strategy_class == TestClass
        metadata = registry.get_metadata('TestStrategy')
        assert metadata.threshold_required == False
        assert metadata.min_data_days == 30


class TestRegistryGet:
    """Tests for Registry.get() method."""

    def setup_method(self):
        Registry.clear()

    def test_get_valid_strategy(self):
        """Test get() with valid strategy returns class."""
        metadata = StrategyMetadata(
            name='MockStrategy',
            threshold_required=True,
            min_data_days=60,
            description='Test strategy'
        )
        registry = Registry()
        registry.register('MockStrategy', metadata)
        registry._classes['MockStrategy'] = MockStrategy

        result = registry.get('MockStrategy')
        assert result == MockStrategy

    def test_get_invalid_strategy(self):
        """Test get() with invalid strategy returns None."""
        registry = Registry()
        result = registry.get('NonExistentStrategy')
        assert result is None


class TestRegistryList:
    """Tests for Registry.list() method."""

    def setup_method(self):
        Registry.clear()

    def test_list_strategies(self):
        """Test list() returns list of strategy names."""
        registry = Registry()
        initial_count = len(registry.list())
        registry.register('Strategy1', StrategyMetadata(name='Strategy1', threshold_required=True, min_data_days=60))
        registry.register('Strategy2', StrategyMetadata(name='Strategy2', threshold_required=False, min_data_days=30))

        result = registry.list()
        assert isinstance(result, list)
        assert len(result) == initial_count + 2
        assert 'Strategy1' in result
        assert 'Strategy2' in result


class TestRegistryIsRegistered:
    """Tests for Registry.is_registered() method."""

    def setup_method(self):
        Registry.clear()

    def test_is_registered(self):
        """Test is_registered() returns correct boolean."""
        registry = Registry()
        registry.register('RegisteredStrategy', StrategyMetadata(name='RegisteredStrategy'))

        assert registry.is_registered('RegisteredStrategy') == True
        assert registry.is_registered('NonExistentStrategy') == False


class TestRegistryFilter:
    """Tests for Registry.filter() method."""

    def setup_method(self):
        Registry.clear()

    def test_filter_by_threshold(self):
        """Test filter(threshold_required=True) filters correctly."""
        registry = Registry()
        registry.register('ThresholdStrategy', StrategyMetadata(name='ThresholdStrategy', threshold_required=True, min_data_days=60))
        registry.register('NoThresholdStrategy', StrategyMetadata(name='NoThresholdStrategy', threshold_required=False, min_data_days=30))

        result = registry.filter(threshold_required=True)
        assert isinstance(result, list)
        assert 'ThresholdStrategy' in result
        assert 'NoThresholdStrategy' not in result

    def test_filter_by_min_data_days(self):
        """Test filter(min_data_days=60) filters correctly."""
        registry = Registry()
        registry.register('HighDaysStrategy', StrategyMetadata(name='HighDaysStrategy', min_data_days=120))
        registry.register('LowDaysStrategy', StrategyMetadata(name='LowDaysStrategy', min_data_days=30))
        registry.register('ExactDaysStrategy', StrategyMetadata(name='ExactDaysStrategy', min_data_days=60))

        result = registry.filter(min_data_days=60)
        assert isinstance(result, list)
        assert 'ExactDaysStrategy' in result


class TestRegistryMetadata:
    """Tests for metadata storage."""

    def setup_method(self):
        Registry.clear()

    def test_metadata_stored(self):
        """Test that metadata is stored correctly."""
        metadata = StrategyMetadata(
            name='MetadataTestStrategy',
            threshold_required=True,
            min_data_days=90,
            description='Detailed description'
        )
        registry = Registry()
        registry.register('MetadataTestStrategy', metadata)

        stored = registry.get_metadata('MetadataTestStrategy')
        assert stored is not None
        assert stored.name == 'MetadataTestStrategy'
        assert stored.threshold_required == True
        assert stored.min_data_days == 90
        assert stored.description == 'Detailed description'