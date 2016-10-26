#!/usr/bin/env python
from stompest.sync import Stomp
from QueueProcessor import QueueProcessor
import math
import smtplib
import os
import sys
import time
from flask import jsonify, json
from LDproxy import calculate_proxy

def toQueue(email=None, tokenId=None):
    resp = ""
    try:
        batchFile = os.path.join('tmp', "inputBatch_"+ tokenId)

        ts = time.strftime("%Y-%m-%d")
        data = json.dumps({ 
            "filepath": batchFile,
            "token": tokenId,
            "timestamp": ts
        })

        client = Stomp(qp.QUEUE)

        # opening connection to queue
        client.connect()
        print "Connected to queue..."

        # sending to queue
        client.send(qp.Q_NAME, data)

        # disconnecting
        client.disconnect()
        print "disconnected from queue..."
        return
    except Exception, e:
        print "In Exeception toQueue"
        errorType, error,traceback = sys.exc_info()
        print errorType
        print error
        print traceback
        print traceback.tb_lineno
        print __FILE__
        resp = jsonify({ "message" : "The batch process was not executed due to an error.\n" + e.args.join(', ') })
        resp.status_code = 400
        return resp

def queueConsumer(self, client, frame):
    resp = ""
    files = []
    try:
        print "<----- Frame body"
        print frame.body
        print frame.body.decode()

        parameters = json.loads(frame.body)

        print "<----------- Params"
        print parameters
        token = parameters['token']
        batchFilename = parameters['batchFile']
        recipient = parameters['recipientEmail']
        timestamp = parameters['timestamp']

        print token
        print batchFilename

        # --------------- THIS MAY CHANGE
        with open(batchFilename) as content_file:
            contents = content_file.read()

        fileContents = json.loads(contents)
        print fileContents

        print "After calculation"

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
              <!-- LDBatch E-Mail description -->
              <strong>For more information, visit <a target="_blank" style="color:#888888" href="http://analysistools.nci.nih.gov">analysistools.nci.nih.gov/ldlink?tab=ldbatch</a>
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
            message = """<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><title>html title</title></head><body>{0}{1}{2}</body>""".format(header, body, footer)
        else:
            message = """<head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><title>html title</title></head><body>{0}</body>""".format(qp.EMAIL_BODY)

        print "sending E-Mail"
        createMail(sendTo=data['queue']['email'],message=message, files=files)
        print "Queue job DONE!"

    except Exception, e:
        errorType, error,traceback = sys.exc_info()
        print errorType
        print error
        print traceback
        print traceback.tb_lineno
        print __FILE__

def processCleanup(self, connect):
    print "in proccessCleanup, Cleaning up...."
    print "<-- Add code for cleanup after queue process complete, if necessary -->"

def createMail(self, sendTo=None, message=None, files=[]):
    print "sending message"
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
            with open(file,"rb") as openfile:
                mimeApp = MIMEApplication(
                    openfile.read(),
                    Content_Disposition = 'attachment; filename="%s"' % os.path.basename(file),
                    Name = os.path.basename(file)
                )       
                packet.attach(mimeApp)

        smtp = smtplib.SMTP(self.MAIL_HOST)
        smtp.sendmail("do.not.reply@nih.gov", recipients, packet.as_string())
    except Exception, e:
        errorType, error,traceback = sys.exc_info()
        print errorType
        print error
        print traceback
        print traceback.tb_lineno
        print __FILE__
        resp = jsonify({ "message": e.args })
        resp.status_code = 400

qp = QueueProcessor(
    PRODUCT_NAME = "LDlink Batch Processing Module",
    CONFIG_FILE = r"config.ini",
    Q_NAME = 'queue.name',
    Q_URL = 'queue.url',
    Q_ERROR = 'queue.error.name',
    MAIL_HOST = 'mail.host',
    MAIL_ADMIN = 'mail.admin',
    PROCESS_FUNCT = calculate_proxy,
    CONSUMER_FUNCT = queueConsumer)