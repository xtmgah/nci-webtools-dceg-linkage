
import os
import sys
import time
import logging
import urllib
import json
import smtplib
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


class QueueProcessor(object):
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

    def __init__(self, CONFIG_FILE=None, Q_NAME=None, Q_URL=None, Q_ERROR=None, PRODUCT_NAME=None, MAIL_HOST=None, MAIL_ADMIN=None, EMAIL_BODY=None, PREFETCH=100, PROCESS_FUNCT=None, CONSUMER_FUNCT=None):
        logging.debug("QueueProcessor __init__")
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

            if CONSUMER_FUNCT is None:
                self.CONSUMER = defaultConsumer
            else:
                self.CONSUMER = CONSUMER_FUNCT

            self.startQueue()

    @defer.inlineCallbacks
    def startQueue(self):
        logging.debug("in startQueue: ")
        if self.QUEUE is not None:
            client = yield Stomp(self.QUEUE).connect()
            headers = {
                StompSpec.ACK_HEADER: StompSpec.ACK_CLIENT_INDIVIDUAL,
                'activemq.prefetchSize': self.PREFETCH
            }

            subListener = SubscriptionListener(
                self.CONSUMER, errorDestination=self.Q_ERROR, onMessageFailed=onFailed)
            client.subscribe(self.QUEUE, headers, listener=subListener)
            client.add(listener=self)

    def onFailed():
        logging.debug("onFailed")

    def onexception(self, headers, message):
        logging.debug('received an error %s' % message)

    def queueConnectionLost(self, connect, reason):
        logging.debug("Connection lost at {0} \n Due to {1}".format(time.strftime("%a, %d %b %Y %H:%M:%S"), reason))
        self.startQueue()

    def defaultConsumer(self, client, frame):
        logging.debug("In defaultConsumer")
        files = []
        starttime = str(time.time())

        try:
            data = json.loads(frame.body.decode())

            logging.debug("<----------- Params")
            logging.debug(data)
            logging.debug(frame.body.decode())

            logging.debug("After calculation")

            if self.EMAIL_BODY is None:
                link = "<a href='{0}'> Here </a>".format(urllib.unquote(data['queue']['url']))
                header = "<h2>{0}</h2>".format(qp.PRODUCT_NAME)
                body = """<div 
                style='background-color:white;border-top:25px solid #142830;border-left:2px solid #142830;border-right:2px solid #142830;border-bottom:2px solid #142830;padding:20px'>
                Hello,<br><p>Here are the results you requested on {0} from the {1}.</p>
                <p><div style='margin:20px auto 40px auto;width:200px;text-align:center;font-size:14px;font-weight:bold;padding:10px;line-height:25px'>
                <div style='font-size:24px;'><a href='{2}'>View Results</a></div></div></p>
                <p>The results will be available online for the next 14 days.</p></div>""".format(timestamp, qp.PRODUCT_NAME, urllib.unquote(data['queue']['url']) )

                footer = """<div><p>(Note:  Please do not reply to this email. If you need assistance, please contact NCILDlinkWebAdmin@mail.nih.gov)</p></div>
                <div style="background-color:#ffffff;color:#888888;font-size:13px;line-height:17px;font-family:sans-serif;text-align:left">
                <p>
                  <strong>About<em>""" + qp.PRODUCT_NAME + """</em></strong></em><br>
                  <!-- E-Mail description -->
                  <strong>For more information, visit <a target="_blank" style="color:#888888" href="<!-- Tool URL -->"><!-- Tool URL --></a>
                  </strong>
                </p>
                <p style="font-size:11px;color:#b0b0b0">If you did not request a calculation please ignore this email. Your privacy is important to us.  
                Please review our <a target="_blank" style="color:#b0b0b0" href="http://www.cancer.gov/policies/privacy-security">Privacy and Security Policy</a>.
                </p>
                <p align="center"><a href="http://cancercontrol.cancer.gov/">Division of Cancer Control & Population Sciences</a>, 
                <span style="white-space:nowrap">a Division of <a href="www.cancer.gov">National Cancer Institute</a></span><br>
                BG 9609 MSC 9760 | 9609 Medical Center Drive | Bethesda, MD 20892-9760 | <span style="white-space:nowrap"><a target="_blank" value="+18004006916" href="tel:1-800-422-6237">1-800-4-CANCER</a></span>
                </p></div>"""

                message = ("""<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><title>html title</title></head><body>{0}{1}{2}</body>""".format(
                    header, body, footer))
            else:
                message = ("""<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><title>html title</title></head><body>{0}</body>""".format(
                    qp.EMAIL_BODY))

            logging.debug("sending E-Mail")
            createMail(self.MAIL_ADMIN.split(","), message=message)
        except Exception, e:
            errorType, error, traceback = sys.exc_info()
            logging.exception(errorType)
            logging.exception(error)
            logging.exception(traceback)
            logging.exception(traceback.tb_lineno)
            logging.exception(__FILE__)

            message = ("Message: {0} \n Exception thrown in defaultConsumer : {1}\n {2}\n {3}\n Line No. {4}".format(message, errorType, error, traceback, traceback.tb_lineno))

            createMail(self.MAIL_ADMIN.split(","), message=message)
            createMail(sendTo=data['queue']['email'],
                       message=message, files=files)
        finally:
            logging.debug("Queue job DONE!")
            return

    def defaultCleanup(self, connect):
        logging.debug("in proccessCleanup, Cleaning up....")
        logging.debug("<-- Add code for cleanup after queue process complete, if necessary -->")
        pass

    def createMail(self, sendTo=None, message=None, files=[]):
        logging.debug("in createMail\n sending message")
        recipients = []

        try:
            if isinstance(sendTo, None):
                recipients = [sendTo]

            packet = MIMEMultipart()
            packet['Subject'] = self.PRODUCT_NAME + " Results"
            packet['From'] = self.PRODUCT_NAME + " <do.not.reply@nih.gov>"
            packet['To'] = ", ".join(recipients)

            packet.attach(MIMEText(message, 'html'))

            for file in files:
                with open(file, "rb") as openfile:
                    mimeApp = MIMEApplication(
                        openfile.read(),
                        Content_Disposition='attachment; filename="%s"' % os.path.basename(
                            file),
                        Name=os.path.basename(file)
                    )
                    packet.attach(mimeApp)

            smtp = smtplib.SMTP(self.MAIL_HOST)
            smtp.sendmail("do.not.reply@nih.gov",
                          recipients, packet.as_string())
        except Exception, e:
            errorType, error, traceback = sys.exc_info()
            logging.exception(errorType)
            logging.exception(error)
            logging.exception(traceback)
            logging.exception(traceback.tb_lineno)
            logging.exception(__FILE__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    QueueProcessor.startQueue()
    reactor.run()