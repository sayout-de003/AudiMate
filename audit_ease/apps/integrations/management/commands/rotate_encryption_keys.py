from django.core.management.base import BaseCommand, CommandError
from services.encryption_manager import get_key_manager
import json


class Command(BaseCommand):
    help = 'Rotate encryption keys for token protection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would happen without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rotation even if key is not yet due'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        
        key_manager = get_key_manager()
        status = key_manager.get_key_status()
        
        self.stdout.write(self.style.SUCCESS("=== Encryption Key Rotation ===\n"))
        self.stdout.write(f"Current key age: {status['key_age_days']} days")
        self.stdout.write(f"Rotation required: {status['rotation_required']}")
        
        # Check if rotation is needed
        if status['rotation_required'] or force:
            self.stdout.write(
                self.style.WARNING(
                    f"\nKey rotation initiated (dry_run={dry_run})\n"
                )
            )
            
            if not dry_run:
                rotation_result = key_manager.rotate_key()
                
                self.stdout.write(self.style.SUCCESS(
                    "Key rotation completed successfully!\n"
                ))
                
                self.stdout.write(self.style.WARNING(
                    "⚠️  UPDATE REQUIRED: Set these environment variables:\n"
                ))
                
                for cmd in rotation_result['env_update_commands']:
                    self.stdout.write(f"  {cmd}")
                
                self.stdout.write(
                    self.style.WARNING(
                        "\nAfter updating environment variables, restart the application."
                    )
                )
                
                # Save rotation details to file for audit trail
                import json
                from pathlib import Path
                audit_file = Path('/var/log/audit_ease/key_rotation.json')
                audit_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(audit_file, 'a') as f:
                    json.dump({
                        'timestamp': rotation_result['rotation_time'],
                        'primary_key_hash': hash(rotation_result['new_primary_key']),
                        'status': 'completed'
                    }, f)
                    f.write('\n')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nAudit trail saved to {audit_file}"
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⏳ Key rotation not yet needed. "
                    f"Days until rotation: {status['days_until_rotation']}"
                )
            )
            self.stdout.write("Use --force to rotate anyway.")
