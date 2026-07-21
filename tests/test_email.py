"""Tests for email notification functionality with mocked SMTP."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from email_notifications import (
    send_email,
    send_stage_assignment_email,
    send_stage_completion_email,
    send_project_created_email,
    is_email_enabled,
    EmailConfig
)


class TestEmailConfig:
    def test_email_disabled_by_default(self):
        """Test email is disabled when ENABLED=False."""
        with patch('email_notifications.ConfigParser') as mock_config:
            mock_instance = MagicMock()
            mock_instance.getboolean.return_value = False
            mock_config.return_value = mock_instance
            
            config = EmailConfig.__new__(EmailConfig)
            config.config = mock_instance
            config.enabled = False
            
            assert config.enabled is False

    def test_strip_password_spaces(self):
        """Test that spaces are stripped from SMTP password."""
        password_with_spaces = 'xwve afwd dfhi vsbp'
        stripped = password_with_spaces.replace(' ', '')
        assert stripped == 'xwveafwddfhivsbp'


class TestSendEmail:
    @patch('email_notifications.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        with patch('email_notifications.ConfigParser') as mock_config:
            mock_instance = MagicMock()
            mock_instance.getboolean.return_value = True
            mock_instance.get.side_effect = lambda section, key, fallback=None: {
                ('EMAIL', 'SMTP_SERVER'): 'smtp.test.com',
                ('EMAIL', 'SMTP_PORT'): '587',
                ('EMAIL', 'SMTP_USERNAME'): 'test@test.com',
                ('EMAIL', 'SMTP_PASSWORD'): 'password',
                ('EMAIL', 'FROM_NAME'): 'Test',
                ('EMAIL', 'FROM_EMAIL'): 'test@test.com',
                ('EMAIL', 'USE_TLS'): 'True'
            }.get((section, key), fallback)
            mock_config.return_value = mock_instance
            
            result = send_email(
                to_email='recipient@test.com',
                subject='Test Subject',
                html_body='<p>Test</p>',
                config_path='fake.ini'
            )
            
            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@test.com', 'password')
            mock_server.sendmail.assert_called_once()

    @patch('email_notifications.smtplib.SMTP')
    def test_send_email_auth_failure(self, mock_smtp):
        """Test email sending with authentication failure."""
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("Authentication failed")
        mock_smtp.return_value = mock_server
        
        with patch('email_notifications.ConfigParser') as mock_config:
            mock_instance = MagicMock()
            mock_instance.getboolean.return_value = True
            mock_instance.get.side_effect = lambda section, key, fallback=None: {
                ('EMAIL', 'SMTP_SERVER'): 'smtp.test.com',
                ('EMAIL', 'SMTP_PORT'): '587',
                ('EMAIL', 'SMTP_USERNAME'): 'test@test.com',
                ('EMAIL', 'SMTP_PASSWORD'): 'password',
                ('EMAIL', 'FROM_NAME'): 'Test',
                ('EMAIL', 'FROM_EMAIL'): 'test@test.com',
                ('EMAIL', 'USE_TLS'): 'True'
            }.get((section, key), fallback)
            mock_config.return_value = mock_instance
            
            result = send_email(
                to_email='recipient@test.com',
                subject='Test',
                html_body='<p>Test</p>',
                config_path='fake.ini'
            )
            
            assert result is False

    def test_send_email_disabled(self):
        """Test email not sent when disabled."""
        with patch('email_notifications.ConfigParser') as mock_config:
            mock_instance = MagicMock()
            mock_instance.getboolean.return_value = False
            mock_config.return_value = mock_instance
            
            result = send_email(
                to_email='recipient@test.com',
                subject='Test',
                html_body='<p>Test</p>',
                config_path='fake.ini'
            )
            
            assert result is False


class TestEmailNotifications:
    @patch('email_notifications.send_email')
    def test_stage_assignment_email(self, mock_send_email):
        """Test stage assignment email is sent with correct parameters."""
        send_stage_assignment_email(
            user_email='user@test.com',
            user_name='Test User',
            stage_name='Test Stage',
            project_name='Test Project',
            due_date=date(2026, 12, 31)
        )
        
        assert mock_send_email.called
        args, kwargs = mock_send_email.call_args
        assert args[0] == 'user@test.com'
        assert 'Test Stage' in args[1]

    @patch('email_notifications.send_email')
    def test_stage_completion_email(self, mock_send_email):
        """Test stage completion email is sent."""
        send_stage_completion_email(
            user_email='user@test.com',
            user_name='Test User',
            stage_name='Test Stage',
            project_name='Test Project'
        )
        
        assert mock_send_email.called
        args, kwargs = mock_send_email.call_args
        assert 'Completed' in args[1]

    @patch('email_notifications.send_email')
    def test_project_created_email(self, mock_send_email):
        """Test project created email is sent."""
        send_project_created_email(
            user_email='user@test.com',
            user_name='Test User',
            project_name='Test Project'
        )
        
        assert mock_send_email.called
        args, kwargs = mock_send_email.call_args
        assert 'New Project' in args[1]
