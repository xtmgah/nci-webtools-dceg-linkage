
import os
import sys
import time
import logging
import urllib
import json
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

                subListener = SubscriptionListener(
                    self.CONSUMER, errorDestination=self.Q_ERROR, onMessageFailed=onFailed)
                client.subscribe(self.QUEUE, headers, listener=subListener)
                # client.add(listener=self)
        except Exception, e:
            errorType, error, traceback = sys.exc_info()
            print "ErrorType: {0}\n Error: {1}\n traceback: {2} at line number '{3}' in {4}".format(errorType, error, traceback, traceback.tb_lineno, __file__)

    def onFailed():
        print "onFailed"
        pass

    def queueConnectionLost(self, connect, reason):
        print "Connection lost at {0} \n Due to {1}".format(time.strftime("%a, %d %b %Y %H:%M:%S"), reason)
        super(QueueProcessor, self).onConnectionLost(connect, reason)
        self.startQueue()

    def defaultConsumer(self, client, frame):
        files = []
        try:
            print "<----- Frame body"
            print frame.body
            print frame.body.decode()

            parameters = json.loads(frame.body)

            print "<----------- Params"
            print parameters

            for key, value in parameters:
                self[key] = value
                print key, value

            print "After calculation"

            link = "<a href='{0}'> Here </a>".format(
                urllib.unquote(data['queue']['url']))
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
            if self.EMAIL_BODY is None:
                message = """<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><title>html title</title></head><body>{0}{1}{2}</body>""".format(
                    header, body, footer)
            else:
                message = """<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><title>html title</title></head><body>{0}</body>""".format(
                    qp.EMAIL_BODY)

            print "sending E-Mail"
            createMail(sendTo=data['queue']['email'],
                       message=message, files=files)
            print "Queue job DONE!"

        except Exception, e:
            errorType, error, traceback = sys.exc_info()
            print errorType
            print error
            print traceback
            print traceback.tb_lineno
            print __FILE__

    def defaultCleanup(self, connect):
        print "in proccessCleanup, Cleaning up...."
        print "<-- Add code for cleanup after queue process complete, if necessary -->"
        pass

    def createMail(self, sendTo=None, message=None, files=[]):
        print "in createMail\n sending message"
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
            print errorType
            print error
            print traceback
            print traceback.tb_lineno
            print __FILE__

    def __init__(self, CONFIG_FILE=None, Q_NAME=None, Q_URL=None, Q_ERROR=None, PRODUCT_NAME=None, MAIL_HOST=None, MAIL_ADMIN=None, EMAIL_BODY=None, PREFETCH=100, PROCESS_FUNCT=None, CONSUMER_FUNCT=None):
        print "QueueProcessor __init__"
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
