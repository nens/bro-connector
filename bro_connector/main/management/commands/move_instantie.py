from django.core.management.base import BaseCommand
from gmw.models import Instantie
from bro.models import Company

class Command(BaseCommand):
    help = 'Move Instantie data from gmw to Company in bro'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting data transfer from gmw.Instantie to bro.Company')

        instanties = Instantie.objects.all()
        companies = []

        for inst in instanties:
            companies.append(Company(
                name=inst.name,
                company_number=inst.company_number,
                color=inst.color,
                bro_user=inst.bro_user,
                bro_token=inst.bro_token
            ))

        Company.objects.bulk_create(companies)

        self.stdout.write('Data transfer completed successfully')