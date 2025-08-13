"""
LittleHorse task workers for Prowler.

This module defines task workers that replace Celery workers.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import littlehorse
from config.littlehorse import LITTLEHORSE_CONFIG, LITTLEHORSE_DEADLOCK_ATTEMPTS
from django_celery_beat.models import PeriodicTask
from littlehorse import LHTaskWorker, WorkerContext

from api.db_utils import rls_transaction
from api.decorators import set_tenant
from api.models import Provider, Scan, StateChoices
from api.v1.serializers import ScanTaskSerializer
from tasks.jobs.backfill import backfill_resource_scan_summaries
from tasks.jobs.connection import check_lighthouse_connection, check_provider_connection
from tasks.jobs.deletion import delete_provider, delete_tenant
from tasks.jobs.export import generate_outputs_job
from tasks.jobs.scan import (
    aggregate_findings,
    create_compliance_requirements,
    perform_prowler_scan,
)
from tasks.utils import get_next_execution_datetime

logger = logging.getLogger(__name__)

# Initialize LittleHorse configuration
lh_config = littlehorse.LHConfig(**LITTLEHORSE_CONFIG)

class ProwlerTaskWorkers:
    """LittleHorse task workers for Prowler operations."""
    
    def __init__(self):
        self.config = lh_config
        
    def perform_prowler_scan_task(self, ctx: WorkerContext):
        """Task worker for performing Prowler scans."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            scan_id = ctx.get_variable("scan_id")
            provider_id = ctx.get_variable("provider_id") 
            checks_to_execute = ctx.get_variable("checks_to_execute", [])
            
            result = perform_prowler_scan(
                tenant_id=tenant_id,
                scan_id=scan_id, 
                provider_id=provider_id,
                checks_to_execute=checks_to_execute
            )
            
            return result
        except Exception as e:
            logger.error(f"Error in perform_prowler_scan_task: {e}")
            raise
    
    def perform_scan_summary_task(self, ctx: WorkerContext):
        """Task worker for aggregating scan findings."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            scan_id = ctx.get_variable("scan_id")
            
            return aggregate_findings(tenant_id=tenant_id, scan_id=scan_id)
        except Exception as e:
            logger.error(f"Error in perform_scan_summary_task: {e}")
            raise
    
    def create_compliance_requirements_task(self, ctx: WorkerContext):
        """Task worker for creating compliance requirements."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            scan_id = ctx.get_variable("scan_id")
            
            return create_compliance_requirements(tenant_id=tenant_id, scan_id=scan_id)
        except Exception as e:
            logger.error(f"Error in create_compliance_requirements_task: {e}")
            raise
            
    def generate_outputs_task(self, ctx: WorkerContext):
        """Task worker for generating scan outputs."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            scan_id = ctx.get_variable("scan_id")
            provider_id = ctx.get_variable("provider_id")
            
            # Import here to avoid circular imports
            from tasks.tasks import generate_outputs_task as generate_outputs_func
            return generate_outputs_func.apply_async(
                kwargs={
                    "tenant_id": tenant_id,
                    "scan_id": scan_id,
                    "provider_id": provider_id
                }
            ).get()
        except Exception as e:
            logger.error(f"Error in generate_outputs_task: {e}")
            raise
    
    def setup_scheduled_scan_task(self, ctx: WorkerContext):
        """Task worker for setting up scheduled scans."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            provider_id = ctx.get_variable("provider_id")
            
            with rls_transaction(tenant_id):
                periodic_task_instance = PeriodicTask.objects.get(
                    name=f"scan-perform-scheduled-{provider_id}"
                )
                
                # Check for existing running scans
                existing_scan = Scan.objects.filter(
                    tenant_id=tenant_id,
                    provider_id=provider_id,
                    trigger=Scan.TriggerChoices.SCHEDULED,
                    state=StateChoices.EXECUTING,
                    scheduler_task_id=periodic_task_instance.id,
                    scheduled_at__date=datetime.now(timezone.utc).date(),
                ).first()
                
                if existing_scan:
                    logger.warning(f"Scheduled scan already running for provider {provider_id}")
                    serializer = ScanTaskSerializer(instance=existing_scan)
                    return {"scan_id": str(existing_scan.id), "duplicate": True, "result": serializer.data}
                
                # Create new scan instance
                next_scan_datetime = get_next_execution_datetime("scheduled", provider_id)
                scan_instance, _ = Scan.objects.get_or_create(
                    tenant_id=tenant_id,
                    provider_id=provider_id,
                    trigger=Scan.TriggerChoices.SCHEDULED,
                    state__in=(StateChoices.SCHEDULED, StateChoices.AVAILABLE),
                    scheduler_task_id=periodic_task_instance.id,
                    defaults={
                        "state": StateChoices.SCHEDULED,
                        "name": "Daily scheduled scan",
                        "scheduled_at": next_scan_datetime - timedelta(days=1),
                    },
                )
                
            return {"scan_id": str(scan_instance.id), "duplicate": False}
        except Exception as e:
            logger.error(f"Error in setup_scheduled_scan_task: {e}")
            raise
            
    def delete_provider_task(self, ctx: WorkerContext):
        """Task worker for deleting providers."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            provider_id = ctx.get_variable("provider_id")
            
            return delete_provider(tenant_id=tenant_id, pk=provider_id)
        except Exception as e:
            logger.error(f"Error in delete_provider_task: {e}")
            raise
            
    def delete_tenant_task(self, ctx: WorkerContext):
        """Task worker for deleting tenants."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            
            return delete_tenant(pk=tenant_id)
        except Exception as e:
            logger.error(f"Error in delete_tenant_task: {e}")
            raise
    
    def check_provider_connection_task(self, ctx: WorkerContext):
        """Task worker for checking provider connections."""
        try:
            provider_id = ctx.get_variable("provider_id")
            
            return check_provider_connection(provider_id=provider_id)
        except Exception as e:
            logger.error(f"Error in check_provider_connection_task: {e}")
            raise
            
    def check_lighthouse_connection_task(self, ctx: WorkerContext):
        """Task worker for checking lighthouse connections."""
        try:
            lighthouse_config_id = ctx.get_variable("lighthouse_config_id")
            
            return check_lighthouse_connection(lighthouse_config_id=lighthouse_config_id)
        except Exception as e:
            logger.error(f"Error in check_lighthouse_connection_task: {e}")
            raise
    
    def backfill_scan_resource_summaries_task(self, ctx: WorkerContext):
        """Task worker for backfilling scan resource summaries."""
        try:
            tenant_id = ctx.get_variable("tenant_id")
            scan_id = ctx.get_variable("scan_id")
            
            return backfill_resource_scan_summaries(tenant_id=tenant_id, scan_id=scan_id)
        except Exception as e:
            logger.error(f"Error in backfill_scan_resource_summaries_task: {e}")
            raise

def start_task_workers():
    """Start all LittleHorse task workers."""
    workers = ProwlerTaskWorkers()
    
    # Create task workers
    task_workers = []
    
    # Scan-related workers
    task_workers.append(LHTaskWorker(workers.perform_prowler_scan_task, "perform-prowler-scan", workers.config))
    task_workers.append(LHTaskWorker(workers.perform_scan_summary_task, "perform-scan-summary", workers.config))
    task_workers.append(LHTaskWorker(workers.create_compliance_requirements_task, "create-compliance-requirements", workers.config))
    task_workers.append(LHTaskWorker(workers.generate_outputs_task, "generate-outputs", workers.config))
    task_workers.append(LHTaskWorker(workers.setup_scheduled_scan_task, "setup-scheduled-scan", workers.config))
    
    # Management workers
    task_workers.append(LHTaskWorker(workers.delete_provider_task, "delete-provider", workers.config))
    task_workers.append(LHTaskWorker(workers.delete_tenant_task, "delete-tenant", workers.config))
    
    # Connection check workers
    task_workers.append(LHTaskWorker(workers.check_provider_connection_task, "check-provider-connection", workers.config))
    task_workers.append(LHTaskWorker(workers.check_lighthouse_connection_task, "check-lighthouse-connection", workers.config))
    
    # Utility workers
    task_workers.append(LHTaskWorker(workers.backfill_scan_resource_summaries_task, "backfill-scan-resource-summaries", workers.config))
    
    logger.info(f"Starting {len(task_workers)} LittleHorse task workers")
    
    # Start all workers
    for worker in task_workers:
        try:
            worker.start()
            logger.info(f"Started task worker: {worker.task_def_name}")
        except Exception as e:
            logger.error(f"Failed to start task worker {worker.task_def_name}: {e}")
            raise
    
    return task_workers

if __name__ == "__main__":
    # Start workers when run directly
    start_task_workers()
    logger.info("LittleHorse task workers started")