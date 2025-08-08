#!/usr/bin/env python3
"""
Test script for preference manager fixes
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_preference_manager():
    """Test the preference manager fixes."""
    try:
        from tests.test_enhanced_notification_system import TestEnhancedNotificationPreferenceManagerComprehensive
        from unittest.mock import Mock, patch
        from sqlalchemy.orm import Session
        from src.database.models import User, UserNotificationPreference
        
        # Create test instance
        test_instance = TestEnhancedNotificationPreferenceManagerComprehensive()
        preference_manager = test_instance.preference_manager()
        
        # Test initialize_user_preferences
        with patch('src.notifications.preference_manager.get_db_session') as mock_get_db, \
             patch.object(preference_manager, 'user_service') as mock_user_service:
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_get_db.return_value.__exit__.return_value = None
            
            # Mock user service
            mock_user_service.get_user_roles.return_value = ['product_manager']
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Test preference initialization
            result = preference_manager.initialize_user_preferences(1, ['product_manager'])
            
            print(f"✅ initialize_user_preferences test passed: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_preference_manager()
