# Reely - Vercel Deployment Guide

This guide helps you deploy the Reely SaaS platform to Vercel with optimal configuration for cost-effectiveness and performance.

## 🚀 Quick Start

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup-vercel.sh
   ```

3. **Deploy**
   ```bash
   vercel --prod
   ```

## 🏗️ Architecture Overview

- **Backend**: FastAPI on Vercel Serverless Functions
- **Database**: Vercel Postgres or Supabase PostgreSQL
- **Cache**: Upstash Redis (serverless-optimized)
- **File Storage**: Vercel Blob or S3-compatible
- **Monitoring**: Built-in Vercel Analytics + Sentry

## 📊 Database Setup Options

### Option 1: Vercel Postgres (Recommended)
```bash
# Install Vercel Postgres
npm install @vercel/postgres

# Create database in Vercel dashboard
# Environment variables are automatically set
```

**Pros**: 
- Automatic configuration
- Built-in connection pooling
- Pay-as-you-go pricing
- Zero maintenance

**Cons**: 
- Newer service
- Limited to Vercel ecosystem

### Option 2: Supabase (Great Alternative)
```bash
# 1. Create project at supabase.com
# 2. Get connection string from dashboard
# 3. Set DATABASE_URL environment variable
```

**Pros**: 
- Generous free tier
- Additional features (auth, real-time, storage)
- Mature and stable
- Great developer experience

**Cons**: 
- Another service to manage
- May have latency if not in same region

### Option 3: Neon (Serverless PostgreSQL)
```bash
# 1. Create database at neon.tech
# 2. Copy connection string
# 3. Set DATABASE_URL environment variable
```

**Pros**: 
- Serverless-first design
- Branching feature for testing
- Good free tier

## 🗄️ Redis Setup (Upstash)

1. **Create Upstash Redis database**
   ```bash
   # Go to upstash.com
   # Create Redis database
   # Copy Redis URL
   ```

2. **Set environment variable**
   ```bash
   vercel env add REDIS_URL production
   # Enter your Upstash Redis URL (rediss://...)
   ```

**Why Upstash**: 
- Pay-per-request pricing (perfect for serverless)
- Global edge locations
- Built for serverless environments
- Free tier with good limits

## 🔧 Environment Variables Setup

### Required Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis  
REDIS_URL=rediss://default:pass@host:port

# Security
JWT_SECRET_KEY=your-super-secure-secret-key

# AI Services
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Payments
STRIPE_SECRET_KEY=sk_live_your-stripe-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# CORS
CORS_ORIGINS=https://yourapp.com,https://app.yourapp.com
```

### Set all variables at once
```bash
# Run the migration assistant
python scripts/migrate-to-vercel.py

# Or use the generated script
./setup-vercel-env.sh
```

## 🏃‍♂️ Local Development

### Docker Development Environment
```bash
# Start development stack
docker-compose -f docker-compose.dev.yml up

# Run with tools (pgAdmin + Redis Commander)
docker-compose -f docker-compose.dev.yml --profile tools up

# Run migrations
docker-compose -f docker-compose.dev.yml run --rm migrate

# Stop and cleanup
docker-compose -f docker-compose.dev.yml down -v
```

### Local Environment Setup
```bash
# Copy environment template
cp .env.local .env

# Edit with your local settings
nano .env

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main_v2:app --reload
```

## 📈 Cost Optimization

### Database Costs
- **Vercel Postgres**: ~$20-100/month for production
- **Supabase**: Free up to 500MB, then $25/month
- **Neon**: Free up to 3GB, then usage-based

### Redis Costs  
- **Upstash**: Pay per request, typically $0-20/month
- **Redis Cloud**: More expensive, fixed pricing

### Vercel Costs
- **Pro Plan**: $20/month per member (required for production)
- **Function invocations**: Generous free tier
- **Bandwidth**: 1TB included

### Estimated Total: $25-75/month for moderate usage

## 🔍 Monitoring & Observability

### Built-in Monitoring
```bash
# Add Sentry for error tracking
vercel env add SENTRY_DSN production
```

### Health Checks
- **Health endpoint**: `/health`
- **Vercel Analytics**: Automatic
- **Custom metrics**: Built into application

### Performance Monitoring
```python
# Built-in performance tracking
# Check /health endpoint for metrics
```

## 🚨 Troubleshooting

### Common Issues

1. **Cold Start Timeouts**
   - Increase function timeout in `vercel.json`
   - Use connection pooling
   - Implement health checks

2. **Database Connection Issues**
   - Check connection string format
   - Verify SSL requirements
   - Test connection locally first

3. **Redis Connection Issues**
   - Ensure using `rediss://` for SSL
   - Check firewall settings
   - Verify Upstash region

4. **Environment Variable Issues**
   ```bash
   # List all env vars
   vercel env ls
   
   # Remove incorrect var
   vercel env rm VARIABLE_NAME production
   
   # Add correct var
   vercel env add VARIABLE_NAME production
   ```

### Debug Mode
```bash
# Deploy with debug logging
vercel env add DEBUG true production
vercel --prod
```

### Logs
```bash
# View function logs
vercel logs your-deployment-url

# Real-time logs
vercel logs --follow
```

## 🔄 CI/CD Pipeline

### Automatic Deployments
```bash
# Connect GitHub repository in Vercel dashboard
# Automatic deployments on push to main branch
```

### Preview Deployments
- Every PR gets a preview deployment
- Test changes before merging
- Environment variables automatically inherited

### Production Deployment
```bash
# Manual production deployment
vercel --prod

# Or push to main branch (if connected to GitHub)
git push origin main
```

## 🔐 Security Checklist

- [ ] Strong JWT secret key (32+ characters)
- [ ] Database connection uses SSL
- [ ] Redis connection uses SSL (rediss://)
- [ ] Stripe webhook secret configured
- [ ] CORS origins properly set
- [ ] Rate limiting enabled
- [ ] Sentry error tracking configured
- [ ] No secrets in code repository

## 📚 Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Supabase Documentation](https://supabase.com/docs)
- [Upstash Redis Documentation](https://docs.upstash.com/redis)

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Vercel function logs
3. Test connections locally first
4. Check environment variables are set correctly

## 🎯 Next Steps After Deployment

1. **Set up custom domain** in Vercel dashboard
2. **Configure Stripe webhooks** with your new domain
3. **Update frontend** API endpoints
4. **Set up monitoring alerts**
5. **Create backup strategy** for database
6. **Plan scaling strategy** as you grow

---

**Happy deploying! 🚀**