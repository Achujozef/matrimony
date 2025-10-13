from django.conf import settings
from django.db import models
import uuid
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = settings.AUTH_USER_MODEL

# ---------- Shakha ----------
class Shakha(models.Model):
    name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=200, blank=True)  # optional locality
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# ---------- Extend User: Profile ----------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    shakha = models.ForeignKey(Shakha, on_delete=models.SET_NULL, null=True, blank=True, related_name="members")
    # Role flags
    is_shakha_president = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)  # blocked by president/admin
    # community meta
    position = models.CharField(max_length=150, blank=True)  # e.g., "Secretary", "Member"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.shakha or 'NoShakha'}"

# ---------- Matrimonial Profile ----------
class MatrimonialProfile(models.Model):
    GENDER_CHOICES = (('M','Male'), ('F','Female'), ('O','Other'))
    STATUS_CHOICES = (('P','Pending'), ('A','Approved'), ('R','Rejected'), ('B','Blocked'))

    profile_owner = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="matrimonial_profile")
    # Basic details
    full_name = models.CharField(max_length=200)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(18), MaxValueValidator(100)])
    education = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=200, blank=True)
    about = models.TextField(blank=True)
    native_place = models.CharField(max_length=200, blank=True)
    maritial_status = models.CharField(max_length=100, default='Never Married', blank=True)
    father_name = models.CharField(max_length=200, blank=True)
    mother_name = models.CharField(max_length=200, blank=True)
    family_details = models.TextField(blank=True)

    # Privacy / visibility controls
    hide_photos_until_connection = models.BooleanField(default=True)
    hide_phone_until_connection = models.BooleanField(default=True)

    # Shakha & approval
    shakha = models.ForeignKey(Shakha, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    status_message = models.TextField(blank=True)  # president/ admin remarks
    verified_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_profiles")
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # convenience
    def approve(self, verifier_profile):
        self.status = 'A'
        self.verified_by = verifier_profile
        self.verified_at = timezone.now()
        self.status_message = ''
        self.save()

    def reject(self, verifier_profile, message=''):
        self.status = 'R'
        self.verified_by = verifier_profile
        self.verified_at = timezone.now()
        self.status_message = message
        self.save()

    def block(self, by_profile, message=''):
        self.status = 'B'
        self.verified_by = by_profile
        self.status_message = message
        self.save()

    def is_visible_publicly(self):
        return self.status == 'A' and not self.profile_owner.is_blocked

    def __str__(self):
        return f"{self.full_name} ({self.get_gender_display()}) - {self.shakha or 'NoShakha'}"

# ---------- Photos ----------
class MatrimonialPhoto(models.Model):
    matrimonial_profile = models.ForeignKey(MatrimonialProfile, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to='matrimonial/photos/')
    caption = models.CharField(max_length=200, blank=True)
    is_private = models.BooleanField(default=True)  # hidden until connection unless profile owner sets otherwise
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo {self.id} for {self.matrimonial_profile.full_name}"

# ---------- Premium subscription & manual payment ----------
class PremiumSubscription(models.Model):
    STATUS = (('P','Pending'), ('A','Active'), ('R','Rejected'), ('E','Expired'))

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="premium_subscriptions")
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS, default='P')
    created_at = models.DateTimeField(auto_now_add=True)
    activated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="activated_subscriptions")
    activated_at = models.DateTimeField(null=True, blank=True)

    # manual payment evidence
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_screenshot = models.ImageField(upload_to='payments/screenshots/', null=True, blank=True)
    payment_message = models.TextField(blank=True)  # optional user note about transaction (e.g., UPI txn id)

    def activate(self, by_profile, days=30):
        self.status = 'A'
        self.start_date = timezone.now()
        self.end_date = self.start_date + timezone.timedelta(days=days)
        self.activated_by = by_profile
        self.activated_at = timezone.now()
        self.save()

    def mark_rejected(self, by_profile, reason=''):
        self.status = 'R'
        self.payment_message = reason
        self.save()

    def is_active(self):
        if self.status != 'A':
            return False
        return self.end_date and self.end_date > timezone.now()

    def __str__(self):
        return f"Premium {self.profile.user.username} - {self.get_status_display()}"

# ---------- Interest (User shows interest in a profile) ----------
class Interest(models.Model):
    # Who showed interest and which matrimonial profile they targeted
    from_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="sent_interests")
    to_profile = models.ForeignKey(MatrimonialProfile, on_delete=models.CASCADE, related_name="received_interests")
    message = models.TextField(blank=True)  # short message from sender
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(null=True, blank=True)  # None: pending, True: accepted, False: declined
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_profile', 'to_profile')  # prevents duplicate interests

    def accept(self):
        self.accepted = True
        self.accepted_at = timezone.now()
        self.save()

    def decline(self):
        self.accepted = False
        self.save()

    def __str__(self):
        return f"Interest from {self.from_profile.user.username} -> {self.to_profile.full_name}"

# ---------- Manual Payment log for admin auditing ----------
class ManualPaymentLog(models.Model):
    subscription = models.ForeignKey(PremiumSubscription, on_delete=models.CASCADE, related_name='payment_logs')
    processed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"PaymentLog for {self.subscription.profile.user.username} at {self.processed_at}"



class PasswordResetOTP(models.Model):
    """
    Temporary OTP store for password resets.
    """
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)  # store OTP as string
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)   # verification attempts
    used = models.BooleanField(default=False)                # whether OTP was used to reset
    resend_count = models.PositiveSmallIntegerField(default=0)
    token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['email', 'code']),
            models.Index(fields=['token']),
        ]

    def is_expired(self, minutes=5):
        return timezone.now() > (self.created_at + timezone.timedelta(minutes=minutes))

    def __str__(self):
        return f"OTP {self.code} for {self.email} (used={self.used})"