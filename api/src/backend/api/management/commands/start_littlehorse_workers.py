"""
Django management command to start LittleHorse task workers.
"""
import logging
from django.core.management.base import BaseCommand
from config.workflows import register_workflows
from tasks.littlehorse_workers import start_task_workers

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start LittleHorse task workers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--register-only',
            action='store_true',
            help='Only register workflows without starting workers',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting LittleHorse integration...')
        
        try:
            # Register workflows first
            self.stdout.write('Registering LittleHorse workflows...')
            register_workflows()
            self.stdout.write(
                self.style.SUCCESS('Successfully registered LittleHorse workflows')
            )
            
            if options['register_only']:
                return
                
            # Start task workers
            self.stdout.write('Starting LittleHorse task workers...')
            workers = start_task_workers()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully started {len(workers)} LittleHorse task workers')
            )
            
            # Keep the command running
            try:
                self.stdout.write('LittleHorse workers are running. Press Ctrl+C to stop.')
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write('\nShutting down LittleHorse workers...')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to start LittleHorse workers: {e}')
            )
            raise