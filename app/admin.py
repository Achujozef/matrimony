from django.contrib import admin
from .models import Shakha,Profile,MatrimonialProfile,MatrimonialPhoto,PremiumSubscription,Interest,ManualPaymentLog,PasswordResetOTP
# Register your models here.
admin.site.register([Shakha,Profile,MatrimonialProfile,MatrimonialPhoto,PremiumSubscription,Interest,ManualPaymentLog,PasswordResetOTP])