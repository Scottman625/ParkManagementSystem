# Generated by Django 5.1.7 on 2025-03-20 08:19

import django.db.models.deletion
import modelCore.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("modelCore", "0006_remove_user_country_code_remove_user_full_phone_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "order_number",
                    models.CharField(help_text="訂單編號", max_length=20, unique=True),
                ),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2, help_text="訂單總金額", max_digits=10
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待付款"),
                            ("paid", "已付款"),
                            ("cancelled", "已取消"),
                            ("refunded", "已退款"),
                        ],
                        default="pending",
                        help_text="訂單狀態",
                        max_length=20,
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(blank=True, help_text="付款方式", max_length=50),
                ),
                ("visit_date", models.DateField(help_text="預計遊玩日期")),
                ("notes", models.TextField(blank=True, help_text="訂單備註")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        help_text="下訂單的用戶",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "訂單",
                "verbose_name_plural": "訂單",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1, help_text="數量")),
                (
                    "unit_price",
                    models.DecimalField(
                        decimal_places=2, help_text="單價", max_digits=10
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        help_text="關聯的訂單",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="modelCore.order",
                    ),
                ),
            ],
            options={
                "verbose_name": "訂單項目",
                "verbose_name_plural": "訂單項目",
            },
        ),
        migrations.CreateModel(
            name="Ticket",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "ticket_number",
                    models.CharField(help_text="票券編號", max_length=20, unique=True),
                ),
                (
                    "qr_code",
                    models.ImageField(
                        blank=True,
                        help_text="QR碼圖片",
                        null=True,
                        upload_to="tickets/qr_codes/",
                    ),
                ),
                ("is_used", models.BooleanField(default=False, help_text="是否已使用")),
                (
                    "used_at",
                    models.DateTimeField(blank=True, help_text="使用時間", null=True),
                ),
                (
                    "guest_name",
                    models.CharField(blank=True, help_text="遊客姓名", max_length=100),
                ),
                (
                    "order_item",
                    models.ForeignKey(
                        help_text="關聯的訂單項目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="modelCore.orderitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "票券",
                "verbose_name_plural": "票券",
                "ordering": ["order_item__order__visit_date"],
            },
        ),
        migrations.CreateModel(
            name="TicketType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(help_text="票券類型名稱", max_length=100)),
                ("description", models.TextField(blank=True, help_text="票券類型說明")),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2, help_text="票券價格", max_digits=10
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=modelCore.models.image_upload_handler,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, help_text="是否可購買"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "park",
                    models.ForeignKey(
                        help_text="關聯的公園",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ticket_types",
                        to="modelCore.park",
                    ),
                ),
            ],
            options={
                "verbose_name": "票券類型",
                "verbose_name_plural": "票券類型",
                "ordering": ["park", "price"],
            },
        ),
        migrations.AddField(
            model_name="orderitem",
            name="ticket_type",
            field=models.ForeignKey(
                help_text="票券類型",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="order_items",
                to="modelCore.tickettype",
            ),
        ),
    ]
