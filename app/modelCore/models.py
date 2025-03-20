from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.
import pathlib
import uuid
import datetime
import random
from django.utils import timezone

def image_upload_handler(instance,filename):
    fpath = pathlib.Path(filename)
    new_fname = str(uuid.uuid1()) #uuid1 -> uuid + timestamp
    return f'images/{new_fname}{fpath.suffix}'

@property
def get_photo_url(self):
    if self.photo and hasattr(self.photo, 'url'):
        return self.photo.url
    else:
        return "/static/web/assets/img/generic/2.jpg"

def generate_default_username():
    return str(uuid.uuid4())

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        """Creates and saves a new user"""
        if not email:
            raise ValueError('使用者必須有電子郵件')
        
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )
        
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password, **extra_fields):
        """Creates and saves a new super user"""
        user = self.create_user(email=email, password=password, **extra_fields)

        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    name = models.CharField(max_length=255, blank=True)
    objects = UserManager()
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    def get_full_name(self):
        """獲取用戶全名"""
        return f"{self.first_name} {self.last_name}".strip() or self.name

    def get_short_name(self):
        """獲取用戶短名"""
        return self.first_name or self.name
    
    MALE = 'M'
    FEMALE = 'F'
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default=MALE)

    address = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to=image_upload_handler, blank=True, null=True)

    line_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    apple_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    is_fcm_notify = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        unique_together = []

    def __str__(self):
        return self.email

class Destination(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    image = models.ImageField(upload_to=image_upload_handler, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # @classmethod
    # def create_from_entity(cls, entity):
    #     """
    #     從 API 返回的 entity 數據創建或更新 Destination 實例
        
    #     Args:
    #         entity (dict): API 返回的目的地數據
            
    #     Returns:
    #         Destination: 創建或更新的 Destination 實例
    #     """
    #     import uuid
        
    #     # 從 entity 中提取必要的數據
    #     destination_id = entity.get('id')
    #     if not destination_id:
    #         raise ValueError("目的地 ID 不能為空")
        
    #     # 創建或更新 Destination 實例
    #     destination, created = cls.objects.update_or_create(
    #         id=uuid.UUID(destination_id),
    #         defaults={
    #             'name': entity.get('name', ''),
    #             'slug': entity.get('slug', ''),
    #         }
    #     )
        
    #     return destination

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Park(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='parks'
    )
    image = models.ImageField(upload_to=image_upload_handler, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # @classmethod
    # def create_from_entity(cls, entity, destination=None):
    #     """
    #     從 API 返回的 entity 數據創建或更新 Park 實例
        
    #     Args:
    #         entity (dict): API 返回的公園數據
    #         destination (Destination, optional): 對應的目的地實例，如果為 None 則從 entity 中獲取
            
    #     Returns:
    #         Park: 創建或更新的 Park 實例
    #     """
    #     import uuid
        
    #     # 從 entity 中提取必要的數據
    #     park_id = entity.get('id')
    #     if not park_id:
    #         raise ValueError("公園 ID 不能為空")
        
    #     # 如果沒有提供 destination 實例，則嘗試從 entity 中獲取目的地信息
    #     if destination is None and 'destination' in entity:
    #         destination_data = entity.get('destination')
    #         destination = Destination.create_from_entity(destination_data)
        
    #     if destination is None:
    #         raise ValueError("缺少目的地信息")
        
    #     # 創建或更新 Park 實例
    #     park, created = cls.objects.update_or_create(
    #         id=uuid.UUID(park_id),
    #         defaults={
    #             'name': entity.get('name', ''),
    #             'destination': destination,
    #         }
    #     )
        
    #     return park

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Attraction(models.Model):
    """
    吸引設施模型
    
    代表主題公園內的遊樂設施、表演或體驗。
    例如：加勒比海盜、小小世界等。
    """
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        related_name='attractions'
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=image_upload_handler, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 新增字段
    timezone = models.CharField(max_length=100, blank=True, null=True, help_text='時區信息')
    entity_type = models.CharField(max_length=50, blank=True, null=True, help_text='實體類型')
    destination_id = models.UUIDField(blank=True, null=True, help_text='關聯的目的地ID')
    attraction_type = models.CharField(max_length=50, blank=True, null=True, help_text='吸引設施類型')
    external_id = models.CharField(max_length=100, blank=True, null=True, help_text='外部系統的ID')
    parent_id = models.UUIDField(blank=True, null=True, help_text='父實體ID')
    
    # 位置相關欄位
    longitude = models.FloatField(blank=True, null=True, help_text='經度')
    latitude = models.FloatField(blank=True, null=True, help_text='緯度')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class GuestReview(models.Model):
    """
    遊客評論模型
    
    用戶對遊樂設施的評價和評論
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attraction = models.ForeignKey(
        Attraction,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text='關聯的遊樂設施'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text='發表評論的用戶'
    )
    rating = models.PositiveSmallIntegerField(
        help_text='評分，1-5分',
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    content = models.TextField(help_text='評論內容')
    visit_date = models.DateField(blank=True, null=True, help_text='遊玩日期')
    is_published = models.BooleanField(default=True, help_text='是否發布')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} - {self.attraction.name} - {self.rating}分"

    class Meta:
        ordering = ['-created_at']
        verbose_name = '遊客評論'
        verbose_name_plural = '遊客評論'
        unique_together = ['user', 'attraction', 'visit_date']

# 票券和訂單相關模型
class TicketType(models.Model):
    """票券類型模型"""
    name = models.CharField(max_length=100, help_text='票券類型名稱')
    description = models.TextField(blank=True, help_text='票券類型說明')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text='票券價格')
    image = models.ImageField(upload_to=image_upload_handler, blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text='是否可購買')
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        related_name='ticket_types',
        help_text='關聯的公園'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.park.name} - {self.name} (${self.price})"
    
    class Meta:
        ordering = ['park', 'price']
        verbose_name = '票券類型'
        verbose_name_plural = '票券類型'

class Order(models.Model):
    """訂單模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='orders',
        help_text='下訂單的用戶'
    )
    order_number = models.CharField(max_length=20, unique=True, help_text='訂單編號')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='訂單總金額')
    
    PENDING = 'pending'
    PAID = 'paid'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (PENDING, '待付款'),
        (PAID, '已付款'),
        (CANCELLED, '已取消'),
        (REFUNDED, '已退款'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text='訂單狀態'
    )
    
    payment_method = models.CharField(max_length=50, blank=True, help_text='付款方式')
    visit_date = models.DateField(help_text='預計遊玩日期')
    notes = models.TextField(blank=True, help_text='訂單備註')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"訂單 {self.order_number} - {self.user.email} - {self.status}"
    
    def save(self, *args, **kwargs):
        # 生成訂單編號
        if not self.order_number:
            today = datetime.date.today().strftime('%Y%m%d')
            random_str = ''.join(random.choices('0123456789', k=8))
            self.order_number = f"ORD{today}{random_str}"
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """計算訂單總金額"""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save()
        return total
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '訂單'
        verbose_name_plural = '訂單'

class OrderItem(models.Model):
    """訂單項目模型"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='關聯的訂單'
    )
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.PROTECT,
        related_name='order_items',
        help_text='票券類型'
    )
    quantity = models.PositiveIntegerField(default=1, help_text='數量')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text='單價')
    
    @property
    def subtotal(self):
        """計算小計金額"""
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.ticket_type.name} x {self.quantity} @ ${self.unit_price}"
    
    class Meta:
        verbose_name = '訂單項目'
        verbose_name_plural = '訂單項目'

class Ticket(models.Model):
    """票券模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='tickets',
        help_text='關聯的訂單項目'
    )
    ticket_number = models.CharField(max_length=20, unique=True, help_text='票券編號')
    qr_code = models.ImageField(upload_to='tickets/qr_codes/', blank=True, null=True, help_text='QR碼圖片')
    is_used = models.BooleanField(default=False, help_text='是否已使用')
    used_at = models.DateTimeField(blank=True, null=True, help_text='使用時間')
    guest_name = models.CharField(max_length=100, blank=True, help_text='遊客姓名')
    
    def __str__(self):
        return f"票券 {self.ticket_number} - {self.order_item.ticket_type.name}"
    
    def save(self, *args, **kwargs):
        # 生成票券編號
        if not self.ticket_number:
            today = datetime.date.today().strftime('%Y%m%d')
            random_str = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))
            self.ticket_number = f"TIX{today}{random_str}"
            
        # 如果是新建票券且沒有QR碼，則生成QR碼
        if not self.pk and not self.qr_code:
            self.generate_qr_code()
            
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """生成QR碼"""
        # 實際項目中應使用QR碼生成庫，此處僅為示例
        pass
    
    def mark_as_used(self):
        """標記票券為已使用"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['order_item__order__visit_date']
        verbose_name = '票券'
        verbose_name_plural = '票券'

class Cart(models.Model):
    """購物車模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total_price(self):
        return sum(item.get_subtotal() for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.email}"

class CartItem(models.Model):
    """購物車項目模型"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_subtotal(self):
        return self.ticket_type.price * self.quantity

    class Meta:
        unique_together = ('cart', 'ticket_type')

    def __str__(self):
        return f"{self.quantity}x {self.ticket_type.name} in {self.cart}"
