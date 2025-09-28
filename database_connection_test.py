#!/usr/bin/env python3
"""
Database Connection Verification Script

This script tests connections to all database services used by the Social Suit application:
- PostgreSQL (main database)
- MongoDB (document storage)
- Redis (caching and sessions)
- Cloudinary (media storage)

It provides detailed connection status, configuration validation, and performance metrics.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Database connection libraries
try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    psycopg2 = None

try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    pymongo = None

try:
    import redis
except ImportError:
    redis = None

try:
    import cloudinary
    import cloudinary.api
    from cloudinary.utils import cloudinary_url
except ImportError:
    cloudinary = None

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

class DatabaseConnectionTester:
    """Comprehensive database connection testing."""
    
    def __init__(self):
        self.results: Dict[str, DatabaseConnectionResult] = {}
        self.start_time = time.time()
        
    def test_postgresql_connection(self) -> DatabaseConnectionResult:
        """Test PostgreSQL database connection."""
        logger.info("🐘 Testing PostgreSQL connection...")
        
        start_time = time.time()
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            return DatabaseConnectionResult(
                service="postgresql",
                connected=False,
                response_time=0,
                error_message="DATABASE_URL environment variable not set"
            )
        
        if not psycopg2:
            return DatabaseConnectionResult(
                service="postgresql",
                connected=False,
                response_time=0,
                error_message="psycopg2 library not installed"
            )
        
        try:
            # Test connection
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # Test performance
            perf_start = time.time()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            query_time = time.time() - perf_start
            
            # Get connection info
            cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
            db_info = cursor.fetchone()
            
            connection_info = {
                "version": version,
                "database": db_info[0],
                "user": db_info[1],
                "host": db_info[2] if db_info[2] else "localhost",
                "port": db_info[3] if db_info[3] else 5432
            }
            
            performance_metrics = {
                "query_response_time": query_time,
                "connection_pool_size": conn.info.backend_pid
            }
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="postgresql",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="postgresql",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def test_mongodb_connection(self) -> DatabaseConnectionResult:
        """Test MongoDB connection."""
        logger.info("🍃 Testing MongoDB connection...")
        
        start_time = time.time()
        mongo_uri = os.getenv('MONGO_URI')
        
        if not mongo_uri:
            return DatabaseConnectionResult(
                service="mongodb",
                connected=False,
                response_time=0,
                error_message="MONGO_URI environment variable not set"
            )
        
        if not pymongo:
            return DatabaseConnectionResult(
                service="mongodb",
                connected=False,
                response_time=0,
                error_message="pymongo library not installed"
            )
        
        try:
            # Test connection
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test server info
            server_info = client.server_info()
            
            # Test database access
            db = client.get_default_database()
            
            # Test performance
            perf_start = time.time()
            db.command("ping")
            ping_time = time.time() - perf_start
            
            connection_info = {
                "version": server_info.get("version"),
                "database": db.name,
                "host": client.address[0] if client.address else "unknown",
                "port": client.address[1] if client.address else 27017
            }
            
            performance_metrics = {
                "ping_response_time": ping_time,
                "max_pool_size": client.max_pool_size
            }
            
            client.close()
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="mongodb",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="mongodb",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def test_redis_connection(self) -> DatabaseConnectionResult:
        """Test Redis connection."""
        logger.info("🔴 Testing Redis connection...")
        
        start_time = time.time()
        redis_url = os.getenv('REDIS_URL')
        
        if not redis_url:
            return DatabaseConnectionResult(
                service="redis",
                connected=False,
                response_time=0,
                error_message="REDIS_URL environment variable not set"
            )
        
        if not redis:
            return DatabaseConnectionResult(
                service="redis",
                connected=False,
                response_time=0,
                error_message="redis library not installed"
            )
        
        try:
            # Test connection
            r = redis.from_url(redis_url, socket_connect_timeout=5)
            
            # Test basic operations
            perf_start = time.time()
            r.ping()
            ping_time = time.time() - perf_start
            
            # Test set/get
            test_key = "social_suit_test"
            r.set(test_key, "test_value", ex=10)
            value = r.get(test_key)
            r.delete(test_key)
            
            # Get server info
            info = r.info()
            
            connection_info = {
                "version": info.get("redis_version"),
                "host": r.connection_pool.connection_kwargs.get("host", "unknown"),
                "port": r.connection_pool.connection_kwargs.get("port", 6379),
                "db": r.connection_pool.connection_kwargs.get("db", 0)
            }
            
            performance_metrics = {
                "ping_response_time": ping_time,
                "memory_usage": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="redis",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DatabaseConnectionResult(
                service="redis",
                connected=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def test_cloudinary_connection(self) -> DatabaseConnectionResult:
        """Test Cloudinary connection."""
        logger.info("☁️ Testing Cloudinary connection...")
        
        start_time = time.time()
        cloudinary_url = os.getenv('CLOUDINARY_URL')
        
        if not cloudinary_url:
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=False,
                response_time=0,
                error_message="CLOUDINARY_URL environment variable not set"
            )
        
        if not cloudinary:
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=False,
                response_time=0,
                error_message="cloudinary library not installed"
            )
        
        try:
            # Configure Cloudinary
            cloudinary.config(cloudinary_url=cloudinary_url)
            
            # Test API access
            perf_start = time.time()
            result = cloudinary.api.ping()
            ping_time = time.time() - perf_start
            
            # Get account info
            usage = cloudinary.api.usage()
            
            connection_info = {
                "cloud_name": cloudinary.config().cloud_name,
                "api_key": cloudinary.config().api_key[:8] + "..." if cloudinary.config().api_key else None,
                "secure": cloudinary.config().secure
            }
            
            performance_metrics = {
                "ping_response_time": ping_time,
                "storage_used": usage.get("storage", {}).get("used_bytes", 0),
                "transformations_used": usage.get("transformations", {}).get("used", 0),
                "requests_used": usage.get("requests", {}).get("used", 0)
            }
            
            response_time = time.time() - start_time
            
            return DatabaseConnectionResult(
                service="cloudinary",
                connected=True,
                response_time=response_time,
                connection_info=connection_info,
                performance_metrics=performance_metrics
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
        logger.info("🗄️ Starting comprehensive database connection tests...")
        
        # Test all database services
        self.results["postgresql"] = self.test_postgresql_connection()
        self.results["mongodb"] = self.test_mongodb_connection()
        self.results["redis"] = self.test_redis_connection()
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
                    recommendations.append(f"Configure {service.upper()}_URL environment variable")
                elif "library not installed" in (result.error_message or ""):
                    recommendations.append(f"Install {service} Python library")
                else:
                    recommendations.append(f"Fix {service} connection: {result.error_message}")
        
        if all(result.connected for result in self.results.values()):
            recommendations.append("All database connections are healthy!")
        
        return recommendations

def main():
    """Main execution function."""
    print("=" * 80)
    print("🗄️ DATABASE CONNECTION VERIFICATION")
    print("=" * 80)
    
    tester = DatabaseConnectionTester()
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
    with open("database_connection_results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    print(f"\n📈 SUMMARY:")
    print(f"  Connected: {report['summary']['connected']}/{report['summary']['total_services']} ({report['summary']['success_rate']:.1f}%)")
    print(f"  Duration: {report['total_duration']:.2f}s")
    print(f"  Average Response Time: {report['performance']['average_response_time']:.3f}s")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    print(f"\n📄 Detailed report saved to: database_connection_results.json")
    
    return 0 if report['summary']['success_rate'] == 100 else 1

if __name__ == "__main__":
    sys.exit(main())