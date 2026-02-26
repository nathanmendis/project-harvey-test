from typing import Dict, Type, Any
from .base import HRMSAdapter
from .adapters.harvey_adapter import HarveyHRMSAdapter

class HRMSAdapterRegistry:
    """Registry for managing and resolving all HRMS adapters dynamically"""
    
    _adapters: Dict[str, Type[HRMSAdapter]] = {
        'harvey': HarveyHRMSAdapter,
        # Add new adapters here seamlessly: 
        # 'workday': WorkdayAdapter,
        # 'bamboohr': BambooHRAdapter,
    }
    
    @classmethod
    def get_adapter(cls, hrms_type: str, config: Dict[str, Any]) -> HRMSAdapter:
        """Get an initialized adapter instance for the given HRMS type"""
        adapter_class = cls._adapters.get(hrms_type.lower())
        if not adapter_class:
            raise ValueError(f"Unknown or unsupported HRMS type: {hrms_type}")
        return adapter_class(config)
    
    @classmethod
    def register_adapter(cls, hrms_type: str, adapter_class: Type[HRMSAdapter]):
        """Register a new adapter dynamically at runtime"""
        cls._adapters[hrms_type.lower()] = adapter_class
