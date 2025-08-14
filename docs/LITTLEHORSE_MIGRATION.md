# LittleHorse Migration Guide

This guide explains how to migrate from Celery+Valkey to LittleHorse for improved parallel scan processing in Prowler.

## Overview

LittleHorse is a workflow orchestration system that replaces Celery for task execution and Valkey as the message broker. This migration provides:

- **Better Parallel Processing**: Removes bottlenecks in parallel scan execution
- **Improved Observability**: Built-in monitoring and workflow visualization
- **Enhanced Reliability**: Better error handling and retry mechanisms
- **Simplified Architecture**: Single system instead of Celery+Valkey combination

## Architecture Changes

### Before (Celery + Valkey)
```
Django API → Celery Tasks → Valkey (Message Broker) → Celery Workers
```

### After (LittleHorse)
```
Django API → LittleHorse Workflows → LittleHorse Server → LittleHorse Task Workers
```

## Migration Components

### 1. Configuration Files
- `config/littlehorse.py` - LittleHorse server connection settings
- `config/workflows.py` - Workflow definitions replacing Celery task chains

### 2. Task Workers  
- `tasks/littlehorse_workers.py` - Task workers replacing Celery workers
- All existing task logic preserved, only execution layer changed

### 3. Compatibility Layer
- `tasks/tasks.py` - Updated to support both Celery and LittleHorse
- Backwards compatible - existing deployments continue to work

### 4. Docker Configuration
- Both `docker-compose.yml` and `docker-compose-dev.yml` updated
- Added LittleHorse server container
- Maintained Valkey for backwards compatibility

### 5. Management Commands
- `start_littlehorse_workers` - Django command to start workers and register workflows

## Environment Configuration

Add these variables to your `.env` file:

```bash
# Enable LittleHorse (set to true to use LittleHorse instead of Celery)
LITTLEHORSE_ENABLED=false

# LittleHorse server configuration
LITTLEHORSE_API_HOST=littlehorse
LITTLEHORSE_API_PORT=2023
LITTLEHORSE_DASHBOARD_PORT=8080

# Task execution timeouts (in milliseconds)
LITTLEHORSE_TASK_TIMEOUT_MS=3600000
LITTLEHORSE_WORKFLOW_TIMEOUT_MS=7200000
LITTLEHORSE_DEADLOCK_ATTEMPTS=5

# TLS configuration (optional)
# LITTLEHORSE_CA_CERT=/path/to/ca.crt
# LITTLEHORSE_CLIENT_CERT=/path/to/client.crt  
# LITTLEHORSE_CLIENT_KEY=/path/to/client.key
```

## Migration Steps

### Phase 1: Preparation (Safe to deploy)

1. **Deploy the code** with `LITTLEHORSE_ENABLED=false`
   ```bash
   git pull origin main
   docker-compose build
   ```

2. **Start services** (LittleHorse will be available but not used)
   ```bash
   docker-compose up -d
   ```

3. **Verify LittleHorse server** is running
   ```bash
   curl http://localhost:2023/api/health
   # Should return healthy status
   ```

### Phase 2: Enable LittleHorse

1. **Register workflows** with LittleHorse server
   ```bash
   docker-compose exec api python manage.py start_littlehorse_workers --register-only
   ```

2. **Enable LittleHorse** in environment
   ```bash
   # Set in .env file
   LITTLEHORSE_ENABLED=true
   ```

3. **Restart services** to pick up the new configuration
   ```bash
   docker-compose restart api worker worker-beat
   ```

4. **Start LittleHorse workers**
   ```bash
   docker-compose exec api python manage.py start_littlehorse_workers
   ```

### Phase 3: Verification

1. **Test scan execution** - create a new scan and verify it uses LittleHorse
2. **Monitor workflows** via LittleHorse dashboard at `http://localhost:8080`
3. **Check logs** for any errors during transition

### Phase 4: Cleanup (Optional)

Once confident in LittleHorse deployment:

1. **Remove Celery workers** from docker-compose if desired
2. **Keep Valkey** as it may be used for other caching purposes

## Workflow Definitions

### Main Scan Workflow
Replaces the Celery task chain:
```
perform_scan_task → [compliance_requirements_task, scan_summary_task] → generate_outputs_task
```

LittleHorse workflow provides better parallel execution of compliance and summary tasks.

### Scheduled Scan Workflow  
Handles scheduled scans with proper deduplication logic.

### Management Workflows
- Provider deletion workflow
- Tenant deletion workflow

## Task Mapping

| Celery Task | LittleHorse Worker | Function |
|-------------|-------------------|-----------|
| `perform_scan_task` | `perform-prowler-scan` | Main scan execution |
| `perform_scheduled_scan_task` | `setup-scheduled-scan` + `scan` workflow | Scheduled scans |
| `perform_scan_summary_task` | `perform-scan-summary` | Aggregate findings |
| `create_compliance_requirements_task` | `create-compliance-requirements` | Compliance records |
| `generate_outputs_task` | `generate-outputs` | Generate output files |
| `delete_provider_task` | `delete-provider` | Provider deletion |
| `delete_tenant_task` | `delete-tenant` | Tenant deletion |

## Monitoring and Observability

### LittleHorse Dashboard
Access at `http://localhost:8080` to view:
- Active workflows
- Task execution status
- Performance metrics
- Error details

### Logging
LittleHorse workers log to the same location as Django application logs.

### Metrics
LittleHorse provides built-in metrics for:
- Workflow execution time
- Task success/failure rates
- System throughput

## Rollback Plan

To rollback to Celery if needed:

1. **Disable LittleHorse**
   ```bash
   # Set in .env file
   LITTLEHORSE_ENABLED=false
   ```

2. **Restart services**
   ```bash
   docker-compose restart
   ```

3. **Ensure Celery workers are running**
   ```bash
   docker-compose exec worker celery inspect active
   ```

## Troubleshooting

### Common Issues

1. **LittleHorse server not reachable**
   - Check if container is running: `docker-compose ps littlehorse`
   - Check connectivity: `curl http://localhost:2023/api/health`

2. **Workflows not registered**
   - Run: `docker-compose exec api python manage.py start_littlehorse_workers --register-only`
   - Check LittleHorse logs: `docker-compose logs littlehorse`

3. **Tasks not executing**
   - Verify workers are running: `docker-compose exec api python manage.py start_littlehorse_workers`
   - Check worker logs for errors

4. **Mixed Celery/LittleHorse execution**
   - Ensure `LITTLEHORSE_ENABLED=true` is set consistently across all services
   - Restart all services after changing configuration

### Debug Mode

For debugging, you can run workers in foreground:
```bash
docker-compose exec api python manage.py start_littlehorse_workers
```

This will show real-time logs from all task workers.

## Performance Expectations

### Improvements Expected
- **Parallel Scanning**: Better resource utilization during scan execution
- **Reduced Bottlenecks**: Elimination of Celery/Valkey message queuing bottlenecks
- **Better Error Handling**: More robust retry and error recovery mechanisms

### Resource Usage
- LittleHorse server adds ~200MB memory usage
- Task workers have similar resource requirements to Celery workers
- Overall system should perform better under high parallel load

## Support

For issues with the LittleHorse integration:

1. Check this documentation
2. Review LittleHorse server logs: `docker-compose logs littlehorse`
3. Review application logs for LittleHorse-related errors
4. Use the LittleHorse dashboard for workflow debugging

The migration is designed to be safe and backwards compatible. You can always rollback to Celery if issues arise.