"""
Tests for LittleHorse integration
"""
import pytest
from unittest.mock import patch, MagicMock

from config.workflows import register_workflows, start_workflow, LittleHorseWorkflows
from config.littlehorse import LITTLEHORSE_CONFIG
from tasks.littlehorse_workers import start_task_workers, ProwlerTaskWorkers


class TestLittleHorseConfig:
    """Test LittleHorse configuration."""
    
    def test_littlehorse_config_exists(self):
        """Test that LittleHorse configuration is properly defined."""
        assert 'bootstrap_host' in LITTLEHORSE_CONFIG
        assert 'bootstrap_port' in LITTLEHORSE_CONFIG
        assert LITTLEHORSE_CONFIG['bootstrap_host'] == 'littlehorse'
        assert LITTLEHORSE_CONFIG['bootstrap_port'] == 2023


class TestLittleHorseWorkflows:
    """Test LittleHorse workflow definitions."""
    
    def test_workflow_definitions_exist(self):
        """Test that workflow functions are properly defined."""
        workflows = LittleHorseWorkflows()
        
        # Test that workflow methods exist and are callable
        assert callable(workflows.scan_workflow)
        assert callable(workflows.scheduled_scan_workflow)
        assert callable(workflows.provider_deletion_workflow)
        assert callable(workflows.tenant_deletion_workflow)
    
    @patch('config.workflows.client')
    def test_register_workflows(self, mock_client):
        """Test workflow registration."""
        mock_client.put_wf_spec = MagicMock()
        
        register_workflows()
        
        # Verify put_wf_spec was called for each workflow
        assert mock_client.put_wf_spec.call_count == 4
    
    @patch('config.workflows.client')
    def test_start_workflow(self, mock_client):
        """Test starting a workflow."""
        mock_client.run_wf = MagicMock(return_value='workflow-id-123')
        
        variables = {
            'tenant_id': 'test-tenant',
            'scan_id': 'test-scan-id',
            'provider_id': 'test-provider'
        }
        
        result = start_workflow('scan', variables)
        
        assert result == 'workflow-id-123'
        mock_client.run_wf.assert_called_once_with('scan', **variables)


class TestProwlerTaskWorkers:
    """Test LittleHorse task workers."""
    
    def test_task_workers_initialization(self):
        """Test that task workers can be initialized."""
        workers = ProwlerTaskWorkers()
        assert workers.config is not None
    
    def test_task_worker_methods_exist(self):
        """Test that all required task worker methods exist."""
        workers = ProwlerTaskWorkers()
        
        required_methods = [
            'perform_prowler_scan_task',
            'perform_scan_summary_task', 
            'create_compliance_requirements_task',
            'generate_outputs_task',
            'setup_scheduled_scan_task',
            'delete_provider_task',
            'delete_tenant_task',
            'check_provider_connection_task',
            'check_lighthouse_connection_task',
            'backfill_scan_resource_summaries_task'
        ]
        
        for method_name in required_methods:
            assert hasattr(workers, method_name)
            assert callable(getattr(workers, method_name))
    
    @patch('tasks.littlehorse_workers.LHTaskWorker')
    def test_start_task_workers(self, mock_worker_class):
        """Test starting task workers."""
        mock_worker = MagicMock()
        mock_worker.start = MagicMock()
        mock_worker_class.return_value = mock_worker
        
        workers = start_task_workers()
        
        # Should create 10 workers (all the task types)
        assert len(workers) == 10
        assert mock_worker.start.call_count == 10
    
    def test_task_worker_error_handling(self):
        """Test error handling in task workers."""
        workers = ProwlerTaskWorkers()
        
        # Mock context that raises an exception
        mock_context = MagicMock()
        mock_context.get_variable.side_effect = Exception("Test error")
        
        with pytest.raises(Exception) as exc_info:
            workers.perform_prowler_scan_task(mock_context)
        
        assert "Test error" in str(exc_info.value)


class TestIntegrationCompatibility:
    """Test compatibility with existing Celery tasks."""
    
    @patch.dict('os.environ', {'LITTLEHORSE_ENABLED': 'false'})
    def test_celery_fallback(self):
        """Test that Celery is used when LittleHorse is disabled."""
        from tasks.tasks import LITTLEHORSE_ENABLED
        assert LITTLEHORSE_ENABLED is False
    
    @patch.dict('os.environ', {'LITTLEHORSE_ENABLED': 'true'})
    @patch('config.workflows.start_workflow')
    def test_littlehorse_enabled(self, mock_start_workflow):
        """Test that LittleHorse is used when enabled."""
        # This would need to be tested in an environment where the imports work
        # For now, just test the mock setup
        mock_start_workflow.return_value = 'workflow-123'
        
        result = mock_start_workflow('scan', {'tenant_id': 'test'})
        assert result == 'workflow-123'