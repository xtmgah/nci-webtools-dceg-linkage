#!/usr/bin/env python
import json
import logging
from stompest.config import StompConfig
from stompest.sync import Stomp
import QueueProcessor
import os
import sys
import time
from flask import jsonify, json

def toQueue(email, tokenId):
    resp = ""
    try:
        qp = QueueProcessor(
            PRODUCT_NAME = "LDlink Batch Processing Module",
            CONFIG_FILE = r"QueueConfig.ini",
            Q_NAME = 'queue.name',
            Q_URL = 'queue.url',
            Q_PORT = 'queue.port',
            Q_ERROR = 'queue.error.name',
            MAIL_HOST = 'mail.host',
            MAIL_ADMIN = 'mail.admin')

        print "after qp"

        batchFile = open(os.path.join('tmp', "inputBatch_"+ tokenId))

        ts = time.strftime("%Y-%m-%d")
        data = json.dumps({ 
            "filepath": batchFile.name,
            "token": tokenId,
            "timestamp": ts
        })

        print "before client connect"
        print "Stomp( {0}, {1} )".format(qp.Q_URL, qp.Q_PORT)
        
        client = Stomp("tcp://{0}:{1}".format(qp.Q_URL, qp.Q_PORT))

        #opening connection to queue
        client.connect()

        print qp.Q_NAME
        print data

        client.send(qp.Q_NAME, data)
        client.disconnect()

        resp = jsonify({ "message": "The batch process has begun. The results will be emailed to " + email })
    except Exception, e:
        errorType, error = sys.exc_info()[:2]
        print errorType
        print error
        print sys.exc_info()[2]
        resp = jsonify({ "message" : "The batch process was not executed due to an error. \n" + e.args })
        resp.status_code = 400
    finally:
        return resp