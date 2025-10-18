from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views import View
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from .models import MatrimonialProfile, Shakha, Interest, Profile, PremiumSubscription
from django.contrib.auth import get_user_model
import random
import string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage

from .models import *
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from datetime import datetime


User = get_user_model()


# ----------------- Registration View -----------------
class UserRegisterView(View):
    print("UserRegisterView class loaded")
    template_name = 'register.html'

    def get(self, request):
        print("GET request called")
        shakhas = Shakha.objects.all()
        print(f"Shakhas loaded: {[s.name for s in shakhas]}")
        return render(request, self.template_name, {'shakhas': shakhas})

    def post(self, request):
        def is_ajax(req):
            return req.headers.get('x-requested-with') == 'XMLHttpRequest'

        print("POST request called")

        try:
            # ---------- User / Profile fields ----------
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            shakha_id = request.POST.get('shakha')
            print(f"Received email: {email}, shakha_id: {shakha_id!r}")

            # ---------- basic validation ----------
            if not email or not password or not confirm_password:
                print("Validation failed: Missing required fields")
                msg = "Email and password are required."
                if is_ajax(request):
                    return JsonResponse({'success': False, 'error': msg})
                messages.error(request, msg)
                return redirect('register')

            if password != confirm_password:
                print("Validation failed: Passwords do not match")
                msg = "Passwords do not match."
                if is_ajax(request):
                    return JsonResponse({'success': False, 'error': msg})
                messages.error(request, msg)
                return redirect('register')

            # generate username from email (basic)
            username_candidate = email.split('@')[0]
            username = username_candidate
            # ensure username uniqueness by appending number if needed
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_candidate}{counter}"
                counter += 1
            print(f"Using username: {username}")

            # ---------- MatrimonialProfile fields ----------
            full_name = request.POST.get('full_name', '').strip()
            dob_str = request.POST.get('dob', '').strip()
            gender = request.POST.get('gender', '').strip()
            education = request.POST.get('education', '').strip()
            occupation = request.POST.get('occupation', '').strip()
            about = request.POST.get('about', '').strip()
            native_place = request.POST.get('native_place', '').strip()
            marital_status = request.POST.get('marital_status', 'Never Married').strip()
            father_name = request.POST.get('father_name', '').strip()
            mother_name = request.POST.get('mother_name', '').strip()
            family_details = request.POST.get('family_details', '').strip()
            print(f"Matrimonial info received: full_name={full_name!r}, dob={dob_str!r}, gender={gender!r}")

            # parse dob safely
            dob = None
            if dob_str:
                try:
                    # Accepts YYYY-MM-DD from <input type="date">
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                    print(f"Parsed DOB: {dob}")
                except ValueError as e:
                    print(f"Could not parse dob '{dob_str}': {e}")
                    # don't fail; send error
                    msg = "Invalid date of birth format."
                    if is_ajax(request):
                        return JsonResponse({'success': False, 'error': msg})
                    messages.error(request, msg)
                    return redirect('register')

            # resolve shakha if provided
            shakha_instance = None
            if shakha_id:
                try:
                    shakha_instance = Shakha.objects.get(pk=shakha_id)
                    print(f"Resolved shakha: {shakha_instance.name}")
                except Shakha.DoesNotExist:
                    print(f"Shakha id {shakha_id} does not exist")
                    msg = "Selected Shakha not found."
                    if is_ajax(request):
                        return JsonResponse({'success': False, 'error': msg})
                    messages.error(request, msg)
                    return redirect('register')

            with transaction.atomic():
                print("Transaction started")

                # ---------- Create User ----------
                user = User.objects.create_user(username=username, email=email, password=password)
                print(f"User created: {user.username} (id={user.pk})")

                # ---------- Create Profile ----------
                profile = Profile.objects.create(
                    user=user,
                    phone=phone,
                    address=address,
                    shakha=shakha_instance  # use instance
                )
                print(f"Profile created for user: {profile.user.username} (profile id={profile.pk})")

                # ---------- Create Matrimonial Profile ----------
                matrimonial_profile = MatrimonialProfile.objects.create(
                    profile_owner=profile,
                    full_name=full_name,
                    dob=dob,
                    gender=gender,
                    education=education,
                    occupation=occupation,
                    about=about,
                    native_place=native_place,
                    maritial_status=marital_status,
                    father_name=father_name,
                    mother_name=mother_name,
                    family_details=family_details,
                    shakha=shakha_instance,
                    status='P'  # pending approval
                )
                print(f"MatrimonialProfile created: {matrimonial_profile.full_name} (id={matrimonial_profile.pk})")

            print("Transaction committed successfully")

            # successful response
            if is_ajax(request):
                return JsonResponse({'success': True, 'message': "Account created successfully! Waiting for approval."})

            messages.success(request, "Account created successfully! Waiting for Shakha president approval.")
            return redirect('login')

        except IntegrityError as e:
            # likely duplicate username/email
            print(f"IntegrityError: {e}")
            msg = "Email/Username already exists."
            if is_ajax(request):
                return JsonResponse({'success': False, 'error': msg})
            messages.error(request, msg)
            return redirect('register')

        except Exception as e:
            print(f"Exception occurred: {e}", type(e))
            if is_ajax(request):
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f"Something went wrong: {str(e)}")
            return redirect('register')

# ----------------- Login View -----------------
class UserLoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        try:
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            print(f"Login attempt with email={email}")

            if not email or not password:
                messages.error(request, "Both email and password are required.")
                return render(request, self.template_name)

            # Get user by email
            try:
                user_obj = User.objects.get(email=email)
                username = user_obj.username  # authenticate still expects username
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return render(request, self.template_name)

            user = authenticate(request, username=username, password=password)
            if user is not None:
                if hasattr(user, 'profile') and user.profile.is_blocked:
                    messages.error(request, "Your account has been blocked. Contact admin.")
                    return render(request, self.template_name)

                login(request, user)
                messages.success(request, f"Welcome {user.username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password.")
                return render(request, self.template_name)
        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return render(request, self.template_name)


# ----------------- Logout View -----------------
@method_decorator(login_required, name='dispatch')
class UserLogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect('login')



# ---------- Password Reset View ----------
class PasswordResetView(View):
    template_name = 'password_reset.html'

    def get(self, request):
        # Render the page (JS will handle the steps)
        return render(request, self.template_name)

    def post(self, request):
        """
        AJAX-based handler. Expects form-data with 'action' = send_otp | verify_otp | reset_password
        """
        def is_ajax(req):
            return req.headers.get('x-requested-with') == 'XMLHttpRequest'

        action = request.POST.get('action')
        email = request.POST.get('email', '').strip().lower()

        if action == 'send_otp':
            # Validate email and user existence
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required.'})

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # For privacy, you may elect to respond success (but here we warn)
                return JsonResponse({'success': False, 'error': 'No account found for that email.'})

            # simple rate limiting: check last OTP created for this email and resend_count/time
            recent_otps = PasswordResetOTP.objects.filter(email=email, used=False).order_by('-created_at')
            if recent_otps.exists():
                last = recent_otps.first()
                # block immediate resends for 90 seconds
                if timezone.now() < last.created_at + timezone.timedelta(seconds=90):
                    remaining = int(((last.created_at + timezone.timedelta(seconds=90)) - timezone.now()).total_seconds())
                    return JsonResponse({'success': False, 'error': f'Please wait {remaining}s before resending OTP.'})

            # generate 6-digit OTP
            code = ''.join(str(random.randint(0, 9)) for _ in range(6))

            otp = PasswordResetOTP.objects.create(email=email, code=code)

            # send email — requires EMAIL_ settings configured in settings.py
            subject = "Kerala Vishwakarma — Password reset OTP"
            message = (f"Your Kerala Vishwakarma password reset code is: {code}\n\n"
                       "This code will expire in 5 minutes. If you did not request this, ignore this email.")
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            try:
                send_mail(subject, message, from_email, [email], fail_silently=False)
            except Exception as e:
                # In dev, you may not have email configured — return helpful error
                return JsonResponse({'success': False, 'error': f'Failed to send email: {e}'})

            return JsonResponse({'success': True, 'message': 'OTP sent', 'token': str(otp.token)})


        elif action == 'verify_otp':
            # Expect 'token' and six-digit 'code' (or code as a single string)
            token = request.POST.get('token')
            code = request.POST.get('code', '').strip()
            if not token or not code:
                return JsonResponse({'success': False, 'error': 'Token and code are required.'})

            try:
                otp = PasswordResetOTP.objects.get(token=token, used=False)
            except PasswordResetOTP.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid or expired OTP token.'})

            if otp.is_expired(minutes=5):
                return JsonResponse({'success': False, 'error': 'OTP expired. Please request a new one.'})

            # protect brute force
            if otp.attempts >= 5:
                return JsonResponse({'success': False, 'error': 'Too many wrong attempts. Request a new OTP.'})

            if otp.code != code:
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
                remaining = max(0, 5 - otp.attempts)
                return JsonResponse({'success': False, 'error': f'Incorrect OTP. {remaining} attempts left.'})

            # mark verified (we won't mark as used until password reset)
            return JsonResponse({'success': True, 'message': 'OTP verified. You can set a new password now.'})


        elif action == 'reset_password':
            # Expect token, code (to re-verify), new_password, confirm_password
            token = request.POST.get('token')
            code = request.POST.get('code', '').strip()
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()

            if not token or not code or not new_password or not confirm_password:
                return JsonResponse({'success': False, 'error': 'All fields are required.'})

            if new_password != confirm_password:
                return JsonResponse({'success': False, 'error': "Passwords do not match."})

            if len(new_password) < 8:
                return JsonResponse({'success': False, 'error': "Password must be at least 8 characters long."})

            try:
                otp = PasswordResetOTP.objects.get(token=token, used=False)
            except PasswordResetOTP.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid or expired OTP token.'})

            if otp.is_expired(minutes=5):
                return JsonResponse({'success': False, 'error': 'OTP expired. Request a new one.'})

            if otp.code != code:
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
                return JsonResponse({'success': False, 'error': 'OTP does not match.'})

            # All good — reset password for user with this email
            try:
                with transaction.atomic():
                    user = User.objects.get(email=otp.email)
                    user.set_password(new_password)
                    user.save()
                    otp.used = True
                    otp.save(update_fields=['used'])
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User not found.'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Could not reset password: {e}'})

            return JsonResponse({'success': True, 'message': 'Password reset successful. Please login.'})

        else:
            return JsonResponse({'success': False, 'error': 'Invalid action.'})
        



class DashboardView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request):
        filters = {
            'q': request.GET.get('q',''),
            'gender': request.GET.get('gender',''),
            'shakha': request.GET.get('shakha',''),
            'min_age': request.GET.get('min_age',''),
            'max_age': request.GET.get('max_age',''),
            'order': request.GET.get('order','recent'),
        }
        qs = MatrimonialProfile.objects.filter(status='A')

        # show only opposite gender
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and hasattr(profile, 'matrimonial_profile'):
                user_gender = profile.matrimonial_profile.gender
                if user_gender == 'M':
                    qs = qs.filter(gender='F')
                elif user_gender == 'F':
                    qs = qs.filter(gender='M')
                # Optional: if gender is 'O', show all
       
        # filters
        if filters['gender']:
            qs = qs.filter(gender=filters['gender'])
        if filters['shakha']:
            qs = qs.filter(shakha_id=filters['shakha'])
        if filters['q']:
            q = filters['q']
            qs = qs.filter(full_name__icontains=q)

        # ordering
        if filters['order'] == 'age_asc':
            qs = qs.order_by('age')
        elif filters['order'] == 'age_desc':
            qs = qs.order_by('-age')
        else:
            qs = qs.order_by('-created_at')

        paginator = Paginator(qs, 12)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # featured profiles (also opposite gender)
        featured_profiles = MatrimonialProfile.objects.filter(status='A')
        if request.user.is_authenticated and profile and hasattr(profile, 'matrimonial_profile'):
            if user_gender == 'M':
                featured_profiles = featured_profiles.filter(gender='F')
            elif user_gender == 'F':
                featured_profiles = featured_profiles.filter(gender='M')
        featured_profiles = featured_profiles.order_by('-created_at')[:6]

        # user premium status
        is_premium = False
        sent_interests = []
        received_interests = []

        if request.user.is_authenticated:
            if profile:
                active_subs = profile.premium_subscriptions.filter(status='A', end_date__gt=timezone.now())
                is_premium = active_subs.exists()

                # fetch sent interests
                sent_interests = list(profile.sent_interests.values_list('to_profile_id', flat=True))

                # fetch received interests via matrimonial profile
                if hasattr(profile, 'matrimonial_profile'):
                    received_interests = (
                        profile.matrimonial_profile.received_interests
                        .select_related('from_profile')
                        .filter(accepted__isnull=True)   # only show pending
                        .order_by('-created_at')
                    )
        print("is_premium :",is_premium)
        print("received_interests :",received_interests)
        context = {
            'page_obj': page_obj,
            'shakhas': Shakha.objects.all(),
            'filters': filters,
            'stats': {
                'total_profiles': MatrimonialProfile.objects.count(),
                'verified': MatrimonialProfile.objects.filter(status='A').count(),
                'pending': MatrimonialProfile.objects.filter(status='P').count(),
            },
            'featured_profiles': featured_profiles,
            'is_premium': is_premium,
            'sent_interests': sent_interests,
            'received_interests': received_interests,
        }
        return render(request, 'dashboard.html', context)

class ProfileDetailView(DetailView):
    model = MatrimonialProfile
    template_name = "profile_detail.html"
    context_object_name = "profile_obj"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile_obj = ctx['profile_obj']  # MatrimonialProfile
        user = self.request.user if self.request.user.is_authenticated else None

        ctx['is_premium_user'] = False
        ctx['can_view_contact'] = False
        ctx['mutual_interest'] = False
        ctx['viewer_sent_interest'] = None
        ctx['has_expressed'] = False

        if user and hasattr(user, 'profile'):
            viewer_profile = user.profile

            # Premium check
            active_subs = viewer_profile.premium_subscriptions.filter(
                status='A', end_date__gt=timezone.now()
            )
            ctx['is_premium_user'] = active_subs.exists()

            # Viewer -> Profile interest
            sent = Interest.objects.filter(
                from_profile=viewer_profile,    # Profile
                to_profile=profile_obj          # MatrimonialProfile
            ).first()
            ctx['viewer_sent_interest'] = sent
            ctx['has_expressed'] = bool(sent)

            # Owner -> Viewer interest
            viewer_matrimonial = getattr(viewer_profile, 'matrimonial_profile', None)
            owner_to_viewer = None
            if viewer_matrimonial:
                owner_to_viewer = Interest.objects.filter(
                    from_profile=profile_obj.profile_owner,   # Profile
                    to_profile=viewer_matrimonial             # MatrimonialProfile
                ).first()

            # Mutual interest rules
            if (sent and sent.accepted) or (sent and owner_to_viewer) or (owner_to_viewer and owner_to_viewer.accepted):
                ctx['mutual_interest'] = True

            # Contact only if mutual
            if ctx['mutual_interest']:
                ctx['can_view_contact'] = True

        return ctx


@login_required
def express_interest_view(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user_profile = getattr(request.user, "profile", None)
    if not user_profile:
        return JsonResponse({"error": "Complete your profile first."}, status=400)

    # Get sender's matrimonial profile
    user_matrimonial = getattr(user_profile, "matrimonial_profile", None)
    if not user_matrimonial:
        return JsonResponse({"error": "You need to create your matrimonial profile first."}, status=400)

    # Target profile
    to_profile = get_object_or_404(MatrimonialProfile, pk=pk)

    # Prevent self-interest
    if to_profile.profile_owner == user_profile:
        return JsonResponse({"error": "Cannot express interest to your own profile."}, status=400)

    # Check if already sent
    existing = Interest.objects.filter(from_profile=user_profile, to_profile=to_profile).first()
    if existing:
        return JsonResponse({"success": True, "message": "Interest already sent."})

    # Create new interest
    interest = Interest.objects.create(from_profile=user_profile, to_profile=to_profile)

    # Check reverse (if the other user already showed interest)
    reverse = Interest.objects.filter(
        from_profile=to_profile.profile_owner,  # profile of the other user
        to_profile=user_matrimonial             # matrimonial profile of current user
    ).first()

    if reverse:
        interest.accept()
        reverse.accept()
        return JsonResponse({"success": True, "message": "It's a Match! 🎉", "mutual": True})

    return JsonResponse({"success": True, "message": "Interest sent.", "mutual": False})


@login_required
def reveal_contact_view(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user_profile = getattr(request.user, 'profile', None)
    if not user_profile:
        return JsonResponse({"error": "Complete your profile first."}, status=400)

    target_profile = get_object_or_404(MatrimonialProfile, pk=pk)
    if target_profile.profile_owner == user_profile:
        return JsonResponse({"error": "This is your profile."}, status=400)

    # check interest status
    sent = Interest.objects.filter(from_profile=user_profile, to_profile=target_profile).first()
    viewer_matrimonial = getattr(user_profile, 'matrimonial_profile', None)
    owner_to_viewer = None
    if viewer_matrimonial:
        owner_to_viewer = Interest.objects.filter(
            from_profile=target_profile.profile_owner, to_profile=viewer_matrimonial
        ).first()

    allowed = False
    if sent and sent.accepted:
        allowed = True
    elif sent and owner_to_viewer:
        allowed = True
    elif owner_to_viewer and owner_to_viewer.accepted:
        allowed = True

    if not allowed:
        return JsonResponse({"error": "Not allowed. Contact visible only after mutual interest."}, status=403)

    phone = target_profile.profile_owner.phone or ""
    email = getattr(target_profile.profile_owner.user, 'email', '') or ""
    return JsonResponse({"success": True, "phone": phone, "email": email})

from django.views.decorators.http import require_POST
from django.http import JsonResponse

@require_POST
def accept_interest(request, pk):
    try:
        user_matrimonial_profile = request.user.profile.matrimonial_profile
    except MatrimonialProfile.DoesNotExist:
        return JsonResponse({"error": "You do not have a matrimonial profile."}, status=400)

    interest = get_object_or_404(Interest, pk=pk, to_profile=user_matrimonial_profile)
    interest.accept()  # use the model method

    return JsonResponse({"status": "accepted"})


@require_POST
def reject_interest(request, pk):
    try:
        user_matrimonial_profile = request.user.profile.matrimonial_profile
    except MatrimonialProfile.DoesNotExist:
        return JsonResponse({"error": "You do not have a matrimonial profile."}, status=400)

    interest = get_object_or_404(Interest, pk=pk, to_profile=user_matrimonial_profile)
    interest.decline()  # use the model method

    return JsonResponse({"status": "rejected"})


@login_required
def my_profile_view(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)
    matrimonial, _ = MatrimonialProfile.objects.get_or_create(profile_owner=user_profile)

    if request.method == "POST" and request.FILES.getlist("photos"):
        # Handle photo uploads (AJAX or standard)
        for file in request.FILES.getlist("photos"):
            MatrimonialPhoto.objects.create(matrimonial_profile=matrimonial, image=file)
        return JsonResponse({"success": True})

    if request.method == "POST" and request.POST.get("delete_photo_id"):
        # Handle photo deletion
        photo_id = request.POST.get("delete_photo_id")
        MatrimonialPhoto.objects.filter(id=photo_id, matrimonial_profile=matrimonial).delete()
        return JsonResponse({"deleted": True})

    if request.method == "POST" and not request.FILES:
        # Normal profile form submission
        user_profile.phone = request.POST.get("phone", "")
        user_profile.address = request.POST.get("address", "")
        shakha_id = request.POST.get("shakha")
        user_profile.shakha_id = shakha_id if shakha_id else None
        user_profile.position = request.POST.get("position", "")
        user_profile.save()

        matrimonial.full_name = request.POST.get("full_name", "")
        matrimonial.dob = request.POST.get("dob") or None
        matrimonial.gender = request.POST.get("gender", "M")
        matrimonial.age = request.POST.get("age") or None
        matrimonial.education = request.POST.get("education", "")
        matrimonial.occupation = request.POST.get("occupation", "")
        matrimonial.about = request.POST.get("about", "")
        matrimonial.native_place = request.POST.get("native_place", "")
        matrimonial.maritial_status = request.POST.get("maritial_status", "")
        matrimonial.father_name = request.POST.get("father_name", "")
        matrimonial.mother_name = request.POST.get("mother_name", "")
        matrimonial.family_details = request.POST.get("family_details", "")
        matrimonial.hide_photos_until_connection = bool(request.POST.get("hide_photos_until_connection"))
        matrimonial.hide_phone_until_connection = bool(request.POST.get("hide_phone_until_connection"))
        matrimonial.shakha_id = shakha_id if shakha_id else None
        matrimonial.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("my_profile")

    shakhas = Shakha.objects.all()
    photos = matrimonial.photos.all()
    return render(request, "my_profile.html", {
        "profile": user_profile,
        "matrimonial": matrimonial,
        "shakhas": shakhas,
        "photos": photos,
    })


@login_required
def premium_view(request):
    profile = request.user.profile
    existing_sub = PremiumSubscription.objects.filter(profile=profile).order_by('-created_at').first()

    if request.method == "POST":
        payment_screenshot = request.FILES.get("payment_screenshot")
        txn_id = request.POST.get("txn_id")
        note = request.POST.get("note")

        if not existing_sub or existing_sub.status in ['R', 'E']:
            new_sub = PremiumSubscription.objects.create(
                profile=profile,
                payment_amount=499.00,
                payment_screenshot=payment_screenshot,
                payment_message=f"Txn ID: {txn_id}\nNote: {note}",
                status='P',
            )

            # ---- SEND EMAIL TO ADMIN ----
            subject = f"New Premium Payment Request - {profile.user.get_full_name() or profile.user.username}"
            body = f"""
A new premium payment has been submitted.

👤 **User Details**
-------------------------
Name: {profile.user.get_full_name() or profile.user.username}
User ID: {profile.id}
Email: {profile.user.email}
Phone: {getattr(profile, 'phone', 'N/A')}
Shakha: {getattr(profile, 'shakha', 'N/A')}

💳 **Payment Details**
-------------------------
Transaction ID: {txn_id}
Note: {note}
Amount: ₹499.00
Status: Pending (P)

📅 Date: {new_sub.created_at.strftime('%d %b %Y, %I:%M %p')}
"""

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['dineshvarkala@gmail.com'],
            )

            # Attach the payment screenshot if present
            if payment_screenshot:
                email.attach(payment_screenshot.name, payment_screenshot.read(), payment_screenshot.content_type)

            email.send(fail_silently=False)

        return redirect('premium')

    context = {
        "profile": profile,
        "subscription": existing_sub,
        "upi_id": "bthinkx@oksbi",
        "account_details": {
            "name": "Kerala Vishwakarma",
            "bank": "State Bank of India",
            "account": "123456789012",
            "ifsc": "SBIN0001234",
        },
        "benefits": [
            "View full profile details and contact numbers",
            "Send unlimited interests",
            "Priority visibility in explore section",
            "Exclusive premium badge on your profile",
            "Access to advanced search filters"
        ]
    }
    return render(request, "premium_purchase.html", context)

class ShakhaPresidentLoginView(View):
    template_name = "shakha_login.html"

    def get(self, request):
        if request.user.is_authenticated:
            try:
                if request.user.profile.is_shakha_president:
                    return redirect('president_dashboard')
            except Profile.DoesNotExist:
                pass
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                profile = user.profile
                if profile.is_shakha_president:
                    login(request, user)
                    return redirect('president_dashboard')
                else:
                    messages.error(request, "Access Denied. Only Shakha Presidents can log in here.")
                    return redirect('shakha_login')
            except Profile.DoesNotExist:
                messages.error(request, "Profile not found. Please contact admin.")
        else:
            messages.error(request, "Invalid username or password.")
        return render(request, self.template_name)

@login_required
def shakha_logout(request):
    logout(request)
    return redirect('shakha_login')


@login_required
def president_dashboard(request):
    profile = request.user.profile
    if not profile.is_shakha_president:
        messages.error(request, "Access Denied.")
        return redirect('shakha_login')

    # Filters
    gender = request.GET.get('gender', 'all')
    status = request.GET.get('status', 'all')
    search = request.GET.get('search', '')

    profiles = MatrimonialProfile.objects.filter(shakha=profile.shakha)

    if gender in ['M', 'F']:
        profiles = profiles.filter(gender=gender)
    if status in ['P', 'A', 'B']:
        profiles = profiles.filter(status=status)
    if search:
        profiles = profiles.filter(full_name__icontains=search)

    # Add premium info
    for p in profiles:
        p.is_premium = PremiumSubscription.objects.filter(
            profile=p.profile_owner, status='A', end_date__gt=timezone.now()
        ).exists()

    return render(request, 'president_dashboard.html', {
        'profile': profile,
        'profiles': profiles,
        'gender': gender,
        'status': status,
        'search': search,
    })

@login_required
def approve_profile(request, pk):
    president = request.user.profile
    if not president.is_shakha_president:
        messages.error(request, "Access Denied.")
        return redirect('shakha_login')
    
    profile = get_object_or_404(MatrimonialProfile, pk=pk, shakha=president.shakha)
    profile.approve(president)
    messages.success(request, f"{profile.full_name} has been approved.")
    return redirect('president_dashboard')


@login_required
def block_profile(request, pk):
    president = request.user.profile
    if not president.is_shakha_president:
        messages.error(request, "Access Denied.")
        return redirect('shakha_login')
    
    profile = get_object_or_404(MatrimonialProfile, pk=pk, shakha=president.shakha)
    profile.block(president, message="Blocked by president.")
    messages.warning(request, f"{profile.full_name} has been blocked.")
    return redirect('president_dashboard')


@login_required
def view_profile(request, pk):
    president = request.user.profile
    if not president.is_shakha_president:
        messages.error(request, "Access Denied.")
        return redirect('shakha_login')

    matrimonial_profile = get_object_or_404(
        MatrimonialProfile, pk=pk, shakha=president.shakha
    )

    # Get the related base profile (user profile)
    base_profile = matrimonial_profile.profile_owner

    # Check premium status
    matrimonial_profile.is_premium = PremiumSubscription.objects.filter(
        profile=base_profile,
        status='A',
        end_date__gt=timezone.now()
    ).exists()

    photos = matrimonial_profile.photos.all()

    return render(request, 'view_profile.html', {
        'profile': matrimonial_profile,
        'base_profile': base_profile,
        'photos': photos,
    })

@login_required
@require_POST
def update_profile_status(request, pk):
    president = request.user.profile
    if not president.is_shakha_president:
        return JsonResponse({'error': 'Access Denied'}, status=403)

    profile = get_object_or_404(MatrimonialProfile, pk=pk, shakha=president.shakha)
    action = request.POST.get('action')

    if action == 'approve':
        profile.approve(president)
        msg = f"{profile.full_name} has been approved."
    elif action == 'block':
        profile.block(president, message="Blocked by president.")
        msg = f"{profile.full_name} has been blocked."
    elif action == 'pending':
        profile.status = 'P'
        profile.save()
        msg = f"{profile.full_name} set to pending."
    elif action == 'unblock':
        profile.status = 'A'
        profile.save()
        msg = f"{profile.full_name} has been unblocked."
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)

    return JsonResponse({'success': msg})