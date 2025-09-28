import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json

# Import the AB testing service and related models
# Note: Adjust imports based on actual project structure
from app.services.ab_testing import create_test, get_test, get_user_tests, update_test, delete_test, record_variant_performance
from app.services.models.ab_testing_model import ABTest, TestStatus, TestVariant
from app.services.models.user_model import User

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_ab_test():
    test = MagicMock(spec=ABTest)
    test.id = "test-1"
    test.user_id = "test-user-id"
    test.name = "Test Campaign"
    test.description = "Testing different post formats"
    test.platform = "instagram"
    test.start_date = datetime.utcnow()
    test.end_date = datetime.utcnow() + timedelta(days=7)
    test.status = TestStatus.ACTIVE
    test.variants = [
        TestVariant(id="variant-a", name="Variant A", content={"text": "Test post A"}),
        TestVariant(id="variant-b", name="Variant B", content={"text": "Test post B"})
    ]
    test.metrics = ["likes", "comments", "shares"]
    test.created_at = datetime.utcnow() - timedelta(days=1)
    test.updated_at = datetime.utcnow() - timedelta(hours=1)
    return test

@pytest.fixture
def mock_ab_testing_repository():
    repo = MagicMock()
    repo.create.return_value = None
    repo.get_by_id.return_value = None
    repo.get_tests_by_user_id.return_value = []
    repo.update.return_value = None
    repo.delete.return_value = None
    repo.record_performance.return_value = True
    return repo

@pytest.fixture
def mock_user_repository():
    repo = MagicMock()
    repo.get_by_id.return_value = None
    return repo

class TestABTestingService:
    def test_create_test(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.create.return_value = mock_ab_test
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = create_test(
                user_id="test-user-id",
                name="Test Campaign",
                description="Testing different post formats",
                platform="instagram",
                variants=[
                    {"name": "Variant A", "content": {"text": "Test post A"}},
                    {"name": "Variant B", "content": {"text": "Test post B"}}
                ],
                metrics=["likes", "comments", "shares"],
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=7)
            )
            
            # Assert
            assert result == mock_ab_test
            mock_ab_testing_repository.create.assert_called_once()
    
    def test_get_test(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = get_test("test-1")
            
            # Assert
            assert result == mock_ab_test
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
    
    def test_get_test_not_found(self, mock_ab_testing_repository):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = None
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = get_test("non-existent-test")
            
            # Assert
            assert result is None
            mock_ab_testing_repository.get_by_id.assert_called_once_with("non-existent-test")
    
    def test_get_user_tests(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.get_tests_by_user_id.return_value = [mock_ab_test]
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = get_user_tests("test-user-id")
            
            # Assert
            assert len(result) == 1
            assert result[0] == mock_ab_test
            mock_ab_testing_repository.get_tests_by_user_id.assert_called_once_with(
                user_id="test-user-id",
                platform=None,
                status=None
            )
    
    def test_get_user_tests_with_filters(self, mock_ab_testing_repository):
        # Setup
        mock_ab_testing_repository.get_tests_by_user_id.return_value = []
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = get_user_tests(
                user_id="test-user-id",
                platform="instagram",
                status=TestStatus.ACTIVE
            )
            
            # Assert
            assert len(result) == 0
            mock_ab_testing_repository.get_tests_by_user_id.assert_called_once_with(
                user_id="test-user-id",
                platform="instagram",
                status=TestStatus.ACTIVE
            )
    
    def test_update_test(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        mock_ab_testing_repository.update.return_value = mock_ab_test
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = update_test(
                test_id="test-1",
                name="Updated Test Campaign",
                description="Updated description",
                end_date=datetime.utcnow() + timedelta(days=14)
            )
            
            # Assert
            assert result == mock_ab_test
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_ab_testing_repository.update.assert_called_once()
    
    def test_update_test_not_found(self, mock_ab_testing_repository):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = None
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = update_test(
                test_id="non-existent-test",
                name="Updated Test Campaign"
            )
            
            # Assert
            assert result is None
            mock_ab_testing_repository.get_by_id.assert_called_once_with("non-existent-test")
            mock_ab_testing_repository.update.assert_not_called()
    
    def test_delete_test(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = delete_test("test-1")
            
            # Assert
            assert result is True
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_ab_testing_repository.delete.assert_called_once_with(mock_ab_test)
    
    def test_delete_test_not_found(self, mock_ab_testing_repository):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = None
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = delete_test("non-existent-test")
            
            # Assert
            assert result is False
            mock_ab_testing_repository.get_by_id.assert_called_once_with("non-existent-test")
            mock_ab_testing_repository.delete.assert_not_called()
    
    def test_record_variant_performance(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        mock_ab_testing_repository.record_performance.return_value = True
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            performance_data = {
                "likes": 150,
                "comments": 25,
                "shares": 10
            }
            result = record_variant_performance(
                test_id="test-1",
                variant_id="variant-a",
                performance_data=performance_data
            )
            
            # Assert
            assert result is True
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_ab_testing_repository.record_performance.assert_called_once_with(
                test_id="test-1",
                variant_id="variant-a",
                performance_data=performance_data
            )
    
    def test_record_variant_performance_test_not_found(self, mock_ab_testing_repository):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = None
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            performance_data = {"likes": 150}
            result = record_variant_performance(
                test_id="non-existent-test",
                variant_id="variant-a",
                performance_data=performance_data
            )
            
            # Assert
            assert result is False
            mock_ab_testing_repository.get_by_id.assert_called_once_with("non-existent-test")
            mock_ab_testing_repository.record_performance.assert_not_called()
    
    def test_record_variant_performance_variant_not_found(self, mock_ab_testing_repository, mock_ab_test):
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        mock_ab_testing_repository.record_performance.side_effect = ValueError("Variant not found")
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute and Assert
            performance_data = {"likes": 150}
            with pytest.raises(ValueError, match="Variant not found"):
                record_variant_performance(
                    test_id="test-1",
                    variant_id="non-existent-variant",
                    performance_data=performance_data
                )
            
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_ab_testing_repository.record_performance.assert_called_once_with(
                test_id="test-1",
                variant_id="non-existent-variant",
                performance_data=performance_data
            )
    
    @patch('services.ab_testing.analyze_test_results')
    def test_get_test_results(self, mock_analyze_test_results, mock_ab_testing_repository, mock_ab_test):
        # Import the function to test
        from services.ab_testing import get_test_results
        
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        mock_analyze_test_results.return_value = {
            "winner": "variant-a",
            "metrics": {
                "variant-a": {"likes": 150, "comments": 25, "shares": 10},
                "variant-b": {"likes": 100, "comments": 15, "shares": 5}
            },
            "improvement": 50,
            "confidence": 95
        }
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = get_test_results("test-1")
            
            # Assert
            assert result["winner"] == "variant-a"
            assert "metrics" in result
            assert "improvement" in result
            assert "confidence" in result
            
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_analyze_test_results.assert_called_once_with(mock_ab_test)
    
    @patch('services.ab_testing.analyze_test_results')
    def test_get_test_results_test_not_found(self, mock_analyze_test_results, mock_ab_testing_repository):
        # Import the function to test
        from services.ab_testing import get_test_results
        
        # Setup
        mock_ab_testing_repository.get_by_id.return_value = None
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = get_test_results("non-existent-test")
            
            # Assert
            assert result is None
            mock_ab_testing_repository.get_by_id.assert_called_once_with("non-existent-test")
            mock_analyze_test_results.assert_not_called()
    
    def test_start_test(self, mock_ab_testing_repository, mock_ab_test):
        # Import the function to test
        from services.ab_testing import start_test
        
        # Setup
        mock_ab_test.status = TestStatus.DRAFT
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        mock_ab_testing_repository.update.return_value = mock_ab_test
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = start_test("test-1")
            
            # Assert
            assert result is True
            assert mock_ab_test.status == TestStatus.ACTIVE
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_ab_testing_repository.update.assert_called_once()
    
    def test_stop_test(self, mock_ab_testing_repository, mock_ab_test):
        # Import the function to test
        from services.ab_testing import stop_test
        
        # Setup
        mock_ab_test.status = TestStatus.ACTIVE
        mock_ab_testing_repository.get_by_id.return_value = mock_ab_test
        mock_ab_testing_repository.update.return_value = mock_ab_test
        
        with patch('services.ab_testing.ab_testing_repository', mock_ab_testing_repository):
            # Execute
            result = stop_test("test-1")
            
            # Assert
            assert result is True
            assert mock_ab_test.status == TestStatus.COMPLETED
            mock_ab_testing_repository.get_by_id.assert_called_once_with("test-1")
            mock_ab_testing_repository.update.assert_called_once()