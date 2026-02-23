module.exports = {
  apps: [
    {
      name: 'crevia-api',
      script: '/var/www/CreviaAnalytics/.venv/bin/uvicorn',
      args: 'api.main:app --host 127.0.0.1 --port 8000',
      cwd: '/var/www/CreviaAnalytics',
      interpreter: 'none',
      env: { PYTHONPATH: '/var/www/CreviaAnalytics' },
      restart_delay: 5000,
    },
    {
      name: 'crevia-web',
      script: 'node_modules/.bin/next',
      args: 'start --port 3001',
      cwd: '/var/www/CreviaAnalytics/web',
      restart_delay: 5000,
    },
    {
      name: 'crevia-engine',
      script: '/var/www/CreviaAnalytics/.venv/bin/python',
      args: 'main.py',
      cwd: '/var/www/CreviaAnalytics',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/var/www/CreviaAnalytics',
        DISPLAY: ':99',
      },
      restart_delay: 10000,
    }
  ]
};
