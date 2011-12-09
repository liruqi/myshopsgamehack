#!/usr/bin/env python
#
# Copyright (c) 2011  liruqi@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# 
# Except as contained in this notice, the name(s) of the above copyright
# holders shall not be used in advertising or otherwise to promote the
# sale, use or other dealings in this Software without prior written
# authorization.
#

import getpass
import httplib
import math
import optparse
import os
import re
import socket
import string
import sys
import time
import urllib2
import urllib
import json 
import time
import operator
import zlib
from xml.dom import minidom

# Global constants
const_timeout = 120
const_api_url = ('https://everybodyloves.myshopsgame.com/bridge.php')

# Global var
global global_init 
global global_xml
global global_opts

log_file = open('myshops.log','a')
writelog = log_file.write

# Print error message, followed by standard advice information, and then exit
def error_advice_exit(error_text):
    sys.stderr.write('Error: %s.\n' % error_text)
    sys.exit('\n')

def getMaxLove(id, level):
    levelMap = [1,2,4]
    if level > 2:
        level = 2
    love = levelMap[level] * global_xml["customer"][id]
    print (id, level, love)
    return love

# Wrapper to create custom requests with typical headers
def request_create(post_data, extra_headers=None, url = const_api_url):
    retval = urllib2.Request(url, urllib.urlencode(post_data))
    
    if extra_headers is not None:
        for header in extra_headers:
            retval.add_header(header, extra_headers[header])
    return retval

# Perform a request, process headers and return response
def perform_request(query, data="None", extra_headers="None"):
    data["query"] = json.dumps(query)
    data["query"] = string.join(data["query"].split(' '), '')
    print query["action"] + " - " + data["query"]
    #writelog("perform_request::data = " + repr(data) + "\n")
    #writelog("perform_request::extra_headers = " + repr(extra_headers) + "\n")
    request = request_create(data, extra_headers)
    response = urllib2.urlopen(request)
    print query["action"] + " done!"
    #print response.info()
    time.sleep(0.1)
    return response

def visitFriends(user, post_data, extra_headers):
    friendsData = global_init["data"]["friendsData"]
    for idx in friendsData:
        friend =idx["user"]
        query = {"action":"getFriendData", "params":{"from_home":1, "user":user, "friend":friend}}
        print (friend, query)
        response = perform_request(query, post_data, extra_headers)

def receiveMakeOrders(user, post_data, extra_headers):
    shop_data = global_init["data"]["userData"]["shop_data"]
    for shop_position in range(len(shop_data)):
        shop = shop_data[shop_position]
        truck_size = 2 * (shop["deliveryUpgrade"]+1)
        
        if "friendDeliveryPending" in shop:
            query = {"params":{"shop_position":shop_position,"user":user},"action":"receiveFriendDelivery"}
            response = perform_request(query, post_data, extra_headers)

        if "order" in shop:
            query = {"params":{"shop_position":shop_position,"user":user},"action":"receiveOrder"}
            response = perform_request(query, post_data, extra_headers)
        
        query = {"params":{"shop_position":shop_position,"user":user,"happy_customers_percentage":100},"action":"sendRush"}
        response = perform_request(query, post_data, extra_headers)

        sorted_goods = {}
        for gid in shop["goods"]:
            quantityPerPack  = eval(global_xml["goods"][gid])
            quantity = quantityPerPack[0]
            #if len(quantityPerPack) == 5:
            #    quantity = quantityPerPack[ shop["deliveryUpgrade"] ]
            upper = quantity * (3 + shop["deliveryUpgrade"])
            print "%s: %d - %d - %d"%(gid, upper, shop["goods"][gid], quantity)
            pack = (upper - shop["goods"][gid]) / quantity
            if pack > 0:
                sorted_goods[gid] = pack
        if (len(sorted_goods) <= 0):
            continue

        sorted_goods = sorted(sorted_goods.iteritems(), key=operator.itemgetter(1))
        sorted_goods.reverse()

        print sorted_goods
        order = {}
        count = 0
        for good in sorted_goods:
            order[good[0]] = 1
            count += 1
            if count >= truck_size:
                break
        print "orders: shop %s, truck_size %d" % (shop_position, truck_size)
        print order
        if order:
            query = {"params":{"shop_position":shop_position,"order":order,"user":user},"action":"makeOrder"}
            response = perform_request(query, post_data, extra_headers)

def makeLoveToCustomer(user, post_data, extra_headers):
    print "makeLoveToCustomer!"
    customer_data = global_init["data"]["userData"]["customer_data"]
    cidList = customer_data.keys()
    cidList.sort()
    cidList.reverse()
    levelLimit = 3
    while (global_init["data"]["userData"]["user_love"] > 0):
        for cid in cidList:
            print cid, customer_data[cid]
            if int(cid) > int(global_opts.upper):
                continue
            if int(cid) < int(global_opts.lower):
                continue
            if customer_data[cid]["level"] >= levelLimit:
                print "level is full"
                continue
            
            familyLevel = 64
            for x in cidList:
                if (int(x)/100) == (int(cid) /100):
                    if customer_data[x]["level"] < familyLevel:
                        familyLevel = customer_data[x]["level"]

            print ("try delightCustomer: "+cid +" sat: %d family level: %d max: %d") % (customer_data[cid]["sat"], familyLevel, getMaxLove(int(cid), familyLevel))
            while customer_data[cid]["sat"] < getMaxLove(int(cid), familyLevel) and global_init["data"]["userData"]["user_love"]:
                query = {"action":"delightCustomer","params":{"user":user,"customer_id":cid}}
                response = perform_request(query, post_data, extra_headers)
                global_init["data"]["userData"]["user_love"] -= 1
                customer_data[cid]["sat"] += 1
                print "love remaining: %d" % global_init["data"]["userData"]["user_love"]
                if not global_opts.crazy:
                    break
        levelLimit += 1
    
def getXmlConfig(extra_headers):
    dom = minidom.parse("goods.xml")
    ele = dom.getElementsByTagName("good")
    goods = {}
    for i in ele:
        goods[ i.getAttribute("id") ] = i.getAttribute("quantityPerPack")
    global_xml["goods"] = goods

    dom = minidom.parse("customers.xml")
    ele = dom.getElementsByTagName("customer")
    sat = {}
    for i in ele:
        sat[ int(i.getAttribute("id")) ] = int(i.getAttribute("maxSatisfaction"))
    global_xml["customer"] = sat

def initGame(user, post_data, extra_headers):
    query = {"params":{"take_rescue_delivery_from":"","user":user},"action":"initGame"}
    extra_headers["Accept-Encoding"] = ""
    response = perform_request(query, post_data, extra_headers)
    #init_str = zlib.decompress(response.read())
    init_str = (response.read())
    writelog("initGame: " + init_str + "\n")
    return json.loads(init_str)

# Create the command line options parser and parse command line
cmdl_usage = 'usage: %prog [options] data_sample'
cmdl_version = '2008.03.22'
cmdl_parser = optparse.OptionParser(usage=cmdl_usage, version=cmdl_version, conflict_handler='resolve')
cmdl_parser.add_option('-h', '--help', action='help', help='print this help text and exit')
cmdl_parser.add_option('-v', '--version', action='version', help='print program version and exit')
cmdl_parser.add_option('-c', '--crazy', action="store_true", dest='crazy', help='crazy mode', default=False)
cmdl_parser.add_option('-u', '--upper-limit', dest='upper', help='set upper limit of customer id', default=10000)
cmdl_parser.add_option('-l', '--lower-limit', dest='lower', help='set lower limit of customer id', default=0)

(cmdl_opts, cmdl_args) = cmdl_parser.parse_args()
print (str(cmdl_opts) + str(cmdl_args) + "\n")

# Set socket timeout
socket.setdefaulttimeout(const_timeout)

# Get video URL
if len(cmdl_args) < 1:
    cmdl_parser.print_help()
    sys.exit('\n')
user = cmdl_args[0]

post_data = {}
"""
post_data_file = open(data_sample)
while True:
    key = post_data_file.readline()
    if not key:
        break
    key = key.strip()

    if (key[-1:] != ":") :
        print "=>" + key
        key, value = key.split(":",1)
    else :
        key = key[:-1]
        value = post_data_file.readline()
    #if (key[:2] != "fb"):
    #    continue
    #print key + " => " + value
    post_data[key] = value
"""
extra_headers = {
    "content-type" : "application/x-www-form-urlencoded",
    "referer" : "http://d13qpkenb3q1p6.cloudfront.net/r2526a/game/MyStreetLoaderR.swf"
}

if (len(cmdl_args)>1):
    sample_header_file = open(cmdl_args[1])
    while True:
        key = sample_header_file.readline()
        if not key:
            break
        key = key[:-2]
        value = sample_header_file.readline()
        print key + " => " + value
        extra_headers[key] = value[:-1]

#print extra_headers 
#for header in extra_headers:
#    print(header, extra_headers[header])
#query = json.loads(post_data["query"])
#user = query["params"]["user"]
print user

try:
    global_xml = {}
    global_opts = cmdl_opts
    getXmlConfig(extra_headers)
    print global_xml
    global_init = initGame(user,post_data, extra_headers)

    makeLoveToCustomer(user, post_data, extra_headers)
    visitFriends(user, post_data, extra_headers)
    receiveMakeOrders(user, post_data, extra_headers)

#except (urllib2.URLError, ValueError, httplib.HTTPException, TypeError, socket.error):
#    print('failed.\n')

except KeyboardInterrupt:
    sys.exit('\n')

# Finish
log_file.close()
sys.exit()
