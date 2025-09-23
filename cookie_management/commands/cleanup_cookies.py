"""
Management command to clean up expired cookies.
"""

from django.core.management.base import BaseCommand
from cookie_management.cookie_manager import cookie_manager


class Command(BaseCommand):
    help = 'Clean up expired cookie files'

    def handle(self, *args, **options):
        cleaned_count = cookie_manager.cleanup_expired_cookies()
        
        if cleaned_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up {cleaned_count} expired cookie files')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No expired cookie files found')
            )
