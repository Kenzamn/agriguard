import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

WILAYA_CHOICES = [
    ('adrar', 'Adrar'), ('chlef', 'Chlef'), ('laghouat', 'Laghouat'),
    ('oum_el_bouaghi', 'Oum El Bouaghi'), ('batna', 'Batna'), ('bejaia', 'Béjaïa'),
    ('biskra', 'Biskra'), ('bechar', 'Béchar'), ('blida', 'Blida'),
    ('bouira', 'Bouira'), ('tamanrasset', 'Tamanrasset'), ('tebessa', 'Tébessa'),
    ('tlemcen', 'Tlemcen'), ('tiaret', 'Tiaret'), ('tizi_ouzou', 'Tizi Ouzou'),
    ('alger', 'Alger'), ('djelfa', 'Djelfa'), ('jijel', 'Jijel'),
    ('setif', 'Sétif'), ('saida', 'Saïda'), ('skikda', 'Skikda'),
    ('sidi_bel_abbes', 'Sidi Bel Abbès'), ('annaba', 'Annaba'),
    ('guelma', 'Guelma'), ('constantine', 'Constantine'), ('medea', 'Médéa'),
    ('mostaganem', 'Mostaganem'), ('msila', 'M\'Sila'), ('mascara', 'Mascara'),
    ('ouargla', 'Ouargla'), ('oran', 'Oran'), ('el_bayadh', 'El Bayadh'),
    ('illizi', 'Illizi'), ('bordj_bou_arreridj', 'Bordj Bou Arréridj'),
    ('boumerdes', 'Boumerdès'), ('el_tarf', 'El Tarf'), ('tindouf', 'Tindouf'),
    ('tissemsilt', 'Tissemsilt'), ('el_oued', 'El Oued'), ('khenchela', 'Khenchela'),
    ('souk_ahras', 'Souk Ahras'), ('tipaza', 'Tipaza'), ('mila', 'Mila'),
    ('ain_defla', 'Aïn Defla'), ('naama', 'Naâma'), ('ain_temouchent', 'Aïn Témouchent'),
    ('ghardaia', 'Ghardaïa'), ('relizane', 'Relizane'),
]

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [('farmer', 'Farmer'), ('admin', 'Admin')]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name  = models.CharField(max_length=150)
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default='farmer')
    wilaya     = models.CharField(max_length=50, choices=WILAYA_CHOICES)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'wilaya']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"