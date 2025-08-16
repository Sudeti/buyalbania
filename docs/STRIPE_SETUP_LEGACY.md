# Stripe Payment Integration Setup

This guide will help you set up Stripe payments for the PropertyAI application.

## Prerequisites

1. A Stripe account (sign up at https://stripe.com)
2. Your Stripe API keys
3. A webhook endpoint URL

## Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

## Setup Steps

### 1. Install Dependencies

The Stripe Python library is already included in `requirements.txt`. Install it with:

```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations

```bash
python manage.py migrate
```

### 3. Set Up Stripe Products and Prices

Run the management command to create subscription plans in both Django and Stripe:

```bash
python manage.py setup_stripe_plans
```

This will:
- Create subscription plans in your Django database
- Create corresponding products and prices in Stripe
- Link the Stripe price IDs to your Django models

### 4. Configure Webhooks

In your Stripe Dashboard:

1. Go to **Developers > Webhooks**
2. Click **Add endpoint**
3. Set the endpoint URL to: `https://yourdomain.com/payments/webhook/stripe/`
4. Select the following events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the webhook signing secret and add it to your `.env` file

### 5. Test the Integration

1. Start your Django development server
2. Go to the services page
3. Click on "Upgrade to Basic" or "Go Premium"
4. Complete the Stripe checkout process
5. Verify that the user's subscription tier is updated

## Available Plans

The system includes three subscription tiers:

### Free Plan
- €0/month
- 1 analysis per month
- Basic features

### Basic Plan
- €19/month
- 10 analyses per month
- Enhanced features including property alerts

### Premium Plan
- €49/month
- Unlimited analyses
- All features including portfolio analytics

## Features

### Payment Processing
- Secure Stripe Checkout for subscription payments
- Automatic subscription management
- Payment history tracking
- Webhook handling for real-time updates

### Subscription Management
- Users can view their current subscription
- Cancel subscriptions (effective at period end)
- Reactivate cancelled subscriptions
- View payment history

### Admin Interface
- Manage subscription plans
- View customer information
- Monitor payments and subscriptions
- Access Stripe customer IDs

## API Endpoints

- `POST /payments/checkout/<plan_id>/` - Create checkout session
- `GET /payments/success/` - Handle successful payments
- `GET /payments/cancel/` - Handle cancelled payments
- `GET /payments/subscription/` - Subscription management
- `POST /payments/webhook/stripe/` - Stripe webhook handler

## Security Considerations

1. **Webhook Verification**: All webhooks are verified using Stripe's signature verification
2. **CSRF Protection**: All payment forms include CSRF protection
3. **Authentication**: All payment endpoints require user authentication
4. **HTTPS**: Ensure your production site uses HTTPS for secure payment processing

## Troubleshooting

### Common Issues

1. **Webhook Failures**: Check that your webhook URL is accessible and the secret is correct
2. **Payment Failures**: Verify your Stripe API keys are correct
3. **Subscription Not Updated**: Check webhook logs for errors

### Testing

Use Stripe's test mode for development:
- Test card numbers: 4242 4242 4242 4242
- Test expiry: Any future date
- Test CVC: Any 3 digits

## Production Deployment

1. Switch to live Stripe keys
2. Update webhook URLs to production domain
3. Ensure HTTPS is enabled
4. Set up proper logging for payment events
5. Monitor webhook delivery in Stripe Dashboard

## Support

For issues with:
- **Stripe Integration**: Check Stripe documentation and logs
- **Django Application**: Check Django logs and admin interface
- **Payment Processing**: Verify webhook configuration and database records
