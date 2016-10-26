
import os
import sys
import time
import logging
import urllib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from stompest.async import Stomp
from stompest.async.listener import SubscriptionListener
from stompest.async.listener import DisconnectListener
from stompest.config import StompConfig
from stompest.protocol import StompSpec
from twisted.internet import reactor, defer
from PropertyUtil import PropertyUtil

class QueueProcessor(SubscriptionListener):
    CONFIG_FILE = None
    QUEUE_CONFIG = None
    Q_NAME = None
    Q_URL = None
    Q_ERROR = None
    MAIL_HOST = None
    MAIL_ADMIN = None
    EMAIL_BODY = None
    PREFETCH = 100
    PRODUCT_NAME = None
    QUEUE = None
    PROCESS_METHOD = None
    CONSUMER = None

    @defer.inlineCallbacks
    def startQueue(self):
        print "in startQueue: "
        try:
            if self.QUEUE is not None:
                client = yield Stomp(self.QUEUE).connect()
                headers = {
                    StompSpec.ACK_HEADER: StompSpec.ACK_CLIENT_INDIVIDUAL,
                    'activemq.prefetchSize': self.PREFETCH
                }

                client.subscribe(self.QUEUE, headers, listener=SubscriptionListener(self.CONSUMER, errorDestination=self.Q_ERROR))
                client.add(listener=self)
        except Exception, e:
            errorType, error,traceback = sys.exc_info()
            print "ErrorType: {0}\n Error: {1}\n traceback: {2} at line number '{3}' in {4}".format(errorType, error, traceback, traceback.tb_lineno, __file__)

    def queueConnectionLost(self, connect, reason):
        print "Connection lost at {0} \n Due to {1}".format(time.strftime("%a, %d %b %Y %H:%M:%S"), reason)
        super(QueueProcessor, self).onConnectionLost(connect, reason)
        self.startQueue()

    def __init__(self, CONFIG_FILE=None, Q_NAME=None, Q_URL=None, Q_ERROR=None, PRODUCT_NAME=None, MAIL_HOST=None, MAIL_ADMIN=None, EMAIL_BODY=None, PREFETCH=100, PROCESS_FUNCT=None, CONSUMER_FUNCT=None):
        print "QueueProcessor init"
        if CONFIG_FILE is not None:
            self.CONFIG_FILE = CONFIG_FILE
            self.QUEUE_CONFIG = PropertyUtil(self.CONFIG_FILE)
            self.Q_URL = self.QUEUE_CONFIG[Q_URL]
            self.QUEUE = StompConfig(self.QUEUE_CONFIG[Q_URL])
            self.Q_NAME = self.QUEUE_CONFIG[Q_NAME]
            self.Q_ERROR = self.QUEUE_CONFIG[Q_ERROR]

            self.MAIL_HOST = self.QUEUE_CONFIG[MAIL_HOST]
            self.MAIL_ADMIN = self.QUEUE_CONFIG[MAIL_ADMIN]
            self.PRODUCT_NAME = PRODUCT_NAME
            self.PREFETCH = str(PREFETCH)

            self.PROCESS_METHOD = PROCESS_FUNCT
            self.CONSUMER = CONSUMER_FUNCT

            config = StompConfig(self.Q_URL)

            self.startQueue()

if __name__ == '__main__':
    print "Queue Processor __main__"
    logging.basicConfig(level=logging.DEBUG)
    QueueProcessor().startQueue()
    reactor.run()