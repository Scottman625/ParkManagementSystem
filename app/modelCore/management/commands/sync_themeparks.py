from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Sync destinations and parks data from ThemeParks API (legacy command, please use sync_entities instead)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync all data, ignore cache',
        )

    def handle(self, *args, **options):
        self.stdout.write('Using sync_entities command to sync data...')
        
        # Call the new sync_entities command
        call_command('sync_entities', force=options.get('force', False))
        
        self.stdout.write(self.style.SUCCESS('Sync completed')) 