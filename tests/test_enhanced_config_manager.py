"""
Unit tests for Enhanced Configuration Manager

Tests comprehensive configuration management capabilities for monitoring
all 50 states plus federal agencies.
"""

import pytest
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.utils.enhanced_config_manager import (
    EnhancedConfigManager, 
    CoverageStatus, 
    CoverageMetrics,
    get_enhanced_config_manager,
    validate_complete_coverage
)


class TestCoverageStatus:
    """Test CoverageStatus enum."""
    
    def test_coverage_status_values(self):
        """Test that CoverageStatus enum has expected values."""
        assert CoverageStatus.COMPLETE.value == "complete"
        assert CoverageStatus.PARTIAL.value == "partial"
        assert CoverageStatus.INCOMPLETE.value == "incomplete"
        assert CoverageStatus.ERROR.value == "error"


class TestCoverageMetrics:
    """Test CoverageMetrics dataclass."""
    
    def test_coverage_metrics_creation(self):
        """Test creating CoverageMetrics instance."""
        metrics = CoverageMetrics(
            total_states=50,
            total_federal_agencies=2,
            total_forms=52,
            active_states=50,
            active_federal_agencies=2,
            active_forms=52,
            coverage_percentage=100.0,
            last_updated=datetime.utcnow(),
            status=CoverageStatus.COMPLETE
        )
        
        assert metrics.total_states == 50
        assert metrics.total_federal_agencies == 2
        assert metrics.total_forms == 52
        assert metrics.coverage_percentage == 100.0
        assert metrics.status == CoverageStatus.COMPLETE


class TestEnhancedConfigManager:
    """Test EnhancedConfigManager class."""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration with all 50 states."""
        config = {
            "federal": {
                "department_of_labor": {
                    "name": "U.S. Department of Labor",
                    "base_url": "https://www.dol.gov",
                    "forms": [
                        {
                            "name": "WH-347",
                            "title": "Statement of Compliance",
                            "url": "https://www.dol.gov/agencies/whd/government-contracts/construction",
                            "check_frequency": "daily"
                        }
                    ],
                    "contact": {
                        "phone": "1-866-487-9243",
                        "email": "WHDInfo@dol.gov"
                    }
                },
                "general_services_administration": {
                    "name": "U.S. General Services Administration",
                    "base_url": "https://www.gsa.gov",
                    "forms": [
                        {
                            "name": "GSA-347",
                            "title": "GSA Certified Payroll Report",
                            "url": "https://www.gsa.gov/reference/forms/gsa-347",
                            "check_frequency": "weekly"
                        }
                    ],
                    "contact": {
                        "phone": "1-844-472-7645",
                        "email": "gsa.forms@gsa.gov"
                    }
                }
            },
            "states": {},
            "monitoring_settings": {
                "default_check_frequency": "weekly",
                "retry_attempts": 3,
                "timeout_seconds": 30
            },
            "notification_settings": {
                "email": {
                    "enabled": True,
                    "smtp_server": "smtp.example.com"
                }
            }
        }
        
        # Add all 50 states
        required_states = [
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
        ]
        
        state_abbreviations = {
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN',
            'mississippi': 'MS', 'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE',
            'nevada': 'NV', 'new_hampshire': 'NH', 'new_jersey': 'NJ',
            'new_mexico': 'NM', 'new_york': 'NY', 'north_carolina': 'NC',
            'north_dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK', 'oregon': 'OR',
            'pennsylvania': 'PA', 'rhode_island': 'RI', 'south_carolina': 'SC',
            'south_dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA',
            'west_virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY'
        }
        
        for state in required_states:
            config["states"][state] = {
                "name": f"{state.title()} Department of Labor",
                "abbreviation": state_abbreviations[state],
                "base_url": f"https://www.{state}.gov",
                "forms": [
                    {
                        "name": f"{state_abbreviations[state]}-PW-001",
                        "title": f"{state.title()} Certified Payroll Report",
                        "url": f"https://www.{state}.gov/prevailing-wage",
                        "check_frequency": "weekly"
                    }
                ],
                "contact": {
                    "phone": "(555) 123-4567",
                    "email": f"prevailingwage@{state}.gov"
                }
            }
        
        return config
    
    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            return f.name
    
    def test_enhanced_config_manager_initialization(self, temp_config_file):
        """Test EnhancedConfigManager initialization with valid config."""
        manager = EnhancedConfigManager(temp_config_file)
        
        assert manager.config is not None
        assert manager.coverage_metrics is not None
        assert manager.coverage_metrics.total_states == 50
        assert manager.coverage_metrics.total_federal_agencies == 2
        assert manager.coverage_metrics.coverage_percentage == 100.0
        assert manager.coverage_metrics.status == CoverageStatus.COMPLETE
    
    def test_enhanced_config_manager_missing_states(self):
        """Test EnhancedConfigManager with missing states."""
        incomplete_config = {
            "federal": {
                "department_of_labor": {
                    "name": "U.S. Department of Labor",
                    "base_url": "https://www.dol.gov",
                    "forms": [{"name": "WH-347"}],
                    "contact": {"phone": "123", "email": "test@test.com"}
                }
            },
            "states": {
                "california": {
                    "name": "California Department of Labor",
                    "abbreviation": "CA",
                    "base_url": "https://www.ca.gov",
                    "forms": [{"name": "CA-PW-001"}],
                    "contact": {"phone": "123", "email": "test@ca.gov"}
                }
            },
            "monitoring_settings": {},
            "notification_settings": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_config, f)
            config_path = f.name
        
        with pytest.raises(ValueError, match="Expected 50 states, found 1"):
            EnhancedConfigManager(config_path)
    
    def test_enhanced_config_manager_missing_federal(self):
        """Test EnhancedConfigManager with missing federal agencies."""
        incomplete_config = {
            "federal": {},
            "states": {},
            "monitoring_settings": {},
            "notification_settings": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_config, f)
            config_path = f.name
        
        with pytest.raises(ValueError, match="No federal agencies configured"):
            EnhancedConfigManager(config_path)
    
    def test_get_coverage_report(self, temp_config_file):
        """Test getting coverage report."""
        manager = EnhancedConfigManager(temp_config_file)
        report = manager.get_coverage_report()
        
        assert "coverage_summary" in report
        assert report["coverage_summary"]["total_states"] == 50
        assert report["coverage_summary"]["total_federal_agencies"] == 2
        assert report["coverage_summary"]["coverage_percentage"] == 100.0
        assert report["coverage_summary"]["status"] == "complete"
        assert "performance_stats" in report
        assert "monitoring_settings" in report
    
    def test_get_optimized_monitoring_batches(self, temp_config_file):
        """Test getting optimized monitoring batches."""
        manager = EnhancedConfigManager(temp_config_file)
        batches = manager.get_optimized_monitoring_batches()
        
        assert len(batches) > 0
        
        # Check batch structure
        for batch in batches:
            assert "batch_id" in batch
            assert "frequency" in batch
            assert "priority" in batch
            assert "forms" in batch
            assert "estimated_duration_minutes" in batch
            assert isinstance(batch["forms"], list)
    
    def test_get_state_coverage_status(self, temp_config_file):
        """Test getting state coverage status."""
        manager = EnhancedConfigManager(temp_config_file)
        state_status = manager.get_state_coverage_status()
        
        assert len(state_status) == 50
        
        # Check a specific state
        ca_status = state_status.get("CA")
        assert ca_status is not None
        assert ca_status["state_name"] == "California Department of Labor"
        assert ca_status["state_key"] == "california"
        assert ca_status["forms_count"] == 1
        assert "CA-PW-001" in ca_status["forms"]
        assert ca_status["status"] == "active"
    
    def test_get_federal_coverage_status(self, temp_config_file):
        """Test getting federal coverage status."""
        manager = EnhancedConfigManager(temp_config_file)
        federal_status = manager.get_federal_coverage_status()
        
        assert len(federal_status) == 2
        
        # Check DOL
        dol_status = federal_status.get("department_of_labor")
        assert dol_status is not None
        assert dol_status["agency_name"] == "U.S. Department of Labor"
        assert dol_status["forms_count"] == 1
        assert "WH-347" in dol_status["forms"]
        assert dol_status["status"] == "active"
    
    def test_validate_configuration_health(self, temp_config_file):
        """Test configuration health validation."""
        manager = EnhancedConfigManager(temp_config_file)
        health = manager.validate_configuration_health()
        
        assert "overall_status" in health
        assert "checks" in health
        assert "recommendations" in health
        assert "last_check" in health
        
        # Should be healthy with complete configuration
        assert health["overall_status"] == "healthy"
        assert health["checks"]["config_loaded"] is True
        assert health["checks"]["coverage_calculated"] is True
    
    def test_get_monitoring_recommendations(self, temp_config_file):
        """Test getting monitoring recommendations."""
        manager = EnhancedConfigManager(temp_config_file)
        recommendations = manager.get_monitoring_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should have some recommendations even with complete config
        assert any("frequency" in rec.lower() for rec in recommendations)
    
    def test_enhanced_config_manager_performance_tracking(self, temp_config_file):
        """Test performance tracking functionality."""
        manager = EnhancedConfigManager(temp_config_file)
        
        # Check initial performance stats
        assert "config_load_time_ms" in manager.performance_stats
        assert manager.performance_stats["config_load_time_ms"] > 0
        
        # Run health check to update validation time
        manager.validate_configuration_health()
        assert "validation_time_ms" in manager.performance_stats
        assert manager.performance_stats["validation_time_ms"] > 0


class TestEnhancedConfigManagerFunctions:
    """Test standalone functions."""
    
    def test_get_enhanced_config_manager(self):
        """Test get_enhanced_config_manager function."""
        with patch('src.utils.enhanced_config_manager.EnhancedConfigManager') as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            
            result = get_enhanced_config_manager("test_config.yaml")
            
            assert result == mock_instance
            mock_manager.assert_called_once_with("test_config.yaml")
    
    def test_validate_complete_coverage_success(self):
        """Test validate_complete_coverage with valid configuration."""
        with patch('src.utils.enhanced_config_manager.EnhancedConfigManager') as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            
            # Mock coverage report
            mock_instance.get_coverage_report.return_value = {
                "coverage_summary": {
                    "total_states": 50,
                    "total_federal_agencies": 2,
                    "coverage_percentage": 100.0
                }
            }
            
            # Mock health status
            mock_instance.validate_configuration_health.return_value = {
                "overall_status": "healthy"
            }
            
            # Mock recommendations
            mock_instance.get_monitoring_recommendations.return_value = [
                "Review check frequencies"
            ]
            
            result = validate_complete_coverage("test_config.yaml")
            
            assert result["valid"] is True
            assert "coverage_report" in result
            assert "health_status" in result
            assert "recommendations" in result
    
    def test_validate_complete_coverage_failure(self):
        """Test validate_complete_coverage with invalid configuration."""
        with patch('src.utils.enhanced_config_manager.EnhancedConfigManager') as mock_manager:
            mock_manager.side_effect = ValueError("Configuration error")
            
            result = validate_complete_coverage("test_config.yaml")
            
            assert result["valid"] is False
            assert "error" in result
            assert "recommendations" in result


class TestEnhancedConfigManagerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_enhanced_config_manager_empty_config(self):
        """Test EnhancedConfigManager with empty configuration."""
        empty_config = {
            "federal": {},
            "states": {},
            "monitoring_settings": {},
            "notification_settings": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(empty_config, f)
            config_path = f.name
        
        with pytest.raises(ValueError):
            EnhancedConfigManager(config_path)
    
    def test_enhanced_config_manager_missing_required_fields(self):
        """Test EnhancedConfigManager with missing required fields."""
        invalid_config = {
            "federal": {
                "department_of_labor": {
                    "name": "U.S. Department of Labor"
                    # Missing base_url and forms
                }
            },
            "states": {},
            "monitoring_settings": {},
            "notification_settings": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            config_path = f.name
        
        with pytest.raises(ValueError, match="missing required field"):
            EnhancedConfigManager(config_path)
    
    def test_enhanced_config_manager_extra_states(self):
        """Test EnhancedConfigManager with extra states (should warn but not fail)."""
        # Create config with 51 states (50 required + 1 extra)
        config = {
            "federal": {
                "department_of_labor": {
                    "name": "U.S. Department of Labor",
                    "base_url": "https://www.dol.gov",
                    "forms": [{"name": "WH-347"}],
                    "contact": {"phone": "123", "email": "test@test.com"}
                }
            },
            "states": {},
            "monitoring_settings": {},
            "notification_settings": {}
        }
        
        # Add all 50 required states
        required_states = [
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
        ]
        
        for state in required_states:
            config["states"][state] = {
                "name": f"{state.title()} Department of Labor",
                "abbreviation": state.upper()[:2],
                "base_url": f"https://www.{state}.gov",
                "forms": [{"name": f"{state.upper()[:2]}-PW-001"}],
                "contact": {"phone": "123", "email": f"test@{state}.gov"}
            }
        
        # Add one extra state
        config["states"]["puerto_rico"] = {
            "name": "Puerto Rico Department of Labor",
            "abbreviation": "PR",
            "base_url": "https://www.pr.gov",
            "forms": [{"name": "PR-PW-001"}],
            "contact": {"phone": "123", "email": "test@pr.gov"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        # Should not raise an exception, but should log a warning
        with patch('src.utils.enhanced_config_manager.logger') as mock_logger:
            manager = EnhancedConfigManager(config_path)
            
            # Should still have 100% coverage (51 states + 1 federal = 52 total)
            assert manager.coverage_metrics.coverage_percentage == 100.0
            assert manager.coverage_metrics.status == CoverageStatus.COMPLETE


if __name__ == "__main__":
    pytest.main([__file__]) 