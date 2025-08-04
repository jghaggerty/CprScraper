import os
import yaml
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Required environment variables for the application
REQUIRED_ENV_VARS = [
    'SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD',
    'FROM_EMAIL', 'ALERT_EMAIL_1'
]

# Optional environment variables with defaults
OPTIONAL_ENV_VARS = {
    'DATABASE_URL': 'sqlite:///./data/payroll_monitor.db',
    'DB_POOL_SIZE': '10',
    'DB_MAX_OVERFLOW': '20',
    'DB_POOL_TIMEOUT': '30',
    'DB_POOL_RECYCLE': '3600',
    'DB_ECHO': 'false',
    'LOG_LEVEL': 'INFO',
    'MONITORING_TIMEOUT': '30',
    'RETRY_ATTEMPTS': '3'
}


def validate_environment_variables() -> None:
    """
    Validate required environment variables are set.
    
    Raises:
        ValueError: If required environment variables are missing
    """
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")


def get_config_path(config_path: Optional[str] = None) -> Path:
    """
    Get the configuration file path.
    
    Args:
        config_path: Optional custom path to configuration file
        
    Returns:
        Path to the configuration file
    """
    if config_path is None:
        # Default to config/agencies.yaml relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "agencies.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    return config_path


def load_agency_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load agency configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file. If None, uses default.
        
    Returns:
        Dictionary containing agency configuration data.
        
    Raises:
        FileNotFoundError: If configuration file is not found
        ValueError: If YAML is invalid or required fields are missing
    """
    try:
        config_file = get_config_path(config_path)
        
        with open(config_file, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        if not config:
            raise ValueError("Configuration file is empty")
        
        # Expand environment variables in configuration
        config = expand_environment_variables(config)
        
        # Validate configuration structure
        errors = validate_config(config)
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        logger.info(f"Configuration loaded successfully from {config_file}")
        return config
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration file: {e}")
        raise ValueError(f"Invalid YAML in configuration file: {e}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


def get_federal_agencies(config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get federal agencies from configuration.
    
    Args:
        config: Configuration dictionary (optional)
        
    Returns:
        Dictionary of federal agencies
    """
    if config is None:
        config = load_agency_config()
    return config.get('federal', {})


def get_state_agencies(config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get state agencies from configuration.
    
    Args:
        config: Configuration dictionary (optional)
        
    Returns:
        Dictionary of state agencies
    """
    if config is None:
        config = load_agency_config()
    return config.get('states', {})


def get_agency_by_name(agency_name: str, config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
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


def get_monitoring_settings(config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get monitoring configuration settings.
    
    Args:
        config: Configuration dictionary (optional)
        
    Returns:
        Monitoring settings dictionary
    """
    if config is None:
        config = load_agency_config()
    
    default_settings = {
        'default_check_frequency': 'weekly',
        'retry_attempts': int(os.getenv('RETRY_ATTEMPTS', '3')),
        'timeout_seconds': int(os.getenv('MONITORING_TIMEOUT', '30')),
        'user_agent': 'PayrollMonitor/1.0 (Government Forms Monitoring)',
        'notification_delay_minutes': 5,
        'backup_frequency': 'daily'
    }
    
    config_settings = config.get('monitoring_settings', {})
    return {**default_settings, **config_settings}


def get_notification_settings(config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get notification configuration settings.
    
    Args:
        config: Configuration dictionary (optional)
        
    Returns:
        Notification settings dictionary
    """
    if config is None:
        config = load_agency_config()
    
    default_settings = {
        'email': {
            'enabled': True,
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': 587,
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_address': os.getenv('FROM_EMAIL'),
            'to_addresses': [os.getenv('ALERT_EMAIL_1')]
        },
        'slack': {
            'enabled': False,
            'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
            'channel': '#payroll-alerts'
        },
        'teams': {
            'enabled': False,
            'webhook_url': os.getenv('TEAMS_WEBHOOK_URL')
        }
    }
    
    config_settings = config.get('notification_settings', {})
    return {**default_settings, **config_settings}


def get_all_forms(config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Get all forms from all agencies.
    
    Args:
        config: Configuration dictionary (optional)
        
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


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration for required fields and structure.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
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
        
        # Validate forms if present
        forms = agency_data.get('forms', [])
        if not isinstance(forms, list):
            errors.append(f"Federal agency '{agency_key}' forms must be a list")
        else:
            for i, form in enumerate(forms):
                if not isinstance(form, dict):
                    errors.append(f"Federal agency '{agency_key}' form {i} must be a dictionary")
                elif 'name' not in form:
                    errors.append(f"Federal agency '{agency_key}' form {i} missing required field: name")
    
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
        
        # Validate forms if present
        forms = state_data.get('forms', [])
        if not isinstance(forms, list):
            errors.append(f"State agency '{state_key}' forms must be a list")
        else:
            for i, form in enumerate(forms):
                if not isinstance(form, dict):
                    errors.append(f"State agency '{state_key}' form {i} must be a dictionary")
                elif 'name' not in form:
                    errors.append(f"State agency '{state_key}' form {i} missing required field: name")
    
    return errors


def expand_environment_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand environment variables in configuration values.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with environment variables expanded
    """
    def expand_value(value: Any) -> Any:
        if isinstance(value, str):
            return os.path.expandvars(value)
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        else:
            return value
    
    return expand_value(config)


def get_environment_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.
    
    Returns:
        Dictionary of environment-based configuration
    """
    config = {}
    
    # Add required environment variables
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if value:
            config[var] = value
    
    # Add optional environment variables with defaults
    for var, default in OPTIONAL_ENV_VARS.items():
        config[var] = os.getenv(var, default)
    
    return config


if __name__ == "__main__":
    # Test the configuration loader
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Validate environment variables
        validate_environment_variables()
        print("✅ Environment variables validation passed")
        
        # Load and validate configuration
        config = load_agency_config()
        print("✅ Configuration loaded successfully!")
        
        # Print summary
        federal = get_federal_agencies(config)
        states = get_state_agencies(config)
        all_forms = get_all_forms(config)
        
        print(f"\n📊 Configuration Summary:")
        print(f"  Federal agencies: {len(federal)}")
        print(f"  State agencies: {len(states)}")
        print(f"  Total forms: {len(all_forms)}")
        
        # Test monitoring settings
        monitoring_settings = get_monitoring_settings(config)
        print(f"  Default check frequency: {monitoring_settings['default_check_frequency']}")
        print(f"  Retry attempts: {monitoring_settings['retry_attempts']}")
        print(f"  Timeout seconds: {monitoring_settings['timeout_seconds']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)