"""
LittleHorse workflow definitions for Prowler tasks.

This module defines workflows that replace Celery task chains with LittleHorse workflows.
"""
import logging
from typing import Any, Dict, List, Optional

import littlehorse
from littlehorse import WorkflowSpec

from config.littlehorse import LITTLEHORSE_CONFIG

logger = logging.getLogger(__name__)

# Initialize LittleHorse client
lh_config = littlehorse.LHConfig(**LITTLEHORSE_CONFIG)
client = littlehorse.LHClient(lh_config)

class LittleHorseWorkflows:
    """Class containing all LittleHorse workflow definitions for Prowler."""
    
    @staticmethod
    def scan_workflow():
        """
        Define the main scan workflow that replaces the Celery task chain.
        
        This workflow orchestrates:
        1. Performing the scan
        2. Aggregating findings
        3. Creating compliance requirements
        4. Generating outputs
        """
        def scan_wf(wf: WorkflowSpec):
            # Input variables
            tenant_id = wf.add_variable("tenant_id", littlehorse.VariableType.STR)
            scan_id = wf.add_variable("scan_id", littlehorse.VariableType.STR)
            provider_id = wf.add_variable("provider_id", littlehorse.VariableType.STR)
            checks_to_execute = wf.add_variable("checks_to_execute", littlehorse.VariableType.JSON_OBJ).with_default_value([])
            
            # Step 1: Perform the actual scan
            scan_result = wf.execute_task(
                "perform-prowler-scan",
                tenant_id=tenant_id.jsonpath("$"),
                scan_id=scan_id.jsonpath("$"),
                provider_id=provider_id.jsonpath("$"),
                checks_to_execute=checks_to_execute.jsonpath("$")
            )
            
            # Step 2: Create compliance requirements (parallel with summary)
            compliance_task = wf.execute_task(
                "create-compliance-requirements",
                tenant_id=tenant_id.jsonpath("$"),
                scan_id=scan_id.jsonpath("$")
            )
            
            # Step 3: Aggregate findings into scan summary
            summary_task = wf.execute_task(
                "perform-scan-summary", 
                tenant_id=tenant_id.jsonpath("$"),
                scan_id=scan_id.jsonpath("$")
            )
            
            # Wait for both compliance and summary to complete
            wf.wait_for_tasks(compliance_task, summary_task)
            
            # Step 4: Generate outputs after summary is complete
            wf.execute_task(
                "generate-outputs",
                tenant_id=tenant_id.jsonpath("$"),
                scan_id=scan_id.jsonpath("$"),
                provider_id=provider_id.jsonpath("$")
            )
            
        return scan_wf
    
    @staticmethod 
    def scheduled_scan_workflow():
        """
        Define the scheduled scan workflow.
        
        This workflow handles scheduled scans with deduplication logic.
        """
        def scheduled_scan_wf(wf: WorkflowSpec):
            tenant_id = wf.add_variable("tenant_id", littlehorse.VariableType.STR)
            provider_id = wf.add_variable("provider_id", littlehorse.VariableType.STR)
            
            # Check for existing scheduled scan and create scan instance
            scan_setup = wf.execute_task(
                "setup-scheduled-scan",
                tenant_id=tenant_id.jsonpath("$"),
                provider_id=provider_id.jsonpath("$")
            )
            
            # Execute the scan workflow
            scan_id = scan_setup.jsonpath("$.scan_id")
            
            wf.spawn_thread("main_scan_thread", "scan", {
                "tenant_id": tenant_id.jsonpath("$"),
                "scan_id": scan_id,
                "provider_id": provider_id.jsonpath("$"),
                "checks_to_execute": []
            })
            
        return scheduled_scan_wf
    
    @staticmethod
    def provider_deletion_workflow():
        """Workflow for deleting providers."""
        def provider_deletion_wf(wf: WorkflowSpec):
            tenant_id = wf.add_variable("tenant_id", littlehorse.VariableType.STR)
            provider_id = wf.add_variable("provider_id", littlehorse.VariableType.STR)
            
            wf.execute_task(
                "delete-provider",
                tenant_id=tenant_id.jsonpath("$"),
                provider_id=provider_id.jsonpath("$")
            )
            
        return provider_deletion_wf
    
    @staticmethod
    def tenant_deletion_workflow():
        """Workflow for deleting tenants."""
        def tenant_deletion_wf(wf: WorkflowSpec):
            tenant_id = wf.add_variable("tenant_id", littlehorse.VariableType.STR)
            
            wf.execute_task(
                "delete-tenant",
                tenant_id=tenant_id.jsonpath("$")
            )
            
        return tenant_deletion_wf

# Register workflows with LittleHorse server
def register_workflows():
    """Register all workflow definitions with the LittleHorse server."""
    try:
        workflows = LittleHorseWorkflows()
        
        # Register scan workflow
        client.put_wf_spec(workflows.scan_workflow(), "scan")
        logger.info("Registered scan workflow")
        
        # Register scheduled scan workflow 
        client.put_wf_spec(workflows.scheduled_scan_workflow(), "scheduled-scan")
        logger.info("Registered scheduled scan workflow")
        
        # Register deletion workflows
        client.put_wf_spec(workflows.provider_deletion_workflow(), "provider-deletion")
        client.put_wf_spec(workflows.tenant_deletion_workflow(), "tenant-deletion")
        logger.info("Registered deletion workflows")
        
    except Exception as e:
        logger.error(f"Failed to register workflows: {e}")
        raise

def start_workflow(workflow_name: str, variables: Dict[str, Any]) -> str:
    """
    Start a workflow instance.
    
    Args:
        workflow_name: Name of the workflow to start
        variables: Input variables for the workflow
        
    Returns:
        Workflow run ID
    """
    try:
        run_id = client.run_wf(workflow_name, **variables)
        logger.info(f"Started workflow {workflow_name} with run ID: {run_id}")
        return str(run_id)
    except Exception as e:
        logger.error(f"Failed to start workflow {workflow_name}: {e}")
        raise