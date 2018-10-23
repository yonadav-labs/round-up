# Solvecore's Django Heroku Shopify App Foundation

- Designed with Django 1.10.5 for Heroku hosting.
- Uses python-2.7.13
- Production environment (Heroku): https://dashboard.heroku.com/apps/vesey 
- Shopify App Listing:: (https://apps.shopify.com/round-up-seamlessly-support-local-non-profits)
- Uses Stripe for payment processing (Josh will need to add you to Vesey Account)
- Uses AWS S3 for media file uploads (You will need to creae a development bucket, the production bucket is already configured)

## How to Use

To use this project, follow these steps:

1. Create your working environment.
2. Install Django (`$ pip install django==1.10.5`)
3. Create a new project using this template

## Creating Your Project

Using this template to create a new Django Shopify app is easy, use GIT to clone the project, then install all base requirements.

    $ git clone 

Configure your project Heroku services through the SETTINGS Django files

## Deployment to Heroku

Configure the Heroku instance (production or development) to perform Continuous Deployment from your github repo branch. This is the easiest way to deploy the project (https://devcenter.heroku.com/articles/github-integration)

## Installation

To set up a development environment quickly, first install Python 2.7 and Git. Then install virtualenv with pip install virtualenv:

    1. C:\Python27\Scripts\pip install virtualenv
    2. cmd: virtualenv -p C:\Python27\python.exe [environment_name]
    3. cmd: environment_path]/[environemnt_nme]/scripts/activate
    4. cmd: cd ..
    
Get project files (from repo location and user):

    1.git clone -b <branch> https://github.com/USERNAME/{repo location}
    
Install all dependencies:

    pip install -t src/lib -r requirements.txt
    
Ensure that you create a file name `veseyenvironment.json` one level ABOVE your project directory. This json file will contain all your private keys that should not enter VCS. An example format of this is below (without keys), and can be review in production in the Heroku -> Settings -> Config Variables section:

```
{
  "DJANGO_SECRET_KEY":"...",    
  "DATABASE_PW": "...",
  "MEMCACHE_PW": "...",
  "CELERY_BROKER_URL": "...",
  "SHOPIFY_APP_SECRET_KEY":"...",
  "SHOPIFY_APP_PUBLIC_KEY":"...",
  "PINAX_STRIPE_PUBLIC_KEY":"...",
  "PINAX_STRIPE_SECRET_KEY":"...",
  "AWS_SECRET_ACCESS_KEY":"...",
  "AWS_ACCESS_KEY_ID":"...",
  "CELERY_BROKER":"..."
}
```

*NOTE: DURING DEVELOPMENT YOU SHOULD USE DEVELOPMENT PRIVATE KEYS AND NOT USE THE PRODUCTION KEYS DEFINED IN THE PRODUCTION HEROKU CONFIG SETTINGS*

Run migrations:

    python manage.py migrate
    python manage.py createsuperuser
   
Run the project:
    
    python manage.py runserver



    
    
