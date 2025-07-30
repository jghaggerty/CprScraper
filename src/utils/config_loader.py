import os
import yaml
from typing import Dict, List, Optional
from pathlib import Path

def load_agency_config(config_path: str = None) -> Dict:
    """
    Load agency configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file. If None, uses default.
        
    Returns:
        Dictionary containing agency configuration data.
    """
    if config_path is None:
        # Default to config/agencies.yaml relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "agencies.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {e}")


def get_federal_agencies(config: Dict = None) -> Dict:
    """Get federal agencies from configuration."""
    if config is None:
        config = load_agency_config()
    return config.get('federal', {})


def get_state_agencies(config: Dict = None) -> Dict:
    """Get state agencies from configuration."""
    if config is None:
        config = load_agency_config()
    return config.get('states', {})


def get_agency_by_name(agency_name: str, config: Dict = None) -> Optional[Dict]:
    """
    Get specific agency configuration by name.
    
    Args:
        agency_name: Name or abbreviation of the agency
        config: Configuration dictionary (optional)
        
    Returns:
        Agency configuration or None if not found
    """
    if config is None:
        config = load_agency_config()
    
    # Check federal agencies
    federal = get_federal_agencies(config)
    for agency_key, agency_data in federal.items():
        if (agency_key.lower() == agency_name.lower() or 
            agency_data.get('name', '').lower() == agency_name.lower()):
            return agency_data
    
    # Check state agencies
    states = get_state_agencies(config)
    for state_key, state_data in states.items():
        if (state_key.lower() == agency_name.lower() or
            state_data.get('name', '').lower() == agency_name.lower() or
            state_data.get('abbreviation', '').lower() == agency_name.lower()):
            return state_data
    
    return None


def get_monitoring_settings(config: Dict = None) -> Dict:
    """Get monitoring configuration settings."""
    if config is None:
        config = load_agency_config()
    return config.get('monitoring_settings', {})


def get_notification_settings(config: Dict = None) -> Dict:
    """Get notification configuration settings."""
    if config is None:
        config = load_agency_config()
    return config.get('notification_settings', {})


def get_all_forms(config: Dict = None) -> List[Dict]:
    """
    Get all forms from all agencies.
    
    Returns:
        List of form dictionaries with agency context
    """
    if config is None:
        config = load_agency_config()
    
    all_forms = []
    
    # Process federal agencies
    federal = get_federal_agencies(config)
    for agency_key, agency_data in federal.items():
        forms = agency_data.get('forms', [])
        for form in forms:
            form_data = form.copy()
            form_data['agency_key'] = agency_key
            form_data['agency_name'] = agency_data.get('name')
            form_data['agency_type'] = 'federal'
            form_data['agency_contact'] = agency_data.get('contact', {})
            all_forms.append(form_data)
    
    # Process state agencies
    states = get_state_agencies(config)
    for state_key, state_data in states.items():
        forms = state_data.get('forms', [])
        for form in forms:
            form_data = form.copy()
            form_data['agency_key'] = state_key
            form_data['agency_name'] = state_data.get('name')
            form_data['agency_type'] = 'state'
            form_data['agency_abbreviation'] = state_data.get('abbreviation')
            form_data['agency_contact'] = state_data.get('contact', {})
            all_forms.append(form_data)
    
    return all_forms


def validate_config(config: Dict = None) -> List[str]:
    """
    Validate configuration for required fields and structure.
    
    Returns:
        List of validation errors (empty if valid)
    """
    if config is None:
        config = load_agency_config()
    
    errors = []
    
    # Check required top-level keys
    required_keys = ['federal', 'states', 'monitoring_settings', 'notification_settings']
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required top-level key: {key}")
    
    # Validate federal agencies
    federal = config.get('federal', {})
    for agency_key, agency_data in federal.items():
        if not isinstance(agency_data, dict):
            errors.append(f"Federal agency '{agency_key}' must be a dictionary")
            continue
            
        required_agency_fields = ['name', 'base_url']
        for field in required_agency_fields:
            if field not in agency_data:
                errors.append(f"Federal agency '{agency_key}' missing required field: {field}")
    
    # Validate state agencies
    states = config.get('states', {})
    for state_key, state_data in states.items():
        if not isinstance(state_data, dict):
            errors.append(f"State agency '{state_key}' must be a dictionary")
            continue
            
        required_state_fields = ['name', 'abbreviation', 'base_url']
        for field in required_state_fields:
            if field not in state_data:
                errors.append(f"State agency '{state_key}' missing required field: {field}")
    
    return errors


def expand_environment_variables(config: Dict) -> Dict:
    """
    Expand environment variables in configuration values.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with environment variables expanded
    """
    def expand_value(value):
        if isinstance(value, str):
            return os.path.expandvars(value)
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        else:
            return value
    
    return expand_value(config)


if __name__ == "__main__":
    # Test the configuration loader
    try:
        config = load_agency_config()
        print("Configuration loaded successfully!")
        
        # Validate configuration
        errors = validate_config(config)
        if errors:
            print("Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Configuration is valid!")
        
        # Print summary
        federal = get_federal_agencies(config)
        states = get_state_agencies(config)
        all_forms = get_all_forms(config)
        
        print(f"\nSummary:")
        print(f"  Federal agencies: {len(federal)}")
        print(f"  State agencies: {len(states)}")
        print(f"  Total forms: {len(all_forms)}")
        
    except Exception as e:
        print(f"Error loading configuration: {e}")