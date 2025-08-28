#!/usr/bin/env python3
"""
Migration script to help transition from local/AWS setup to Vercel
This script helps migrate data and configuration
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional

def load_env_file(file_path: str) -> Dict[str, str]:
    """Load environment variables from a .env file"""
    env_vars = {}
    
    if not os.path.exists(file_path):
        print(f"❌ Environment file {file_path} not found")
        return env_vars
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"\'')
    
    return env_vars

def check_required_env_vars(env_vars: Dict[str, str]) -> List[str]:
    """Check which required environment variables are missing"""
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL', 
        'JWT_SECRET_KEY',
        'CORS_ORIGINS'
    ]
    
    missing = []
    for var in required_vars:
        if var not in env_vars or not env_vars[var] or 'your-' in env_vars[var].lower():
            missing.append(var)
    
    return missing

def suggest_database_migration(current_db_url: str) -> Dict[str, str]:
    """Suggest database migration options"""
    suggestions = {
        'vercel_postgres': {
            'name': 'Vercel Postgres',
            'description': 'Managed PostgreSQL by Vercel',
            'setup': 'Install @vercel/postgres and create database in Vercel dashboard',
            'connection': 'Automatic environment variables (POSTGRES_URL)',
            'cost': 'Free tier available, pay as you go',
            'recommended': True
        },
        'supabase': {
            'name': 'Supabase',
            'description': 'Open source Firebase alternative with PostgreSQL',
            'setup': 'Create project at supabase.com',
            'connection': 'Use connection string from Supabase dashboard',
            'cost': 'Free tier with good limits',
            'recommended': True
        },
        'planetscale': {
            'name': 'PlanetScale',
            'description': 'Serverless MySQL platform',
            'setup': 'Create database at planetscale.com',
            'connection': 'Use connection string from PlanetScale',
            'cost': 'Free tier available',
            'recommended': False,  # Would need MySQL adapter changes
            'note': 'Requires changing from PostgreSQL to MySQL'
        },
        'neon': {
            'name': 'Neon',
            'description': 'Serverless PostgreSQL',
            'setup': 'Create database at neon.tech',
            'connection': 'Use connection string from Neon dashboard',
            'cost': 'Free tier available',
            'recommended': True
        }
    }
    
    return suggestions

def suggest_redis_migration(current_redis_url: str) -> Dict[str, str]:
    """Suggest Redis migration options"""
    suggestions = {
        'upstash': {
            'name': 'Upstash Redis',
            'description': 'Serverless Redis designed for serverless functions',
            'setup': 'Create database at upstash.com',
            'connection': 'Use Redis URL from Upstash dashboard (supports TLS)',
            'cost': 'Pay per request model, very cost effective',
            'recommended': True
        },
        'redis_cloud': {
            'name': 'Redis Cloud',
            'description': 'Managed Redis by Redis Inc',
            'setup': 'Create database at redis.com',
            'connection': 'Use connection string from Redis Cloud',
            'cost': 'Free tier available',
            'recommended': False  # More expensive for serverless
        }
    }
    
    return suggestions

def generate_vercel_env_commands(env_vars: Dict[str, str]) -> List[str]:
    """Generate Vercel CLI commands to set environment variables"""
    commands = []
    
    # Safe variables that can be set automatically
    safe_vars = [
        'ENVIRONMENT', 'DEBUG', 'APP_NAME', 'APP_VERSION',
        'RATE_LIMIT_REQUESTS_PER_MINUTE', 'RATE_LIMIT_BURST',
        'MAX_LOGIN_ATTEMPTS', 'LOCKOUT_DURATION_MINUTES',
        'MAX_FILE_SIZE_MB', 'TEMP_FILE_CLEANUP_HOURS',
        'FREE_TIER_MONTHLY_TRIMS', 'FREE_TIER_MONTHLY_HOOKS',
        'ANALYTICS_RETENTION_DAYS', 'ENABLE_USAGE_ANALYTICS',
        'ENABLE_SECURITY_HEADERS'
    ]
    
    for key, value in env_vars.items():
        if key in safe_vars and value and 'your-' not in value.lower():
            commands.append(f'vercel env add {key} production "{value}"')
    
    # Sensitive variables that need manual setup
    sensitive_vars = [
        'DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY',
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
        'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET',
        'SENTRY_DSN'
    ]
    
    manual_commands = []
    for var in sensitive_vars:
        if var in env_vars:
            manual_commands.append(f'vercel env add {var} production')
    
    return commands, manual_commands

def main():
    """Main migration function"""
    print("🚀 Reely - Vercel Migration Assistant")
    print("=" * 50)
    
    # Load current environment
    env_file = '.env'
    if os.path.exists('.env.local'):
        env_file = '.env.local'
    elif os.path.exists('.env.production'):
        env_file = '.env.production'
    
    print(f"📁 Loading environment from {env_file}")
    env_vars = load_env_file(env_file)
    
    if not env_vars:
        print("❌ No environment file found. Please create .env file first.")
        return
    
    # Check requirements
    print("\n🔍 Checking current configuration...")
    missing_vars = check_required_env_vars(env_vars)
    
    if missing_vars:
        print(f"⚠️  Missing required variables: {', '.join(missing_vars)}")
    else:
        print("✅ All required environment variables found")
    
    # Database migration suggestions
    current_db = env_vars.get('DATABASE_URL', '')
    print(f"\n💾 Current database: {current_db[:50]}...")
    
    print("\n📊 Database Migration Options:")
    db_suggestions = suggest_database_migration(current_db)
    for key, suggestion in db_suggestions.items():
        status = "✅ RECOMMENDED" if suggestion.get('recommended') else "ℹ️  OPTION"
        print(f"{status} {suggestion['name']}")
        print(f"   📝 {suggestion['description']}")
        print(f"   💰 {suggestion['cost']}")
        if suggestion.get('note'):
            print(f"   ⚠️  {suggestion['note']}")
        print()
    
    # Redis migration suggestions
    current_redis = env_vars.get('REDIS_URL', '')
    print(f"🗄️  Current Redis: {current_redis[:50]}...")
    
    print("\n🔧 Redis Migration Options:")
    redis_suggestions = suggest_redis_migration(current_redis)
    for key, suggestion in redis_suggestions.items():
        status = "✅ RECOMMENDED" if suggestion.get('recommended') else "ℹ️  OPTION"
        print(f"{status} {suggestion['name']}")
        print(f"   📝 {suggestion['description']}")
        print(f"   💰 {suggestion['cost']}")
        print()
    
    # Generate Vercel commands
    print("\n⚙️  Vercel Environment Setup:")
    auto_commands, manual_commands = generate_vercel_env_commands(env_vars)
    
    if auto_commands:
        print("\n📋 Automatic setup commands (safe variables):")
        for cmd in auto_commands:
            print(f"  {cmd}")
    
    if manual_commands:
        print("\n🔐 Manual setup required (sensitive variables):")
        for cmd in manual_commands:
            print(f"  {cmd}")
        print("\n   You'll be prompted to enter values for each variable.")
    
    # Generate setup script
    setup_script = f"""#!/bin/bash
# Generated Vercel setup script for Reely

echo "Setting up Vercel environment variables..."

# Automatic variables
{chr(10).join(auto_commands)}

echo "✅ Safe variables set automatically"
echo "⚠️  Please set the following variables manually:"

# Manual variables (user will be prompted)
{chr(10).join(manual_commands)}

echo "✅ Environment setup complete!"
echo "Next steps:"
echo "1. Set up your database (recommended: Vercel Postgres or Supabase)"
echo "2. Set up Redis (recommended: Upstash)"
echo "3. Run: vercel --prod"
"""
    
    # Save setup script
    script_path = 'setup-vercel-env.sh'
    with open(script_path, 'w') as f:
        f.write(setup_script)
    
    os.chmod(script_path, 0o755)
    print(f"\n💾 Generated setup script: {script_path}")
    print(f"Run: ./{script_path}")
    
    print("\n🎯 Migration Checklist:")
    print("□ Set up Vercel Postgres or Supabase database")
    print("□ Set up Upstash Redis")
    print("□ Run the generated setup script")
    print("□ Update your frontend API endpoints")
    print("□ Test the deployment with a staging environment")
    print("□ Update Stripe webhook URLs")
    print("□ Set up custom domain (optional)")
    
    print("\n✨ Migration planning complete!")

if __name__ == "__main__":
    main()