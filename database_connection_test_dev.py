#!/usr/bin/env python3
"""
Development Database Connection Test

This script tests database connections for development environment:
- SQLite (instead of PostgreSQL for local development)
- Mock MongoDB connection
- Mock Redis connection  
- Cloudinary (using demo account)

Designed for local development without requiring full database server setup.
"""

import os
import sys
import time
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConnectionResult:
    """Result of a database connection test."""
    service: str
    connected: bool
    response_time: float
    error_message: Optional[str] = None
    connection_info: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class DevDatabaseConnectionTester:
    """Development database connection testing."""
    
    def __init__(self):
        self.results: Dict[str, DatabaseConnectionResult] = {}
        self.start_time = time.time()
        
    def test_sqlite_connection(self) -> DatabaseConnectionResult:
        """Test SQLite database connection (PostgreSQL replacement for dev)."""
        logger.info("🗃️ Testing SQLite connection...")
        
        start_time = time.time()
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./socialsuit.db')
        
        if not database_url.startswith('sqlite:'):
            return DatabaseConnectionResult(
                service="sqlite",
                connected=False,
                response_time=0,
                error_message="DATABASE_URL is not configured for SQLite"
            )
        
        try:
            # Extract SQLite file path
            db_path = database_url.replace('sqlite:///', './').replace('sqlite://', '')
            
            # Test connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT sqlite_version();")
            version = cursor.fetchone()[0]
            
            # Test performance
            perf_start = time.time()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            query_time = time.time() - perf_start
            
            # Create a test table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test insert/select
            cursor.execute("INSERT OR REPLACE INTO test_table (id, name) VALUES (1, 'test')")
            cursor.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            
            conn.commit()
            
            connection_info = {
                "version": f"SQLite {version}",
                "database_path": os.path.abspath(db_path),
                "file_size": os.path.getsize(db_path) if os.path.exists(db_path) else 0,
                "test_records": count
            }
            
            performance_metrics = {
                "query_response_time": query_time,
                "file_based": True
            }
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="sqlite",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="sqlite",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def test_mongodb_mock(self) -> DatabaseConnectionResult:
        """Test MongoDB connection (mock for development)."""
        logger.info("🍃 Testing MongoDB (mock mode)...")
        
        start_time = time.time()
        mongo_uri = os.getenv('MONGO_URI')
        
        if not mongo_uri:
            return DatabaseConnectionResult(
                service="mongodb_mock",
                connected=False,
                response_time=0,
                error_message="MONGO_URI environment variable not set"
            )
        
        try:
            # Mock MongoDB connection for development
            # In a real scenario, this would connect to MongoDB
            time.sleep(0.1)  # Simulate connection time
            
            connection_info = {
                "mode": "mock",
                "configured_uri": mongo_uri,
                "note": "MongoDB not required for basic development"
            }
            
            performance_metrics = {
                "mock_response_time": 0.1,
                "status": "mocked"
            }
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="mongodb_mock",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="mongodb_mock",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def test_redis_mock(self) -> DatabaseConnectionResult:
        """Test Redis connection (mock for development)."""
        logger.info("🔴 Testing Redis (mock mode)...")
        
        start_time = time.time()
        redis_url = os.getenv('REDIS_URL')
        
        if not redis_url:
            return DatabaseConnectionResult(
                service="redis_mock",
                connected=False,
                response_time=0,
                error_message="REDIS_URL environment variable not set"
            )
        
        try:
            # Mock Redis connection for development
            # In a real scenario, this would connect to Redis
            time.sleep(0.05)  # Simulate connection time
            
            connection_info = {
                "mode": "mock",
                "configured_url": redis_url,
                "note": "Redis not required for basic development"
            }
            
            performance_metrics = {
                "mock_response_time": 0.05,
                "status": "mocked"
            }
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="redis_mock",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="redis_mock",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def test_cloudinary_connection(self) -> DatabaseConnectionResult:
        """Test Cloudinary connection."""
        logger.info("☁️ Testing Cloudinary connection...")
        
        start_time = time.time()
        cloudinary_url = os.getenv('CLOUDINARY_URL')
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        
        if not cloudinary_url and not (cloud_name and api_key):
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=False,
                response_time=0,
                error_message="CLOUDINARY_URL or individual Cloudinary variables not set"
            )
        
        try:
            # Try to import cloudinary
            import cloudinary
            import cloudinary.api
            
            # Configure Cloudinary
            if cloudinary_url:
                cloudinary.config(cloudinary_url=cloudinary_url)
            else:
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=os.getenv('CLOUDINARY_API_SECRET')
                )
            
            # Test API access
            perf_start = time.time()
            result = cloudinary.api.ping()
            ping_time = time.time() - perf_start
            
            connection_info = {
                "cloud_name": cloudinary.config().cloud_name,
                "api_key": cloudinary.config().api_key[:8] + "..." if cloudinary.config().api_key else None,
                "secure": cloudinary.config().secure,
                "status": "connected"
            }
            
            performance_metrics = {
                "ping_response_time": ping_time,
                "api_accessible": True
            }
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except ImportError:
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=False,
                response_time=time.time() - start_time,
                error_message="cloudinary library not installed"
            )
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def run_all_tests(self) -> Dict[str, DatabaseConnectionResult]:
        """Run all database connection tests."""
        logger.info("🗄️ Starting development database connection tests...")
        
        # Test all database services
        self.results["sqlite"] = self.test_sqlite_connection()
        self.results["mongodb_mock"] = self.test_mongodb_mock()
        self.results["redis_mock"] = self.test_redis_mock()
        self.results["cloudinary"] = self.test_cloudinary_connection()
        
        return self.results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive database connection report."""
        total_duration = time.time() - self.start_time
        
        # Calculate statistics
        total_services = len(self.results)
        connected_services = sum(1 for result in self.results.values() if result.connected)
        failed_services = total_services - connected_services
        success_rate = (connected_services / total_services * 100) if total_services > 0 else 0
        
        # Performance metrics
        avg_response_time = sum(result.response_time for result in self.results.values()) / total_services if total_services > 0 else 0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "development",
            "total_duration": total_duration,
            "summary": {
                "total_services": total_services,
                "connected": connected_services,
                "failed": failed_services,
                "success_rate": success_rate
            },
            "performance": {
                "average_response_time": avg_response_time,
                "total_test_duration": total_duration
            },
            "services": {
                service: asdict(result) for service, result in self.results.items()
            },
            "recommendations": self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> list:
        """Generate recommendations based on test results."""
        recommendations = []
        
        for service, result in self.results.items():
            if not result.connected:
                if "environment variable not set" in (result.error_message or ""):
                    recommendations.append(f"Configure {service.upper()} environment variables")
                elif "library not installed" in (result.error_message or ""):
                    recommendations.append(f"Install required Python library for {service}")
                else:
                    recommendations.append(f"Fix {service} connection: {result.error_message}")
        
        if all(result.connected for result in self.results.values()):
            recommendations.append("All development database connections are working!")
            recommendations.append("For production, configure actual PostgreSQL, MongoDB, and Redis servers")
        
        return recommendations

def main():
    """Main execution function."""
    print("=" * 80)
    print("🗄️ DEVELOPMENT DATABASE CONNECTION TEST")
    print("=" * 80)
    
    tester = DevDatabaseConnectionTester()
    results = tester.run_all_tests()
    
    # Print results
    print("\n📊 CONNECTION RESULTS:")
    for service, result in results.items():
        status = "✅" if result.connected else "❌"
        print(f"  {status} {service.upper()}: {'Connected' if result.connected else 'Failed'} ({result.response_time:.3f}s)")
        if not result.connected and result.error_message:
            print(f"    Error: {result.error_message}")
    
    # Generate and save report
    report = tester.generate_report()
    
    # Save JSON report
    with open("dev_database_connection_results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    print(f"\n📈 SUMMARY:")
    print(f"  Connected: {report['summary']['connected']}/{report['summary']['total_services']} ({report['summary']['success_rate']:.1f}%)")
    print(f"  Duration: {report['total_duration']:.2f}s")
    print(f"  Average Response Time: {report['performance']['average_response_time']:.3f}s")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    print(f"\n📄 Detailed report saved to: dev_database_connection_results.json")
    
    return 0 if report['summary']['success_rate'] >= 75 else 1

if __name__ == "__main__":
    sys.exit(main())