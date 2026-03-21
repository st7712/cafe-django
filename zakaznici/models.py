from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid 
import secrets

class Drink(models.Model):
    name = models.CharField(max_length=100, verbose_name="Název nápoje")
    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Cena (Kč)")
    
    def __str__(self):
        return f"{self.name} ({self.price} Kč)"
    
class DrinkType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Název typu nápoje")
    drink = models.ForeignKey(Drink, on_delete=models.CASCADE, related_name='types', verbose_name="Nápoj")
    
    def __str__(self):
        return f"{self.drink.name} - {self.name}"

class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="UUID stolu")
    number = models.IntegerField(unique=True, verbose_name="Číslo stolu")
    seats = models.IntegerField(verbose_name="Počet míst")
    
    def __str__(self):
        return f"Stůl {self.number} ({self.seats} míst)"

class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'NEW', 'Nová'
        ACCEPTED = 'ACCEPTED', 'Přijatá'
        REJECTED = 'REJECTED', 'Odmítnutá'
        FINISHED = 'FINISHED', 'Dokončená'
        MISSED = 'MISSED', 'Propáslá (10m)'
        MISSED_DEADLINE = 'MISSED_DEADLINE', 'Nestihnutá (15m)'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="UUID objednávky")
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders', verbose_name="Stůl")
    drink = models.ForeignKey(Drink, on_delete=models.CASCADE, verbose_name="Nápoj")
    drink_type = models.ForeignKey(DrinkType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Typ nápoje")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Stav objednávky"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Datum a čas vytvoření")
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Datum a čas přijetí")
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        type_str = f" ({self.drink_type.name})" if self.drink_type else ""
        return f"Stůl {self.table.number}: {self.drink.name}{type_str} - {self.status}"
    
    def check_time_limits(self):
        """Kontrola času a případná aktualizace stavu objednávky"""
        now = timezone.now()
        is_changed = False

        # Propáslá, pokud je NOVÁ a uběhlo 10 minut od vytvoření
        if self.status == self.Status.NEW:
            if now > self.created_at + timedelta(minutes=10):
                self.status = self.Status.MISSED
                is_changed = True

        # Nestihnutá, pokud je PŘIJATÁ a uběhlo 15 minut od přijetí
        elif self.status == self.Status.ACCEPTED and self.accepted_at:
            if now > self.accepted_at + timedelta(minutes=15):
                self.status = self.Status.MISSED_DEADLINE
                is_changed = True
            
        if is_changed:
            self.save()
            
class StaffUser(models.Model):
    username = models.CharField(max_length=150, unique=True, verbose_name="Uživatelské jméno")
    password = models.CharField(max_length=128, verbose_name="Heslo (hash)")
    token = models.CharField(max_length=64, unique=True, blank=True, verbose_name="API token")

    def save(self, *args, **kwargs):
        # Pokud token neexistuje, vygenerujeme nový
        if not self.token:
            self.token = secrets.token_hex(32) 
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username