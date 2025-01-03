# Generated by Django 5.1.3 on 2024-11-20 22:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('IMS_production', '0002_alter_stockmovement_movement_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='total_amount',
            field=models.IntegerField(verbose_name='Total Amount'),
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['name', 'created'], name='IMS_product_name_68a588_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['price', 'name'], name='IMS_product_price_26af83_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['quantity'], name='IMS_product_quantit_cd03d9_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['name', 'price', 'quantity'], name='IMS_product_name_334d5b_idx'),
        ),
        migrations.AddIndex(
            model_name='salessummary',
            index=models.Index(fields=['total_sold'], name='IMS_product_total_s_216996_idx'),
        ),
        migrations.AddIndex(
            model_name='salessummary',
            index=models.Index(fields=['total_revenue'], name='IMS_product_total_r_aa84db_idx'),
        ),
    ]
