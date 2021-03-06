# Generated by Django 3.1.6 on 2021-02-19 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mlmtools', '0003_auto_20210219_0836'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketernode',
            name='can_have_children',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='marketernode',
            name='parent_cut',
            field=models.DecimalField(decimal_places=2, default=50.0, help_text='How much to sent up the tree', max_digits=5),
        ),
        migrations.AddField(
            model_name='marketernode',
            name='split_type',
            field=models.CharField(choices=[('fixed', 'fixed'), ('tree split', 'treesplit')], default='fixed', help_text='How to split, fixed amount (1 level), or tree split (recursively sent up the tree)', max_length=16),
        ),
    ]
