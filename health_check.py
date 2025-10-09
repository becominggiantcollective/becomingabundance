import psutil
import redis
from web3 import Web3
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, password=os.getenv('REDIS_PASS'))

def send_alert(message):
    robust_redis(redis_client, lambda: redis_client.publish('trades', json.dumps({'event': 'alert', 'message': message})))

def check_disk():
    return psutil.disk_usage('/').free / 1024 / 1024 > 100

def check_redis():
    return robust_redis(redis_client, lambda: redis_client.ping())

def check_hit_rate():
    hit_rate = float(redis_client.get('ml_hit_rate') or 0)
    if hit_rate < 0.12:
        send_alert(f'Low hit rate: {hit_rate}%')

def check_health(config):
    status = {
        'cpu': psutil.cpu_percent() < 80,
        'disk': check_disk(),
        'redis': check_redis(),
        'rpc': Web3(Web3.HTTPProvider(config['chains'][0]['rpc_url'])).is_connected()
    }
    if not status['cpu']:
        send_alert('High CPU usage!')
    if not status['disk']:
        send_alert('Low disk space!')
    check_hit_rate()
    robust_redis(redis_client, lambda: redis_client.publish('health', json.dumps(status)))
    return status