from django.core.management.base import BaseCommand
from supplytracking.utils import create_scripts

class Command(BaseCommand):

    def handle(self, **options):
        ####  create supply tracking scripts ####
        create_scripts()