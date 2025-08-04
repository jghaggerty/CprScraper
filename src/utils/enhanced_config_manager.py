"""
Enhanced Configuration Manager

This module provides advanced configuration management capabilities for monitoring
all 50 states plus federal agencies, including coverage validation, performance
optimization, and comprehensive reporting.
"""

import os
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .config_loader import load_agency_config, get_all_forms, get_monitoring_settings

logger = logging.getLogger(__name__)


class CoverageStatus(Enum):
    """Enumeration for coverage status."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    ERROR = "error"


@dataclass
class CoverageMetrics:
    """Data class for coverage metrics."""
    total_states: int
    total_federal_agencies: int
    total_forms: int
    active_states: int
    active_federal_agencies: int
    active_forms: int
    coverage_percentage: float
    last_updated: datetime
    status: CoverageStatus


class EnhancedConfigManager:
    """
    Enhanced configuration manager for comprehensive monitoring coverage.
    
    Features:
    - Complete 50-state plus federal agency coverage validation
    - Performance optimization for large-scale monitoring
    - Coverage metrics and reporting
    - Configuration health monitoring
    - Batch processing optimization
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the enhanced configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = None
        self.coverage_metrics = None
        self._load_config()
        
        # Performance tracking
        self.performance_stats = {
            "config_load_time_ms": 0,
            "validation_time_ms": 0,
            "last_health_check": None,
            "health_status": "unknown"
        }
    
    def _load_config(self) -> None:
        """Load and validate the configuration."""
        start_time = datetime.utcnow()
        
        try:
            self.config = load_agency_config(self.config_path)
            self._validate_comprehensive_coverage()
            self._calculate_coverage_metrics()
            
            load_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.performance_stats["config_load_time_ms"] = load_time
            
            logger.info(f"Enhanced configuration loaded successfully in {load_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Failed to load enhanced configuration: {e}")
            self.config = None
            self.coverage_metrics = None
            raise
    
    def _validate_comprehensive_coverage(self) -> None:
        """
        Validate that the configuration covers all 50 states plus federal agencies.
        
        Raises:
            ValueError: If coverage is incomplete
        """
        if not self.config:
            raise ValueError("Configuration not loaded")
        
        # Check federal agencies
        federal_agencies = self.config.get('federal', {})
        if not federal_agencies:
            raise ValueError("No federal agencies configured")
        
        # Check state agencies
        state_agencies = self.config.get('states', {})
        if len(state_agencies) != 50:
            raise ValueError(f"Expected 50 states, found {len(state_agencies)}")
        
        # Validate all required states are present
        required_states = {
            'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
            'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
            'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
            'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
            'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
            'new_hampshire', 'new_jersey', 'new_mexico', 'new_york',
            'north_carolina', 'north_dakota', 'ohio', 'oklahoma', 'oregon',
            'pennsylvania', 'rhode_island', 'south_carolina', 'south_dakota',
            'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
            'west_virginia', 'wisconsin', 'wyoming'
        }
        
        configured_states = set(state_agencies.keys())
        missing_states = required_states - configured_states
        extra_states = configured_states - required_states
        
        if missing_states:
            raise ValueError(f"Missing states: {missing_states}")
        
        if extra_states:
            logger.warning(f"Extra states found: {extra_states}")
        
        # Validate each state has required fields
        for state_key, state_data in state_agencies.items():
            required_fields = ['name', 'abbreviation', 'base_url', 'forms']
            for field in required_fields:
                if field not in state_data:
                    raise ValueError(f"State {state_key} missing required field: {field}")
            
            # Validate forms
            forms = state_data.get('forms', [])
            if not forms:
                raise ValueError(f"State {state_key} has no forms configured")
            
            for form in forms:
                if 'name' not in form:
                    raise ValueError(f"State {state_key} has form without name")
    
    def _calculate_coverage_metrics(self) -> None:
        """Calculate comprehensive coverage metrics."""
        if not self.config:
            return
        
        federal_agencies = self.config.get('federal', {})
        state_agencies = self.config.get('states', {})
        
        # Count forms
        total_forms = 0
        active_forms = 0
        
        # Federal forms
        for agency_data in federal_agencies.values():
            forms = agency_data.get('forms', [])
            total_forms += len(forms)
            active_forms += len(forms)  # Assume all federal forms are active
        
        # State forms
        for state_data in state_agencies.values():
            forms = state_data.get('forms', [])
            total_forms += len(forms)
            active_forms += len(forms)  # Assume all state forms are active
        
        # Calculate coverage percentage
        expected_total = 52  # 50 states + 2 federal agencies
        actual_total = len(federal_agencies) + len(state_agencies)
        coverage_percentage = (actual_total / expected_total) * 100
        
        # Determine status
        if coverage_percentage >= 100:
            status = CoverageStatus.COMPLETE
        elif coverage_percentage >= 80:
            status = CoverageStatus.PARTIAL
        else:
            status = CoverageStatus.INCOMPLETE
        
        self.coverage_metrics = CoverageMetrics(
            total_states=len(state_agencies),
            total_federal_agencies=len(federal_agencies),
            total_forms=total_forms,
            active_states=len(state_agencies),
            active_federal_agencies=len(federal_agencies),
            active_forms=active_forms,
            coverage_percentage=coverage_percentage,
            last_updated=datetime.utcnow(),
            status=status
        )
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get comprehensive coverage report.
        
        Returns:
            Dictionary containing coverage report
        """
        if not self.coverage_metrics:
            return {"error": "Coverage metrics not available"}
        
        return {
            "coverage_summary": {
                "total_states": self.coverage_metrics.total_states,
                "total_federal_agencies": self.coverage_metrics.total_federal_agencies,
                "total_forms": self.coverage_metrics.total_forms,
                "coverage_percentage": self.coverage_metrics.coverage_percentage,
                "status": self.coverage_metrics.status.value,
                "last_updated": self.coverage_metrics.last_updated.isoformat()
            },
            "performance_stats": self.performance_stats,
            "monitoring_settings": get_monitoring_settings(self.config),
            "health_status": self.performance_stats["health_status"]
        }
    
    def get_optimized_monitoring_batches(self, 
                                       max_concurrent_agencies: int = 10,
                                       max_concurrent_forms: int = 25) -> List[Dict[str, Any]]:
        """
        Get optimized monitoring batches for large-scale processing.
        
        Args:
            max_concurrent_agencies: Maximum agencies to monitor concurrently
            max_concurrent_forms: Maximum forms to monitor concurrently
            
        Returns:
            List of monitoring batches
        """
        if not self.config:
            return []
        
        all_forms = get_all_forms(self.config)
        
        # Group forms by frequency for optimal scheduling
        frequency_groups = {
            "daily": [],
            "weekly": [],
            "monthly": []
        }
        
        for form in all_forms:
            frequency = form.get('check_frequency', 'weekly')
            if frequency in frequency_groups:
                frequency_groups[frequency].append(form)
            else:
                frequency_groups["weekly"].append(form)
        
        # Create optimized batches
        batches = []
        
        # Daily forms (high priority, smaller batches)
        daily_forms = frequency_groups["daily"]
        for i in range(0, len(daily_forms), max_concurrent_forms // 2):
            batch = daily_forms[i:i + max_concurrent_forms // 2]
            batches.append({
                "batch_id": f"daily_{len(batches) + 1}",
                "frequency": "daily",
                "priority": "high",
                "forms": batch,
                "estimated_duration_minutes": len(batch) * 2  # 2 minutes per form
            })
        
        # Weekly forms (medium priority, standard batches)
        weekly_forms = frequency_groups["weekly"]
        for i in range(0, len(weekly_forms), max_concurrent_forms):
            batch = weekly_forms[i:i + max_concurrent_forms]
            batches.append({
                "batch_id": f"weekly_{len(batches) + 1}",
                "frequency": "weekly",
                "priority": "medium",
                "forms": batch,
                "estimated_duration_minutes": len(batch) * 1.5  # 1.5 minutes per form
            })
        
        # Monthly forms (low priority, larger batches)
        monthly_forms = frequency_groups["monthly"]
        for i in range(0, len(monthly_forms), max_concurrent_forms * 2):
            batch = monthly_forms[i:i + max_concurrent_forms * 2]
            batches.append({
                "batch_id": f"monthly_{len(batches) + 1}",
                "frequency": "monthly",
                "priority": "low",
                "forms": batch,
                "estimated_duration_minutes": len(batch) * 1  # 1 minute per form
            })
        
        return batches
    
    def get_state_coverage_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed coverage status for each state.
        
        Returns:
            Dictionary mapping state abbreviations to coverage details
        """
        if not self.config:
            return {}
        
        state_agencies = self.config.get('states', {})
        coverage_status = {}
        
        for state_key, state_data in state_agencies.items():
            abbreviation = state_data.get('abbreviation', state_key.upper())
            forms = state_data.get('forms', [])
            
            coverage_status[abbreviation] = {
                "state_name": state_data.get('name'),
                "state_key": state_key,
                "forms_count": len(forms),
                "forms": [form.get('name') for form in forms],
                "check_frequencies": list(set(form.get('check_frequency', 'weekly') for form in forms)),
                "base_url": state_data.get('base_url'),
                "contact": state_data.get('contact', {}),
                "status": "active" if forms else "inactive"
            }
        
        return coverage_status
    
    def get_federal_coverage_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed coverage status for federal agencies.
        
        Returns:
            Dictionary mapping agency keys to coverage details
        """
        if not self.config:
            return {}
        
        federal_agencies = self.config.get('federal', {})
        coverage_status = {}
        
        for agency_key, agency_data in federal_agencies.items():
            forms = agency_data.get('forms', [])
            
            coverage_status[agency_key] = {
                "agency_name": agency_data.get('name'),
                "agency_key": agency_key,
                "forms_count": len(forms),
                "forms": [form.get('name') for form in forms],
                "check_frequencies": list(set(form.get('check_frequency', 'weekly') for form in forms)),
                "base_url": agency_data.get('base_url'),
                "contact": agency_data.get('contact', {}),
                "status": "active" if forms else "inactive"
            }
        
        return coverage_status
    
    def validate_configuration_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive configuration health check.
        
        Returns:
            Dictionary containing health check results
        """
        start_time = datetime.utcnow()
        health_status = {
            "overall_status": "unknown",
            "checks": {},
            "recommendations": [],
            "last_check": datetime.utcnow().isoformat()
        }
        
        try:
            # Check configuration loading
            if self.config:
                health_status["checks"]["config_loaded"] = True
            else:
                health_status["checks"]["config_loaded"] = False
                health_status["recommendations"].append("Configuration failed to load")
            
            # Check coverage metrics
            if self.coverage_metrics:
                health_status["checks"]["coverage_calculated"] = True
                health_status["checks"]["coverage_percentage"] = self.coverage_metrics.coverage_percentage
                
                if self.coverage_metrics.coverage_percentage < 100:
                    health_status["recommendations"].append(
                        f"Coverage is {self.coverage_metrics.coverage_percentage:.1f}% - consider adding missing agencies"
                    )
            else:
                health_status["checks"]["coverage_calculated"] = False
                health_status["recommendations"].append("Coverage metrics not available")
            
            # Check performance
            if self.performance_stats["config_load_time_ms"] > 5000:
                health_status["recommendations"].append("Configuration load time is slow")
            
            # Check for common issues
            if self.config:
                # Check for missing URLs
                missing_urls = []
                for state_key, state_data in self.config.get('states', {}).items():
                    if not state_data.get('base_url'):
                        missing_urls.append(f"State {state_key}")
                
                if missing_urls:
                    health_status["checks"]["urls_complete"] = False
                    health_status["recommendations"].append(f"Missing URLs for: {', '.join(missing_urls[:5])}")
                else:
                    health_status["checks"]["urls_complete"] = True
            
            # Determine overall status
            if all(health_status["checks"].values()):
                health_status["overall_status"] = "healthy"
            elif any(health_status["checks"].values()):
                health_status["overall_status"] = "degraded"
            else:
                health_status["overall_status"] = "unhealthy"
            
            # Update performance stats
            validation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.performance_stats["validation_time_ms"] = validation_time
            self.performance_stats["last_health_check"] = datetime.utcnow()
            self.performance_stats["health_status"] = health_status["overall_status"]
            
        except Exception as e:
            health_status["overall_status"] = "error"
            health_status["checks"]["error"] = str(e)
            health_status["recommendations"].append(f"Health check failed: {e}")
        
        return health_status
    
    def get_monitoring_recommendations(self) -> List[str]:
        """
        Get recommendations for optimizing monitoring performance.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not self.coverage_metrics:
            recommendations.append("Coverage metrics not available - check configuration")
            return recommendations
        
        # Performance recommendations
        if self.performance_stats["config_load_time_ms"] > 3000:
            recommendations.append("Consider optimizing configuration file size")
        
        # Coverage recommendations
        if self.coverage_metrics.coverage_percentage < 100:
            recommendations.append(f"Coverage is {self.coverage_metrics.coverage_percentage:.1f}% - add missing agencies")
        
        # Batch processing recommendations
        total_forms = self.coverage_metrics.total_forms
        if total_forms > 100:
            recommendations.append("Consider implementing batch processing for large form sets")
        
        if total_forms > 50:
            recommendations.append("Monitor system resources during peak processing times")
        
        # Frequency recommendations
        recommendations.append("Review check frequencies based on agency update patterns")
        recommendations.append("Consider implementing adaptive frequency adjustment")
        
        return recommendations


def get_enhanced_config_manager(config_path: Optional[str] = None) -> EnhancedConfigManager:
    """
    Get enhanced configuration manager instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        EnhancedConfigManager instance
    """
    return EnhancedConfigManager(config_path)


def validate_complete_coverage(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate complete coverage of all 50 states plus federal agencies.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Validation results
    """
    try:
        manager = EnhancedConfigManager(config_path)
        return {
            "valid": True,
            "coverage_report": manager.get_coverage_report(),
            "health_status": manager.validate_configuration_health(),
            "recommendations": manager.get_monitoring_recommendations()
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "recommendations": ["Fix configuration errors", "Check file permissions"]
        }


if __name__ == "__main__":
    # Test the enhanced configuration manager
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test with complete configuration
        manager = EnhancedConfigManager("config/agencies_complete.yaml")
        
        print("✅ Enhanced configuration manager initialized successfully!")
        
        # Print coverage report
        coverage_report = manager.get_coverage_report()
        print(f"\n📊 Coverage Report:")
        print(f"  Total States: {coverage_report['coverage_summary']['total_states']}")
        print(f"  Total Federal Agencies: {coverage_report['coverage_summary']['total_federal_agencies']}")
        print(f"  Total Forms: {coverage_report['coverage_summary']['total_forms']}")
        print(f"  Coverage: {coverage_report['coverage_summary']['coverage_percentage']:.1f}%")
        print(f"  Status: {coverage_report['coverage_summary']['status']}")
        
        # Print health status
        health_status = manager.validate_configuration_health()
        print(f"\n🏥 Health Status: {health_status['overall_status']}")
        
        # Print recommendations
        recommendations = manager.get_monitoring_recommendations()
        print(f"\n💡 Recommendations:")
        for rec in recommendations:
            print(f"  - {rec}")
        
        # Print optimized batches
        batches = manager.get_optimized_monitoring_batches()
        print(f"\n📦 Monitoring Batches: {len(batches)}")
        for batch in batches[:3]:  # Show first 3 batches
            print(f"  - {batch['batch_id']}: {len(batch['forms'])} forms ({batch['frequency']})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1) 