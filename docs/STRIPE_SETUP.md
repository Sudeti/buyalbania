# Stripe Payment Setup Guide

This guide covers setting up Stripe payments for the PropertyAI application.

## Quick Start (Demo Mode)

The application includes a **demo mode** that works without Stripe configuration:

1. Click any upgrade button on the services page
2. You'll be redirected to a demo upgrade page
3. Click "Activate Plan" to get instant access
4. No payment required - perfect for testing

## Live Stripe Setup

### 1. Get Stripe API Keys

1. Sign up at [Stripe Dashboard](https://dashboard.stripe.com/)
2. Go to **Developers → API Keys**
3. Copy your **Publishable Key** and **Secret Key**

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 3. Create Stripe Products and Prices

Run the management command:

```bash
python manage.py setup_stripe_plans
```

This will:
- Create subscription plans in your Django database
- Create corresponding products and prices in Stripe
- Link Stripe price IDs to your Django models

### 4. Configure Webhooks

In your Stripe Dashboard:

1. Go to **Developers → Webhooks**
2. Click **Add endpoint**
3. Set endpoint URL: `https://yourdomain.com/payments/webhook/stripe/`
4. Select these events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the webhook signing secret to your `.env` file

### 5. Test the Integration

1. Start your Django server
2. Go to the services page
3. Click "Upgrade to Basic" or "Go Premium"
4. Complete the Stripe checkout
5. Verify subscription activation

## Available Plans

| Plan | Price | Analyses | Features |
|------|-------|----------|----------|
| **Free** | €0/month | 1/month | Basic analysis, PDF reports |
| **Basic** | €19/month | 10/month | + Property alerts, Enhanced analytics |
| **Premium** | €49/month | Unlimited | + Portfolio dashboard, Priority support |

## Testing

### Test Cards

Use these Stripe test cards:

- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **Expiry**: Any future date
- **CVC**: Any 3 digits

### Test Scenarios

1. **Successful Payment**: Use 4242 card number
2. **Failed Payment**: Use 4000 card number
3. **Webhook Testing**: Use Stripe CLI or Dashboard events

## Troubleshooting

### Common Issues

#### "Invalid API Key" Error
- Check your Stripe secret key is correct
- Ensure you're using test keys for development
- Verify the key starts with `sk_test_` or `sk_live_`

#### "Payment plan not configured" Error
- Run `python manage.py setup_stripe_plans` again
- Check that `stripe_price_id_monthly` fields are populated in database

#### Webhook Failures
- Verify webhook URL is accessible
- Check webhook secret matches environment variable
- Test webhook events in Stripe Dashboard

#### Payment Not Processing
- Check Stripe Dashboard for payment status
- Verify webhook events are being received
- Check Django logs for errors

### Debug Steps

1. **Check Environment Variables**:
   ```bash
   python manage.py shell -c "from django.conf import settings; print('Stripe keys configured:', bool(settings.STRIPE_SECRET_KEY))"
   ```

2. **Verify Plans in Database**:
   ```bash
   python manage.py shell -c "from apps.payments.models import SubscriptionPlan; print('Plans:', [(p.tier, p.stripe_price_id_monthly) for p in SubscriptionPlan.objects.all()])"
   ```

3. **Test Webhook Endpoint**:
   ```bash
   curl -X POST http://localhost:8000/payments/webhook/stripe/ -H "Content-Type: application/json" -d '{"test": "data"}'
   ```

## Production Deployment

### Checklist

- [ ] Switch to live Stripe keys (`sk_live_` instead of `sk_test_`)
- [ ] Update webhook URLs to production domain
- [ ] Ensure HTTPS is enabled
- [ ] Set up proper logging for payment events
- [ ] Monitor webhook delivery in Stripe Dashboard
- [ ] Test live payments with small amounts

### Environment Variables for Production

```bash
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_key
STRIPE_SECRET_KEY=sk_live_your_live_key
STRIPE_WEBHOOK_SECRET=whsec_your_live_webhook_secret
```

## Security Considerations

1. **Webhook Verification**: All webhooks are verified using Stripe's signature verification
2. **CSRF Protection**: All payment forms include CSRF protection
3. **Authentication**: All payment endpoints require user authentication
4. **HTTPS**: Ensure your production site uses HTTPS for secure payment processing

## Support

For Stripe-specific issues:
- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Support](https://support.stripe.com/)
- [Stripe Dashboard](https://dashboard.stripe.com/)

For application-specific issues:
- Check Django logs and admin interface
- Review webhook configuration and database records
- Contact the development team
