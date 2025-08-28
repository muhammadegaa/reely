# Reely Vercel Deployment Checklist

## Pre-deployment Setup

### 1. Database Setup
- [ ] **Option A: Vercel Postgres**
  - [ ] Go to Vercel Dashboard > Storage > Create Database
  - [ ] Select PostgreSQL
  - [ ] Copy connection details to environment variables
  
- [ ] **Option B: Supabase (Recommended)**
  - [ ] Create account at [supabase.com](https://supabase.com)
  - [ ] Create new project
  - [ ] Go to Settings > Database
  - [ ] Copy connection string
  - [ ] Set `DATABASE_URL` in Vercel environment variables

- [ ] **Option C: Neon**
  - [ ] Create account at [neon.tech](https://neon.tech)
  - [ ] Create database
  - [ ] Copy connection string

### 2. Redis Setup (Upstash)
- [ ] Create account at [upstash.com](https://upstash.com)
- [ ] Create Redis database
- [ ] Choose region closest to your users
- [ ] Copy Redis URL (starts with `rediss://`)
- [ ] Set `REDIS_URL` in Vercel environment variables

### 3. API Keys Setup
- [ ] **OpenAI** (for AI features)
  - [ ] Get API key from [platform.openai.com](https://platform.openai.com)
  - [ ] Set `OPENAI_API_KEY` in Vercel

- [ ] **Anthropic** (optional, alternative AI provider)
  - [ ] Get API key from [console.anthropic.com](https://console.anthropic.com)
  - [ ] Set `ANTHROPIC_API_KEY` in Vercel

### 4. Stripe Setup (for payments)
- [ ] Get Stripe keys from [dashboard.stripe.com](https://dashboard.stripe.com)
- [ ] Set `STRIPE_SECRET_KEY` (live key for production)
- [ ] Set `STRIPE_PUBLISHABLE_KEY`
- [ ] Create products and prices
- [ ] Set `STRIPE_PRICE_ID_PRO` and `STRIPE_PRICE_ID_PREMIUM`
- [ ] Set up webhook endpoint (after deployment)

### 5. Security Configuration
- [ ] Generate strong JWT secret: `openssl rand -hex 32`
- [ ] Set `JWT_SECRET_KEY` in Vercel
- [ ] Configure `CORS_ORIGINS` with your frontend domains

## Deployment Steps

### 1. Install Vercel CLI
```bash
npm install -g vercel
# or
npm install -g @vercel/cli
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Initialize Project
```bash
# In your backend directory
vercel

# Follow the prompts:
# - Link to existing project or create new one
# - Set project name (e.g., "reely-backend")
# - Choose settings
```

### 4. Set Environment Variables
```bash
# Use the setup script
./scripts/setup-vercel.sh

# Or manually set each variable
vercel env add DATABASE_URL production
vercel env add REDIS_URL production
vercel env add JWT_SECRET_KEY production
vercel env add OPENAI_API_KEY production
vercel env add STRIPE_SECRET_KEY production
vercel env add CORS_ORIGINS production
```

### 5. Deploy
```bash
# Preview deployment (for testing)
vercel

# Production deployment
vercel --prod
```

## Post-deployment Configuration

### 1. Database Migration
- [ ] Run database migrations (if using Supabase/external DB)
- [ ] Verify tables are created correctly
- [ ] Test database connection

### 2. Stripe Webhook Configuration
- [ ] Go to Stripe Dashboard > Webhooks
- [ ] Add endpoint: `https://your-domain.vercel.app/webhook/stripe`
- [ ] Select events: `invoice.payment_succeeded`, `customer.subscription.updated`, etc.
- [ ] Copy webhook secret
- [ ] Set `STRIPE_WEBHOOK_SECRET` in Vercel

### 3. Domain Setup (optional)
- [ ] Add custom domain in Vercel Dashboard
- [ ] Update DNS settings
- [ ] Update CORS origins with new domain
- [ ] Update Stripe webhook URL

### 4. Frontend Configuration
- [ ] Update frontend API base URL to your Vercel domain
- [ ] Update CORS settings if needed
- [ ] Test all API endpoints

## Testing Checklist

### API Endpoints
- [ ] Health check: `GET /health`
- [ ] Authentication: `POST /auth/register`, `POST /auth/login`
- [ ] Video processing: `POST /trim` (may be limited in serverless)
- [ ] Payments: `POST /stripe/create-subscription`
- [ ] User data: `GET /user/profile`

### Database
- [ ] User registration/login works
- [ ] Data persistence across requests
- [ ] Usage tracking functions

### Redis
- [ ] Caching works
- [ ] Rate limiting functions
- [ ] Session management

### External Services
- [ ] OpenAI API calls work
- [ ] Stripe payments process
- [ ] Webhook events are received

## Monitoring Setup

### 1. Error Tracking
- [ ] Set up Sentry (optional)
- [ ] Set `SENTRY_DSN` in environment variables

### 2. Analytics
- [ ] Vercel Analytics is enabled by default
- [ ] Set up custom events if needed

### 3. Logging
- [ ] Check Vercel function logs
- [ ] Set up log aggregation if needed

## Performance Optimization

### 1. Cold Start Optimization
- [ ] Database connection pooling configured
- [ ] Minimal imports in serverless functions
- [ ] Static assets cached

### 2. Resource Limits
- [ ] File size limits set appropriately
- [ ] Processing timeouts configured
- [ ] Memory usage optimized

## Security Checklist

- [ ] All secrets properly set in environment variables
- [ ] No secrets in code repository
- [ ] HTTPS enforced
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Input validation in place

## Cost Management

### Expected Monthly Costs (moderate usage):
- **Vercel Pro**: $20/month
- **Database**: $0-25/month (depending on choice)
- **Redis (Upstash)**: $0-10/month
- **OpenAI API**: $10-50/month
- **Stripe**: 2.9% + $0.30 per transaction

### Optimization Tips:
- [ ] Monitor Vercel function invocations
- [ ] Optimize database queries
- [ ] Use Redis for caching
- [ ] Implement proper cleanup for temporary files

## Troubleshooting

### Common Issues:
1. **Database connection errors**
   - Check connection string format
   - Verify SSL requirements
   - Test connection locally

2. **Function timeouts**
   - Optimize video processing
   - Implement async processing for large files
   - Use background jobs

3. **CORS errors**
   - Verify CORS_ORIGINS includes all frontend domains
   - Check protocol (http vs https)

4. **Environment variable issues**
   - Use `vercel env ls` to check variables
   - Redeploy after changing environment variables

## Success Criteria

- [ ] API responds to health checks
- [ ] User registration/login works
- [ ] Video processing completes (for small files)
- [ ] Payments process successfully
- [ ] Frontend can communicate with API
- [ ] All environment variables configured
- [ ] Monitoring shows healthy metrics

## Next Steps After Deployment

1. **Scale Planning**
   - Monitor usage patterns
   - Plan for auto-scaling
   - Consider CDN for file delivery

2. **Feature Rollout**
   - Gradual rollout of new features
   - A/B testing setup
   - User feedback collection

3. **Maintenance**
   - Regular dependency updates
   - Security patches
   - Performance monitoring

---

**Deployment Complete!** 🚀

Your Reely backend is now running on Vercel with production-grade infrastructure!