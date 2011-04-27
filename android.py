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
const_api_url = ('http://everybodyloves.myshopsgame.com/bridge.php')

# Global var
global global_init 
global global_xml

log_file = open('myshops.log','a')
writelog = log_file.write

# Print error message, followed by standard advice information, and then exit
def error_advice_exit(error_text):
	sys.stderr.write('Error: %s.\n' % error_text)
	sys.exit('\n')

# Wrapper to create custom requests with typical headers
def request_create(post_data, extra_headers=None, url = const_api_url):
	retval = urllib2.Request(url, urllib.urlencode(post_data))
	# Try to mimic Firefox, at least a little bit
	"""
	retval.add_header('Accept', '*/*')
	retval.add_header('Accept-Charset', 'UTF-8,*;q=0.5')
	retval.add_header('Accept-Language', 'en-us,en;q=0.5')
	retval.add_header('Referer', 'http://d13qpkenb3q1p6.cloudfront.net/r2526/game/MyStreetLoaderR.swf')
	retval.add_header('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.205 Safari/534.16')
	retval.add_header('content-type', 'application/x-www-form-urlencoded')
	"""
	if extra_headers is not None:
		for header in extra_headers:
			retval.add_header(header, extra_headers[header])
	return retval

# Perform a request, process headers and return response
def perform_request(query, data="None", extra_headers="None"):
	print query["action"]
	data["query"] = json.dumps(query)
	writelog("perform_request::data = " + repr(data) + "\n")
	#writelog("perform_request::extra_headers = " + repr(extra_headers) + "\n")
	request = request_create(data, extra_headers)
	response = urllib2.urlopen(request)
	print query["action"] + " done!"
	print response.info()
	time.sleep(2)
	return response

def visitFriends(user, post_data, extra_headers):
	if time.localtime().tm_hour != 15:
		return	
	secret = global_init["data"]["secret"]
	friendsData = global_init["data"]["friendsData"]
	for idx in friendsData:
		friend =idx["user"]
		query = {"action":"getFriendData", "params":{"from_home":1, "user":user,"secret":secret, "friend":friend}}
		print (friend, query)
		response = perform_request(query, post_data, extra_headers)

def receiveMakeOrders(user, post_data, extra_headers):
	secret = global_init["data"]["secret"]
	shop_data = global_init["data"]["userData"]["shop_data"]
	for shop_position in range(len(shop_data)):
		shop = shop_data[shop_position]
		truck_size = 2 * (shop["deliveryUpgrade"]+1)
		query = {"params":{"shop_position":shop_position,"secret":secret,"user":user},"action":"receiveOrder"}
		response = perform_request(query, post_data, extra_headers)
		
		sorted_goods = []
		for gid in shop["goods"]:
			quantityPerPack  = eval(global_xml["goods"][gid])
			quantity = quantityPerPack[0]
			#if len(quantityPerPack) == 5:
			#	quantity = quantityPerPack[ shop["deliveryUpgrade"] ]
			upper = quantity * (3 + shop["deliveryUpgrade"])
			print "%s: %d - %d - %d"%(gid, upper, shop["goods"][gid], quantity)
			pack = (upper - shop["goods"][gid]) / quantity
			if pack > 0:
				sorted_goods.append((gid, pack))
		#sorted_goods = sorted(shop["goods"].iteritems(), key=operator.itemgetter(1))
		print sorted_goods
		order = {}
		count = 0
		for good in sorted_goods:
			order[good[0]] = 1
			count += 1
			if count >= truck_size:
				break
		print "orders: shop %s" % (shop_position)
		print order
		query = {"params":{"shop_position":shop_position,"order":order,"user":user,"secret":secret},"action":"makeOrder"}
		response = perform_request(query, post_data, extra_headers)

def makeLoveToCustomer(user, post_data, extra_headers):
	secret = global_init["data"]["secret"]
	customer_data = global_init["data"]["userData"]["customer_data"]
	
	for cid in customer_data:
		if customer_data[cid]["sat"] < 8:
			query = {"action":"delightCustomer","params":{"user":user,"customer_id":cid,"secret":secret}}
			print "delightCustomer: "+cid
			response = perform_request(query, post_data, extra_headers)
			global_init["data"]["userData"]["user_love"] -= 1
			if (global_init["data"]["userData"]["user_love"] <= 0):
				break
			
def getXmlConfig(extra_headers):
	dom = minidom.parse("goods.xml")
	ele = dom.getElementsByTagName("good")
	goods = {}
	for i in ele:
		goods[ i.getAttribute("id") ] = i.getAttribute("quantityPerPack")
	global_xml["goods"] = goods

def initGame(user, post_data, extra_headers):
	query = {"params":{"take_rescue_delivery_from":"","user":1567749701},"action":"initGame"}
	extra_headers["Accept-Encoding"] = ""
	response = perform_request(query, post_data, extra_headers)
	#init_str = zlib.decompress(response.read())
	init_str = (response.read())
	writelog("initGame: " + init_str)
	return json.loads(init_str)

# Create the command line options parser and parse command line
cmdl_usage = 'usage: %prog [options] data_sample'
cmdl_version = '2008.03.22'
cmdl_parser = optparse.OptionParser(usage=cmdl_usage, version=cmdl_version, conflict_handler='resolve')
cmdl_parser.add_option('-h', '--help', action='help', help='print this help text and exit')
cmdl_parser.add_option('-v', '--version', action='version', help='print program version and exit')
cmdl_parser.add_option('-x', '--header', dest='header', metavar='header', help='http header')
(cmdl_opts, cmdl_args) = cmdl_parser.parse_args()
writelog(str(cmdl_opts) + str(cmdl_args) + "\n")

# Set socket timeout
socket.setdefaulttimeout(const_timeout)

# Get video URL
if len(cmdl_args) != 2:
	cmdl_parser.print_help()
	sys.exit('\n')
data_sample = cmdl_args[0]
post_data_file = open(data_sample)
post_data = {}
while True:
	key = post_data_file.readline()
	if not key:
		break
	key = key[:-2]
	#if (key[:2] != "fb"):
	#	continue
	value = post_data_file.readline()
	#print key + " => " + value
	post_data[key] = value

extra_headers = {}
sample_header_file = open(cmdl_args[1])
while True:
	key = sample_header_file.readline()
	if not key:
		break
	key = key[:-2]
	value = sample_header_file.readline()
	#print key + " => " + value
	extra_headers[key] = value[:-1]

#print extra_headers 
#for header in extra_headers:
#	print(header, extra_headers[header])
query = json.loads(post_data["query"])
user = query["params"]["user"]
print user

try:
	global_xml = {}
	getXmlConfig(extra_headers)
	print global_xml
	global_init = initGame(user,post_data, extra_headers)
	makeLoveToCustomer(user, post_data, extra_headers)
	visitFriends(user, post_data, extra_headers)
	receiveMakeOrders(user, post_data, extra_headers)

#except (urllib2.URLError, ValueError, httplib.HTTPException, TypeError, socket.error):
#	print('failed.\n')

except KeyboardInterrupt:
	sys.exit('\n')

# Finish
log_file.close()
sys.exit()
