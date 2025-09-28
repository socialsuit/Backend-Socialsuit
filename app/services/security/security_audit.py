"""
Security Audit Module for Social Suit Application

This module provides comprehensive security auditing capabilities for:
- Token handling and JWT security
- Database query security and SQL injection prevention
- Scheduler task security
- API endpoint security
- Configuration security
"""

import re
import os
import ast
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import secrets
from dataclasses import dataclass
from enum import Enum

# Security audit result levels
class SecurityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class SecurityFinding:
    """Represents a security audit finding."""
    level: SecurityLevel
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None
    code_snippet: Optional[str] = None

class SecurityAuditor:
    """Main security auditor class."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []
        self.logger = logging.getLogger(__name__)
        
        # Security patterns to detect
        self.sql_injection_patterns = [
            r'f".*{.*}.*".*execute',  # f-string in SQL
            r'".*\+.*".*execute',     # String concatenation in SQL
            r'%.*%.*execute',         # String formatting in SQL
            r'\.format\(.*\).*execute',  # .format() in SQL
        ]
        
        self.jwt_security_patterns = [
            r'jwt\.decode\([^,]*,\s*verify=False',  # JWT decode without verification
            r'jwt\.decode\([^,]*,\s*options={"verify_signature":\s*False}',
            r'SECRET_KEY\s*=\s*["\'][^"\']*["\']',  # Hardcoded secrets
            r'JWT_SECRET\s*=\s*["\'][^"\']*["\']',
        ]
        
        self.dangerous_imports = [
            'eval', 'exec', 'compile', '__import__',
            'subprocess.call', 'os.system', 'os.popen'
        ]
        
        self.sensitive_data_patterns = [
            r'password\s*=\s*["\'][^"\']*["\']',
            r'api_key\s*=\s*["\'][^"\']*["\']',
            r'secret\s*=\s*["\'][^"\']*["\']',
            r'token\s*=\s*["\'][^"\']*["\']',
        ]

    def audit_all(self) -> List[SecurityFinding]:
        """Run complete security audit."""
        self.findings = []
        
        self.logger.info("Starting comprehensive security audit...")
        
        # Audit different components
        self.audit_jwt_security()
        self.audit_database_security()
        self.audit_scheduler_security()
        self.audit_api_endpoints()
        self.audit_configuration_security()
        self.audit_file_permissions()
        self.audit_dependencies()
        self.audit_input_validation()
        self.audit_error_handling()
        self.audit_logging_security()
        
        self.logger.info(f"Security audit completed. Found {len(self.findings)} findings.")
        return self.findings

    def audit_jwt_security(self):
        """Audit JWT token handling security."""
        self.logger.info("Auditing JWT security...")
        
        jwt_files = [
            'services/auth/jwt_handler.py',
            'services/auth/auth_guard.py'
        ]
        
        for file_path in jwt_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self._audit_file_for_jwt_issues(full_path)
        
        # Check for JWT configuration issues
        self._check_jwt_configuration()

    def _audit_file_for_jwt_issues(self, file_path: Path):
        """Audit a specific file for JWT security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for insecure JWT patterns
            for i, line in enumerate(lines, 1):
                for pattern in self.jwt_security_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.CRITICAL,
                            category="JWT Security",
                            title="Insecure JWT Configuration",
                            description=f"Potentially insecure JWT handling detected",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            recommendation="Enable JWT signature verification and use secure secret keys"
                        ))
            
            # Check for hardcoded secrets
            self._check_hardcoded_secrets(file_path, content)
            
            # Check JWT algorithm security
            if 'algorithm=' in content:
                if '"none"' in content.lower() or "'none'" in content.lower():
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.CRITICAL,
                        category="JWT Security",
                        title="Insecure JWT Algorithm",
                        description="JWT 'none' algorithm detected - allows unsigned tokens",
                        file_path=str(file_path),
                        recommendation="Use secure algorithms like HS256, RS256, or ES256"
                    ))
            
        except Exception as e:
            self.logger.error(f"Error auditing JWT file {file_path}: {e}")

    def _check_jwt_configuration(self):
        """Check JWT configuration security."""
        config_file = self.project_root / 'core' / 'config.py'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for JWT secret configuration
                if 'JWT_SECRET' not in content and 'jwt_secret' not in content:
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.HIGH,
                        category="JWT Security",
                        title="Missing JWT Secret Configuration",
                        description="No JWT secret configuration found",
                        file_path=str(config_file),
                        recommendation="Configure JWT_SECRET in environment variables"
                    ))
                
                # Check for weak JWT expiration
                if 'JWT_EXPIRATION' in content or 'jwt_expiration' in content:
                    # Look for very long expiration times
                    expiration_patterns = [
                        r'(\d+)\s*\*\s*24\s*\*\s*3600',  # days in seconds
                        r'timedelta\(days=(\d+)\)',       # timedelta days
                    ]
                    for pattern in expiration_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            days = int(match)
                            if days > 30:  # More than 30 days
                                self.findings.append(SecurityFinding(
                                    level=SecurityLevel.MEDIUM,
                                    category="JWT Security",
                                    title="Long JWT Expiration Time",
                                    description=f"JWT expiration set to {days} days",
                                    file_path=str(config_file),
                                    recommendation="Use shorter JWT expiration times (1-7 days) for better security"
                                ))
                
            except Exception as e:
                self.logger.error(f"Error checking JWT configuration: {e}")

    def audit_database_security(self):
        """Audit database query security."""
        self.logger.info("Auditing database security...")
        
        # Find all Python files that might contain database queries
        db_files = []
        for pattern in ['**/*repository*.py', '**/database/*.py', '**/models/*.py']:
            db_files.extend(self.project_root.glob(pattern))
        
        for file_path in db_files:
            self._audit_file_for_sql_injection(file_path)
            self._audit_file_for_nosql_injection(file_path)
        
        # Check database configuration
        self._check_database_configuration()

    def _audit_file_for_sql_injection(self, file_path: Path):
        """Audit file for SQL injection vulnerabilities."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check for dangerous SQL patterns
                for pattern in self.sql_injection_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.HIGH,
                            category="Database Security",
                            title="Potential SQL Injection",
                            description="Unsafe SQL query construction detected",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            recommendation="Use parameterized queries or ORM methods"
                        ))
                
                # Check for raw SQL execution
                if re.search(r'execute\s*\([^)]*["\'][^"\']*["\'][^)]*\)', line, re.IGNORECASE):
                    if not re.search(r'execute\s*\([^)]*%s', line):  # Not parameterized
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.MEDIUM,
                            category="Database Security",
                            title="Raw SQL Execution",
                            description="Raw SQL execution without parameterization",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            recommendation="Use parameterized queries"
                        ))
        
        except Exception as e:
            self.logger.error(f"Error auditing SQL injection in {file_path}: {e}")

    def _audit_file_for_nosql_injection(self, file_path: Path):
        """Audit file for NoSQL injection vulnerabilities."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check for MongoDB injection patterns
                nosql_patterns = [
                    r'\$where.*eval',
                    r'\$where.*function',
                    r'find\([^)]*\+[^)]*\)',  # String concatenation in find
                    r'aggregate\([^)]*\+[^)]*\)',  # String concatenation in aggregate
                ]
                
                for pattern in nosql_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.HIGH,
                            category="Database Security",
                            title="Potential NoSQL Injection",
                            description="Unsafe NoSQL query construction detected",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            recommendation="Use proper query builders and avoid string concatenation"
                        ))
        
        except Exception as e:
            self.logger.error(f"Error auditing NoSQL injection in {file_path}: {e}")

    def _check_database_configuration(self):
        """Check database configuration security."""
        config_file = self.project_root / 'core' / 'config.py'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for hardcoded database credentials
                db_patterns = [
                    r'DATABASE_URL\s*=\s*["\'][^"\']*://[^:]*:[^@]*@',
                    r'MONGODB_URL\s*=\s*["\'][^"\']*://[^:]*:[^@]*@',
                    r'REDIS_URL\s*=\s*["\'][^"\']*://[^:]*:[^@]*@',
                ]
                
                for pattern in db_patterns:
                    if re.search(pattern, content):
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.CRITICAL,
                            category="Database Security",
                            title="Hardcoded Database Credentials",
                            description="Database credentials found in source code",
                            file_path=str(config_file),
                            recommendation="Use environment variables for database credentials"
                        ))
                
                # Check for SSL/TLS configuration
                if 'sslmode=disable' in content or 'ssl=false' in content.lower():
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.MEDIUM,
                        category="Database Security",
                        title="Disabled Database SSL",
                        description="Database SSL/TLS appears to be disabled",
                        file_path=str(config_file),
                        recommendation="Enable SSL/TLS for database connections"
                    ))
            
            except Exception as e:
                self.logger.error(f"Error checking database configuration: {e}")

    def audit_scheduler_security(self):
        """Audit scheduler task security."""
        self.logger.info("Auditing scheduler security...")
        
        scheduler_files = list(self.project_root.glob('**/scheduler*.py'))
        scheduler_files.extend(self.project_root.glob('**/tasks/*.py'))
        
        for file_path in scheduler_files:
            self._audit_scheduler_file(file_path)

    def _audit_scheduler_file(self, file_path: Path):
        """Audit scheduler file for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for dangerous operations in scheduler
            dangerous_patterns = [
                r'os\.system\(',
                r'subprocess\.call\(',
                r'eval\(',
                r'exec\(',
                r'__import__\(',
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern in dangerous_patterns:
                    if re.search(pattern, line):
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.HIGH,
                            category="Scheduler Security",
                            title="Dangerous Operation in Scheduler",
                            description="Potentially dangerous operation in scheduled task",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip(),
                            recommendation="Avoid system calls and code execution in scheduled tasks"
                        ))
            
            # Check for unvalidated input processing
            if 'request' in content and 'validate' not in content:
                self.findings.append(SecurityFinding(
                    level=SecurityLevel.MEDIUM,
                    category="Scheduler Security",
                    title="Unvalidated Input in Scheduler",
                    description="Scheduler processes input without validation",
                    file_path=str(file_path),
                    recommendation="Validate all input data in scheduled tasks"
                ))
        
        except Exception as e:
            self.logger.error(f"Error auditing scheduler file {file_path}: {e}")

    def audit_api_endpoints(self):
        """Audit API endpoint security."""
        self.logger.info("Auditing API endpoint security...")
        
        endpoint_files = list(self.project_root.glob('**/endpoint/*.py'))
        endpoint_files.extend(self.project_root.glob('**/*api*.py'))
        
        for file_path in endpoint_files:
            self._audit_endpoint_file(file_path)

    def _audit_endpoint_file(self, file_path: Path):
        """Audit endpoint file for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for missing authentication
            has_auth_decorator = any(
                re.search(r'@auth_required|@admin_required|@optional_auth', line)
                for line in lines
            )
            
            has_endpoints = any(
                re.search(r'@app\.|@router\.|@.*\.(get|post|put|delete)', line)
                for line in lines
            )
            
            if has_endpoints and not has_auth_decorator:
                self.findings.append(SecurityFinding(
                    level=SecurityLevel.MEDIUM,
                    category="API Security",
                    title="Missing Authentication",
                    description="API endpoints without authentication decorators",
                    file_path=str(file_path),
                    recommendation="Add appropriate authentication decorators to endpoints"
                ))
            
            # Check for missing input validation
            for i, line in enumerate(lines, 1):
                if re.search(r'@.*\.(post|put|patch)', line):
                    # Look for Pydantic models in the next few lines
                    next_lines = lines[i:i+5] if i < len(lines) - 5 else lines[i:]
                    has_validation = any(
                        re.search(r':\s*\w+Request|:\s*\w+Model|:\s*BaseModel', next_line)
                        for next_line in next_lines
                    )
                    
                    if not has_validation:
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.MEDIUM,
                            category="API Security",
                            title="Missing Input Validation",
                            description="POST/PUT endpoint without Pydantic validation",
                            file_path=str(file_path),
                            line_number=i,
                            recommendation="Use Pydantic models for input validation"
                        ))
        
        except Exception as e:
            self.logger.error(f"Error auditing endpoint file {file_path}: {e}")

    def audit_configuration_security(self):
        """Audit configuration security."""
        self.logger.info("Auditing configuration security...")
        
        config_files = [
            'core/config.py',
            '.env',
            '.env.example',
            'config.py',
            'settings.py'
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                self._audit_config_file(file_path)

    def _audit_config_file(self, file_path: Path):
        """Audit configuration file for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for hardcoded secrets
            self._check_hardcoded_secrets(file_path, content)
            
            # Check for debug mode in production
            if re.search(r'DEBUG\s*=\s*True', content, re.IGNORECASE):
                self.findings.append(SecurityFinding(
                    level=SecurityLevel.HIGH,
                    category="Configuration Security",
                    title="Debug Mode Enabled",
                    description="Debug mode appears to be enabled",
                    file_path=str(file_path),
                    recommendation="Disable debug mode in production"
                ))
            
            # Check for insecure CORS settings
            cors_patterns = [
                r'allow_origins\s*=\s*\[\s*["\*"\']\s*\]',
                r'CORS_ALLOW_ALL_ORIGINS\s*=\s*True',
            ]
            
            for pattern in cors_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.MEDIUM,
                        category="Configuration Security",
                        title="Insecure CORS Configuration",
                        description="CORS configured to allow all origins",
                        file_path=str(file_path),
                        recommendation="Restrict CORS to specific trusted origins"
                    ))
        
        except Exception as e:
            self.logger.error(f"Error auditing config file {file_path}: {e}")

    def _check_hardcoded_secrets(self, file_path: Path, content: str):
        """Check for hardcoded secrets in file content."""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.sensitive_data_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's clearly using environment variables
                    if 'os.environ' in line or 'getenv' in line:
                        continue
                    
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.CRITICAL,
                        category="Configuration Security",
                        title="Hardcoded Sensitive Data",
                        description="Sensitive data found in source code",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Use environment variables for sensitive data"
                    ))

    def audit_file_permissions(self):
        """Audit file permissions for security issues."""
        self.logger.info("Auditing file permissions...")
        
        # Check for overly permissive files
        sensitive_files = [
            '.env',
            'config.py',
            'core/config.py',
            'private_key.pem',
            'id_rsa',
        ]
        
        for file_name in sensitive_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                try:
                    stat_info = file_path.stat()
                    permissions = oct(stat_info.st_mode)[-3:]
                    
                    # Check if file is world-readable or world-writable
                    if permissions[-1] in ['4', '5', '6', '7']:  # World-readable
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.MEDIUM,
                            category="File Security",
                            title="World-Readable Sensitive File",
                            description=f"Sensitive file {file_name} is world-readable",
                            file_path=str(file_path),
                            recommendation="Restrict file permissions (chmod 600)"
                        ))
                    
                    if permissions[-1] in ['2', '3', '6', '7']:  # World-writable
                        self.findings.append(SecurityFinding(
                            level=SecurityLevel.HIGH,
                            category="File Security",
                            title="World-Writable Sensitive File",
                            description=f"Sensitive file {file_name} is world-writable",
                            file_path=str(file_path),
                            recommendation="Restrict file permissions (chmod 600)"
                        ))
                
                except Exception as e:
                    self.logger.error(f"Error checking permissions for {file_path}: {e}")

    def audit_dependencies(self):
        """Audit dependencies for known vulnerabilities."""
        self.logger.info("Auditing dependencies...")
        
        requirements_files = [
            'requirements.txt',
            'requirements-dev.txt',
            'Pipfile',
            'pyproject.toml'
        ]
        
        for req_file in requirements_files:
            file_path = self.project_root / req_file
            if file_path.exists():
                self._audit_requirements_file(file_path)

    def _audit_requirements_file(self, file_path: Path):
        """Audit requirements file for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for unpinned versions
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Check if version is pinned
                    if '==' not in line and '>=' not in line and '~=' not in line:
                        if not line.startswith('-'):  # Skip pip options
                            self.findings.append(SecurityFinding(
                                level=SecurityLevel.LOW,
                                category="Dependency Security",
                                title="Unpinned Dependency Version",
                                description=f"Dependency {line} has no version constraint",
                                file_path=str(file_path),
                                line_number=i,
                                recommendation="Pin dependency versions for reproducible builds"
                            ))
            
            # Check for known vulnerable packages (basic check)
            vulnerable_packages = [
                'django<3.2.13',  # Example - update based on current vulnerabilities
                'flask<2.0.0',
                'requests<2.20.0',
            ]
            
            for vuln_pkg in vulnerable_packages:
                if vuln_pkg.split('<')[0] in content:
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.HIGH,
                        category="Dependency Security",
                        title="Potentially Vulnerable Dependency",
                        description=f"Package {vuln_pkg.split('<')[0]} may be vulnerable",
                        file_path=str(file_path),
                        recommendation="Update to latest secure version"
                    ))
        
        except Exception as e:
            self.logger.error(f"Error auditing requirements file {file_path}: {e}")

    def audit_input_validation(self):
        """Audit input validation across the application."""
        self.logger.info("Auditing input validation...")
        
        # This is partially covered by endpoint auditing, but we can add more specific checks
        python_files = list(self.project_root.glob('**/*.py'))
        
        for file_path in python_files:
            if 'test' in str(file_path) or '__pycache__' in str(file_path):
                continue
            
            self._audit_input_validation_in_file(file_path)

    def _audit_input_validation_in_file(self, file_path: Path):
        """Audit input validation in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for direct use of request data without validation
            dangerous_patterns = [
                r'request\.json\[',
                r'request\.form\[',
                r'request\.args\[',
                r'request\.values\[',
            ]
            
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                for pattern in dangerous_patterns:
                    if re.search(pattern, line):
                        # Check if there's validation nearby
                        context_lines = lines[max(0, i-3):i+3]
                        has_validation = any(
                            'validate' in context_line.lower() or
                            'pydantic' in context_line.lower() or
                            'schema' in context_line.lower()
                            for context_line in context_lines
                        )
                        
                        if not has_validation:
                            self.findings.append(SecurityFinding(
                                level=SecurityLevel.MEDIUM,
                                category="Input Validation",
                                title="Unvalidated Request Data",
                                description="Direct access to request data without validation",
                                file_path=str(file_path),
                                line_number=i,
                                code_snippet=line.strip(),
                                recommendation="Validate all input data using Pydantic or similar"
                            ))
        
        except Exception as e:
            self.logger.error(f"Error auditing input validation in {file_path}: {e}")

    def audit_error_handling(self):
        """Audit error handling for information disclosure."""
        self.logger.info("Auditing error handling...")
        
        python_files = list(self.project_root.glob('**/*.py'))
        
        for file_path in python_files:
            if 'test' in str(file_path) or '__pycache__' in str(file_path):
                continue
            
            self._audit_error_handling_in_file(file_path)

    def _audit_error_handling_in_file(self, file_path: Path):
        """Audit error handling in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Check for bare except clauses
            for i, line in enumerate(lines, 1):
                if re.search(r'except\s*:', line):
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.LOW,
                        category="Error Handling",
                        title="Bare Except Clause",
                        description="Bare except clause may hide errors",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Catch specific exceptions instead of using bare except"
                    ))
                
                # Check for error messages that might leak information
                if 'raise' in line and any(word in line.lower() for word in ['password', 'secret', 'key', 'token']):
                    self.findings.append(SecurityFinding(
                        level=SecurityLevel.MEDIUM,
                        category="Error Handling",
                        title="Sensitive Information in Error",
                        description="Error message may contain sensitive information",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Avoid including sensitive data in error messages"
                    ))
        
        except Exception as e:
            self.logger.error(f"Error auditing error handling in {file_path}: {e}")

    def audit_logging_security(self):
        """Audit logging for security issues."""
        self.logger.info("Auditing logging security...")
        
        python_files = list(self.project_root.glob('**/*.py'))
        
        for file_path in python_files:
            if 'test' in str(file_path) or '__pycache__' in str(file_path):
                continue
            
            self._audit_logging_in_file(file_path)

    def _audit_logging_in_file(self, file_path: Path):
        """Audit logging in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Check for logging of sensitive information
            for i, line in enumerate(lines, 1):
                if re.search(r'log\w*\.|logger\.|print\(', line, re.IGNORECASE):
                    # Check if sensitive data might be logged
                    sensitive_keywords = ['password', 'secret', 'key', 'token', 'credential']
                    for keyword in sensitive_keywords:
                        if keyword in line.lower():
                            self.findings.append(SecurityFinding(
                                level=SecurityLevel.MEDIUM,
                                category="Logging Security",
                                title="Sensitive Data in Logs",
                                description="Potentially sensitive data being logged",
                                file_path=str(file_path),
                                line_number=i,
                                code_snippet=line.strip(),
                                recommendation="Avoid logging sensitive information"
                            ))
        
        except Exception as e:
            self.logger.error(f"Error auditing logging in {file_path}: {e}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security audit report."""
        if not self.findings:
            self.audit_all()
        
        # Group findings by severity
        findings_by_level = {}
        for level in SecurityLevel:
            findings_by_level[level.value] = [
                f for f in self.findings if f.level == level
            ]
        
        # Group findings by category
        findings_by_category = {}
        for finding in self.findings:
            if finding.category not in findings_by_category:
                findings_by_category[finding.category] = []
            findings_by_category[finding.category].append(finding)
        
        # Calculate security score (0-100)
        total_findings = len(self.findings)
        critical_count = len(findings_by_level[SecurityLevel.CRITICAL.value])
        high_count = len(findings_by_level[SecurityLevel.HIGH.value])
        medium_count = len(findings_by_level[SecurityLevel.MEDIUM.value])
        
        # Weighted scoring
        security_score = max(0, 100 - (
            critical_count * 25 +
            high_count * 10 +
            medium_count * 5
        ))
        
        return {
            'audit_timestamp': datetime.utcnow().isoformat(),
            'security_score': security_score,
            'total_findings': total_findings,
            'findings_by_level': {
                level: len(findings) for level, findings in findings_by_level.items()
            },
            'findings_by_category': {
                category: len(findings) for category, findings in findings_by_category.items()
            },
            'critical_findings': [
                {
                    'title': f.title,
                    'description': f.description,
                    'file_path': f.file_path,
                    'line_number': f.line_number,
                    'recommendation': f.recommendation
                }
                for f in findings_by_level[SecurityLevel.CRITICAL.value]
            ],
            'recommendations': self._generate_recommendations(),
            'all_findings': [
                {
                    'level': f.level.value,
                    'category': f.category,
                    'title': f.title,
                    'description': f.description,
                    'file_path': f.file_path,
                    'line_number': f.line_number,
                    'recommendation': f.recommendation,
                    'code_snippet': f.code_snippet
                }
                for f in self.findings
            ]
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate high-level security recommendations."""
        recommendations = []
        
        # Count findings by category
        category_counts = {}
        for finding in self.findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        
        # Generate recommendations based on findings
        if category_counts.get('JWT Security', 0) > 0:
            recommendations.append(
                "Implement secure JWT handling with proper signature verification and short expiration times"
            )
        
        if category_counts.get('Database Security', 0) > 0:
            recommendations.append(
                "Use parameterized queries and enable database SSL/TLS connections"
            )
        
        if category_counts.get('API Security', 0) > 0:
            recommendations.append(
                "Add authentication and input validation to all API endpoints"
            )
        
        if category_counts.get('Configuration Security', 0) > 0:
            recommendations.append(
                "Move all sensitive configuration to environment variables and disable debug mode"
            )
        
        if category_counts.get('Input Validation', 0) > 0:
            recommendations.append(
                "Implement comprehensive input validation using Pydantic models"
            )
        
        # Add general recommendations
        recommendations.extend([
            "Implement rate limiting to prevent abuse",
            "Set up security monitoring and alerting",
            "Regular security audits and dependency updates",
            "Implement proper error handling without information disclosure"
        ])
        
        return recommendations

def run_security_audit(project_root: str) -> Dict[str, Any]:
    """Run a complete security audit and return the report."""
    auditor = SecurityAuditor(project_root)
    return auditor.generate_report()

if __name__ == "__main__":
    import sys
    
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    report = run_security_audit(project_root)
    
    print(f"Security Audit Report")
    print(f"====================")
    print(f"Security Score: {report['security_score']}/100")
    print(f"Total Findings: {report['total_findings']}")
    print(f"Critical: {report['findings_by_level']['critical']}")
    print(f"High: {report['findings_by_level']['high']}")
    print(f"Medium: {report['findings_by_level']['medium']}")
    print(f"Low: {report['findings_by_level']['low']}")
    
    if report['critical_findings']:
        print(f"\nCritical Findings:")
        for finding in report['critical_findings']:
            print(f"- {finding['title']}: {finding['description']}")