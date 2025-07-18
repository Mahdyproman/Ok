import os
from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import models
from django.contrib.auth.models import User
from django import forms
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import admin
from django.urls import path
from django.utils import timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
settings.configure(
    DEBUG=True,
    SECRET_KEY='your-secret-key',
    ROOT_URLCONF=__name__,
    ALLOWED_HOSTS=['*'],
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ],
    INSTALLED_APPS=[
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        '__main__',
    ],
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR],
        'APP_DIRS': True,
    }],
    STATIC_URL='/static/',
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    },
    TIME_ZONE='Asia/Amman',
    LANGUAGE_CODE='ar',
    USE_I18N=True,
    USE_TZ=True,
)

class InvestmentPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    annual_rate = models.FloatField()
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="مدة الخطة بالشهور")
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name

class Transaction(models.Model):
    TYPES = (
        ('deposit', 'إيداع'),
        ('withdrawal', 'سحب'),
    )
    METHODS = (
        ('bank', 'تحويل بنكي'),
        ('paypal', 'PayPal'),
        ('qrcode', 'QR Code'),
        ('cash', 'نقدي'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHODS)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='pending')
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount}"

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.CASCADE)
    invested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    subscribed_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

class Transfer(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transfers')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_transfers')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='completed')
    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.amount}"

class RegisterForm(forms.Form):
    username = forms.CharField(label='اسم المستخدم')
    password = forms.CharField(widget=forms.PasswordInput, label='كلمة المرور')
    email = forms.EmailField(label='البريد الإلكتروني')

class LoginForm(forms.Form):
    username = forms.CharField(label='اسم المستخدم')
    password = forms.CharField(widget=forms.PasswordInput, label='كلمة المرور')

class TransactionForm(forms.Form):
    transaction_type = forms.ChoiceField(choices=Transaction.TYPES, label='النوع')
    amount = forms.DecimalField(label='القيمة (بالدينار الأردني)', min_value=1)
    method = forms.ChoiceField(choices=Transaction.METHODS, label='طريقة الدفع')

class SubscriptionForm(forms.Form):
    plan_id = forms.IntegerField(widget=forms.HiddenInput)
    invested_amount = forms.DecimalField(label='قيمة الاستثمار (بالدينار الأردني)', min_value=1)

class TransferForm(forms.Form):
    receiver_username = forms.CharField(label='اسم المستخدم المستقبل')
    amount = forms.DecimalField(label='المبلغ', min_value=1)

from django.template import engines

def render_template(template_string, context):
    django_engine = engines['django']
    template = django_engine.from_string(template_string)
    return template.render(context)

def get_wallet_balance(user):
    deposits = Transaction.objects.filter(user=user, transaction_type='deposit').aggregate(models.Sum('amount'))['amount__sum'] or 0
    withdrawals = Transaction.objects.filter(user=user, transaction_type='withdrawal').aggregate(models.Sum('amount'))['amount__sum'] or 0
    invested = Subscription.objects.filter(user=user).aggregate(models.Sum('invested_amount'))['invested_amount__sum'] or 0
    sent = Transfer.objects.filter(sender=user).aggregate(models.Sum('amount'))['amount__sum'] or 0
    received = Transfer.objects.filter(receiver=user).aggregate(models.Sum('amount'))['amount__sum'] or 0
    return deposits - withdrawals - invested - (sent or 0) + (received or 0)

TEMPLATE_INDEX = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>استثمار الدينار الأردني</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl" class="bg-light">
<div class="container py-5">
    <h1 class="mb-4">منصة الاستثمار الأردنية والمحفظة الإلكترونية</h1>
    <a href="/register/" class="btn btn-success">تسجيل جديد</a>
    <a href="/login/" class="btn btn-primary">تسجيل دخول</a>
    <hr>
    <h2>خطط الاستثمار المميزة</h2>
    <div class="row">
        {% for plan in plans %}
        <div class="col-md-4">
            <div class="card mb-3 shadow">
                <div class="card-body">
                    <h5 class="card-title">{{ plan.name }}</h5>
                    <p>{{ plan.description }}</p>
                    <p>نسبة الربح السنوية: <b>{{ plan.annual_rate }}%</b></p>
                    <p>الحد الأدنى: <b>{{ plan.min_amount }} دينار</b></p>
                    <p>المدة: <b>{{ plan.duration }} شهر</b></p>
                    <a href="/subscribe/{{ plan.id }}/" class="btn btn-outline-success">اشترك الآن</a>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
</body>
</html>
"""

TEMPLATE_REGISTER = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تسجيل مستخدم جديد</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl">
<div class="container py-5">
    <h1>تسجيل مستخدم جديد</h1>
    <form method="POST">{% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-success">تسجيل</button>
        <a href="/login/" class="btn btn-link">لدي حساب بالفعل</a>
    </form>
</div>
</body>
</html>
"""

TEMPLATE_LOGIN = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تسجيل الدخول</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl">
<div class="container py-5">
    <h1>تسجيل الدخول</h1>
    <form method="POST">{% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-primary">دخول</button>
        <a href="/register/" class="btn btn-link">حساب جديد</a>
    </form>
</div>
</body>
</html>
"""

TEMPLATE_DASHBOARD = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>لوحة المستخدم</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl">
<div class="container py-5">
    <h1>لوحة التحكم</h1>
    <a href="/logout/" class="btn btn-danger mb-3">تسجيل خروج</a>
    <hr>
    <h2>رصيد المحفظة الإلكترونية</h2>
    <div class="alert alert-info">الرصيد الحالي: <b>{{ wallet_balance }} دينار أردني</b></div>
    <a href="/transfer/" class="btn btn-outline-primary mb-3">تحويل رصيد لمستخدم آخر</a>
    <h2>استثماراتي</h2>
    <table class="table table-bordered">
        <tr>
            <th>الخطة</th><th>المبلغ المستثمر</th><th>تاريخ الاشتراك</th>
        </tr>
        {% for sub in subs %}
        <tr>
            <td>{{ sub.plan.name }}</td>
            <td>{{ sub.invested_amount }} دينار</td>
            <td>{{ sub.subscribed_at|date:"Y-m-d" }}</td>
        </tr>
        {% endfor %}
    </table>
    <h2>عمليات السحب والإيداع</h2>
    <table class="table table-bordered">
        <tr>
            <th>النوع</th><th>القيمة</th><th>الطريقة</th><th>التاريخ</th><th>الحالة</th>
        </tr>
        {% for t in trans %}
        <tr>
            <td>{{ t.get_transaction_type_display }}</td>
            <td>{{ t.amount }} دينار</td>
            <td>{{ t.get_method_display }}</td>
            <td>{{ t.created_at|date:"Y-m-d" }}</td>
            <td>{{ t.status }}</td>
        </tr>
        {% endfor %}
    </table>
    <a href="/transaction/" class="btn btn-warning">طلب سحب/إيداع</a>
    <hr>
    <h2>سجل التحويلات المالية</h2>
    <table class="table table-bordered">
        <tr>
            <th>مرسل</th><th>مستقبل</th><th>المبلغ</th><th>التاريخ</th><th>الحالة</th>
        </tr>
        {% for tr in sent_transfers %}
        <tr>
            <td>{{ tr.sender.username }}</td>
            <td>{{ tr.receiver.username }}</td>
            <td>{{ tr.amount }} دينار</td>
            <td>{{ tr.timestamp|date:"Y-m-d H:i" }}</td>
            <td>{{ tr.status }}</td>
        </tr>
        {% endfor %}
        {% for tr in received_transfers %}
        <tr>
            <td>{{ tr.sender.username }}</td>
            <td>{{ tr.receiver.username }}</td>
            <td>{{ tr.amount }} دينار</td>
            <td>{{ tr.timestamp|date:"Y-m-d H:i" }}</td>
            <td>{{ tr.status }}</td>
        </tr>
        {% endfor %}
    </table>
    <hr>
    <h2>الخطط المتاحة</h2>
    <div class="row">
        {% for plan in plans %}
        <div class="col-md-4">
            <div class="card mb-3 shadow">
                <div class="card-body">
                    <h5 class="card-title">{{ plan.name }}</h5>
                    <p>{{ plan.description }}</p>
                    <p>نسبة الربح السنوية: <b>{{ plan.annual_rate }}%</b></p>
                    <p>الحد الأدنى: <b>{{ plan.min_amount }} دينار</b></p>
                    <p>المدة: <b>{{ plan.duration }} شهر</b></p>
                    <a href="/subscribe/{{ plan.id }}/" class="btn btn-outline-success">اشترك الآن</a>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
</body>
</html>
"""

TEMPLATE_SUBSCRIBE = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>الاشتراك في الخطة</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl">
<div class="container py-5">
    <h1>الاشتراك في خطة: {{ plan.name }}</h1>
    <form method="POST">{% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-success">اشترك</button>
        <a href="/dashboard/" class="btn btn-link">عودة</a>
    </form>
</div>
</body>
</html>
"""

TEMPLATE_TRANSACTION = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>طلب سحب أو إيداع</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl">
<div class="container py-5">
    <h1>طلب سحب أو إيداع</h1>
    <form method="POST">{% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-warning">إرسال الطلب</button>
        <a href="/dashboard/" class="btn btn-link">عودة</a>
    </form>
</div>
</body>
</html>
"""

TEMPLATE_TRANSFER = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تحويل رصيد لمستخدم آخر</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">
</head>
<body dir="rtl">
<div class="container py-5">
    <h1>تحويل رصيد لمستخدم آخر</h1>
    <form method="POST">{% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-primary">تحويل</button>
        <a href="/dashboard/" class="btn btn-link">عودة</a>
    </form>
    {% if error %}
    <div class="alert alert-danger mt-3">{{ error }}</div>
    {% endif %}
    {% if success %}
    <div class="alert alert-success mt-3">{{ success }}</div>
    {% endif %}
</div>
</body>
</html>
"""

def index(request):
    plans = InvestmentPlan.objects.filter(is_active=True)
    html = render_template(TEMPLATE_INDEX, {'plans': plans})
    return HttpResponse(html)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                email=form.cleaned_data['email'])
            return redirect('login')
    else:
        form = RegisterForm()
    html = render_template(TEMPLATE_REGISTER, {'form': form})
    return HttpResponse(html)

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'])
            if user:
                login(request, user)
                return redirect('dashboard')
    else:
        form = LoginForm()
    html = render_template(TEMPLATE_LOGIN, {'form': form})
    return HttpResponse(html)

def logout_view(request):
    logout(request)
    return redirect('index')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    subs = Subscription.objects.filter(user=request.user)
    trans = Transaction.objects.filter(user=request.user)
    plans = InvestmentPlan.objects.filter(is_active=True)
    wallet_balance = get_wallet_balance(request.user)
    sent_transfers = Transfer.objects.filter(sender=request.user)
    received_transfers = Transfer.objects.filter(receiver=request.user)
    html = render_template(TEMPLATE_DASHBOARD, {
        'subs': subs, 'trans': trans, 'plans': plans,
        'wallet_balance': wallet_balance,
        'sent_transfers': sent_transfers,
        'received_transfers': received_transfers,
    })
    return HttpResponse(html)

def subscribe(request, plan_id):
    if not request.user.is_authenticated:
        return redirect('login')
    plan = InvestmentPlan.objects.get(id=plan_id)
    wallet_balance = get_wallet_balance(request.user)
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['invested_amount']
            if amount > wallet_balance:
                error = "رصيد المحفظة غير كافٍ!"
                html = render_template(TEMPLATE_SUBSCRIBE, {'form': form, 'plan': plan, 'error': error})
                return HttpResponse(html)
            Subscription.objects.create(
                user=request.user,
                plan=plan,
                invested_amount=amount)
            return redirect('dashboard')
    else:
        form = SubscriptionForm(initial={'plan_id': plan.id})
    html = render_template(TEMPLATE_SUBSCRIBE, {'form': form, 'plan': plan})
    return HttpResponse(html)

def transaction(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            Transaction.objects.create(
                user=request.user,
                transaction_type=form.cleaned_data['transaction_type'],
                amount=form.cleaned_data['amount'],
                method=form.cleaned_data['method'])
            return redirect('dashboard')
    else:
        form = TransactionForm()
    html = render_template(TEMPLATE_TRANSACTION, {'form': form})
    return HttpResponse(html)

def transfer_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    error = ''
    success = ''
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            receiver_username = form.cleaned_data['receiver_username']
            amount = form.cleaned_data['amount']
            receiver = User.objects.filter(username=receiver_username).first()
            balance = get_wallet_balance(request.user)
            if not receiver:
                error = "المستخدم المستقبل غير موجود."
            elif receiver == request.user:
                error = "لا يمكنك تحويل رصيد لنفسك."
            elif amount > balance:
                error = "رصيدك لا يكفي لإتمام التحويل."
            else:
                Transfer.objects.create(sender=request.user, receiver=receiver, amount=amount)
                success = f"تم تحويل {amount} دينار إلى المستخدم {receiver.username} بنجاح."
                form = TransferForm()
    else:
        form = TransferForm()
    html = render_template(TEMPLATE_TRANSFER, {'form': form, 'error': error, 'success': success})
    return HttpResponse(html)

class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'annual_rate', 'min_amount', 'duration', 'is_active']

class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'method', 'created_at', 'status']

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'invested_amount', 'subscribed_at']

class TransferAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'amount', 'timestamp', 'status']

admin.site.register(InvestmentPlan, InvestmentPlanAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Transfer, TransferAdmin)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('subscribe/<int:plan_id>/', subscribe, name='subscribe'),
    path('transaction/', transaction, name='transaction'),
    path('transfer/', transfer_view, name='transfer'),
]

def create_default_superuser():
    from django.contrib.auth.models import User
    if not User.objects.filter(username='herojo').exists():
        User.objects.create_superuser('herojo', 'admin@example.com', 'Herojo@282')
try:
    import django
    django.setup()
    create_default_superuser()
except Exception:
    pass

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '__main__')
    execute_from_command_line()
