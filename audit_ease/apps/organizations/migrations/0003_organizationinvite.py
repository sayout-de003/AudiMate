# Generated migration for OrganizationInvite model and related enhancements

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add fields to Organization for better indexing
        migrations.AddField(
            model_name='organization',
            name='name_index',
            field=models.CharField(db_index=True, default='', max_length=255),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='organization',
            name='name_index',
        ),
        migrations.AlterField(
            model_name='organization',
            name='name',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='organization',
            name='slug',
            field=models.SlugField(db_index=True, max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='organization',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),

        # Add fields to Membership for better tracking and indexing
        migrations.AddField(
            model_name='membership',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='membership',
            name='user',
            field=models.ForeignKey(
                db_index=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='memberships',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(
                db_index=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='members',
                to='organizations.organization'
            ),
        ),
        migrations.AlterField(
            model_name='membership',
            name='joined_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        
        # Create OrganizationInvite model
        migrations.CreateModel(
            name='OrganizationInvite',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('role', models.CharField(
                    choices=[('ADMIN', 'Admin'), ('MEMBER', 'Member'), ('VIEWER', 'Viewer')],
                    default='MEMBER',
                    max_length=20
                )),
                ('token', models.CharField(editable=False, max_length=64, unique=True, db_index=True)),
                ('status', models.CharField(
                    choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('EXPIRED', 'Expired')],
                    db_index=True,
                    default='PENDING',
                    max_length=20
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('accepted_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='accepted_invites',
                    to=settings.AUTH_USER_MODEL
                )),
                ('invited_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sent_invites',
                    to=settings.AUTH_USER_MODEL
                )),
                ('organization', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invites',
                    to='organizations.organization'
                )),
            ],
            options={
                'verbose_name': 'Organization Invite',
                'verbose_name_plural': 'Organization Invites',
                'ordering': ['-created_at'],
            },
        ),

        # Add constraints and indexes
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['slug'], name='organizations_organization_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['owner'], name='organizations_organization_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='membership',
            index=models.Index(fields=['user', 'organization'], name='organizations_membership_user_org_idx'),
        ),
        migrations.AddIndex(
            model_name='membership',
            index=models.Index(fields=['organization', 'role'], name='organizations_membership_org_role_idx'),
        ),
        migrations.AddIndex(
            model_name='organizationinvite',
            index=models.Index(fields=['organization', 'email'], name='organizations_invite_org_email_idx'),
        ),
        migrations.AddIndex(
            model_name='organizationinvite',
            index=models.Index(fields=['status'], name='organizations_invite_status_idx'),
        ),
        migrations.AddIndex(
            model_name='organizationinvite',
            index=models.Index(fields=['expires_at'], name='organizations_invite_expires_idx'),
        ),

        # Add unique constraints
        migrations.AddConstraint(
            model_name='organizationinvite',
            constraint=models.UniqueConstraint(
                fields=['organization', 'email'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_invite_per_email'
            ),
        ),
    ]
