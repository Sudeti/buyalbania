# Stripe Payment Setup Guide

## Current Status
The subscription plans are created in the database, but Stripe API keys need to be configured for live payments.

## Quick Setup (Demo Mode)
For testing, the system now includes a demo mode that allows upgrades without Stripe:

1. **Demo Upgrade**: Click any upgrade button → Demo upgrade page → Instant access
2. **No Payment Required**: Users get immediate access to paid features
3. **Demo Records**: Creates demo subscription records in database

## Live Stripe Setup

### 1. Get Stripe API Keys
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Create account or sign in
3. Go to Developers → API Keys
4. Copy your **Publishable Key** and **Secret Key**

### 2. Update Environment Variables
Add to your `.env` file:
```bash
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 3. Create Stripe Products and Prices
Run the setup command:
```bash
python manage.py setup_stripe_plans
```

This will:
- Create products in Stripe for each plan
- Create price objects for monthly billing
- Update database with Stripe price IDs

### 4. Configure Webhooks
1. In Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/payments/webhook/stripe/`
3. Select events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy webhook secret to environment variable

### 5. Test the Integration
1. Try upgrading a user account
2. Check Stripe Dashboard for test payments
3. Verify webhook events are received

## Database Plans
Current plans in database:
- **Free**: €0/month, 1 analysis
- **Basic**: €19/month, 10 analyses  
- **Premium**: €49/month, unlimited analyses

## Troubleshooting

### "Invalid API Key" Error
- Check your Stripe secret key is correct
- Ensure you're using test keys for development
- Verify the key starts with `sk_test_` or `sk_live_`

### "Payment plan not configured" Error
- Run `python manage.py setup_stripe_plans` again
- Check that `stripe_price_id_monthly` fields are populated

### Webhook Issues
- Verify webhook URL is accessible
- Check webhook secret matches environment variable
- Test webhook events in Stripe Dashboard

## Demo Mode Features
- ✅ Instant upgrades without payment
- ✅ Full subscription management
- ✅ All paid features accessible
- ✅ Demo subscription records
- ✅ Profile tier updates

## Production Checklist
- [ ] Valid Stripe API keys configured
- [ ] Webhooks set up and tested
- [ ] SSL certificate installed
- [ ] Domain configured in Stripe
- [ ] Test payments working
- [ ] Webhook events processing correctly
