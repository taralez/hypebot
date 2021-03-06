import sys
import json
import tweepy
import requests
import logging
import settings
# import paho.mqtt.client as mqtt
from time import sleep
import signal
from kafka import KafkaProducer

# def on_mqtt_disconnect(a, b, c):
#     logging.warning("MQTT disconnected.")
#     a.reconnect()
#
#
# def on_mqtt_connect(a, b, c):
#     logging.info("MQTT connected.")

root = logging.getLogger()
root.setLevel(settings.LOGLEVEL)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(settings.LOGLEVEL)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

r = requests.get("https://api.coinmarketcap.com/v1/ticker/")
jsond = json.loads(r.content)

totrack = [('$'+e['symbol']) for e in jsond]

logging.info(totrack)

class Producer():
    def __init__(self):
        import socket
        self.remote_ip = \
            socket.gethostbyname("creep.local")
        print(self.remote_ip)
        producer = KafkaProducer(bootstrap_servers=f'{self.remote_ip}:9092', api_version=(0, 10, 1))

    def stop(self):
        self.stop_event.set()

    def run(self):


        while not self.stop_event.is_set():
            producer.send('mytpc', b"test")
            producer.send('mytpc', b"\xc2Hola, mundo!")
            time.sleep(1)

        producer.close()

# Inherit from the StreamListener object
class MyStreamListener(tweepy.StreamListener):

    def on_data(self, data):
        client.publish("hypebot/twitter_stream", json.dumps(json.loads(data)), qos=2)
        logging.info("Tweet pushed.")
        return True

    # Error handling
    def on_status(self, status):
        logging.error(status)
        return True

    # Error handling
    def on_error(self, status):
        logging.error(status)
        return True

    # Timeout handling
    def on_timeout(self):
        logging.error("Timeout.")
        return True


def signal_term_handler(signal, frame):
    logging.warning('Got a terminating signal')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_term_handler)
signal.signal(signal.SIGINT, signal_term_handler)

while True:
    # client = mqtt.Client(client_id='hypebot_twitter_streamer', clean_session=False)
    # try:
    #     client.username_pw_set(settings.MQTT_USER_PUBLISHER, settings.MQTT_PASS_PUBLISHER)
    # except:
    #     pass
    #
    # logging.info("Connecting to MQTT.")
    # client.connect(settings.MQTT_HOST_PUBLISHER, settings.MQTT_PORT_PUBLISHER)
    #
    # client.on_connect = on_mqtt_connect
    # client.on_disconnect = on_mqtt_disconnect

    logging.info("Connecting to Twitter.")
    # Switching to application authentication (instead of user authentication)
    auth = tweepy.OAuthHandler('2m1s1mQ55amokrW0Q0RTN2DHw', 'QAjdsUis7fnLTvNbEZmUD9RA4wdU1HNVZXerYyLgYkdVSCTU6U')
    auth.set_access_token('53643197-LOTzjjxPprcWqW7djxkveth2ITHyXhSzcCqGRm8X8',
                          'NG0Lg6TXgS1ENtYvrhtHZ7zzkysde548MWfH1P3XhBcXa')
    api = tweepy.API(auth)
    if (not api):
        print("Problem connecting to Twitter API")

    logging.info("Register listener of Twitter stream.")
    twitter_stream = tweepy.Stream(auth, MyStreamListener())
    try:
        logging.info("Start tracking of Twitter stream.")
        twitter_stream.filter(track=totrack[0:300], stall_warnings=True)
    except BaseException as e:
        logging.exception("Exception thrown.")
        # logging.info("Disconnecting from MQTT.")
        # client.disconnect()
        logging.info("Disconnecting from Twitter.")
        twitter_stream.disconnect()
        logging.info("Sleep for 10s")
        sleep(10)
        logging.info("Retrying...")
        pass

