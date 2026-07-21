"""
Email notification module for Development Tracking System.
Supports SMTP-based notifications for stage assignments, overdue stages, and project updates.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from configparser import ConfigParser
from datetime import date

logger = logging.getLogger(__name__)


class EmailConfig:
    """Load email settings from config.ini"""

    def __init__(self, config_path='config.ini'):
        self.config = ConfigParser()
        self.config.read(config_path)
        self.enabled = self.config.getboolean('EMAIL', 'ENABLED', fallback=False)
        self.smtp_server = self.config.get('EMAIL', 'SMTP_SERVER', fallback='smtp.gmail.com')
        self.smtp_port = self.config.getint('EMAIL', 'SMTP_PORT', fallback=587)
        self.username = self.config.get('EMAIL', 'SMTP_USERNAME', fallback='')
        self.password = self.config.get('EMAIL', 'SMTP_PASSWORD', fallback='').replace(' ', '')
        self.from_name = self.config.get('EMAIL', 'FROM_NAME', fallback='Development Tracking System')
        self.from_email = self.config.get('EMAIL', 'FROM_EMAIL', fallback=self.username)
        self.use_tls = self.config.getboolean('EMAIL', 'USE_TLS', fallback=True)


def is_email_enabled(config_path='config.ini'):
    """Quick check if email is enabled."""
    config = ConfigParser()
    config.read(config_path)
    return config.getboolean('EMAIL', 'ENABLED', fallback=False)


def send_email(to_email, subject, html_body, text_body=None, config_path='config.ini'):
    """Send a single email using SMTP settings from config.ini."""
    email_config = EmailConfig(config_path)

    if not email_config.enabled:
        logger.debug("Email notifications disabled; skipping send to %s", to_email)
        return False

    if not to_email:
        logger.warning("No recipient email provided; skipping send.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{email_config.from_name} <{email_config.from_email}>"
    msg['To'] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        if email_config.use_tls:
            server = smtplib.SMTP(email_config.smtp_server, email_config.smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(email_config.smtp_server, email_config.smtp_port, timeout=30)

        if email_config.username and email_config.password:
            server.login(email_config.username, email_config.password)

        server.sendmail(email_config.from_email, [to_email], msg.as_string())
        server.quit()
        logger.info("Email sent to %s | subject=%s", to_email, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def send_stage_assignment_email(user_email, user_name, stage_name, project_name, due_date=None, config_path='config.ini'):
    """Notify user when they are assigned to a stage."""
    subject = f"Stage Assigned: {stage_name}"
    html = f"""
    <html>
      <body style='font-family: Arial, sans-serif; color: #333;'>
        <h2 style='color: #2c3e50;'>Stage Assignment</h2>
        <p>Hi {user_name},</p>
        <p>You have been assigned to the following stage:</p>
        <ul>
          <li><strong>Project:</strong> {project_name}</li>
          <li><strong>Stage:</strong> {stage_name}</li>
          {f"<li><strong>Due Date:</strong> {due_date.strftime('%d %b %Y')}</li>" if due_date else ''}
        </ul>
        <p>Please log in to the Development Tracking System to view details.</p>
        <p style='color: #888; font-size: 0.9em;'>This is an automated notification.</p>
      </body>
    </html>
    """
    text = (
        f"Hi {user_name},\n\n"
        f"You have been assigned to stage '{stage_name}' in project '{project_name}'.\n"
        + (f"Due date: {due_date.strftime('%d %b %Y')}\n" if due_date else '')
        + "\nPlease log in to the Development Tracking System for details.\n"
    )
    return send_email(user_email, subject, html, text, config_path)


def send_stage_completion_email(user_email, user_name, stage_name, project_name, config_path='config.ini'):
    """Notify relevant users when a stage is completed."""
    subject = f"Stage Completed: {stage_name}"
    html = f"""
    <html>
      <body style='font-family: Arial, sans-serif; color: #333;'>
        <h2 style='color: #27ae60;'>Stage Completed</h2>
        <p>Hi {user_name},</p>
        <p>The following stage has been marked as completed:</p>
        <ul>
          <li><strong>Project:</strong> {project_name}</li>
          <li><strong>Stage:</strong> {stage_name}</li>
        </ul>
        <p>Please review the project progress in the Development Tracking System.</p>
        <p style='color: #888; font-size: 0.9em;'>This is an automated notification.</p>
      </body>
    </html>
    """
    text = (
        f"Hi {user_name},\n\n"
        f"Stage '{stage_name}' in project '{project_name}' has been completed.\n"
        "\nPlease review the project progress in the Development Tracking System.\n"
    )
    return send_email(user_email, subject, html, text, config_path)


def send_overdue_stage_email(user_email, user_name, stage_name, project_name, expected_end_date, config_path='config.ini'):
    """Notify user about an overdue stage."""
    subject = f"Overdue Stage Alert: {stage_name}"
    html = f"""
    <html>
      <body style='font-family: Arial, sans-serif; color: #333;'>
        <h2 style='color: #e74c3c;'>Overdue Stage Alert</h2>
        <p>Hi {user_name},</p>
        <p>The following stage is overdue:</p>
        <ul>
          <li><strong>Project:</strong> {project_name}</li>
          <li><strong>Stage:</strong> {stage_name}</li>
          <li><strong>Expected End Date:</strong> {expected_end_date.strftime('%d %b %Y')}</li>
        </ul>
        <p>Please take necessary action to complete this stage.</p>
        <p style='color: #888; font-size: 0.9em;'>This is an automated notification.</p>
      </body>
    </html>
    """
    text = (
        f"Hi {user_name},\n\n"
        f"Stage '{stage_name}' in project '{project_name}' is overdue.\n"
        f"Expected end date: {expected_end_date.strftime('%d %b %Y')}\n"
        "\nPlease take necessary action to complete this stage.\n"
    )
    return send_email(user_email, subject, html, text, config_path)


def send_project_created_email(user_email, user_name, project_name, config_path='config.ini'):
    """Notify project head when a new project is created."""
    subject = f"New Project Created: {project_name}"
    html = f"""
    <html>
      <body style='font-family: Arial, sans-serif; color: #333;'>
        <h2 style='color: #3498db;'>New Project Created</h2>
        <p>Hi {user_name},</p>
        <p>A new project has been created and you have been assigned as the project head:</p>
        <ul>
          <li><strong>Project:</strong> {project_name}</li>
        </ul>
        <p>Please log in to the Development Tracking System to view and manage the project.</p>
        <p style='color: #888; font-size: 0.9em;'>This is an automated notification.</p>
      </body>
    </html>
    """
    text = (
        f"Hi {user_name},\n\n"
        f"A new project '{project_name}' has been created and you have been assigned as the project head.\n"
        "\nPlease log in to the Development Tracking System to view and manage the project.\n"
    )
    return send_email(user_email, subject, html, text, config_path)
