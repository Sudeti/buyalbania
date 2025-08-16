# PropertyAI - AI-Powered Property Investment Analysis

A Django-based web application that provides AI-powered investment analysis for Albanian real estate properties. Users can analyze properties from Century 21 Albania listings and receive comprehensive investment insights.

## 🚀 Features

### Core Functionality
- **AI Property Analysis**: Get investment scores and recommendations for any Albanian property
- **Market Analytics**: Compare properties with market data and comparable sales
- **PDF Reports**: Receive detailed analysis reports via email
- **Property Alerts**: Get notified of new properties below market value
- **Portfolio Tracking**: Monitor your property analyses and investment decisions

### Subscription Tiers
- **Free**: 1 analysis per month
- **Basic**: 10 analyses per month (€19/month)
- **Premium**: Unlimited analyses (€49/month)

## 🛠️ Technology Stack

- **Backend**: Django 4.x, Python 3.8+
- **Database**: PostgreSQL
- **Payment Processing**: Stripe
- **Task Queue**: Celery with Redis
- **AI/ML**: Custom AI engine for property analysis
- **Frontend**: Bootstrap 5, HTML/CSS/JavaScript
- **Email**: Django email backend
- **Scraping**: Custom scrapers for Century 21 Albania

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Redis (for Celery)
- Stripe account (for payments)
- Virtual environment

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd property_ai
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root:
```bash
# Django Settings
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/property_ai

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com

# Stripe (see Stripe Setup section)
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start Development Server
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to see the application.

## 💳 Stripe Payment Setup

### Demo Mode (No Stripe Required)
The application includes a demo mode that allows testing without Stripe:
- Click any upgrade button
- Get instant access to paid features
- No payment required
- Perfect for development and testing

### Live Stripe Integration

#### 1. Get Stripe API Keys
1. Sign up at [Stripe Dashboard](https://dashboard.stripe.com/)
2. Go to **Developers → API Keys**
3. Copy your **Publishable Key** and **Secret Key**

#### 2. Update Environment Variables
Add to your `.env` file:
```bash
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

#### 3. Create Stripe Products and Prices
```bash
python manage.py setup_stripe_plans
```

#### 4. Configure Webhooks
In Stripe Dashboard → **Developers → Webhooks**:
- Add endpoint: `https://yourdomain.com/payments/webhook/stripe/`
- Select events:
  - `checkout.session.completed`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

#### 5. Test Payments
Use Stripe test cards:
- **Success**: 4242 4242 4242 4242
- **Decline**: 4000 0000 0000 0002
- **Expiry**: Any future date
- **CVC**: Any 3 digits

## 🔧 Development Setup

### Running Celery (Background Tasks)
```bash
# Start Redis (if not running)
redis-server

# Start Celery worker
celery -A config worker -l info

# Start Celery beat (for scheduled tasks)
celery -A config beat -l info
```

### Database Management
```bash
# Create new migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only)
python manage.py flush
```

### Static Files
```bash
python manage.py collectstatic
```

## 📁 Project Structure

```
property_ai/
├── apps/
│   ├── accounts/          # User authentication and profiles
│   ├── core/             # Core models and utilities
│   ├── payments/         # Stripe payment integration
│   └── property_ai/      # Main application logic
├── config/               # Django settings
├── static/               # Static files
├── templates/            # Global templates
├── requirements.txt      # Python dependencies
└── manage.py            # Django management script
```

## 🧪 Testing

### Run Tests
```bash
python manage.py test
```

### Test Payment Flow
1. Create a test user account
2. Go to services page
3. Click "Upgrade to Basic"
4. Complete demo upgrade or Stripe payment
5. Verify subscription activation

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure production database
- [ ] Set up HTTPS/SSL
- [ ] Configure production email settings
- [ ] Set up Stripe live keys
- [ ] Configure webhooks for production domain
- [ ] Set up monitoring and logging
- [ ] Configure Celery for production

### Environment Variables for Production
```bash
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
STRIPE_PUBLISHABLE_KEY=pk_live_your_key
STRIPE_SECRET_KEY=sk_live_your_key
```

## 📊 Admin Interface

Access the Django admin at `/admin/` to manage:
- User accounts and profiles
- Subscription plans and payments
- Property analyses
- System configuration

## 🔍 API Endpoints

### Payment Endpoints
- `POST /payments/checkout/<plan_id>/` - Create checkout session
- `GET /payments/success/` - Handle successful payments
- `GET /payments/cancel/` - Handle cancelled payments
- `GET /payments/subscription/` - Subscription management
- `POST /payments/webhook/stripe/` - Stripe webhook handler

### Property Analysis Endpoints
- `POST /analyze/` - Analyze a property
- `GET /analysis/<id>/` - View analysis results
- `GET /my-analyses/` - User's analysis history

## 🐛 Troubleshooting

### Common Issues

#### Payment Issues
- **Invalid API Key**: Check Stripe keys in environment variables
- **Webhook Failures**: Verify webhook URL and secret
- **Payment Not Processing**: Check Stripe Dashboard logs

#### Database Issues
- **Migration Errors**: Run `python manage.py migrate --fake-initial`
- **Connection Errors**: Verify database URL and credentials

#### Celery Issues
- **Tasks Not Running**: Ensure Redis is running and Celery workers are started
- **Email Not Sending**: Check email configuration in settings

### Getting Help
- Check Django logs: `python manage.py runserver --verbosity=2`
- Check Celery logs: `celery -A config worker -l debug`
- Review Stripe Dashboard for payment issues

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:
- Email: support@propertyai.com
- Documentation: Check the `/docs/` directory
- Issues: Use the GitHub issue tracker

---

**PropertyAI** - Making property investment decisions smarter with AI.
